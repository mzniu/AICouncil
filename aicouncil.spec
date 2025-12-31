# -*- mode: python ; coding: utf-8 -*-
"""
AICouncil PyInstaller 配置文件（.spec）
生成时间: 2025-12-30
说明: 此文件用于 PyInstaller 打包，定义了所有打包参数
"""

import sys
import os
from pathlib import Path
import importlib.util

# 导入构建配置（避免与 build.py 冲突）
build_config_path = Path.cwd() / 'build' / 'build_config.py'
spec = importlib.util.spec_from_file_location("build_config", build_config_path)
build_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_config)

# 导入配置常量
APP_VERSION = build_config.APP_VERSION
APP_NAME = build_config.APP_NAME
PACKAGING_MODE = build_config.PACKAGING_MODE
BUNDLE_TYPE = build_config.BUNDLE_TYPE
PROJECT_ROOT = build_config.PROJECT_ROOT
SRC_DIR = build_config.SRC_DIR
DATA_FILES = build_config.DATA_FILES
HIDDEN_IMPORTS = build_config.HIDDEN_IMPORTS
EXCLUDED_MODULES = build_config.EXCLUDED_MODULES
ICON_FILE = build_config.ICON_FILE
DEBUG_MODE = build_config.DEBUG_MODE
USE_UPX = build_config.USE_UPX
UPX_EXCLUDE = build_config.UPX_EXCLUDE
CONSOLE_MODE = build_config.CONSOLE_MODE

# 导入辅助函数
get_output_name = build_config.get_output_name
get_version_string = build_config.get_version_string
get_build_mode_description = build_config.get_build_mode_description

# ═══════════════════════════════════════════════════════════
# Analysis 阶段：分析依赖
# ═══════════════════════════════════════════════════════════
block_cipher = None

a = Analysis(
    # 入口脚本（launcher.py 提供友好启动体验）
    ['launcher.py'],
    
    # 搜索路径
    pathex=[str(PROJECT_ROOT), str(SRC_DIR)],
    
    # 二进制文件
    binaries=[],
    
    # 数据文件
    datas=DATA_FILES,
    
    # 隐藏导入
    hiddenimports=HIDDEN_IMPORTS,
    
    # Hook 文件目录
    hookspath=[],
    
    # Hook 运行时
    hooksconfig={},
    
    # 运行时 Hook
    runtime_hooks=[],
    
    # 排除的模块
    excludes=EXCLUDED_MODULES,
    
    # 加密选项
    cipher=block_cipher,
    
    # 不压缩的库
    noarchive=False,
)

# ═══════════════════════════════════════════════════════════
# PYZ 阶段：压缩 Python 模块
# ═══════════════════════════════════════════════════════════
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

# ═══════════════════════════════════════════════════════════
# EXE 阶段：生成可执行文件
# ═══════════════════════════════════════════════════════════
if BUNDLE_TYPE == "onefile":
    # 单文件模式
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=get_output_name(),
        debug=DEBUG_MODE,
        bootloader_ignore_signals=False,
        strip=False,
        upx=USE_UPX,
        upx_exclude=UPX_EXCLUDE,
        runtime_tmpdir=None,
        console=CONSOLE_MODE,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON_FILE,
    )
else:
    # 单目录模式（推荐）
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=get_output_name(),
        debug=DEBUG_MODE,
        bootloader_ignore_signals=False,
        strip=False,
        upx=USE_UPX,
        console=CONSOLE_MODE,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON_FILE,
    )
    
    # COLLECT 阶段：收集所有文件到输出目录
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=USE_UPX,
        upx_exclude=UPX_EXCLUDE,
        name=APP_NAME,
    )

# ═══════════════════════════════════════════════════════════
# 打包信息输出
# ═══════════════════════════════════════════════════════════
print("\n" + "═" * 60)
print(f"  {get_version_string()} - PyInstaller 配置")
print("═" * 60)
print(f"入口脚本: src/web/app.py")
print(f"打包模式: {get_build_mode_description()}")
print(f"输出名称: {get_output_name()}")
print(f"数据文件数量: {len(DATA_FILES)}")
print(f"隐藏导入数量: {len(HIDDEN_IMPORTS)}")
print(f"排除模块数量: {len(EXCLUDED_MODULES)}")
print("═" * 60 + "\n")
