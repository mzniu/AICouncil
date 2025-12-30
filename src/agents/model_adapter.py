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
from src.utils import logger


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


def call_deepseek(model: str, prompt: str, timeout: int = 60, max_retries: int = 3, stream: bool = False):
    """调用 DeepSeek API (OpenAI 兼容接口)，带重试机制。"""
    url = f"{config.DEEPSEEK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 清理可能导致 JSON 解析失败的不可见控制字符，并记录长度
    clean_prompt = "".join(c for c in prompt if c.isprintable() or c in "\n\r\t")
    logger.info(f"DeepSeek prompt length: {len(clean_prompt)} characters")
    
    payload = {
        "model": model or config.DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": clean_prompt}],
        "stream": stream
    }
    
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
            return data["choices"][0]["message"]["content"]
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


def call_openai(model: str, prompt: str, timeout: int = 60, max_retries: int = 3, stream: bool = False):
    """调用 OpenAI API，带重试机制。"""
    url = f"{config.OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model or config.OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream
    }
    
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
            return data["choices"][0]["message"]["content"]
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
