#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包前检查工具
检查项目是否准备好进行打包
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


def print_header(title):
    """打印标题"""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print()


def check_dependencies():
    """检查核心依赖"""
    print_header("🔍 检查核心依赖")
    
    required = {
        "langchain": "必需",
        "flask": "必需",
        "requests": "必需",
        "bs4": "必需",
        "pydantic": "必需",
    }
    
    optional = {
        "playwright": "可选（PDF导出）",
        "DrissionPage": "可选（搜索增强）",
        "pyinstaller": "必需（打包）",
    }
    
    missing_required = []
    missing_optional = []
    
    print("核心依赖:")
    for pkg, desc in required.items():
        try:
            __import__(pkg)
            print(f"  ✅ {pkg:<20} {desc}")
        except ImportError:
            print(f"  ❌ {pkg:<20} {desc}")
            missing_required.append(pkg)
    
    print()
    print("可选依赖:")
    for pkg, desc in optional.items():
        try:
            __import__(pkg)
            print(f"  ✅ {pkg:<20} {desc}")
        except ImportError:
            print(f"  ⚠️  {pkg:<20} {desc} - 未安装")
            if pkg == "pyinstaller":
                missing_required.append(pkg)
            else:
                missing_optional.append(pkg)
    
    print()
    if missing_required:
        print(f"❌ 缺少必需依赖: {', '.join(missing_required)}")
        print(f"   请运行: pip install {' '.join(missing_required)}")
        return False
    
    if missing_optional:
        print(f"ℹ️  缺少可选依赖: {', '.join(missing_optional)}")
        print("   这不影响打包，但部分功能可能不可用")
    
    print("✅ 所有必需依赖已安装")
    return True


def check_files():
    """检查必要文件"""
    print_header("📁 检查必要文件")
    
    required_files = [
        "launcher.py",
        "aicouncil.spec",
        "build.py",
        "src/web/app.py",
        "src/config_defaults.py",
        "src/config_manager.py",
        "src/first_run_setup.py",
        "src/utils/path_manager.py",
    ]
    
    required_dirs = [
        "src/web/templates",
        "src/web/static",
        "src/web/static/vendor",
    ]
    
    missing = []
    
    print("必要文件:")
    for file_path in required_files:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists():
            size = full_path.stat().st_size / 1024
            print(f"  ✅ {file_path:<40} ({size:.1f} KB)")
        else:
            print(f"  ❌ {file_path:<40} 不存在")
            missing.append(file_path)
    
    print()
    print("必要目录:")
    for dir_path in required_dirs:
        full_path = PROJECT_ROOT / dir_path
        if full_path.exists() and full_path.is_dir():
            file_count = len(list(full_path.rglob('*')))
            print(f"  ✅ {dir_path:<40} ({file_count} 文件)")
        else:
            print(f"  ❌ {dir_path:<40} 不存在")
            missing.append(dir_path)
    
    print()
    if missing:
        print(f"❌ 缺少文件/目录: {len(missing)} 个")
        return False
    
    print("✅ 所有必要文件/目录存在")
    return True


def check_echarts():
    """检查 ECharts 文件"""
    print_header("📊 检查 ECharts")
    
    echarts_path = PROJECT_ROOT / "src/web/static/vendor/echarts.min.js"
    
    if echarts_path.exists():
        size = echarts_path.stat().st_size / (1024 * 1024)
        print(f"✅ ECharts 文件存在: {size:.2f} MB")
        return True
    else:
        print("❌ ECharts 文件不存在")
        print("   路径: src/web/static/vendor/echarts.min.js")
        print("   下载: https://registry.npmmirror.com/echarts/5.4.3/files/dist/echarts.min.js")
        return False


def check_config():
    """检查配置文件"""
    print_header("⚙️ 检查配置")
    
    config_template = PROJECT_ROOT / "src/config_template.py"
    config_file = PROJECT_ROOT / "src/config.py"
    
    if not config_template.exists():
        print("❌ config_template.py 不存在")
        return False
    
    print(f"✅ 配置模板: config_template.py")
    
    if config_file.exists():
        print(f"✅ 配置文件: config.py (已存在)")
    else:
        print(f"ℹ️  配置文件: config.py (打包后首次运行会创建)")
    
    return True


def estimate_size():
    """估算打包体积"""
    print_header("📦 估算打包体积")
    
    # 统计源码大小
    src_size = 0
    for file in (PROJECT_ROOT / "src").rglob("*.py"):
        src_size += file.stat().st_size
    
    # 统计静态资源
    static_size = 0
    static_dir = PROJECT_ROOT / "src/web/static"
    if static_dir.exists():
        for file in static_dir.rglob("*"):
            if file.is_file():
                static_size += file.stat().st_size
    
    # 统计模板
    template_size = 0
    template_dir = PROJECT_ROOT / "src/web/templates"
    if template_dir.exists():
        for file in template_dir.rglob("*"):
            if file.is_file():
                template_size += file.stat().st_size
    
    total_project = src_size + static_size + template_size
    
    print(f"源代码:     {src_size / (1024 * 1024):.2f} MB")
    print(f"静态资源:   {static_size / (1024 * 1024):.2f} MB")
    print(f"模板文件:   {template_size / (1024 * 1024):.2f} MB")
    print(f"项目总计:   {total_project / (1024 * 1024):.2f} MB")
    print()
    print("预估打包体积:")
    print(f"  最小版 (minimal):  ~80-120 MB")
    print(f"  完整版 (full):     ~150-250 MB")
    print()
    print("💡 实际大小取决于:")
    print("   - Python 解释器: ~40-60 MB")
    print("   - 依赖库: ~30-100 MB")
    print("   - Playwright (可选): ~150 MB")


def main():
    """主函数"""
    print()
    print("=" * 70)
    print("  🏛️ AICouncil 打包前检查")
    print("=" * 70)
    
    checks = [
        ("依赖检查", check_dependencies),
        ("文件检查", check_files),
        ("ECharts检查", check_echarts),
        ("配置检查", check_config),
    ]
    
    failed = []
    for name, check_func in checks:
        try:
            if not check_func():
                failed.append(name)
        except Exception as e:
            print(f"❌ {name} 检查失败: {e}")
            failed.append(name)
    
    # 体积估算（信息性）
    try:
        estimate_size()
    except Exception as e:
        print(f"⚠️ 体积估算失败: {e}")
    
    # 总结
    print()
    print("=" * 70)
    if failed:
        print("❌ 检查未通过")
        print()
        print("失败项目:")
        for item in failed:
            print(f"  - {item}")
        print()
        print("请修复上述问题后重新检查")
        return 1
    else:
        print("✅ 所有检查通过")
        print()
        print("准备就绪！可以执行打包:")
        print("  1. 安装 PyInstaller: pip install pyinstaller")
        print("  2. 运行构建脚本: python build.py")
        print()
        return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print("⚠️ 检查被用户中断")
        sys.exit(130)
    except Exception as e:
        print()
        print(f"❌ 检查过程发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
