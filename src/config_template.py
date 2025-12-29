"""Configuration for local model backend and API keys.

Keep secrets out of source control in production (use environment variables or a secrets manager).
"""
import os

# Logging configuration
LOG_FILE = os.getenv('LOG_FILE', 'aicouncil.log')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Backend type: 'ollama' (default). Future values: 'openai', 'deepseek'
MODEL_BACKEND = os.getenv('MODEL_BACKEND', 'ollama')

# Default local Ollama model name (user has qwen3:8b-q8_0)
MODEL_NAME = os.getenv('MODEL_NAME', 'qwen3:4b')

# OpenAI API key (optional for future use). Read from env by default.
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# DeepSeek API configuration
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-reasoner')

# Aliyun (DashScope) API configuration
ALIYUN_API_KEY = os.getenv('ALIYUN_API_KEY', '')
ALIYUN_BASE_URL = os.getenv('ALIYUN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
ALIYUN_MODEL = os.getenv('ALIYUN_MODEL', 'qwen-plus')

# OpenAI API configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_BASE_URL = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'google/gemini-3-flash-preview')

# Search API configuration (Tavily is recommended for LLM search)
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')
# 搜索引擎选项: 'tavily', 'duckduckgo', 'bing', 'baidu', 'yahoo', 'mojeek'
# 支持多选，用逗号分隔，例如: 'yahoo,bing,baidu'
# yahoo: 底层使用Bing引擎，无需API key，支持中英文
# mojeek: 独立搜索引擎，无需API key，英文效果较好
SEARCH_PROVIDER = os.getenv('SEARCH_PROVIDER', 'baidu')  # Options: 'tavily', 'duckduckgo', 'bing', 'baidu', 'yahoo', 'mojeek' (comma separated for multiple)

# Ollama HTTP endpoint (if running local HTTP server)
OLLAMA_HTTP_URL = os.getenv('OLLAMA_HTTP_URL', 'http://127.0.0.1:11434/api/generate')

# Browser path for DrissionPage (Baidu search)
# If empty, DrissionPage will try to find Chrome/Edge automatically
from src.utils.browser_utils import find_browser_path
BROWSER_PATH = os.getenv('BROWSER_PATH', find_browser_path() or '')
