#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AICouncil 构建脚本
自动化 PyInstaller 打包流程
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
SPEC_FILE = PROJECT_ROOT / "aicouncil.spec"


def print_header(title):
    """打印标题"""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print()


def clean_build():
    """清理旧的构建文件"""
    print_header("🧹 清理旧构建文件")
    
    dirs_to_clean = [
        BUILD_DIR / "aicouncil",
        DIST_DIR,
        PROJECT_ROOT / "__pycache__",
    ]
    
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            print(f"删除: {dir_path}")
            shutil.rmtree(dir_path)
    
    print("✅ 清理完成")


def check_dependencies():
    """检查依赖"""
    print_header("🔍 检查依赖")
    
    required = [('PyInstaller', 'pyinstaller')]
    missing = []
    
    for import_name, display_name in required:
        try:
            __import__(import_name)
            print(f"✅ {display_name}")
        except ImportError:
            print(f"❌ {display_name} (未安装)")
            missing.append(display_name)
    
    if missing:
        print()
        print("⚠️ 缺少依赖，请运行：")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True


def run_pyinstaller(mode="onedir"):
    """运行 PyInstaller"""
    print_header(f"🔨 开始打包 ({mode} 模式)")
    
    if not SPEC_FILE.exists():
        print(f"❌ spec 文件不存在: {SPEC_FILE}")
        return False
    
    # 设置环境变量
    env = os.environ.copy()
    env['PYTHONOPTIMIZE'] = '1'  # 优化字节码
    
    # 构建命令
    cmd = [
        sys.executable,
        '-m', 'PyInstaller',
        str(SPEC_FILE),
        '--clean',  # 清理缓存
        '--noconfirm',  # 不询问覆盖
    ]
    
    print(f"命令: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            env=env,
            check=True,
            text=True
        )
        print()
        print("✅ 打包完成")
        return True
        
    except subprocess.CalledProcessError as e:
        print()
        print(f"❌ 打包失败: {e}")
        return False


def check_output():
    """检查输出文件"""
    print_header("📦 检查输出")
    
    # 查找输出目录
    output_dirs = list(DIST_DIR.glob("AICouncil*"))
    
    if not output_dirs:
        print("❌ 未找到输出目录")
        return False
    
    output_dir = output_dirs[0]
    print(f"输出目录: {output_dir}")
    print()
    
    # 查找可执行文件
    exe_files = list(output_dir.glob("*.exe"))
    
    if not exe_files:
        print("❌ 未找到可执行文件")
        return False
    
    exe_file = exe_files[0]
    size_mb = exe_file.stat().st_size / (1024 * 1024)
    
    print(f"可执行文件: {exe_file.name}")
    print(f"文件大小: {size_mb:.2f} MB")
    print()
    
    # 统计目录大小
    total_size = sum(f.stat().st_size for f in output_dir.rglob('*') if f.is_file())
    total_mb = total_size / (1024 * 1024)
    
    print(f"总大小: {total_mb:.2f} MB")
    print()
    
    # 列出主要文件
    print("主要文件:")
    important_files = [
        "*.exe",
        "*.dll",
        "_internal/",
    ]
    
    for pattern in important_files:
        files = list(output_dir.glob(pattern))
        for f in files[:5]:  # 只显示前5个
            if f.is_file():
                f_size = f.stat().st_size / (1024 * 1024)
                print(f"  - {f.name} ({f_size:.2f} MB)")
            elif f.is_dir():
                print(f"  - {f.name}/ (目录)")
    
    print()
    print("✅ 输出检查完成")
    return True


def create_release_package():
    """创建发布压缩包（可选）"""
    print_header("📦 创建发布包")
    
    output_dirs = list(DIST_DIR.glob("AICouncil*"))
    if not output_dirs:
        print("⚠️ 未找到输出目录，跳过")
        return False
    
    output_dir = output_dirs[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"AICouncil_{timestamp}"
    
    print(f"创建压缩包: {zip_name}.zip")
    
    try:
        shutil.make_archive(
            str(DIST_DIR / zip_name),
            'zip',
            output_dir.parent,
            output_dir.name
        )
        
        zip_file = DIST_DIR / f"{zip_name}.zip"
        zip_size = zip_file.stat().st_size / (1024 * 1024)
        
        print(f"✅ 压缩包已创建: {zip_file.name} ({zip_size:.2f} MB)")
        return True
        
    except Exception as e:
        print(f"⚠️ 创建压缩包失败: {e}")
        return False


def main():
    """主函数"""
    print()
    print("=" * 70)
    print("  🏛️ AICouncil 打包工具")
    print("=" * 70)
    print()
    
    # 1. 检查依赖
    if not check_dependencies():
        return 1
    
    # 2. 清理旧文件
    clean_build()
    
    # 3. 运行打包
    if not run_pyinstaller():
        return 1
    
    # 4. 检查输出
    if not check_output():
        return 1
    
    # 5. 创建发布包（可选）
    try:
        create_release_package()
    except Exception as e:
        print(f"⚠️ 创建发布包时出错（非致命）: {e}")
    
    # 完成
    print_header("🎉 构建完成")
    print("下一步：")
    print("  1. 测试 dist/ 目录中的可执行文件")
    print("  2. 在纯净环境中验证功能")
    print("  3. 检查是否缺少依赖或资源")
    print()
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print()
        print("⚠️ 构建被用户中断")
        sys.exit(130)
    except Exception as e:
        print()
        print(f"❌ 构建过程发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
