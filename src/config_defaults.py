"""
配置默认值定义

此模块定义所有配置项的默认值，在开发环境和打包环境中都可以使用。
打包后，这些默认值会被嵌入到 EXE 中。
"""
import os

# ============= 日志配置 =============
DEFAULT_LOG_FILE = 'aicouncil.log'
DEFAULT_LOG_LEVEL = 'INFO'

# ============= 模型后端配置 =============
DEFAULT_MODEL_BACKEND = 'ollama'
DEFAULT_MODEL_NAME = 'qwen3:4b'

# ============= OpenAI 配置 =============
DEFAULT_OPENAI_API_KEY = ''
DEFAULT_OPENAI_BASE_URL = 'https://api.openai.com/v1'
DEFAULT_OPENAI_MODEL = 'gpt-4o'

# ============= DeepSeek 配置 =============
DEFAULT_DEEPSEEK_API_KEY = ''
DEFAULT_DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
DEFAULT_DEEPSEEK_MODEL = 'deepseek-reasoner'

# ============= Aliyun DashScope 配置 =============
DEFAULT_ALIYUN_API_KEY = ''
DEFAULT_ALIYUN_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
DEFAULT_ALIYUN_MODEL = 'qwen-plus'

# ============= OpenRouter 配置 =============
DEFAULT_OPENROUTER_API_KEY = ''
DEFAULT_OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
DEFAULT_OPENROUTER_MODEL = 'google/gemini-2.0-flash-exp:free'

# ============= 搜索引擎配置 =============
DEFAULT_TAVILY_API_KEY = ''
DEFAULT_SEARCH_PROVIDER = 'yahoo,mojeek'  # 默认使用无需API key的搜索引擎

# ============= Ollama 配置 =============
DEFAULT_OLLAMA_HTTP_URL = 'http://127.0.0.1:11434/api/generate'

# ============= 浏览器路径配置 =============
DEFAULT_BROWSER_PATH = ''  # 空字符串表示自动检测

# ============= 配置优先级说明 =============
"""
配置加载优先级（从高到低）：
1. 环境变量（最高优先级）
2. 用户配置文件（开发环境: src/config.py, 打包环境: %APPDATA%/AICouncil/config.py）
3. 默认值（此文件，最低优先级）

打包环境配置文件位置：
- Windows: %APPDATA%/AICouncil/config.py
- 首次运行时，会从 config_template.py 自动复制到该位置
"""
