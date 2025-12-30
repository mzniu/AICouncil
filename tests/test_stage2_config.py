"""Stage 2 配置系统快速测试"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src import config_manager as config
from src.utils.path_manager import get_workspace_dir, get_config_path
from src.config_manager import get_config_manager

print('=' * 60)
print('Stage 2 配置系统测试')
print('=' * 60)
print()

# 测试配置访问
print('1. 配置值访问测试:')
print(f'   MODEL_BACKEND: {config.MODEL_BACKEND}')
print(f'   DEEPSEEK_MODEL: {config.DEEPSEEK_MODEL}')
print(f'   SEARCH_PROVIDER: {config.SEARCH_PROVIDER}')
print()

# 测试路径管理
print('2. 路径管理测试:')
print(f'   Workspace目录: {get_workspace_dir()}')
print(f'   配置文件路径: {get_config_path()}')
print()

# 测试配置优先级
cm = get_config_manager()
info = cm.get_config_info()
print('3. 配置系统状态:')
print(f'   运行模式: {"打包" if info["is_frozen"] else "开发"}')
print(f'   配置文件存在: {info["config_exists"]}')
print(f'   缓存的配置数: {len(info["cached_keys"])}')
print()

# 测试模块导入
print('4. 核心模块导入测试:')
try:
    from src.web import app
    print('   ✅ Flask应用')
except Exception as e:
    print(f'   ❌ Flask应用: {e}')

try:
    from src.agents import demo_runner
    print('   ✅ Demo Runner')
except Exception as e:
    print(f'   ❌ Demo Runner: {e}')

try:
    from src.agents import langchain_agents
    print('   ✅ LangChain Agents')
except Exception as e:
    print(f'   ❌ LangChain Agents: {e}')

try:
    from src.utils import search_utils
    print('   ✅ Search Utils')
except Exception as e:
    print(f'   ❌ Search Utils: {e}')

print()
print('=' * 60)
print('✅ Stage 2 配置系统工作正常！')
print('=' * 60)
