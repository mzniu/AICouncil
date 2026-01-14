"""
AICouncil 打包配置文件
用于 PyInstaller 打包的参数配置和路径定义
"""

import os
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# 项目基础路径
# ═══════════════════════════════════════════════════════════
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
SRC_DIR = PROJECT_ROOT / "src"
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"

# ═══════════════════════════════════════════════════════════
# 应用信息
# ═══════════════════════════════════════════════════════════
APP_NAME = "AICouncil"
APP_VERSION = "2.0.1"
APP_AUTHOR = "AICouncil Team"
APP_DESCRIPTION = "多智能体协商式决策系统"
APP_COPYRIGHT = "Copyright © 2025 AICouncil Team"

# ═══════════════════════════════════════════════════════════
# 打包模式配置
# ═══════════════════════════════════════════════════════════
# 打包模式配置
# ═══════════════════════════════════════════════════════════
# 选择打包方案：
# - "minimal": 精简版本 (~80-120MB，不含 Playwright/浏览器)
# - "full": 完整功能版本 (~150-200MB，内嵌 Playwright)
PACKAGING_MODE = "full"  # 使用完整版本，包含 Playwright

# 打包类型：
# - "onedir": 单目录模式（更快启动，推荐）
# - "onefile": 单文件模式（体积更小，启动慢）
BUNDLE_TYPE = "onefile"

# 是否使用 UPX 压缩（可减少 30-40% 体积）
USE_UPX = True

# 是否启用控制台窗口（调试时设为 True）
CONSOLE_MODE = True

# ═══════════════════════════════════════════════════════════
# 数据文件配置（需要打包的非 Python 文件）
# ═══════════════════════════════════════════════════════════
DATA_FILES = [
    # Web 模板文件
    (str(SRC_DIR / "web" / "templates"), "src/web/templates"),
    
    # 静态资源（CSS/JS/Images）
    (str(SRC_DIR / "web" / "static"), "src/web/static"),
    
    # 配置模板
    (str(SRC_DIR / "config_template.py"), "src/"),
    
    # 角色定义文件（作为只读模板，实际使用会复制到用户目录）
    (str(SRC_DIR / "agents" / "roles"), "src/agents/roles"),
    
    # 默认配置（打包环境使用）
    # 注意：实际的 config.py 不打包，运行时从用户目录读取
]

# 如果是完整功能版本，添加 Playwright 相关文件
if PACKAGING_MODE == "full":
    import site
    from pathlib import Path
    
    # 1. 打包 Playwright 驱动程序
    playwright_pkg = None
    for site_pkg in site.getsitepackages():
        playwright_path = Path(site_pkg) / "playwright"
        if playwright_path.exists():
            playwright_pkg = playwright_path
            break
    
    if playwright_pkg:
        # 打包 playwright 驱动和依赖
        DATA_FILES.append((str(playwright_pkg / "driver"), "playwright/driver"))
    
    # 2. 打包 Chromium 浏览器（用户的 AppData）
    playwright_browsers = Path.home() / "AppData" / "Local" / "ms-playwright"
    if playwright_browsers.exists():
        # 打包chromium_headless_shell（Playwright优先使用）和chromium（fallback）
        browser_patterns = ["chromium_headless_shell-*", "chromium-*"]
        for pattern in browser_patterns:
            for browser_dir in sorted(playwright_browsers.glob(pattern), reverse=True):
                if browser_dir.is_dir():
                    DATA_FILES.append((str(browser_dir), f"playwright/browsers/{browser_dir.name}"))
                    print(f"✅ 已添加 Playwright 浏览器: {browser_dir.name}")
                    break  # 只取最新版本

# ═══════════════════════════════════════════════════════════
# 隐藏导入（动态导入的模块，PyInstaller 无法自动检测）
# ═══════════════════════════════════════════════════════════
HIDDEN_IMPORTS = [
    # LangChain 相关
    "langchain",
    "langchain_core",
    "langchain_core.prompts",
    "langchain_core.language_models",
    "langchain_core.outputs",
    
    # Pydantic
    "pydantic",
    "pydantic.types",
    
    # Flask 扩展
    "flask",
    "flask.json",
    
    # HTTP 客户端
    "requests",
    "urllib3",
    
    # HTML 解析
    "bs4",  # beautifulsoup4 的导入名
    
    # 工具模块
    "dotenv",
    
    # 项目内部模块（确保打包）
    "src.agents.langchain_agents",
    "src.agents.langchain_llm",
    "src.agents.model_adapter",
    "src.agents.schemas",
    "src.utils.logger",
    "src.utils.search_utils",
    "src.utils.browser_utils",
    "src.utils.pdf_exporter",
]

# 根据打包模式添加可选依赖
if PACKAGING_MODE == "full":
    HIDDEN_IMPORTS.extend([
        "playwright",
        "playwright.async_api",
        "playwright.sync_api",
        "greenlet",  # Playwright依赖
        "DrissionPage",
    ])

# ═══════════════════════════════════════════════════════════
# 排除模块（不需要打包的模块，减少体积）
# ═══════════════════════════════════════════════════════════
EXCLUDED_MODULES = [
    # 测试工具
    "pytest",
    "unittest",
    "_pytest",
    
    # 开发工具
    "setuptools",
    "pip",
    "wheel",
    
    # 不需要的 GUI 库
    "tkinter",
    "PyQt5",
    "PySide2",
    
    # 科学计算库（AICouncil不需要）
    "torch",
    "torchvision",
    "torchaudio", 
    "pandas",
    "numpy",
    "scipy",
    "matplotlib",
    "PIL",
    "pillow",
    "cv2",
    "sklearn",
    "tensorflow",
    "keras",
    
    # 文档生成
    "sphinx",
    "docutils",
    
    # Jupyter
    "IPython",
    "jupyter",
    "notebook",
]

# ═══════════════════════════════════════════════════════════
# 图标和资源文件
# ═══════════════════════════════════════════════════════════
ICON_FILE = str(PROJECT_ROOT / "assets" / "senate.ico")  # 🏛️ 元老院图标

# ═══════════════════════════════════════════════════════════
# Windows 版本信息
# ═══════════════════════════════════════════════════════════
VERSION_INFO = {
    "version": APP_VERSION,
    "description": APP_DESCRIPTION,
    "copyright": APP_COPYRIGHT,
    "company": APP_AUTHOR,
    "product": APP_NAME,
}

# ═══════════════════════════════════════════════════════════
# UPX 配置
# ═══════════════════════════════════════════════════════════
# UPX 路径（如果未安装，设为 None）
UPX_DIR = None  # 自动检测系统 PATH 中的 UPX

# 不压缩的文件（某些库压缩后可能无法运行）
UPX_EXCLUDE = [
    "vcruntime140.dll",
    "python3*.dll",
]

# ═══════════════════════════════════════════════════════════
# 调试选项
# ═══════════════════════════════════════════════════════════
# 是否显示详细打包日志
DEBUG_MODE = True

# 是否清理临时文件
CLEAN_BUILD = True

# ═══════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════
def get_version_string():
    """获取版本信息字符串"""
    return f"{APP_NAME} v{APP_VERSION}"

def get_output_name():
    """获取输出文件名"""
    if BUNDLE_TYPE == "onefile":
        return f"{APP_NAME}.exe"
    else:
        return APP_NAME

def get_build_mode_description():
    """获取打包模式描述"""
    mode_desc = {
        "lightweight": "轻量级版本（延迟安装 Playwright）",
        "full": "完整功能版本（内嵌 Chromium）"
    }
    bundle_desc = {
        "onedir": "单目录模式",
        "onefile": "单文件模式"
    }
    return f"{mode_desc.get(PACKAGING_MODE, 'Unknown')} - {bundle_desc.get(BUNDLE_TYPE, 'Unknown')}"

# ═══════════════════════════════════════════════════════════
# 配置验证
# ═══════════════════════════════════════════════════════════
def validate_config():
    """验证配置有效性"""
    errors = []
    
    # 检查路径是否存在
    if not SRC_DIR.exists():
        errors.append(f"源码目录不存在: {SRC_DIR}")
    
    # 检查必要文件
    required_files = [
        SRC_DIR / "web" / "app.py",
        SRC_DIR / "agents" / "langchain_agents.py",
    ]
    for file in required_files:
        if not file.exists():
            errors.append(f"必需文件不存在: {file}")
    
    # 检查打包模式
    if PACKAGING_MODE not in ["lightweight", "full"]:
        errors.append(f"无效的打包模式: {PACKAGING_MODE}")
    
    if errors:
        print("❌ 配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("✅ 配置验证通过")
    return True

if __name__ == "__main__":
    print("═" * 60)
    print(f"  {get_version_string()}")
    print("═" * 60)
    print(f"打包模式: {get_build_mode_description()}")
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"源码目录: {SRC_DIR}")
    print(f"输出目录: {DIST_DIR}")
    print(f"使用 UPX: {'是' if USE_UPX else '否'}")
    print(f"控制台模式: {'是' if CONSOLE_MODE else '否'}")
    print("═" * 60)
    validate_config()
