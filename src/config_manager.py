"""
配置管理器

负责在开发环境和打包环境中加载配置，处理配置优先级：
1. 环境变量（最高）
2. 用户配置文件（src/config.py 或 %APPDATA%/AICouncil/config.py）
3. 默认值（config_defaults.py，最低）
"""
import os
import sys
from pathlib import Path
from typing import Any, Optional

# 确保可以导入项目模块
if __name__ == '__main__':
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

# 尝试导入 path_manager，如果导入失败使用简单实现
try:
    from src.utils.path_manager import is_frozen, get_config_path, get_base_dir
except (ImportError, ModuleNotFoundError):
    # 简单实现，避免循环依赖
    def is_frozen():
        return getattr(sys, 'frozen', False)
    
    def get_base_dir():
        if is_frozen():
            return Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
        return Path(__file__).resolve().parent.parent
    
    def get_config_path():
        if is_frozen():
            appdata = Path(os.getenv('APPDATA', os.path.expanduser('~')))
            config_dir = appdata / 'AICouncil'
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir / 'config.py'
        return get_base_dir() / 'src' / 'config.py'

# 导入默认值
from src.config_defaults import (
    DEFAULT_LOG_FILE, DEFAULT_LOG_LEVEL,
    DEFAULT_MODEL_BACKEND, DEFAULT_MODEL_NAME,
    DEFAULT_OPENAI_API_KEY, DEFAULT_OPENAI_BASE_URL, DEFAULT_OPENAI_MODEL,
    DEFAULT_DEEPSEEK_API_KEY, DEFAULT_DEEPSEEK_BASE_URL, DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_ALIYUN_API_KEY, DEFAULT_ALIYUN_BASE_URL, DEFAULT_ALIYUN_MODEL,
    DEFAULT_OPENROUTER_API_KEY, DEFAULT_OPENROUTER_BASE_URL, DEFAULT_OPENROUTER_MODEL,
    DEFAULT_TAVILY_API_KEY, DEFAULT_SEARCH_PROVIDER,
    DEFAULT_OLLAMA_HTTP_URL, DEFAULT_BROWSER_PATH
)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self._config_cache = {}
        self._user_config = None
        self._load_user_config()
    
    def _load_user_config(self):
        """加载用户配置文件"""
        config_path = get_config_path()
        
        if not config_path.exists():
            # 配置文件不存在，使用默认值
            return
        
        # 动态加载配置文件
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("user_config", config_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self._user_config = module
        except Exception as e:
            # 配置文件加载失败，记录警告但不中断
            print(f"Warning: Failed to load config from {config_path}: {e}")
            self._user_config = None
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        优先级：环境变量 > 用户配置文件 > 默认值 > default参数
        
        Args:
            key: 配置键名（大写）
            default: 如果所有来源都没有该配置，返回此默认值
        
        Returns:
            配置值
        """
        # 检查缓存
        if key in self._config_cache:
            return self._config_cache[key]
        
        # 1. 检查环境变量（最高优先级）
        env_value = os.getenv(key)
        if env_value is not None:
            self._config_cache[key] = env_value
            return env_value
        
        # 2. 检查用户配置文件
        if self._user_config and hasattr(self._user_config, key):
            user_value = getattr(self._user_config, key)
            self._config_cache[key] = user_value
            return user_value
        
        # 3. 检查默认值
        default_key = f'DEFAULT_{key}'
        if default_key in globals():
            default_value = globals()[default_key]
            self._config_cache[key] = default_value
            return default_value
        
        # 4. 返回传入的默认值
        return default
    
    def set(self, key: str, value: Any):
        """
        设置配置值（仅在内存中，不会写入文件）
        
        Args:
            key: 配置键名
            value: 配置值
        """
        self._config_cache[key] = value
    
    def reload(self):
        """重新加载配置"""
        self._config_cache.clear()
        self._user_config = None
        self._load_user_config()
    
    def get_config_info(self) -> dict:
        """
        获取配置信息（用于调试）
        
        Returns:
            包含配置来源和路径的字典
        """
        config_path = get_config_path()
        return {
            'is_frozen': is_frozen(),
            'config_path': str(config_path),
            'config_exists': config_path.exists(),
            'base_dir': str(get_base_dir()),
            'cached_keys': list(self._config_cache.keys())
        }


# 全局单例
_config_manager = None

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器单例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


# 便捷函数
def get_config(key: str, default: Any = None) -> Any:
    """获取配置值的便捷函数"""
    return get_config_manager().get(key, default)


def set_config(key: str, value: Any):
    """设置配置值的便捷函数（仅内存）"""
    get_config_manager().set(key, value)


def reload_config():
    """重新加载配置的便捷函数"""
    get_config_manager().reload()


# 向后兼容的配置访问方式
LOG_FILE = get_config('LOG_FILE')
LOG_LEVEL = get_config('LOG_LEVEL')
MODEL_BACKEND = get_config('MODEL_BACKEND')
MODEL_NAME = get_config('MODEL_NAME')
OPENAI_API_KEY = get_config('OPENAI_API_KEY')
OPENAI_BASE_URL = get_config('OPENAI_BASE_URL')
OPENAI_MODEL = get_config('OPENAI_MODEL')
DEEPSEEK_API_KEY = get_config('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = get_config('DEEPSEEK_BASE_URL')
DEEPSEEK_MODEL = get_config('DEEPSEEK_MODEL')
ALIYUN_API_KEY = get_config('ALIYUN_API_KEY')
ALIYUN_BASE_URL = get_config('ALIYUN_BASE_URL')
ALIYUN_MODEL = get_config('ALIYUN_MODEL')
OPENROUTER_API_KEY = get_config('OPENROUTER_API_KEY')
OPENROUTER_BASE_URL = get_config('OPENROUTER_BASE_URL')
OPENROUTER_MODEL = get_config('OPENROUTER_MODEL')
TAVILY_API_KEY = get_config('TAVILY_API_KEY')
SEARCH_PROVIDER = get_config('SEARCH_PROVIDER')
OLLAMA_HTTP_URL = get_config('OLLAMA_HTTP_URL')
BROWSER_PATH = get_config('BROWSER_PATH')


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("配置管理器测试")
    print("=" * 60)
    
    cm = get_config_manager()
    info = cm.get_config_info()
    
    print(f"\n运行模式: {'打包环境' if info['is_frozen'] else '开发环境'}")
    print(f"配置文件路径: {info['config_path']}")
    print(f"配置文件存在: {info['config_exists']}")
    print(f"基础目录: {info['base_dir']}")
    
    print("\n配置值示例:")
    print(f"  LOG_FILE: {cm.get('LOG_FILE')}")
    print(f"  MODEL_BACKEND: {cm.get('MODEL_BACKEND')}")
    print(f"  DEEPSEEK_MODEL: {cm.get('DEEPSEEK_MODEL')}")
    print(f"  SEARCH_PROVIDER: {cm.get('SEARCH_PROVIDER')}")
    
    print("\n缓存的配置键:")
    for key in info['cached_keys']:
        print(f"  - {key}")
    
    print("\n" + "=" * 60)
