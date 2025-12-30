"""
路径管理器 - 自适应开发/打包环境
用于统一管理资源路径、工作空间目录、配置文件位置等

设计原则：
1. 开发环境：使用相对路径（原有逻辑）
2. 打包环境：使用 PyInstaller 的 _MEIPASS 和用户目录
3. 自动检测运行模式，无需手动切换

作者：AICouncil Team
日期：2025-12-30
"""

import os
import sys
from pathlib import Path
from typing import Optional

# 延迟导入 logger，避免循环依赖
try:
    from src.utils import logger
except ImportError:
    # 如果直接运行此文件，logger 可能不可用
    import logging
    logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# 环境检测
# ═══════════════════════════════════════════════════════════

def is_frozen() -> bool:
    """
    检测是否运行在打包环境（PyInstaller）
    
    Returns:
        bool: True 表示打包环境，False 表示开发环境
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_running_mode() -> str:
    """
    获取当前运行模式的描述
    
    Returns:
        str: "打包环境" 或 "开发环境"
    """
    return "打包环境" if is_frozen() else "开发环境"


# ═══════════════════════════════════════════════════════════
# 项目根目录
# ═══════════════════════════════════════════════════════════

def get_project_root() -> Path:
    """
    获取项目根目录
    
    开发环境：项目根目录（包含 src/、docs/ 等）
    打包环境：PyInstaller 的临时解压目录 (_MEIPASS)
    
    Returns:
        Path: 项目根目录路径
    """
    if is_frozen():
        # 打包环境：使用 PyInstaller 的临时目录
        return Path(sys._MEIPASS)
    else:
        # 开发环境：从当前文件向上找到项目根目录
        # 当前文件：src/utils/path_manager.py
        # 向上两级：src/ -> 项目根/
        current_file = Path(__file__).resolve()
        return current_file.parent.parent.parent


# ═══════════════════════════════════════════════════════════
# 资源路径解析
# ═══════════════════════════════════════════════════════════

def get_resource_path(relative_path: str) -> Path:
    """
    获取资源文件的绝对路径（自适应开发/打包环境）
    
    用途：模板文件、静态资源、配置文件等
    
    Args:
        relative_path: 相对于项目根目录的路径
                      例如：'src/web/templates'、'src/web/static/vendor/echarts.min.js'
    
    Returns:
        Path: 资源文件的绝对路径
    
    Examples:
        >>> get_resource_path('src/web/templates')
        # 开发环境：D:/git/MyCouncil/src/web/templates
        # 打包环境：C:/Users/.../Temp/_MEIPASS123/src/web/templates
    """
    base_path = get_project_root()
    full_path = base_path / relative_path
    
    # 调试日志（仅在第一次调用时输出）
    if not hasattr(get_resource_path, '_logged'):
        logger.debug(f"[path_manager] 运行模式: {get_running_mode()}")
        logger.debug(f"[path_manager] 项目根目录: {base_path}")
        get_resource_path._logged = True
    
    return full_path


def get_templates_dir() -> Path:
    """
    获取 Web 模板目录
    
    Returns:
        Path: templates 目录路径
    """
    return get_resource_path('src/web/templates')


def get_static_dir() -> Path:
    """
    获取静态资源目录
    
    Returns:
        Path: static 目录路径
    """
    return get_resource_path('src/web/static')


# ═══════════════════════════════════════════════════════════
# 用户数据目录
# ═══════════════════════════════════════════════════════════

def get_user_data_dir() -> Path:
    """
    获取用户数据目录（用于存放配置、工作空间等）
    
    开发环境：项目根目录（不改变原有行为）
    打包环境：%APPDATA%/AICouncil/
    
    目录结构（打包环境）：
    %APPDATA%/AICouncil/
    ├── config.py           # 用户配置
    ├── workspaces/         # 讨论工作空间
    ├── logs/               # 日志文件
    └── temp/               # 临时文件
    
    Returns:
        Path: 用户数据目录路径
    """
    if is_frozen():
        # 打包环境：使用 Windows AppData 目录
        appdata = os.getenv('APPDATA')
        if not appdata:
            # 备用方案：使用用户主目录
            appdata = str(Path.home())
            logger.warning("[path_manager] APPDATA 环境变量未找到，使用用户主目录")
        
        user_data_dir = Path(appdata) / 'AICouncil'
        
        # 自动创建目录（如果不存在）
        if not user_data_dir.exists():
            try:
                user_data_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"[path_manager] 创建用户数据目录: {user_data_dir}")
            except Exception as e:
                logger.error(f"[path_manager] 创建用户数据目录失败: {e}")
        
        return user_data_dir
    else:
        # 开发环境：使用项目根目录（保持原有行为）
        return get_project_root()


def get_workspace_dir() -> Path:
    """
    获取工作空间目录（存放讨论记录）
    
    开发环境：./workspaces/
    打包环境：%APPDATA%/AICouncil/workspaces/
    
    Returns:
        Path: 工作空间目录路径
    """
    if is_frozen():
        workspace_dir = get_user_data_dir() / 'workspaces'
    else:
        workspace_dir = get_project_root() / 'workspaces'
    
    # 自动创建目录
    if not workspace_dir.exists():
        try:
            workspace_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[path_manager] 创建工作空间目录: {workspace_dir}")
        except Exception as e:
            logger.error(f"[path_manager] 创建工作空间目录失败: {e}")
    
    return workspace_dir


def get_config_path() -> Path:
    """
    获取配置文件路径
    
    开发环境：./src/config.py
    打包环境：%APPDATA%/AICouncil/config.py
    
    Returns:
        Path: 配置文件路径
    """
    if is_frozen():
        return get_user_data_dir() / 'config.py'
    else:
        return get_project_root() / 'src' / 'config.py'


def get_logs_dir() -> Path:
    """
    获取日志目录
    
    开发环境：项目根目录（保持原有行为）
    打包环境：%APPDATA%/AICouncil/logs/
    
    Returns:
        Path: 日志目录路径
    """
    if is_frozen():
        logs_dir = get_user_data_dir() / 'logs'
    else:
        logs_dir = get_project_root()
    
    # 自动创建目录
    if not logs_dir.exists():
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[path_manager] 创建日志目录: {logs_dir}")
        except Exception as e:
            logger.error(f"[path_manager] 创建日志目录失败: {e}")
    
    return logs_dir


# ═══════════════════════════════════════════════════════════
# 路径规范化
# ═══════════════════════════════════════════════════════════

def normalize_path(path: str | Path) -> Path:
    """
    规范化路径（转为绝对路径、解析符号链接）
    
    Args:
        path: 输入路径
    
    Returns:
        Path: 规范化后的路径
    """
    return Path(path).resolve()


def ensure_dir_exists(dir_path: str | Path) -> Path:
    """
    确保目录存在（不存在则创建）
    
    Args:
        dir_path: 目录路径
    
    Returns:
        Path: 目录路径
    
    Raises:
        OSError: 创建目录失败
    """
    path = Path(dir_path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"[path_manager] 创建目录: {path}")
    return path


# ═══════════════════════════════════════════════════════════
# 首次运行检测
# ═══════════════════════════════════════════════════════════

def is_first_run() -> bool:
    """
    检测是否首次运行（打包环境）
    
    判断依据：用户数据目录中是否存在 config.py
    
    Returns:
        bool: True 表示首次运行
    """
    if not is_frozen():
        # 开发环境永远不是首次运行
        return False
    
    config_path = get_config_path()
    return not config_path.exists()


def mark_first_run_completed():
    """
    标记首次运行已完成
    
    创建标记文件：.first_run_completed
    """
    if is_frozen():
        marker_file = get_user_data_dir() / '.first_run_completed'
        try:
            marker_file.touch()
            logger.info("[path_manager] 首次运行设置完成")
        except Exception as e:
            logger.warning(f"[path_manager] 创建首次运行标记失败: {e}")


# ═══════════════════════════════════════════════════════════
# 调试信息输出
# ═══════════════════════════════════════════════════════════

def print_environment_info():
    """
    打印环境信息（用于调试）
    """
    print("═" * 60)
    print("  AICouncil 路径管理器 - 环境信息")
    print("═" * 60)
    print(f"运行模式:       {get_running_mode()}")
    print(f"是否打包:       {is_frozen()}")
    print(f"项目根目录:     {get_project_root()}")
    print(f"用户数据目录:   {get_user_data_dir()}")
    print(f"工作空间目录:   {get_workspace_dir()}")
    print(f"配置文件路径:   {get_config_path()}")
    print(f"日志目录:       {get_logs_dir()}")
    print(f"模板目录:       {get_templates_dir()}")
    print(f"静态资源目录:   {get_static_dir()}")
    print(f"首次运行:       {is_first_run()}")
    print("═" * 60)


# ═══════════════════════════════════════════════════════════
# 模块初始化
# ═══════════════════════════════════════════════════════════

# 模块加载时输出环境信息（调试用）
if __name__ != "__main__":
    logger.debug(f"[path_manager] 加载完成，运行模式: {get_running_mode()}")


# ═══════════════════════════════════════════════════════════
# 命令行测试
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 直接运行此文件时，输出环境信息
    print_environment_info()
    
    # 测试路径解析
    print("\n测试路径解析:")
    test_paths = [
        'src/web/templates',
        'src/web/static/vendor/echarts.min.js',
        'src/config.py',
    ]
    for path in test_paths:
        resolved = get_resource_path(path)
        exists = "✅ 存在" if resolved.exists() else "❌ 不存在"
        print(f"  {path}")
        print(f"    → {resolved}")
        print(f"    {exists}")
