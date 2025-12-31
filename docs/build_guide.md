# AICouncil 构建指南

本文档介绍如何从源代码构建 AICouncil 的可执行文件（EXE）。

---

## 📋 目录

- [前置要求](#前置要求)
- [快速开始](#快速开始)
- [构建步骤](#构建步骤)
- [构建配置](#构建配置)
- [常见问题](#常见问题)
- [高级选项](#高级选项)

---

## 前置要求

### 系统要求
- **操作系统**: Windows 10/11 (64位)
- **Python**: 3.9 或更高版本
- **磁盘空间**: 至少 2GB 可用空间
- **内存**: 建议 4GB 以上

### 软件依赖
```bash
# 1. 安装核心依赖
pip install -r requirements.txt

# 或精简安装（更小体积）
pip install -r requirements-minimal.txt

# 2. 安装打包工具
pip install pyinstaller

# 3. (可选) 安装增强功能
pip install -r requirements-optional.txt
```

---

## 快速开始

### 一键构建
```bash
# 1. 进入项目目录
cd AICouncil

# 2. 运行构建脚本
python build.py
```

构建完成后，可执行文件位于 `dist/AICouncil/` 目录。

---

## 构建步骤

### Step 1: 检查构建准备
在开始构建前，建议先运行检查工具：

```bash
python check_packaging.py
```

检查内容包括：
- ✅ 核心依赖是否安装
- ✅ 必要文件是否完整
- ✅ ECharts 资源是否存在
- ✅ 配置文件是否正确
- 📦 体积估算

**示例输出**：
```
======================================================================
  🏛️ AICouncil 打包前检查
======================================================================

✅ 核心依赖: langchain, flask, requests, bs4, pydantic
✅ 所有必要文件/目录存在
✅ ECharts 文件存在: 0.98 MB
✅ 配置检查通过

预估打包体积:
  最小版 (minimal):  ~80-120 MB
  完整版 (full):     ~150-250 MB
```

### Step 2: 配置构建参数（可选）

编辑 `build/build_config.py` 自定义构建：

```python
# 应用信息
APP_NAME = "AICouncil"
APP_VERSION = "1.0.0"

# 打包模式
BUNDLE_TYPE = "onedir"  # 或 "onefile"
PACKAGING_MODE = "minimal"  # 或 "full"

# 优化选项
USE_UPX = True  # 启用 UPX 压缩
CONSOLE_MODE = False  # 隐藏控制台窗口
DEBUG_MODE = False  # 关闭调试模式
```

### Step 3: 执行构建

```bash
python build.py
```

构建过程包括：
1. 🧹 清理旧构建文件
2. 🔍 检查依赖
3. 🔨 运行 PyInstaller
4. 📦 检查输出文件
5. 📦 创建发布压缩包（可选）

**构建时间**: 约 5-15 分钟（取决于机器性能）

### Step 4: 验证构建产物

```bash
# 进入输出目录
cd dist/AICouncil

# 运行可执行文件
./AICouncil.exe
```

程序应该：
- ✅ 自动打开控制台窗口（首次运行）
- ✅ 显示欢迎信息和配置引导
- ✅ 启动 Flask 服务器
- ✅ 自动在浏览器打开 Web 界面

---

## 构建配置

### 打包模式

#### 单目录模式（推荐）
```python
BUNDLE_TYPE = "onedir"
```

**特点**：
- ✅ 启动速度快
- ✅ 更新方便（只需替换部分文件）
- ✅ 调试友好
- ❌ 多个文件/文件夹

**目录结构**：
```
AICouncil/
├── AICouncil.exe          # 主程序
├── _internal/             # 依赖文件
│   ├── python39.dll
│   ├── *.pyd
│   └── ...
└── workspaces/            # 数据目录（首次运行创建）
```

#### 单文件模式
```python
BUNDLE_TYPE = "onefile"
```

**特点**：
- ✅ 单个 EXE 文件
- ✅ 分发方便
- ❌ 首次启动慢（需解压）
- ❌ 体积较大

### 依赖级别

#### 最小依赖（推荐）
```python
PACKAGING_MODE = "minimal"
```

**包含**：
- Python 解释器
- 核心依赖（langchain, flask, requests, bs4, pydantic）
- Web 界面资源
- ECharts 图表库

**体积**: ~80-120 MB

**不包含**：
- ❌ Playwright（PDF 高质量导出）
- ❌ DrissionPage（Baidu/Bing 搜索增强）

**适用场景**：
- 内存/磁盘受限环境
- 仅使用 Yahoo/Mojeek/DuckDuckGo 搜索
- 使用浏览器导出 PDF（传统方式）

#### 完整依赖
```python
PACKAGING_MODE = "full"
```

**额外包含**：
- ✅ Playwright（PDF 导出）
- ✅ DrissionPage（浏览器搜索）

**体积**: ~150-250 MB

### 优化选项

#### UPX 压缩
```python
USE_UPX = True
```

- 减少 30-50% 体积
- 需安装 UPX: https://upx.github.io/
- 可能触发部分杀毒软件误报

#### 控制台窗口
```python
CONSOLE_MODE = False  # 隐藏控制台
CONSOLE_MODE = True   # 显示控制台（方便调试）
```

---

## 常见问题

### Q1: PyInstaller 打包失败
**错误**: `ModuleNotFoundError: No module named 'xxx'`

**解决**：
1. 检查依赖是否安装：`pip list`
2. 添加到隐藏导入（`build_config.py`）：
   ```python
   HIDDEN_IMPORTS = [
       # ... 现有模块
       "missing_module_name",
   ]
   ```

### Q2: 打包后运行出错
**错误**: 缺少配置文件或资源

**解决**：
1. 检查 `DATA_FILES` 是否包含所需文件
2. 确保资源文件路径正确：
   ```python
   DATA_FILES = [
       (str(SRC_DIR / "web/templates"), "src/web/templates"),
       (str(SRC_DIR / "web/static"), "src/web/static"),
   ]
   ```

### Q3: EXE 被杀毒软件拦截
**原因**: PyInstaller 打包的程序可能被误报

**解决**：
1. 关闭 UPX 压缩：`USE_UPX = False`
2. 添加到杀毒软件白名单
3. 使用代码签名证书（推荐）

### Q4: 首次启动很慢
**原因**: 单文件模式需解压到临时目录

**解决**：
- 使用单目录模式：`BUNDLE_TYPE = "onedir"`
- 或添加启动画面提示用户等待

### Q5: 路径相关错误
**错误**: 找不到配置文件/工作空间

**检查**：
- `path_manager.py` 是否正确检测环境
- 打包环境使用 `%APPDATA%/AICouncil/`
- 开发环境使用 `./workspaces/`

---

## 高级选项

### 自定义图标
```python
# build_config.py
ICON_FILE = str(PROJECT_ROOT / "assets" / "icon.ico")
```

要求：
- 格式：`.ico` (Windows)
- 尺寸：256x256 或多尺寸
- 工具：[IcoFX](https://icofx.ro/), [RealWorld Paint](http://www.rw-designer.com/)

### 版本信息
```python
VERSION_INFO = {
    "version": "1.0.0",
    "description": "AI Council - Multi-Agent Deliberation System",
    "copyright": "Copyright (C) 2024-2025",
    "company": "AICouncil Team",
}
```

### 排除不需要的模块
减少体积，排除不使用的库：

```python
EXCLUDED_MODULES = [
    "pytest",      # 测试工具
    "tkinter",     # GUI 库
    "matplotlib",  # 图表库（如果不用）
]
```

### 创建安装程序（可选）

使用 **Inno Setup**:

1. 下载：https://jrsoftware.org/isinfo.php
2. 创建 `installer.iss` 脚本
3. 编译生成 `AICouncil_Setup.exe`

**优点**：
- 专业的安装/卸载流程
- 创建开始菜单快捷方式
- 关联文件类型
- 检查系统要求

---

## 构建产物

### 目录结构
```
dist/
└── AICouncil/              # 主输出目录
    ├── AICouncil.exe       # 可执行文件
    ├── _internal/          # 依赖库
    │   ├── python39.dll
    │   ├── base_library.zip
    │   └── ... (其他 DLL 和 PYD)
    └── (首次运行后创建)
        ├── config.py       # 用户配置（%APPDATA%）
        └── workspaces/     # 工作空间（%APPDATA%）
```

### 文件清单
| 文件/目录 | 大小 | 说明 |
|----------|------|------|
| `AICouncil.exe` | 5-10 MB | 启动器 |
| `_internal/` | 70-200 MB | Python 运行时 + 依赖 |
| `config.py` | ~2 KB | 配置文件（首次运行创建）|
| `workspaces/` | 动态 | 讨论数据（用户数据）|

---

## 分发准备

### 创建发布包
```bash
# 自动创建 ZIP
python build.py  # 会自动生成 AICouncil_YYYYMMDD_HHMMSS.zip
```

### 上传到 GitHub Release
1. 创建 Git Tag：`git tag v1.0.0`
2. 推送 Tag：`git push origin v1.0.0`
3. 在 GitHub 创建 Release
4. 上传 `AICouncil_*.zip`

### README 更新
添加下载链接：
```markdown
## 📦 下载

- [Windows 版本](https://github.com/mzniu/AICouncil/releases/latest)
- 解压后运行 `AICouncil.exe`
```

---

## 技术细节

### PyInstaller 工作原理
1. **分析阶段**: 扫描入口脚本，分析依赖
2. **收集阶段**: 收集 Python 模块、C 扩展、数据文件
3. **打包阶段**: 创建 bootloader + 打包资源
4. **输出阶段**: 生成可执行文件

### 路径管理
- 使用 `sys._MEIPASS` 获取打包后资源路径
- 开发环境：`__file__` 相对路径
- 打包环境：临时解压目录

### 首次运行流程
1. 检测 `%APPDATA%/AICouncil/config.py` 是否存在
2. 不存在 → 复制 `config_defaults.py`
3. 提示用户配置 API 密钥
4. 启动 Flask 服务器
5. 打开浏览器

---

## 参考资源

- [PyInstaller 官方文档](https://pyinstaller.org/en/stable/)
- [UPX 压缩工具](https://upx.github.io/)
- [Inno Setup 官网](https://jrsoftware.org/isinfo.php)
- [AICouncil 项目仓库](https://github.com/mzniu/AICouncil)

---

## 联系与支持

如有问题或建议，请：
- 提交 Issue: https://github.com/mzniu/AICouncil/issues
- 查看文档: [docs/](../docs/)
- 运行检查: `python check_packaging.py`

---

*最后更新: 2025-12-30*
