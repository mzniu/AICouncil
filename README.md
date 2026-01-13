# 🏛️ AI 元老院 (AICouncil)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)

中文 | [English](README_EN.md)

**AICouncil** 是一个基于大语言模型（LLM）的多智能体协作决策系统。它模拟了古代元老院的议事流程，通过多个不同职责的 AI 智能体（议长、策论家、监察官、记录员）进行多轮辩论、质疑与汇总，最终为复杂问题提供深度、客观且多维度的决策建议。

---

## 🌟 核心特性

- **🔐 企业级认证系统**：
  - **用户注册与登录**：支持公开注册（可配置禁用）、密码强度策略、账户锁定机制。
  - **多因素认证 (MFA)**：基于 TOTP (RFC 6238) 的双因素认证，支持 Google Authenticator / Microsoft Authenticator 等应用。
  - **备份码系统**：每个用户生成 10 个一次性备份码，丢失设备时可用备份码登录。
  - **会话管理**：支持"记住我"功能、会话版本控制（登出所有设备）、安全 Cookie 配置。
  - **审计日志**：完整记录登录历史（成功/失败/IP/User-Agent），支持安全审计。
  - **详细文档**：参见 [认证系统文档](docs/authentication.md)。
- **🎭 多角色协同**：
  - **议长 (Leader)**：负责议题拆解、流程引导及最终报告汇总。
  - **策论家 (Planner)**：基于搜索增强（RAG）提供专业方案与深度见解。
  - **监察官 (Auditor)**：对策论家的方案进行批判性审查，指出潜在风险与漏洞。
  - **质疑官 (Devil's Advocate)**：扮演"红队"角色，挑战议长的假设与逻辑，识别盲点，强制进行闭环修正。
  - **记录员 (Reporter)**：实时记录议事过程，确保信息不遗漏。
- **🔍 增强型搜索**：集成 **Google**（官方 API）、Bing、Baidu、DuckDuckGo、Yahoo、Mojeek 等多引擎并行搜索。采用 **Requests-First** 架构，优先通过轻量级请求获取数据，并具备**智能相关性校验**与**查询优化**功能（自动识别并规避搜索引擎的无关热点干扰）。**Google Custom Search API** 提供高质量搜索结果，国内可直接访问（免费 100 次/天）。其中 Yahoo、Mojeek 和 Google 为纯 HTTP 实现，无需浏览器依赖，运行更稳定。
- **💻 实时监控面板**：基于 Flask 的 Web 界面，实时展示智能体思考过程、搜索进度及辩论流。支持窗口**最大化/还原**，方便深度阅读。
- **📄 深度报告生成**：自动生成结构化的 HTML 议事报告，支持一键复制、**整合式下载菜单**（支持 HTML / 长图 / PDF）。
- **📊 丰富的图表支持**：报告支持 **ECharts** 数据可视化（柱状图、饼图、雷达图等）和 **Mermaid** 流程图（流程图、时序图、甘特图、类图、状态图等）。所有图表库均本地化部署（/static/vendor/），避免 CDN 依赖，离线和 iframe 场景均可用。
- **📜 历史管理**：完整的会话持久化，支持随时回溯、加载或删除历史议事记录。
- **💾 阵型预设**：支持保存、加载和管理常用的元老院配置（包括后端模型、议事轮数、智能体数量等），方便快速启动不同场景的议事。
- **✋ 用户介入**：支持在议事过程中随时输入指令，实时引导智能体的讨论方向。
- **📊 进度可视化**：实时显示当前议事轮数及详细状态。进度条逻辑经过优化，议事结束即达 100%，无需等待报告生成。
- **🤖 广泛的模型支持**：原生支持 **DeepSeek**、**OpenAI**、**Azure OpenAI**（中国区/全球区）、**Anthropic (Claude)**、**Google Gemini**、**Aliyun (Qwen)**、**OpenRouter** 及本地 **Ollama** 模型。
- **🧭 议事编排官（Deliberation Orchestrator）智能编排**（新功能）：根据需求自动选择最优讨论框架（罗伯特议事规则/图尔敏论证模型/批判性思维），动态配置角色和阶段化执行。详见 [议事编排官使用指南](#-议事编排官智能框架编排)。

---

## 🧭 议事编排官智能框架编排

**议事编排官（Deliberation Orchestrator）** 是 AICouncil 的高级功能，能够根据用户需求**自动选择最优讨论框架**并**动态配置角色**，实现更加专业化和结构化的议事流程。

### ✨ 核心能力

- **🤖 智能需求分析**：自动分析问题类型（决策类/论证类/分析类）和复杂度，推荐最优讨论策略
- **📋 框架自动匹配**：从 3 个预定义框架中选择最适合的方案：
  - **罗伯特议事规则**（Roberts Rules of Order）：适用于结构化决策和表决场景
  - **图尔敏论证模型**（Toulmin Model）：适用于深度论证和逻辑推理
  - **批判性思维框架**（Critical Thinking）：适用于质疑和风险识别
- **👥 角色智能配置**：
  - 自动匹配现有角色（Leader、Planner、Auditor、Reporter、Devil's Advocate 等）
  - 必要时调用 Role Designer 创建新的专业角色
- **📊 阶段化执行**：将复杂任务分解为多个 Stage（规划 → 执行 → 审查 → 报告），逐步推进
- **📈 流程可视化**：Reporter 自动生成 Mermaid 流程图，展示框架执行过程（从需求分析到最终报告）

### 🚀 使用方式

#### 方式 1: 命令行（开发环境）

```bash
# 仅生成规划方案（不执行）- 快速了解系统如何编排
python src/agents/demo_runner.py --use-meta-orchestrator --issue "如何提高团队协作效率？"

# 完整执行（规划 + 执行 + 报告）- 实际议事流程
python src/agents/demo_runner.py --use-meta-orchestrator --issue "设计一个高可用分布式系统" --backend deepseek --model deepseek-chat
```

**命令行参数说明**：
- `--use-meta-orchestrator`：启用议事编排官模式
- `--issue`：议题描述
- `--backend`：模型后端（deepseek/openai/aliyun/ollama 等）
- `--model`：具体模型名称（如 deepseek-chat、gpt-4o）

#### 方式 2: API 端点

```python
import requests

# Plan Only 模式：仅返回规划方案（推荐用于预览）
response = requests.post("http://localhost:5000/api/orchestrate", json={
    "issue": "如何优化代码性能？",
    "mode": "plan_only",
    "backend": "deepseek",
    "model": "deepseek-chat"
})
plan = response.json()["plan"]
print(f"选择的框架：{plan['framework_selection']['framework_name']}")
print(f"总轮次：{plan['execution_config']['total_rounds']}")

# Plan and Execute 模式：后台执行完整流程
response = requests.post("http://localhost:5000/api/orchestrate", json={
    "issue": "如何优化代码性能？",
    "mode": "plan_and_execute",
    "backend": "deepseek",
    "model": "deepseek-chat"
})
workspace_dir = response.json()["workspace_dir"]
# 通过 /api/status 轮询获取执行进度
```

**API 参数说明**：
- `mode`：`plan_only`（仅规划）或 `plan_and_execute`（完整执行）
- `issue`：议题描述
- `backend`：模型后端
- `model`：模型名称
- `agent_configs`（可选）：为特定角色指定不同模型

#### 方式 3: Web 界面（即将推出）

在设置页面启用 **议事编排官模式**，系统将自动进行智能编排。

### 📚 详细文档

- **[议事编排官完整指南](docs/meta_orchestrator.md)**：深度解析架构设计、工作流程、框架库、API 参考
- **[架构设计](docs/architecture.md)**：系统架构图和核心模块交互
- **[框架库文档](docs/frameworks.md)**：预定义框架详解和自定义框架指南

### 🎯 典型应用场景

- **决策类问题**：产品方向选择、技术栈选型、预算分配 → **罗伯特议事规则**
- **论证类问题**：学术假设验证、法律案例分析、因果关系推理 → **图尔敏论证模型**
- **分析类问题**：风险评估、漏洞挖掘、质量审查 → **批判性思维框架**

---

## 📸 界面展示

![AI 元老院界面展示](assets/demo.png)

---

## 🚀 快速部署

### 方式 1: 下载独立可执行文件（⭐ 强烈推荐）

**适用于 Windows 用户，无需安装任何环境，双击即用！**

#### 📥 下载

从 [GitHub Releases](https://github.com/mzniu/AICouncil/releases) 下载最新版本的 `AICouncil.exe`（约 340 MB）

#### 🚀 使用步骤

1. **下载 EXE 文件**
   - 直接下载 `AICouncil.exe` 到任意目录（建议放在英文路径）
   - 例如：`C:\AICouncil\AICouncil.exe` 或 `D:\Tools\AICouncil.exe`

2. **首次运行**
   - 双击 `AICouncil.exe` 启动
   - Windows Defender 可能提示"未识别的应用"，点击"**更多信息** → **仍要运行**"
   - 程序会自动启动，并在控制台显示日志
   - 等待几秒后，浏览器会自动打开 `http://127.0.0.1:5000`

3. **配置 API 密钥**
   - 点击页面右上角「⚙️ 设置」按钮
   - 在模型配置中填入您的 API 密钥：
     - **DeepSeek**: 推荐使用 deepseek-chat（性价比高）
     - **OpenAI**: 支持 GPT-4 系列模型
     - **Azure OpenAI**: 支持中国区和全球区部署
     - **Anthropic**: Claude 3.5 Sonnet 等模型
     - **Google Gemini**: Gemini 1.5 Pro/Flash 等模型
     - **OpenRouter**: 支持多种第三方模型
   - 点击「保存设置」

4. **开始议事**
   - 在主页输入您的议题（例如："如何提高团队协作效率？"）
   - 选择讨论轮数（建议从 1-2 轮开始）
   - 点击「🚀 开始议事」

5. **查看结果**
   - 实时查看各智能体的思考过程
   - 讨论结束后自动生成 HTML 报告
   - 支持导出为 **HTML / PDF / 图片 / Markdown** 格式

#### ⚙️ 核心功能

- ✅ **单文件模式**: 无需安装 Python、依赖包、浏览器
- ✅ **内置 Playwright**: 支持高质量 PDF 导出（带超链接、图表）
- ✅ **自动配置**: 首次运行自动创建工作目录和配置文件
- ✅ **丰富图表**: 内嵌 ECharts + Mermaid，支持数据可视化和流程图
- ✅ **多格式导出**: HTML、PDF、图片、Markdown 四种格式任选
- ✅ **多引擎搜索**: 支持 Google API、Baidu、Bing、Yahoo、Mojeek、DuckDuckGo
- ✅ **控制台日志**: 实时显示运行状态，方便排查问题

#### ⚠️ 注意事项

1. **首次启动较慢**
   - EXE 解压到临时目录需要 10-30 秒
   - 后续启动会更快（5-10 秒）

2. **杀毒软件误报**
   - PyInstaller 打包的 EXE 可能被误报为病毒
   - 建议添加到白名单或使用源代码运行

3. **文件路径要求**
   - 避免中文路径（可能导致编码问题）
   - 建议路径：`C:\AICouncil\` 或 `D:\Tools\AICouncil\`

4. **数据存储位置**
   - 配置文件：与 EXE 同级目录 `src/config.py`
   - 工作空间：`workspaces/` 子目录（包含所有讨论记录）
   - 日志文件：`aicouncil.log`

5. **控制台窗口**
   - 不要关闭控制台窗口（关闭会终止程序）
   - 所有日志会实时显示在控制台
   - 可以最小化窗口到任务栏

6. **停止程序**
   - 关闭浏览器页面不会停止程序
   - 需要在控制台按 `Ctrl+C` 或直接关闭控制台窗口

#### 📚 详细文档

- [EXE 用户手册](docs/user_manual_exe.md) - 完整使用指南
- [PDF 导出说明](docs/pdf_export_guide.md) - PDF 功能详解
- [构建 EXE 指南](docs/build_guide.md) - 自行打包说明

#### 🔧 常见问题

**Q: EXE 无法启动？**
- 确认 Windows 版本 ≥ Windows 10
- 检查是否被杀毒软件拦截
- 尝试以管理员身份运行

**Q: PDF 导出失败？**
- 确认 EXE 完整下载（342 MB）
- 查看控制台日志中的错误信息
- 降级使用"下载为图片"功能

**Q: 内存占用高？**
- 正常情况下占用 200-500 MB
- 讨论过程中可能达到 1-2 GB（取决于轮数和智能体数量）
- 讨论结束后会自动释放大部分内存

---

### 方式 2: 从源代码运行

#### 1. 环境准备
- **Python**: 确保您的系统已安装 Python 3.9 或更高版本。
- **浏览器**: 建议安装 **Google Chrome** 或 **Microsoft Edge**。部分搜索引擎（Baidu/Bing）需要调用浏览器内核进行自动化抓取。如果不安装浏览器，您仍可使用 Yahoo、Mojeek 或 DuckDuckGo 进行联网搜索。

##### 2. 克隆项目
```bash
git clone https://github.com/mzniu/AICouncil.git
cd AICouncil
```

##### 3. 安装依赖
建议使用虚拟环境：
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows)
.\venv\Scripts\activate

## 如出现Windows PowerShell 的执行策略（Execution Policy） 限制了脚本运行，请执行以下命令，并选择Y
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 激活虚拟环境 (Linux/macOS)
source .venv/bin/activate

# 安装依赖（推荐方式）
pip install -r requirements.txt

# 或者精简安装（适用于内存/磁盘受限环境）
pip install -r requirements-minimal.txt
# 可选：按需安装增强功能
pip install -r requirements-optional.txt
# 如安装playwright，需额外运行: playwright install chromium
```

**依赖说明**：
- `requirements.txt`: 完整依赖（包含所有功能）
- `requirements-minimal.txt`: 核心依赖（基本功能，体积更小）
- `requirements-optional.txt`: 可选增强（PDF导出、浏览器搜索）

#### 4. 配置 API 密钥
1. 复制配置模板文件：
   ```bash
   cp src/config_template.py src/config.py
   ```
2. 编辑 `src/config.py`，填入您的 API 密钥及相关配置：
   ```python
   # DeepSeek API（推荐，性价比高）
   DEEPSEEK_API_KEY = "您的密钥"
   DEEPSEEK_MODEL = "deepseek-chat"  # 或 deepseek-reasoner
   
   # OpenAI API
   OPENAI_API_KEY = "您的密钥"
   OPENAI_MODEL = "gpt-4o"
   
   # Azure OpenAI（支持中国区和全球区）
   AZURE_OPENAI_API_KEY = "您的Azure密钥"
   AZURE_OPENAI_ENDPOINT = "https://your-resource.openai.azure.cn"  # 中国区
   # AZURE_OPENAI_ENDPOINT = "https://your-resource.openai.azure.com"  # 全球区
   AZURE_OPENAI_API_VERSION = "2024-12-01-preview"
   AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4o"  # 您的部署名称
   
   # Anthropic Claude API
   ANTHROPIC_API_KEY = "您的Anthropic密钥"  # 获取地址：console.anthropic.com
   ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"  # 推荐模型
   
   # Google Gemini API
   GEMINI_API_KEY = "您的Gemini密钥"  # 获取地址：aistudio.google.com
   GEMINI_MODEL = "gemini-1.5-flash"  # 或 gemini-1.5-pro
   
   # Aliyun (Qwen)
   ALIYUN_API_KEY = "您的密钥"
   ALIYUN_MODEL = "qwen-plus"
   
   # OpenRouter（支持多种第三方模型）
   OPENROUTER_API_KEY = "您的密钥"
   OPENROUTER_MODEL = "google/gemini-3-flash-preview"
   
   # ... 其他配置
   ```
或者您也可以在项目根目录下创建 `.env` 文件，程序会自动读取环境变量。

**【建议】或者您也可以在页面右上角的设置中进行配置。**

#### 5. 初始化认证系统（可选）

如果您需要用户认证功能（登录/注册/MFA），需要先初始化数据库：

```bash
# 创建 .env 文件（从模板复制）
cp .env.example .env

# 编辑 .env，至少配置以下必需项：
# SECRET_KEY=your-secret-key-min-32-bytes  # 生成密钥：python -c "import secrets; print(secrets.token_hex(32))"
# DATABASE_URL=sqlite:///aicouncil.db      # 或使用 PostgreSQL
# ALLOW_PUBLIC_REGISTRATION=true           # 是否允许公开注册

# 初始化数据库
python -c "from src.models import db; from src.web.app import app; app.app_context().push(); db.create_all()"

# 验证环境配置（可选）
python scripts/validate_env.py
```

**详细配置说明**：
- 认证系统使用文档：[docs/authentication.md](docs/authentication.md)
- 生产部署指南：[docs/production_deployment.md](docs/production_deployment.md)
- 环境变量说明：参见 `.env.example` 文件

**快速测试认证功能**：
```bash
# 运行测试用例（需要先安装 pytest）
pip install pytest
python -m pytest tests/test_auth_endpoints.py tests/test_mfa_security.py -v
```

#### 6. 启动应用
```bash
python src/web/app.py
```
启动后，在浏览器访问 `http://127.0.0.1:5000` 即可开始议事。

**首次访问**：
- 如果启用了认证系统，将跳转到登录页面 `/login`
- 如果允许公开注册，可点击"注册账号"创建用户
- 如果未配置认证，直接访问首页开始议事

#### 7. 报告图表（ECharts + Mermaid）

#### ECharts 数据可视化
- 已内置 ECharts 5.4.3：文件位于 `src/web/static/vendor/echarts.min.js`
- 支持图表类型：柱状图、折线图、饼图、雷达图、散点图等
- 适用场景：数据对比、统计分析、趋势展示
- 加载方式：`<script src="/static/vendor/echarts.min.js"></script>`
- 若文件缺失，可从 https://registry.npmmirror.com/echarts/5.4.3/files/dist/echarts.min.js 下载

#### Mermaid 流程图与架构图
- 已内置 Mermaid 10.x：文件位于 `src/web/static/vendor/mermaid.min.js`
- 支持图表类型：
  - **流程图 (flowchart)**：业务流程、决策树、算法逻辑
  - **时序图 (sequenceDiagram)**：系统交互、API 调用流程
  - **甘特图 (gantt)**：项目规划、时间线、里程碑管理
  - **类图 (classDiagram)**：系统架构、模块关系
  - **状态图 (stateDiagram)**：状态机、生命周期
  - **ER图 (erDiagram)**：数据库设计、实体关系
  - **用户旅程图 (journey)**：用户体验流程
  - **饼图 (pie)**：简单占比展示
- 加载方式：
  ```html
  <script src="/static/vendor/mermaid.min.js"></script>
  <script>mermaid.initialize({ startOnLoad: true, theme: 'default' });</script>
  ```
- 若文件缺失，可从 https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js 下载

**测试页面**：启动服务后访问 http://127.0.0.1:5000/static/test_mermaid.html 查看所有 Mermaid 图表示例

---

## � 从源代码构建 EXE

如果您希望自己打包 AICouncil 为 EXE 可执行文件：

1. **安装打包依赖**：
   ```bash
   pip install pyinstaller>=5.0
   ```

2. **一键打包**：
   ```bash
   python build.py
   ```
   构建脚本会自动：
   - 检查依赖完整性
   - 验证关键文件存在
   - 使用 PyInstaller 打包
   - 生成发行版 ZIP 包

3. **查看构建结果**：
   - 打包文件位于 `dist/AICouncil/` 目录
   - 发行版 ZIP 位于 `dist/release/`

4. **详细说明**：
   - 完整构建指南：[docs/build_guide.md](docs/build_guide.md)
   - 打包前检查工具：`python check_packaging.py`

---

## �🛠️ 技术栈

- **后端**: Python, Flask, LangChain
- **前端**: Tailwind CSS, JavaScript (ES6+)
- **搜索**: Google Custom Search API, DrissionPage (自动化抓取), Requests + BeautifulSoup4 (轻量级抓取)
- **导出**: Playwright (PDF), BeautifulSoup4 (Markdown)
- **可视化**: ECharts 5.4.3 (数据图表), Mermaid 10.9.5 (流程图)
- **模型**: OpenAI API 兼容接口, Ollama (本地)

---

## 📂 项目结构

```text
AICouncil/
├── src/
│   ├── agents/          # 智能体核心逻辑与提示词模板
│   ├── web/             # Flask Web 服务与前端模板
│   │   ├── templates/   # HTML 模板（包括认证页面）
│   │   └── static/      # 静态资源
│   ├── utils/           # 搜索、日志等工具类
│   ├── models.py        # 数据库模型（User, LoginHistory）
│   ├── auth_routes.py   # 认证 API 端点
│   ├── auth_config.py   # 认证系统配置
│   └── config.py        # 全局配置文件
├── build/               # 构建工具与打包脚本
│   ├── build_config.py  # 构建配置
│   ├── path_manager.py  # 路径管理
│   └── config_manager.py # 配置管理
├── scripts/             # 部署脚本
│   └── validate_env.py  # 环境变量验证工具
├── workspaces/          # 议事历史记录存储目录
├── tests/               # 单元测试
│   ├── test_auth_endpoints.py  # 认证端点测试
│   └── test_mfa_security.py    # MFA 安全测试
├── docs/                # 项目文档
│   ├── authentication.md    # 认证系统文档 🔐
│   ├── production_deployment.md # 生产部署指南
│   ├── build_guide.md       # 构建打包指南
│   └── user_manual_exe.md   # 打包版用户手册
├── requirements.txt     # 完整依赖
├── requirements-minimal.txt # 核心依赖
├── requirements-optional.txt # 可选依赖
├── launcher.py          # EXE 启动器
├── build.py             # 自动构建脚本
├── check_packaging.py   # 打包前检查工具
├── aicouncil.spec       # PyInstaller 配置
└── README.md            # 项目说明文档
```

---

## 📝 TODOs

### 已完成
- [x] **多智能体架构**：实现议长、策论家、监察官、记录员的协同工作流。
- [x] **企业级认证系统**：用户注册/登录、MFA (TOTP)、备份码、会话管理、账户锁定、审计日志（42 个测试用例覆盖）。
- [x] **增强型搜索**：集成 DrissionPage 支持多引擎（Baidu, Bing, DuckDuckGo, Yahoo, Mojeek）并行搜索。
- [x] **UI 交互升级**：全站移除原生弹窗，采用 Tailwind CSS 自定义模态框。
- [x] **历史记录管理**：支持议事记录的持久化存储、回溯及物理删除。
- [x] **模型适配**：支持 DeepSeek, OpenAI, Azure OpenAI, Anthropic (Claude), Google Gemini, OpenRouter, Ollama 等主流模型。
- [x] **报告导出**：支持 HTML 报告生成、长图导出及 PDF 导出功能。
- [x] **用户介入模式**：允许用户在议事过程中随时"插话"，引导辩论方向。
- [x] **多语言支持**：实现前端界面的国际化 (i18n)。
- [x] **阵型预设**：支持保存和一键加载常用的议事配置（模型、轮数、人数）。
- [x] **多语言文档**：提供中英文双语 README。
- [x] **EXE 打包**：支持将应用打包为 Windows 可执行文件（双击即用，无需 Python）。
- [x] **搜索源扩展**：接入 Google Search API 等专业搜索服务。
- [x] **议事编排官智能编排**：实现自动框架匹配（罗伯特议事规则/图尔敏论证模型/批判性思维）、角色智能配置、阶段化执行。

### 计划中
- [ ] **更多 Agent 类型**：增加经济学家、法律顾问、技术专家等垂直领域智能体。
- [ ] **本地知识库 (RAG)**：支持上传 PDF/Word/Markdown 等文档作为议事参考。
- [ ] **跨平台打包**：支持 Linux 和 macOS 打包。

---

## 🤝 贡献指南

我们欢迎任何形式的贡献！如果您有好的建议或发现了 Bug，请提交 Issue 或 Pull Request。

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

---

## 📄 开源协议

本项目采用 [MIT 协议](LICENSE) 开源。

---

## 🏛️ 愿景

让 AI 不再只是简单的问答工具，而是成为能够深度思考、多维辩论的决策智囊团。

---

## 📈 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=mzniu/AICouncil&type=Date)](https://star-history.com/#mzniu/AICouncil&Date)

---
*如果这个项目对您有帮助，请给一个 ⭐️ Star，这是对我们最大的支持！*
