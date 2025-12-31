"""
Playwright 自动安装工具

在打包环境首次运行时，检测并安装 Playwright + Chromium
"""
import os
import sys
import subprocess
from pathlib import Path
from src.utils.logger import logger
from src.utils.path_manager import is_frozen, get_user_data_dir


def is_playwright_installed() -> bool:
    """检测 Playwright 是否已安装"""
    try:
        from playwright.async_api import async_playwright
        
        # 检查 Chromium 浏览器是否已下载
        if is_frozen():
            # 打包环境：检查用户数据目录
            playwright_dir = get_user_data_dir() / 'playwright'
            chromium_path = playwright_dir / 'chromium-*' / 'chrome-win' / 'chrome.exe'
            
            # 使用 glob 查找
            import glob
            matches = glob.glob(str(chromium_path))
            return len(matches) > 0
        else:
            # 开发环境：检查默认位置
            home = Path.home()
            playwright_dir = home / 'AppData' / 'Local' / 'ms-playwright'
            return playwright_dir.exists()
            
    except ImportError:
        return False


def get_playwright_install_path() -> Path:
    """获取 Playwright 安装路径"""
    if is_frozen():
        # 打包环境：安装到用户数据目录
        return get_user_data_dir() / 'playwright'
    else:
        # 开发环境：使用默认路径
        return Path.home() / 'AppData' / 'Local' / 'ms-playwright'


def install_playwright(callback=None) -> bool:
    """
    安装 Playwright + Chromium 浏览器
    
    Args:
        callback: 进度回调函数 callback(message: str)
    
    Returns:
        True if 安装成功, False otherwise
    """
    try:
        def log(msg):
            logger.info(f"[playwright_installer] {msg}")
            if callback:
                callback(msg)
        
        log("开始安装 Playwright...")
        
        # 1. 检查 playwright 包是否已安装
        try:
            import playwright
            log("Playwright 包已安装")
        except ImportError:
            log("安装 Playwright 包...")
            
            # 获取 pip 可执行文件路径
            if is_frozen():
                # 打包环境：使用打包的 Python
                python_exe = sys.executable
                pip_cmd = [python_exe, "-m", "pip"]
            else:
                # 开发环境
                pip_cmd = [sys.executable, "-m", "pip"]
            
            # 安装 playwright 包
            result = subprocess.run(
                pip_cmd + ["install", "playwright"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                log(f"安装 Playwright 包失败: {result.stderr}")
                return False
            
            log("Playwright 包安装成功")
        
        # 2. 安装 Chromium 浏览器
        log("下载 Chromium 浏览器（约 150MB，首次运行需要 2-5 分钟）...")
        
        # 设置环境变量，指定安装路径
        install_path = get_playwright_install_path()
        install_path.mkdir(parents=True, exist_ok=True)
        
        env = os.environ.copy()
        env['PLAYWRIGHT_BROWSERS_PATH'] = str(install_path)
        
        # 执行 playwright install chromium
        if is_frozen():
            python_exe = sys.executable
            playwright_cmd = [python_exe, "-m", "playwright", "install", "chromium"]
        else:
            playwright_cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
        
        log(f"执行命令: {' '.join(playwright_cmd)}")
        log(f"安装路径: {install_path}")
        
        # 使用 Popen 实时显示输出
        process = subprocess.Popen(
            playwright_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
            universal_newlines=True
        )
        
        # 读取输出
        for line in process.stdout:
            line = line.strip()
            if line:
                log(f"  {line}")
        
        process.wait()
        
        if process.returncode != 0:
            log("Chromium 安装失败")
            return False
        
        log("Chromium 浏览器安装成功！")
        
        # 3. 验证安装
        if is_playwright_installed():
            log("✅ Playwright 安装完成并验证成功")
            return True
        else:
            log("⚠️ Playwright 安装完成，但验证失败")
            return False
        
    except Exception as e:
        logger.error(f"[playwright_installer] 安装失败: {e}", exc_info=True)
        if callback:
            callback(f"安装失败: {e}")
        return False


def ensure_playwright_installed(force_install=False) -> bool:
    """
    确保 Playwright 已安装（自动检测并安装）
    
    Args:
        force_install: 强制重新安装
    
    Returns:
        True if 已安装或安装成功, False otherwise
    """
    if not force_install and is_playwright_installed():
        logger.info("[playwright_installer] Playwright 已安装")
        return True
    
    logger.info("[playwright_installer] Playwright 未安装，开始自动安装...")
    return install_playwright()


def get_chromium_executable_path() -> str:
    """获取 Chromium 可执行文件路径"""
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            executable_path = browser._impl_obj._executable_path
            browser.close()
            return executable_path
            
    except Exception as e:
        logger.error(f"[playwright_installer] 获取 Chromium 路径失败: {e}")
        return ""


if __name__ == "__main__":
    # 测试安装
    print("检测 Playwright 安装状态...")
    
    if is_playwright_installed():
        print("✅ Playwright 已安装")
        print(f"浏览器路径: {get_chromium_executable_path()}")
    else:
        print("❌ Playwright 未安装")
        print("\n开始安装...")
        
        success = install_playwright(callback=lambda msg: print(f"  {msg}"))
        
        if success:
            print("\n✅ 安装成功！")
        else:
            print("\n❌ 安装失败")
