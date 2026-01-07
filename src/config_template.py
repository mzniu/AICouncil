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

# Azure OpenAI API configuration
# 中国区 endpoint: https://your-resource.openai.azure.cn
# 全球区 endpoint: https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY', '')
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT', '')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview')
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')

# Anthropic API configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
ANTHROPIC_BASE_URL = os.getenv('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')
ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
ANTHROPIC_API_VERSION = os.getenv('ANTHROPIC_API_VERSION', '2023-06-01')

# Search API configuration (Tavily is recommended for LLM search)
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')

# Google Custom Search API configuration (推荐：稳定快速，国内无需代理)
# 配置步骤：https://developers.google.com/custom-search/v1/overview
# 1. 创建 API Key: https://console.cloud.google.com/apis/credentials
# 2. 创建 Search Engine: https://programmablesearchengine.google.com/
# 免费额度：100 次/天 | 付费：$5/1000次
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
GOOGLE_SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID', '')

# Google 搜索代理配置（仅 Playwright 方案需要，国内环境必需）
# 格式：http://127.0.0.1:7890 或 socks5://127.0.0.1:1080
GOOGLE_SEARCH_PROXY = os.getenv('GOOGLE_SEARCH_PROXY', '')

# 搜索引擎选项: 'tavily', 'duckduckgo', 'bing', 'baidu', 'yahoo', 'mojeek', 'google'
# 支持多选，用逗号分隔，例如: 'google,yahoo,bing'
# - google: 使用 Google Custom Search API（推荐，需配置 GOOGLE_API_KEY）
#          如未配置 API，自动降级为 Playwright 方案（国内需要代理）
# - google_api: 强制使用 API 方案
# - google_playwright: 强制使用 Playwright 方案（需代理）
# - yahoo: 底层使用Bing引擎，无需API key，支持中英文
# - mojeek: 独立搜索引擎，无需API key，英文效果较好
SEARCH_PROVIDER = os.getenv('SEARCH_PROVIDER', 'baidu')  # Options: 'tavily', 'duckduckgo', 'bing', 'baidu', 'yahoo', 'mojeek', 'google' (comma separated for multiple)

# Ollama HTTP endpoint (if running local HTTP server)
OLLAMA_HTTP_URL = os.getenv('OLLAMA_HTTP_URL', 'http://127.0.0.1:11434/api/generate')

# Browser path for DrissionPage (Baidu search)
# If empty, DrissionPage will try to find Chrome/Edge automatically
from src.utils.browser_utils import find_browser_path
BROWSER_PATH = os.getenv('BROWSER_PATH', find_browser_path() or '')
