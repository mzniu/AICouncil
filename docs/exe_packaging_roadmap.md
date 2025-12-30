# AICouncil 完整版 EXE 打包实施路线图

> **创建时间**: 2025-12-30  
> **目标**: 将 AICouncil 打包成独立可执行的 Windows EXE 文件  
> **原则**: 最小化对原有代码的侵入，保持开发环境兼容性

---

## 阶段零：准备工作（无代码改动）✅

### Step 0.1: 依赖审计
- [x] 检查 `requirements.txt`，标记可选依赖
- [x] 测试移除开发工具后功能是否正常
- [x] 创建 `requirements-runtime.txt`（打包专用）
- **影响**: 无 | **风险**: 极低 | **可回滚**: 完全

### Step 0.2: 创建打包配置文件
- [ ] 新建 `build/` 目录
- [ ] 创建 `build_config.py`（打包参数配置）
- [ ] 创建 `.spec` 文件草稿
- **影响**: 无（新增文件）| **风险**: 无 | **可回滚**: 删除即可

---

## 阶段一：资源路径抽象层（低侵入）🔧

### Step 1.1: 创建路径管理器
**新增文件**: `src/utils/path_manager.py`

**功能**:
- `get_resource_path(relative_path)` → 兼容开发/打包环境
- `get_user_data_dir()` → 用户配置/工作空间目录
- `is_frozen()` → 检测是否在打包环境运行

**实现原理**:
```python
def get_resource_path(relative_path):
    """自动检测运行环境"""
    if getattr(sys, 'frozen', False):
        # 打包环境：从 _MEIPASS 读取
        base_path = sys._MEIPASS
    else:
        # 开发环境：使用相对路径（原有逻辑）
        base_path = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)
```

- **影响**: 无（新增模块）| **风险**: 无 | **可回滚**: 删除文件

### Step 1.2: 替换静态资源路径（中等侵入）
**修改文件**:
- `src/web/app.py`: Flask `static_folder`/`template_folder`
- `src/agents/langchain_agents.py`: 报告模板路径
- `src/utils/search_utils.py`: 浏览器路径（如需要）

**改动示例**:
```python
# 改动前
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# 改动后
from src.utils.path_manager import get_resource_path
app = Flask(__name__, 
            template_folder=get_resource_path('src/web/templates'),
            static_folder=get_resource_path('src/web/static'))
```

- **影响**: 3-4个文件，~10处路径 | **风险**: 低 | **可回滚**: Git revert

### Step 1.3: 工作空间目录迁移
**修改内容**:
- `workspaces/` → `%APPDATA%/AICouncil/workspaces/`（仅打包环境）
- 添加首次运行检测，自动创建目录结构

**实现**:
```python
def get_workspace_dir():
    if getattr(sys, 'frozen', False):
        # 打包环境：用户目录
        return os.path.join(os.getenv('APPDATA'), 'AICouncil', 'workspaces')
    else:
        # 开发环境：项目根目录（原有逻辑）✅
        return os.path.join(os.getcwd(), 'workspaces')
```

- **影响**: `demo_runner.py`、`app.py` | **风险**: 低 | **可回滚**: 改回相对路径

---

## 阶段二：配置系统重构（中等侵入）⚙️

### Step 2.1: 配置文件分离
**新增**:
- `src/config_defaults.py`（默认配置，打包进 EXE）
- `%APPDATA%/AICouncil/config.py`（用户配置）

**修改**:
- 现有代码从 `config.py` 导入 → 改为 `ConfigManager` 类

**配置查找优先级**:
```python
CONFIG_SEARCH_PATHS = [
    "%APPDATA%/AICouncil/config.py",     # 优先级1：用户配置（打包环境）
    "./src/config.py",                   # 优先级2：源码配置（开发环境）✅
    sys._MEIPASS + "/config_defaults.py" # 优先级3：默认配置（打包环境）
]
```

- **影响**: 所有导入 config 的模块（~8个文件）| **风险**: 中 | **可回滚**: 保留旧 config.py

### Step 2.2: 首次运行向导
**新增文件**: `src/utils/first_run_setup.py`

**功能**:
- 检测 `config.py` 是否存在
- 不存在 → 复制 `config_defaults.py` 并提示配置
- 可选：简单的命令行配置界面

- **影响**: `app.py` 启动流程 | **风险**: 低 | **可回滚**: 跳过检测逻辑

---

## 阶段三：依赖优化（中等影响）📦

### Step 3.1: Playwright 策略选择

#### 选项 A（推荐）：延迟安装
- 首次导出 PDF 时检测 Playwright
- 未安装 → 提示用户运行 `install_playwright.bat`
- **优点**: 体积小（~100MB）
- **缺点**: 首次使用需联网

#### 选项 B：完整打包
- 手动复制 Chromium 到 `_internal/`
- 修改 Playwright 查找路径
- **优点**: 离线可用
- **缺点**: 体积大（+150MB）

- **影响**: `pdf_exporter.py` | **风险**: 中 | **可回滚**: 恢复原检测逻辑

### Step 3.2: 搜索引擎简化（可选）
**如果选择减小体积**:
- 移除 DrissionPage 依赖
- Baidu/Bing 改为纯 Requests 实现
- 或仅保留 Yahoo/Mojeek/DuckDuckGo

- **影响**: `search_utils.py` | **风险**: 低 | **可回滚**: 保留原实现作为备份

---

## 阶段四：PyInstaller 集成（新增为主）🎁

### Step 4.1: 创建 .spec 文件
**新增文件**: `aicouncil.spec`

**配置内容**:
- 入口点：`src/web/app.py`
- 数据文件（datas）：templates、static、echarts.min.js
- 隐藏导入（hiddenimports）：动态导入的模块
- 配置图标、版本信息

- **影响**: 无（构建配置）| **风险**: 无 | **可回滚**: 删除文件

### Step 4.2: 创建构建脚本
**新增文件**: `build.py`

**功能**:
- 自动化打包流程
- 清理临时文件
- 复制必要资源
- 生成发布压缩包

- **影响**: 无（辅助脚本）| **风险**: 无 | **可回滚**: 删除文件

### Step 4.3: 创建启动器包装
**新增文件**: `launcher.py`（真正的入口）

**功能**:
- 检查环境（首次运行设置）
- 启动 Flask 服务器
- 自动打开浏览器
- 添加托盘图标（可选）

- **影响**: 无（新模块）| **风险**: 低 | **可回滚**: 直接运行 app.py

---

## 阶段五：测试与优化（验证为主）🧪

### Step 5.1: 打包测试
- 构建 EXE（单目录模式）
- 在纯净 Windows 环境测试
- 验证所有功能：启动、讨论、PDF、搜索
- 记录问题和缺失依赖

- **影响**: 无 | **风险**: 无 | **可回滚**: 不适用

### Step 5.2: 体积优化
- 启用 UPX 压缩
- 排除不必要的库（如 tkinter）
- 测试单文件模式（可选）
- 比较体积和性能

- **影响**: `.spec` 配置 | **风险**: 低 | **可回滚**: 修改 .spec

### Step 5.3: 用户体验优化
- 添加启动画面（splash screen）
- 改进首次运行引导
- 添加桌面快捷方式创建
- 编写用户手册

- **影响**: `launcher.py` | **风险**: 极低 | **可回滚**: 移除新增代码

---

## 阶段六：发布准备（文档为主）📝

### Step 6.1: 安装程序（可选）
使用 **Inno Setup** 或 **NSIS**:
- 创建安装向导
- 注册卸载程序
- 创建开始菜单快捷方式

- **影响**: 无（独立工具）| **风险**: 无 | **可回滚**: 不适用

### Step 6.2: 文档更新
**新增/修改**:
- `docs/build_guide.md`（构建说明）
- `docs/user_manual.md`（用户手册）
- `README.md`（添加下载链接）

- **影响**: 文档 | **风险**: 无 | **可回滚**: Git revert

---

## 风险矩阵

| 阶段 | 代码改动量 | 风险等级 | 回滚难度 | 预计耗时 |
|------|----------|---------|---------|---------|
| 0 - 准备 | 0行 | ⭐ 无风险 | 零 | 1小时 |
| 1 - 路径抽象 | ~50行 | ⭐⭐ 低 | 易 | 3-4小时 |
| 2 - 配置重构 | ~100行 | ⭐⭐⭐ 中 | 中等 | 4-6小时 |
| 3 - 依赖优化 | ~80行 | ⭐⭐ 低 | 易 | 2-3小时 |
| 4 - 打包集成 | ~200行（新增为主）| ⭐⭐ 低 | 易 | 6-8小时 |
| 5 - 测试优化 | ~50行 | ⭐ 低 | 易 | 4-6小时 |
| 6 - 发布准备 | 文档为主 | ⭐ 无风险 | 零 | 2-3小时 |

**总计**: ~480行新增代码，~22-31小时（3-4个工作日）

---

## 关键设计原则

✅ **每步可独立测试** - 每个阶段完成后都能正常运行  
✅ **向后兼容** - 开发环境不受影响，可同时维护  
✅ **渐进式迁移** - 先新增抽象层，再替换调用点  
✅ **失败安全** - 打包失败不影响源码正常运行  

---

## 打包方案对比

### 方案A：轻量级版本 (~100MB)
**移除依赖**:
- pytest（开发工具）
- python-dotenv（如果未使用）

**延迟安装**:
- playwright（首次PDF导出时提示）
- DrissionPage（简化搜索引擎）

**保留功能**:
- ✅ 核心讨论流程
- ✅ 多模型支持
- ✅ HTML报告生成
- ⚠️ PDF导出（降级到jsPDF或提示安装）
- ⚠️ 搜索（仅Yahoo/Mojeek/DuckDuckGo）

### 方案B：完整功能版本 (~250MB) - **推荐**
**移除依赖**:
- pytest（开发工具）

**内嵌打包**:
- playwright + Chromium（~170MB）
- DrissionPage（保留浏览器搜索）

**保留功能**:
- ✅ 所有功能完整可用
- ✅ 离线PDF导出
- ✅ 完整搜索引擎支持

---

## 执行顺序建议

### 快速验证路线（2天）
```
Step 0.1 → 0.2 → 1.1 → 4.1 → 4.2 → 5.1
（跳过配置重构，仅验证打包可行性）
```

### 完整实施路线（4天）- **推荐**
```
按阶段顺序执行所有步骤
每个阶段结束后 Git commit
遇到问题可回滚到上一阶段
```

---

## 开发体验保证

### ✅ 团队协作不受影响
```bash
git clone https://github.com/xxx/AICouncil.git
cd AICouncil
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python src/web/app.py  # 完全正常运行
```

### ✅ 调试方式不变
```bash
# 仍然可以打断点、修改代码、即时生效
python -m pdb src/web/app.py
```

### ✅ 测试命令不变
```bash
pytest tests/
python tests/test_playwright_pdf.py
```

---

## 实际使用对比

| 操作 | 开发环境（改动后） | 打包后 EXE |
|------|------------------|-----------|
| **启动方式** | `python src/web/app.py` ✅ | 双击 `AICouncil.exe` |
| **配置文件** | 编辑 `src/config.py` ✅ | 编辑 `%APPDATA%/AICouncil/config.py` |
| **工作空间** | `./workspaces/` ✅ | `%APPDATA%/AICouncil/workspaces/` |
| **静态资源** | `src/web/static/` ✅ | 内嵌在 EXE |
| **依赖安装** | `pip install -r requirements.txt` ✅ | 不需要（已内嵌）|
| **浏览器** | 系统 Chrome/Edge ✅ | 内嵌 Chromium 或系统浏览器 |

---

## 核心承诺

🎯 **零破坏性改动**

- 所有新代码都是 **"加法"**，不是 **"减法"**
- 通过 **环境检测** 自动适配运行模式
- 开发环境永远走 **原有逻辑分支**
- 改动前后对比：
  - Git 改动文件数：~10个
  - 破坏性修改：**0处**
  - 新增抽象层：~5个模块
  - 开发命令变化：**无**

随时可以回滚：
```bash
git checkout -- .  # 回滚到改动前
python src/web/app.py  # 立即恢复正常
```

---

## 附录：技术栈说明

- **打包工具**: PyInstaller 5.x
- **目标平台**: Windows 10/11 (x64)
- **Python 版本**: 3.9+
- **压缩工具**: UPX 4.x（可选）
- **安装制作**: Inno Setup 6.x（可选）
