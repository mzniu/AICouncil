"""
测试 Playwright 自动安装功能
"""
import sys
import pathlib

# 添加项目根目录到 sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.playwright_installer import (
    is_playwright_installed,
    install_playwright,
    get_playwright_install_path
)
from src.utils.pdf_exporter import PLAYWRIGHT_AVAILABLE

print("=" * 60)
print("  Playwright 安装测试工具")
print("=" * 60)
print()

# 1. 检查当前状态
print("1. 检查当前安装状态...")
print(f"   - Playwright 包已导入: {PLAYWRIGHT_AVAILABLE}")
print(f"   - 浏览器已安装: {is_playwright_installed()}")
print(f"   - 安装路径: {get_playwright_install_path()}")
print()

# 2. 如果未安装，提供安装选项
if not is_playwright_installed():
    print("2. Playwright 未完整安装")
    choice = input("   是否立即安装？(y/n): ").strip().lower()
    
    if choice == 'y':
        print()
        print("开始安装 Playwright + Chromium...")
        print("（约 150MB，需要 2-5 分钟）")
        print("-" * 60)
        
        def progress_callback(msg):
            print(f"  {msg}")
        
        success = install_playwright(callback=progress_callback)
        
        print("-" * 60)
        if success:
            print()
            print("✅ 安装成功！")
            print()
            print("验证:")
            print(f"   - 浏览器已安装: {is_playwright_installed()}")
        else:
            print()
            print("❌ 安装失败，请查看日志")
    else:
        print("   跳过安装")
else:
    print("2. ✅ Playwright 已完整安装，可以使用 PDF 导出功能")

print()
print("=" * 60)
print("测试完成")
print("=" * 60)
