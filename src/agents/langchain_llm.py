from typing import Optional, Dict, Any
from langchain_core.language_models.llms import LLM
from langchain_core.outputs import GenerationChunk
from pydantic import BaseModel
import json
import traceback
from src.agents import model_adapter
from src.utils.logger import logger
from src import config_manager as config


class ModelConfig(BaseModel):
    type: str = config.MODEL_BACKEND
    model: Optional[str] = config.MODEL_NAME
    reasoning: Optional[Dict[str, Any]] = None


class AdapterLLM(LLM):
    """A thin LangChain LLM wrapper that delegates to our model_adapter.call_model.

    This keeps LangChain usage local and testable while allowing switching between
    mock and Ollama backends via backend_config.
    """

    backend_config: ModelConfig = ModelConfig()

    def _call(self, prompt: str, stop: Optional[list] = None) -> str:
        # call underlying adapter
        m_cfg = self._get_model_config_dict()
        res = model_adapter.call_model("", prompt, model_config=m_cfg, stream=False)
        return self._handle_response(res)

    def stream(self, input: Any, config: Optional[Any] = None, *, stop: Optional[list] = None, **kwargs: Any) -> Any:
        """Override to return GenerationChunk instead of str to preserve metadata."""
        yield from self._stream(str(input), stop=stop, **kwargs)

    def _stream(self, prompt: str, stop: Optional[list] = None, **kwargs) -> Any:
        """Implement streaming for LangChain."""
        m_cfg = self._get_model_config_dict()
        response = model_adapter.call_model("", prompt, model_config=m_cfg, stream=True)
        
        mtype = m_cfg.get("type")
        
        if mtype == "ollama":
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    content = chunk.get("response", "")
                    if content:
                        yield GenerationChunk(text=content)
        elif mtype in ["deepseek", "aliyun", "openai", "openrouter", "azure", "anthropic", "gemini"]:
            line_count = 0
            has_yielded_incremental = False  # 跟踪是否已经通过 part/delta 输出了增量内容
            for line in response.iter_lines():
                if line:
                    line_count += 1
                    line_str = line.decode('utf-8').strip()
                    
                    # 调试日志：记录前几行非空输出
                    if line_count <= 10:
                        logger.debug(f"[{mtype}] Stream line {line_count}: {line_str[:200]}")

                    # 处理 SSE 格式
                    if line_str.lower().startswith("data:"):
                        data_str = line_str[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            chunk_type = chunk.get("type", "unknown")
                            
                            # 如果已经有了增量输出，忽略所有“完成”类型的块，防止重复
                            # OpenRouter 会在增量输出后发送 response.content_part.done, response.output_text.done 等包含全量的块
                            if has_yielded_incremental and (
                                chunk_type.endswith(".done") or 
                                chunk_type == "response.completed" or 
                                chunk_type == "response.done"
                            ):
                                logger.debug(f"[{mtype}] Skipping final chunk {chunk_type} to avoid double output")
                                continue

                            # 调试：记录每个 chunk 的关键信息
                            # logger.debug(f"[{mtype}] Processing chunk: type={chunk_type}, keys={list(chunk.keys())}, has_yielded={has_yielded_incremental}")
                            
                            # 调试：记录包含 output 或 response 的 chunk，这可能是导致重复的原因
                            if "output" in chunk or "response" in chunk:
                                logger.debug(f"[{mtype}] Found potential full-response chunk. Keys: {list(chunk.keys())}, has_yielded_incremental: {has_yielded_incremental}")
                            
                            reasoning = None
                            content = None
                            
                            # 1. 优先检查 OpenRouter Response API 格式 (part.text 或 delta)
                            if "part" in chunk and isinstance(chunk["part"], dict):
                                part = chunk["part"]
                                p_type = part.get("type")
                                p_text = part.get("text") or part.get("delta")
                                
                                if p_type == "reasoning_text":
                                    reasoning = p_text
                                    if reasoning:
                                        logger.debug(f"[{mtype}] Extracted reasoning from part: {reasoning[:50]}...")
                                        has_yielded_incremental = True
                                else:
                                    content = p_text
                                    if content:
                                        logger.debug(f"[{mtype}] Extracted content from part: {content[:50]}...")
                                        has_yielded_incremental = True
                            
                            # 2. 检查 OpenRouter /responses 根部格式 (output/reasoning)
                            # 仅在没有增量输出且 part 没找到时作为补充
                            if not has_yielded_incremental and content is None and "output" in chunk:
                                output = chunk.get("output")
                                if isinstance(output, list):
                                    text_parts = []
                                    reasoning_parts = []
                                    for item in output:
                                        if item.get("type") == "message":
                                            content_list = item.get("content", [])
                                            for c in content_list:
                                                if c.get("type") == "output_text":
                                                    text_parts.append(c.get("text", ""))
                                        elif item.get("type") == "reasoning":
                                            summary = item.get("summary")
                                            if isinstance(summary, list):
                                                reasoning_parts.extend(summary)
                                            elif isinstance(summary, str):
                                                reasoning_parts.append(summary)
                                    
                                    if text_parts:
                                        content = "".join(text_parts)
                                    if reasoning_parts and reasoning is None:
                                        reasoning = "\n".join(reasoning_parts)
                                    
                                    if content or reasoning:
                                        logger.debug(f"[{mtype}] Extracted from output list. content_len={len(content or '')}, reasoning_len={len(reasoning or '')}")
                                        has_yielded_incremental = True
                                else:
                                    content = output
                                    if content:
                                        logger.debug(f"[{mtype}] Extracted from output root: {content[:50]}...")
                                        has_yielded_incremental = True
                            
                            if reasoning is None and not has_yielded_incremental and "reasoning" in chunk:
                                reasoning = chunk.get("reasoning")
                                if reasoning:
                                    logger.debug(f"[{mtype}] Extracted from reasoning root: {reasoning[:50]}...")
                                    has_yielded_incremental = True
                                
                            # 3. 检查根级别的 delta (某些 OpenRouter 响应)
                            if content is None and "delta" in chunk:
                                d_val = chunk.get("delta")
                                d_type = chunk.get("type", "")
                                
                                if isinstance(d_val, str):
                                    # 如果 type 包含 reasoning，则视为推理内容
                                    if "reasoning" in d_type:
                                        reasoning = d_val
                                    else:
                                        content = d_val
                                elif isinstance(d_val, dict):
                                    content = d_val.get("content")
                                    if not reasoning:
                                        reasoning = d_val.get("reasoning_content")
                                
                                if content or reasoning:
                                    logger.debug(f"[{mtype}] Extracted from root delta. content_len={len(content or '')}, reasoning_len={len(reasoning or '')}")
                                    has_yielded_incremental = True

                            # 4. 检查标准 OpenAI /choices 格式
                            if content is None and not reasoning and "choices" in chunk and len(chunk["choices"]) > 0:
                                choice = chunk["choices"][0]
                                if "delta" in choice:
                                    delta = choice.get("delta", {})
                                    content = delta.get("content")
                                    if not reasoning:
                                        reasoning = delta.get("reasoning_content") or delta.get("reasoning")
                                    if content or reasoning:
                                        logger.debug(f"[{mtype}] Extracted from choices delta. content_len={len(content or '')}, reasoning_len={len(reasoning or '')}")
                                        has_yielded_incremental = True
                                elif "text" in choice:
                                    content = choice.get("text")
                                    if content:
                                        logger.debug(f"[{mtype}] Extracted from choices text: {content[:50]}...")
                                        has_yielded_incremental = True

                            # 5. 检查 OpenRouter Response API 的最终结果 (response.output_text)
                            if not has_yielded_incremental and content is None and not reasoning and "response" in chunk:
                                resp_obj = chunk["response"]
                                if isinstance(resp_obj, dict):
                                    content = resp_obj.get("output_text")
                                    if content:
                                        logger.debug(f"[{mtype}] Extracted from response.output_text: {content[:50]}...")

                            # 6. 检查 OpenRouter 特有的顶级错误或元数据
                            if content is None and reasoning is None:
                                if "error" in chunk:
                                    logger.error(f"[{mtype}] API Error in stream: {chunk['error']}")
                                    continue

                            # 产生生成块
                            if reasoning:
                                if reasoning == content:
                                    content = None
                                yield GenerationChunk(text="", generation_info={"reasoning": reasoning})
                            
                            if content is not None:
                                yield GenerationChunk(text=content)
                                
                        except Exception as e:
                            logger.error(f"Error parsing {mtype} stream chunk: {e}")
                            logger.error(f"Problematic data: {data_str}")
                            continue
                    else:
                        # 兜底逻辑：处理非标准 SSE 格式（直接返回 JSON 块的情况）
                        if not has_yielded_incremental and line_str.startswith("{") and line_str.endswith("}"):
                            try:
                                chunk = json.loads(line_str)
                                # 避免处理 OpenRouter 的元数据块
                                if "choices" not in chunk and "part" not in chunk and "output" not in chunk and "response" not in chunk:
                                    continue
                                    
                                content = chunk.get("output") or chunk.get("content")
                                reasoning = chunk.get("reasoning")
                                
                                if content is None and "response" in chunk:
                                    content = chunk["response"].get("output_text")

                                # 处理 OpenRouter output 列表格式
                                if isinstance(content, list):
                                    text_parts = []
                                    reasoning_parts = []
                                    for item in content:
                                        if item.get("type") == "message":
                                            for c in item.get("content", []):
                                                if c.get("type") == "output_text":
                                                    text_parts.append(c.get("text", ""))
                                        elif item.get("type") == "reasoning":
                                            summary = item.get("summary")
                                            if isinstance(summary, list): reasoning_parts.extend(summary)
                                            elif isinstance(summary, str): reasoning_parts.append(summary)
                                    content = "".join(text_parts) if text_parts else None
                                    if reasoning_parts and not reasoning:
                                        reasoning = "\n".join(reasoning_parts)
                                
                                if reasoning and reasoning == content:
                                    content = None
                                    
                                if reasoning:
                                    yield GenerationChunk(text="", generation_info={"reasoning": reasoning})
                                if content is not None:
                                    has_yielded_incremental = True
                                    yield GenerationChunk(text=content)
                            except Exception as e:
                                logger.error(f"Error in fallback parser: {e}")
            
            if line_count == 0:
                logger.warning(f"{mtype} stream returned NO lines. Status code: {response.status_code}")

    def _get_model_config_dict(self) -> Dict[str, Any]:
        m_cfg = self.backend_config
        if hasattr(m_cfg, "dict"):
            return m_cfg.model_dump()
        elif hasattr(m_cfg, "model_dump"):
            return m_cfg.model_dump()
        return m_cfg

    def _handle_response(self, res: Any) -> str:
        # If adapter returned a dict (parsed JSON), return its JSON string
        if isinstance(res, dict):
            try:
                return json.dumps(res, ensure_ascii=False)
            except Exception:
                return str(res)
        return str(res)

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        m_cfg = self.backend_config
        if hasattr(m_cfg, "dict"):
            m_cfg = m_cfg.model_dump()
        elif hasattr(m_cfg, "model_dump"):
            m_cfg = m_cfg.model_dump()
        return {"backend_config": m_cfg}

    @property
    def _llm_type(self) -> str:
        return "adapter"
