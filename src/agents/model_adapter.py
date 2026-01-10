"""
模型适配器：支持本地 Ollama（HTTP 优先，CLI 回退）。
此版本已移除 mock 实现，调用失败将抛出异常以便测试本地 Ollama 行为。
"""
import json
import time
from typing import Dict
import subprocess
import requests
from requests.exceptions import RequestException
import traceback
from src import config_manager as config
from src.utils.logger import logger


def mock_generate_plan(agent_id: str, issue_text: str) -> Dict:
    # 返回符合 PlanSchema 的字典示例
    return {
        "id": f"{agent_id}-plan1",
        "core_idea": f"基于{issue_text}的初步思路",
        "steps": ["步骤1：调研", "步骤2：试点", "步骤3：推广"],
        "feasibility": {"advantages": ["低成本"], "requirements": ["资源A", "资源B"]},
        "limitations": ["时间较长"]
    }





def call_ollama_http(model: str, prompt: str, timeout: int = 60, stream: bool = False):
    """尝试通过 Ollama 的本地 HTTP API 调用模型。"""
    url = config.OLLAMA_HTTP_URL
    payload = {"model": model, "prompt": prompt, "stream": stream}
    try:
        logger.info(f"Ollama HTTP call starting to {url} (stream={stream})...")
        resp = requests.post(url, json=payload, timeout=timeout, stream=stream)
        logger.info(f"Ollama HTTP response received (status: {resp.status_code})")
        resp.raise_for_status()
        if stream:
            return resp
        data = resp.json()
        return data.get("response", "")
    except RequestException as e:
        raise RuntimeError(f"Ollama HTTP request failed: {e}")


def call_ollama_cli(model: str, prompt: str, timeout: int = 30) -> str:
    """尝试使用本地 ollama CLI（若已安装）作为回退方案。"""
    try:
        # ollama run <model> "<prompt>"
        completed = subprocess.run(["ollama", "run", model, prompt], capture_output=True, text=True, timeout=timeout)
        if completed.returncode != 0:
            raise RuntimeError(f"ollama CLI error: {completed.stderr.strip()}")
        return completed.stdout
    except FileNotFoundError:
        raise RuntimeError("ollama CLI not found on PATH")


def call_model_with_ollama_fallback(model: str, prompt: str) -> str:
    """优先尝试 HTTP，然后回退到 CLI。如果都失败则抛出异常。"""
    # 首选 HTTP API
    try:
        return call_ollama_http(model, prompt)
    except Exception:
        # 回退到 CLI
        return call_ollama_cli(model, prompt)


def call_deepseek(model: str, prompt: str, timeout: int = 60, max_retries: int = 3, stream: bool = False, tools: list = None, tool_choice: str = "auto"):
    """调用 DeepSeek API (OpenAI 兼容接口)，带重试机制。
    
    Args:
        model: 模型名称
        prompt: 提示词或消息列表
        timeout: 超时时间
        max_retries: 最大重试次数
        stream: 是否流式输出
        tools: OpenAI Function Calling格式的工具定义列表
        tool_choice: 工具选择策略 ("auto"/"none"或特定工具名)
    """
    url = f"{config.DEEPSEEK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 清理可能导致 JSON 解析失败的不可见控制字符，并记录长度
    if isinstance(prompt, str):
        clean_prompt = "".join(c for c in prompt if c.isprintable() or c in "\n\r\t")
        logger.info(f"DeepSeek prompt length: {len(clean_prompt)} characters")
        messages = [{"role": "user", "content": clean_prompt}]
    else:
        # 支持直接传入消息列表（用于多轮对话）
        messages = prompt
        logger.info(f"DeepSeek messages count: {len(messages)}")
    
    payload = {
        "model": model or config.DEEPSEEK_MODEL,
        "messages": messages,
        "stream": stream
    }
    
    # 添加工具调用支持
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice
        logger.info(f"DeepSeek: Enabled function calling with {len(tools)} tools")
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"DeepSeek API call starting (attempt {attempt + 1}/{max_retries}, stream={stream})...")
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout, stream=stream)
            logger.info(f"DeepSeek API response received (status: {resp.status_code})")
            if resp.status_code != 200:
                try:
                    error_detail = resp.json()
                    logger.error(f"DeepSeek API error detail: {error_detail}")
                except:
                    logger.error(f"DeepSeek API error body: {resp.text}")
            resp.raise_for_status()
            if stream:
                return resp
            data = resp.json()
            
            # 检查是否有tool_calls
            message = data["choices"][0]["message"]
            if message.get("tool_calls"):
                logger.info(f"DeepSeek returned {len(message['tool_calls'])} tool calls")
                return message  # 返回完整消息（包含tool_calls）
            
            return message.get("content", "")
        except RequestException as e:
            last_exception = e
            logger.warning(f"DeepSeek API attempt {attempt + 1} failed: {e}. Retrying...")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))  # 简单的指数退避
            
    raise RuntimeError(f"DeepSeek API request failed after {max_retries} attempts: {last_exception}")


def call_aliyun(model: str, prompt: str, timeout: int = 60, max_retries: int = 3, stream: bool = False):
    """调用阿里云 DashScope API (OpenAI 兼容接口)，带重试机制。"""
    url = f"{config.ALIYUN_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.ALIYUN_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model or config.ALIYUN_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream
    }
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Aliyun API call starting (attempt {attempt + 1}/{max_retries}, stream={stream})...")
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout, stream=stream)
            logger.info(f"Aliyun API response received (status: {resp.status_code})")
            resp.raise_for_status()
            if stream:
                return resp
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except RequestException as e:
            last_exception = e
            logger.warning(f"Aliyun API attempt {attempt + 1} failed: {e}. Retrying...")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            
    raise RuntimeError(f"Aliyun API request failed after {max_retries} attempts: {last_exception}")


def call_openai(model: str, prompt: str, timeout: int = 60, max_retries: int = 3, stream: bool = False, tools: list = None, tool_choice: str = "auto"):
    """调用 OpenAI API，带重试机制。
    
    Args:
        model: 模型名称
        prompt: 提示词或消息列表
        timeout: 超时时间
        max_retries: 最大重试次数
        stream: 是否流式输出
        tools: OpenAI Function Calling格式的工具定义列表
        tool_choice: 工具选择策略
    """
    url = f"{config.OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 支持字符串或消息列表
    if isinstance(prompt, str):
        messages = [{"role": "user", "content": prompt}]
    else:
        messages = prompt
        
    payload = {
        "model": model or config.OPENAI_MODEL,
        "messages": messages,
        "stream": stream
    }
    
    # 添加工具调用支持
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice
        logger.info(f"OpenAI: Enabled function calling with {len(tools)} tools")
    
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"OpenAI API call starting (attempt {attempt + 1}/{max_retries}, stream={stream})...")
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout, stream=stream)
            logger.info(f"OpenAI API response received (status: {resp.status_code})")
            resp.raise_for_status()
            if stream:
                return resp
            data = resp.json()
            
            # 检查是否有tool_calls
            message = data["choices"][0]["message"]
            if message.get("tool_calls"):
                logger.info(f"OpenAI returned {len(message['tool_calls'])} tool calls")
                return message  # 返回完整消息（包含tool_calls）
            
            return message.get("content", "")
        except RequestException as e:
            last_exception = e
            logger.warning(f"OpenAI API attempt {attempt + 1} failed: {e}. Retrying...")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            
    raise RuntimeError(f"OpenAI API request failed after {max_retries} attempts: {last_exception}")


def call_openrouter(model: str, prompt: str, timeout: int = 120, max_retries: int = 3, stream: bool = False, reasoning: dict = None):
    """调用 OpenRouter API，带重试机制。"""
    # 如果提供了 reasoning，使用 /responses 接口 (OpenRouter 统一响应接口)
    if reasoning:
        url = f"{config.OPENROUTER_BASE_URL.replace('/chat/completions', '')}/responses"
        payload = {
            "model": model or config.OPENROUTER_MODEL,
            "input": prompt,
            "reasoning": reasoning,
            "stream": stream
        }
    else:
        url = f"{config.OPENROUTER_BASE_URL}/chat/completions"
        payload = {
            "model": model or config.OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream
        }
    
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/AICouncil", # 选填
        "X-Title": "AICouncil" # 选填
    }
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"OpenRouter API call starting (attempt {attempt + 1}/{max_retries}, stream={stream}, reasoning={reasoning})...")
            logger.info(f"OpenRouter prompt length: {len(prompt)} characters")
            
            # 对于推理模型，增加超时时间
            current_timeout = timeout
            if reasoning:
                current_timeout = max(timeout, 180) # 至少 3 分钟
                
            resp = requests.post(url, json=payload, headers=headers, timeout=current_timeout, stream=stream)
            logger.info(f"OpenRouter API response received (status: {resp.status_code})")
            
            if resp.status_code != 200:
                logger.error(f"OpenRouter Error Body: {resp.text}")
                
            resp.raise_for_status()
            if stream:
                return resp
            data = resp.json()
            
            # 处理 /responses 和 /chat/completions 不同的返回格式
            if reasoning:
                output = data.get("output")
                # 如果 output 是列表（OpenRouter /responses 标准非流式格式）
                if isinstance(output, list):
                    text_content = ""
                    for item in output:
                        if item.get("type") == "message":
                            content_list = item.get("content", [])
                            for c in content_list:
                                if c.get("type") == "output_text":
                                    text_content += c.get("text", "")
                    if text_content:
                        return text_content
                
                # 兜底逻辑：如果是字符串则直接返回，否则尝试 choices 格式
                if isinstance(output, str):
                    return output
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                return data["choices"][0]["message"]["content"]
        except RequestException as e:
            last_exception = e
            logger.warning(f"OpenRouter API attempt {attempt + 1} failed: {e}. Retrying...")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            
    raise RuntimeError(f"OpenRouter API request failed after {max_retries} attempts: {last_exception}")


def call_azure_openai(deployment: str, prompt: str, timeout: int = 60, max_retries: int = 3, stream: bool = False):
    """
    调用 Azure OpenAI API（支持中国区和全球区）
    
    Args:
        deployment: Azure OpenAI 部署名称（不是模型名）
        prompt: 输入提示词
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
        stream: 是否流式输出
    
    Azure 中国区和全球区差异：
    - 中国区 endpoint: https://{resource}.openai.azure.cn
    - 全球区 endpoint: https://{resource}.openai.azure.com
    - 认证方式：使用 api-key header（不是 Authorization: Bearer）
    - URL 格式：/openai/deployments/{deployment}/chat/completions?api-version={version}
    """
    if not config.AZURE_OPENAI_API_KEY:
        raise ValueError("AZURE_OPENAI_API_KEY not configured")
    if not config.AZURE_OPENAI_ENDPOINT:
        raise ValueError("AZURE_OPENAI_ENDPOINT not configured")
    
    # 构建 Azure OpenAI URL
    url = (f"{config.AZURE_OPENAI_ENDPOINT}/openai/deployments/{deployment}"
           f"/chat/completions?api-version={config.AZURE_OPENAI_API_VERSION}")
    
    headers = {
        "api-key": config.AZURE_OPENAI_API_KEY,  # Azure 使用 api-key，不是 Authorization
        "Content-Type": "application/json"
    }
    
    clean_prompt = "".join(c for c in prompt if c.isprintable() or c in "\n\r\t")
    logger.info(f"Azure OpenAI prompt length: {len(clean_prompt)} characters")
    
    payload = {
        "messages": [{"role": "user", "content": clean_prompt}],
        "stream": stream
    }
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Azure OpenAI API call starting (attempt {attempt + 1}/{max_retries}, deployment={deployment}, stream={stream})...")
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout, stream=stream)
            logger.info(f"Azure OpenAI API response received (status: {resp.status_code})")
            
            if resp.status_code != 200:
                logger.error(f"Azure OpenAI Error Body: {resp.text}")
                
            resp.raise_for_status()
            if stream:
                return resp
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except RequestException as e:
            last_exception = e
            logger.warning(f"Azure OpenAI API attempt {attempt + 1} failed: {e}. Retrying...")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
    
    raise RuntimeError(f"Azure OpenAI API request failed after {max_retries} attempts: {last_exception}")


def call_anthropic(model: str, prompt: str, timeout: int = 60, max_retries: int = 3, stream: bool = False):
    """
    调用 Anthropic Claude API
    
    Args:
        model: Claude 模型名称（如 claude-3-5-sonnet-20241022）
        prompt: 输入提示词
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
        stream: 是否流式输出
    
    Anthropic API 特点：
    - Endpoint: https://api.anthropic.com/v1/messages
    - 认证方式：x-api-key header
    - API版本：通过 anthropic-version header 指定
    """
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not configured")
    
    url = f"{config.ANTHROPIC_BASE_URL}/v1/messages"
    
    headers = {
        "x-api-key": config.ANTHROPIC_API_KEY,
        "anthropic-version": getattr(config, 'ANTHROPIC_API_VERSION', '2023-06-01'),
        "Content-Type": "application/json"
    }
    
    clean_prompt = "".join(c for c in prompt if c.isprintable() or c in "\n\r\t")
    logger.info(f"Anthropic API prompt length: {len(clean_prompt)} characters")
    
    payload = {
        "model": model or config.ANTHROPIC_MODEL,
        "messages": [{"role": "user", "content": clean_prompt}],
        "max_tokens": 4096,
        "stream": stream
    }
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Anthropic API call starting (attempt {attempt + 1}/{max_retries}, model={model}, stream={stream})...")
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout, stream=stream)
            logger.info(f"Anthropic API response received (status: {resp.status_code})")
            
            if resp.status_code != 200:
                logger.error(f"Anthropic Error Body: {resp.text}")
                
            resp.raise_for_status()
            if stream:
                return resp
            data = resp.json()
            # Anthropic 返回格式: {"content": [{"type": "text", "text": "..."}]}
            return data["content"][0]["text"]
        except RequestException as e:
            last_exception = e
            logger.warning(f"Anthropic API attempt {attempt + 1} failed: {e}. Retrying...")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
    
    raise RuntimeError(f"Anthropic API request failed after {max_retries} attempts: {last_exception}")


def call_gemini(model: str, prompt: str, timeout: int = 60, max_retries: int = 3, stream: bool = False):
    """
    调用 Google Gemini API
    
    Args:
        model: Gemini 模型名称（如 gemini-1.5-pro, gemini-1.5-flash）
        prompt: 输入提示词
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
        stream: 是否流式输出
    
    Google Gemini API 特点：
    - Endpoint: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
    - 认证方式：API key 作为 query 参数
    - 支持流式输出：streamGenerateContent
    """
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured")
    
    model_name = model or config.GEMINI_MODEL
    api_version = getattr(config, 'GEMINI_API_VERSION', 'v1beta')
    endpoint = 'streamGenerateContent' if stream else 'generateContent'
    url = f"{config.GEMINI_BASE_URL}/{api_version}/models/{model_name}:{endpoint}?key={config.GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    clean_prompt = "".join(c for c in prompt if c.isprintable() or c in "\n\r\t")
    logger.info(f"Gemini API prompt length: {len(clean_prompt)} characters")
    
    payload = {
        "contents": [{
            "parts": [{"text": clean_prompt}]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192
        }
    }
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Gemini API call starting (attempt {attempt + 1}/{max_retries}, model={model_name}, stream={stream})...")
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout, stream=stream)
            logger.info(f"Gemini API response received (status: {resp.status_code})")
            
            if resp.status_code != 200:
                logger.error(f"Gemini Error Body: {resp.text}")
                
            resp.raise_for_status()
            if stream:
                return resp
            data = resp.json()
            # Gemini 返回格式: {"candidates": [{"content": {"parts": [{"text": "..."}]}}]}
            if data.get("candidates") and len(data["candidates"]) > 0:
                parts = data["candidates"][0].get("content", {}).get("parts", [])
                if parts and len(parts) > 0:
                    return parts[0].get("text", "")
            return ""
        except RequestException as e:
            last_exception = e
            logger.warning(f"Gemini API attempt {attempt + 1} failed: {e}. Retrying...")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
    
    raise RuntimeError(f"Gemini API request failed after {max_retries} attempts: {last_exception}")


def get_openrouter_models():
    """获取 OpenRouter 支持的模型列表。"""
    url = f"{config.OPENROUTER_BASE_URL.replace('/chat/completions', '')}/models"
    headers = {"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception as e:
        logger.error(f"Failed to fetch OpenRouter models: {e}")
        return []


def get_deepseek_models():
    """获取 DeepSeek 支持的模型列表。"""
    url = f"{config.DEEPSEEK_BASE_URL}/models"
    headers = {"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception as e:
        logger.error(f"Failed to fetch DeepSeek models: {e}")
        return []


def call_model(agent_id: str, prompt: str, model_config: dict = None, stream: bool = False):
    """统一调用接口：
    - model_config: {"type": "ollama"/"openai"/"deepseek", "model": "<model-name>"}
    - stream: 是否开启流式输出
    """
    if model_config is None:
        model_config = {"type": config.MODEL_BACKEND, "model": config.MODEL_NAME}
    
    mtype = model_config.get("type")
    mname = model_config.get("model")

    logger.info(f"Calling model backend: {mtype}, model: {mname}, stream: {stream}")

    if mtype == "ollama":
        if stream:
            return call_ollama_http(mname, prompt, stream=True)
        out = call_model_with_ollama_fallback(mname, prompt)
    elif mtype == "deepseek":
        res = call_deepseek(mname, prompt, stream=stream)
        if stream:
            return res
        out = res
    elif mtype == "aliyun":
        res = call_aliyun(mname, prompt, stream=stream)
        if stream:
            return res
        out = res
    elif mtype == "openai":
        res = call_openai(mname, prompt, stream=stream)
        if stream:
            return res
        out = res
    elif mtype == "openrouter":
        reasoning = model_config.get("reasoning")
        res = call_openrouter(mname, prompt, stream=stream, reasoning=reasoning)
        if stream:
            return res
        out = res
    elif mtype == "azure":
        # Azure OpenAI: 使用部署名称（deployment name），不是模型名
        deployment = mname or config.AZURE_OPENAI_DEPLOYMENT_NAME
        res = call_azure_openai(deployment, prompt, stream=stream)
        if stream:
            return res
        out = res
    elif mtype == "anthropic":
        # Anthropic Claude API
        res = call_anthropic(mname, prompt, stream=stream)
        if stream:
            return res
        out = res
    elif mtype == "gemini":
        # Google Gemini API
        res = call_gemini(mname, prompt, stream=stream)
        if stream:
            return res
        out = res
    else:
        raise RuntimeError(f"Unsupported model backend: {mtype}")

    logger.info(f"Model response received (length: {len(out)})")
    logger.debug(f"Full raw response:\n{out}")

    # 尝试解析 JSON
    try:
        cleaned = out.strip()
        # 寻找第一个 { 和最后一个 }
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start != -1 and end != -1:
            json_candidate = cleaned[start:end+1]
            return json.loads(json_candidate)
        
        # 如果没找到 {}，或者解析失败，则返回原始文本
        # 注意：这里不再强制返回 {"text": out}，而是直接返回字符串
        # 这样非 JSON 任务（如 Reporter）能拿到原始文本
        return out
    except Exception as e:
        logger.warning(f"JSON parsing failed: {e}. Returning raw output.")
        logger.error(traceback.format_exc())
        return out


# ========== Function Calling支持 ==========

def call_model_with_tools(agent_id: str, messages: list, model_config: dict = None, tools: list = None, max_tool_rounds: int = 5):
    """
    支持Function Calling的模型调用（多轮工具调用循环）
    
    Args:
        agent_id: Agent标识符
        messages: 消息列表 [{"role": "user/assistant/tool", "content": "..."}]
        model_config: 模型配置
        tools: 工具定义列表（OpenAI Function Calling格式）
        max_tool_rounds: 最大工具调用轮次
        
    Returns:
        最终的文本响应或消息对象
    """
    if model_config is None:
        model_config = {"type": config.MODEL_BACKEND, "model": config.MODEL_NAME}
    
    mtype = model_config.get("type")
    mname = model_config.get("model")
    
    if not tools:
        # 如果没有工具，直接调用普通模式
        prompt = messages if isinstance(messages, list) else [{"role": "user", "content": messages}]
        return call_model(agent_id, prompt, model_config, stream=False)
    
    logger.info(f"[call_model_with_tools] Starting with {len(tools)} tools, max_tool_rounds={max_tool_rounds}")
    
    # 导入工具执行器
    from src.agents.meta_tools import execute_tool, format_tool_result_for_llm
    
    conversation = messages.copy()
    tool_round = 0
    
    while tool_round < max_tool_rounds:
        tool_round += 1
        logger.info(f"[call_model_with_tools] Round {tool_round}/{max_tool_rounds}")
        
        # 调用LLM
        if mtype == "deepseek":
            response = call_deepseek(mname, conversation, tools=tools, tool_choice="auto")
        elif mtype == "openai":
            response = call_openai(mname, conversation, tools=tools, tool_choice="auto")
        else:
            logger.warning(f"Model type {mtype} may not support function calling, falling back to normal mode")
            return call_model(agent_id, conversation, model_config, stream=False)
        
        # 检查响应类型
        if isinstance(response, dict) and response.get("tool_calls"):
            # LLM要求调用工具
            tool_calls = response["tool_calls"]
            logger.info(f"[call_model_with_tools] LLM requested {len(tool_calls)} tool calls")
            
            # 将assistant消息添加到对话历史
            conversation.append({
                "role": "assistant",
                "content": response.get("content"),
                "tool_calls": tool_calls
            })
            
            # 执行所有工具调用
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args_str = tool_call["function"]["arguments"]
                tool_id = tool_call["id"]
                
                try:
                    # 解析参数
                    tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                    logger.info(f"[call_model_with_tools] Executing tool: {tool_name} with args: {tool_args}")
                    
                    # 执行工具
                    tool_result = execute_tool(tool_name, tool_args)
                    
                    # 格式化结果
                    result_text = format_tool_result_for_llm(tool_name, tool_result)
                    
                    # 将工具结果添加到对话历史
                    conversation.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": tool_name,
                        "content": result_text
                    })
                    
                    logger.info(f"[call_model_with_tools] Tool {tool_name} executed successfully")
                    
                except Exception as e:
                    logger.error(f"[call_model_with_tools] Tool {tool_name} execution failed: {str(e)}")
                    # 添加错误结果
                    conversation.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "name": tool_name,
                        "content": f"❌ 工具执行失败: {str(e)}"
                    })
            
            # 继续循环，让LLM处理工具结果
            continue
        
        elif isinstance(response, dict) and response.get("content"):
            # LLM返回了最终文本响应
            logger.info(f"[call_model_with_tools] LLM returned final response (length: {len(response['content'])})")
            return response["content"]
        
        elif isinstance(response, str):
            # 直接返回的文本
            logger.info(f"[call_model_with_tools] LLM returned text response (length: {len(response)})")
            return response
        
        else:
            logger.warning(f"[call_model_with_tools] Unexpected response type: {type(response)}")
            return str(response)
    
    # 达到最大轮次
    logger.warning(f"[call_model_with_tools] Reached max tool rounds ({max_tool_rounds}), returning last response")
    if isinstance(conversation[-1], dict) and conversation[-1].get("role") == "assistant":
        return conversation[-1].get("content", "")
    return "工具调用超过最大轮次限制"


def parse_tool_calls_from_response(response: dict) -> list:
    """
    从LLM响应中解析工具调用
    
    Args:
        response: LLM API响应字典
        
    Returns:
        工具调用列表 [{"name": "tool_name", "arguments": {...}}]
    """
    if not isinstance(response, dict):
        return []
    
    tool_calls = response.get("tool_calls", [])
    if not tool_calls:
        return []
    
    parsed_calls = []
    for tc in tool_calls:
        try:
            func = tc.get("function", {})
            parsed_calls.append({
                "id": tc.get("id"),
                "name": func.get("name"),
                "arguments": json.loads(func.get("arguments", "{}")) if isinstance(func.get("arguments"), str) else func.get("arguments", {})
            })
        except Exception as e:
            logger.error(f"Failed to parse tool call: {tc}, error: {e}")
    
    return parsed_calls
