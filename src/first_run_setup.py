"""
首次运行设置

在打包环境首次运行时，复制 config_template.py 到用户配置目录。
"""
import os
import shutil
from pathlib import Path

try:
    from src.utils.path_manager import is_frozen, get_config_path, get_resource_path, get_base_dir
    from src.utils.logger import logger
except (ImportError, ModuleNotFoundError):
    # 简单实现避免依赖问题
    import sys
    import logging
    
    logger = logging.getLogger(__name__)
    
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
    
    def get_resource_path(relative_path):
        if is_frozen():
            base_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
            return base_path / relative_path
        return get_base_dir() / relative_path


def is_first_run() -> bool:
    """
    检查是否是首次运行
    
    首次运行的判断条件：
    1. 在打包环境中运行
    2. 用户配置文件不存在
    
    Returns:
        True if 首次运行, False otherwise
    """
    if not is_frozen():
        return False
    
    config_path = get_config_path()
    return not config_path.exists()


def setup_first_run() -> bool:
    """
    执行首次运行设置
    
    操作：
    1. 检查是否是首次运行
    2. 创建用户配置目录
    3. 复制 config_template.py 到用户配置目录并重命名为 config.py
    4. 创建 .aicouncil_version 文件记录版本信息
    
    Returns:
        True if 设置成功, False otherwise
    """
    if not is_first_run():
        logger.info("非首次运行或开发环境，跳过首次运行设置")
        return True
    
    try:
        logger.info("检测到首次运行，开始初始化配置...")
        
        # 获取路径
        config_path = get_config_path()
        config_dir = config_path.parent
        template_path = get_resource_path('src/config_template.py')
        
        # 创建配置目录
        config_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建配置目录: {config_dir}")
        
        # 检查模板文件是否存在
        if not template_path.exists():
            logger.error(f"配置模板文件不存在: {template_path}")
            return False
        
        # 复制配置模板
        shutil.copy2(template_path, config_path)
        logger.info(f"复制配置文件: {template_path} -> {config_path}")
        
        # 创建版本标记文件
        version_file = config_dir / '.aicouncil_version'
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write('1.0.0\n')
        logger.info(f"创建版本文件: {version_file}")
        
        # 创建 README
        readme_path = config_dir / 'README.txt'
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write("""AICouncil 配置文件说明

此目录包含 AICouncil 的用户配置文件。

文件说明：
- config.py: 主配置文件，包含 API 密钥和模型配置
- .aicouncil_version: 版本标记文件
- workspaces/: 讨论会话工作空间目录

修改配置：
1. 使用文本编辑器打开 config.py
2. 修改对应的配置项（如 API 密钥）
3. 保存文件
4. 重启 AICouncil

注意：
- 请妥善保管 API 密钥，不要分享给他人
- 删除此目录会导致配置丢失，请谨慎操作
- 重新安装时会保留此配置目录

更多信息：https://github.com/mzniu/AICouncil
""")
        logger.info(f"创建说明文件: {readme_path}")
        
        logger.info("首次运行设置完成！")
        logger.info(f"配置文件位置: {config_path}")
        logger.info("请编辑配置文件设置 API 密钥")
        
        return True
        
    except Exception as e:
        logger.error(f"首次运行设置失败: {e}", exc_info=True)
        return False


def get_config_info() -> dict:
    """
    获取配置信息（用于诊断）
    
    Returns:
        包含配置路径和状态的字典
    """
    config_path = get_config_path()
    config_dir = config_path.parent
    
    return {
        'is_frozen': is_frozen(),
        'is_first_run': is_first_run(),
        'config_path': str(config_path),
        'config_exists': config_path.exists(),
        'config_dir': str(config_dir),
        'config_dir_exists': config_dir.exists(),
        'base_dir': str(get_base_dir())
    }


def print_config_info():
    """打印配置信息（用于调试）"""
    info = get_config_info()
    
    print("=" * 60)
    print("首次运行设置 - 配置信息")
    print("=" * 60)
    print(f"运行模式: {'打包环境' if info['is_frozen'] else '开发环境'}")
    print(f"首次运行: {'是' if info['is_first_run'] else '否'}")
    print(f"配置目录: {info['config_dir']}")
    print(f"配置目录存在: {'是' if info['config_dir_exists'] else '否'}")
    print(f"配置文件路径: {info['config_path']}")
    print(f"配置文件存在: {'是' if info['config_exists'] else '否'}")
    print(f"基础目录: {info['base_dir']}")
    print("=" * 60)


if __name__ == '__main__':
    import sys
    
    # 添加项目根目录到 sys.path
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 打印配置信息
    print_config_info()
    
    # 如果是首次运行，执行设置
    if is_first_run():
        print("\n检测到首次运行，开始初始化...")
        success = setup_first_run()
        if success:
            print("\n✅ 首次运行设置完成！")
        else:
            print("\n❌ 首次运行设置失败！")
    else:
        print("\n非首次运行，无需设置")
