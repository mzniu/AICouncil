# 🏛️ AI 元老院 (AICouncil)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)

中文 | [English](README_EN.md)

**AICouncil** 是一个基于大语言模型（LLM）的多智能体协作决策系统。它模拟了古代元老院的议事流程，通过多个不同职责的 AI 智能体（议长、策论家、监察官、记录员）进行多轮辩论、质疑与汇总，最终为复杂问题提供深度、客观且多维度的决策建议。

---

## 🌟 核心特性

- **🎭 多角色协同**：
  - **议长 (Leader)**：负责议题拆解、流程引导及最终报告汇总。
  - **策论家 (Planner)**：基于搜索增强（RAG）提供专业方案与深度见解。
  - **监察官 (Auditor)**：对策论家的方案进行批判性审查，指出潜在风险与漏洞。
  - **记录员 (Reporter)**：实时记录议事过程，确保信息不遗漏。
- **🔍 增强型搜索**：集成 Bing、Baidu、DuckDuckGo、Yahoo、Mojeek 等多引擎并行搜索。采用 **Requests-First** 架构，优先通过轻量级请求获取数据，并具备**智能相关性校验**与**查询优化**功能（自动识别并规避搜索引擎的无关热点干扰）。其中 Yahoo 和 Mojeek 为纯 Requests 实现，无需浏览器依赖，运行更稳定。
- **💻 实时监控面板**：基于 Flask 的 Web 界面，实时展示智能体思考过程、搜索进度及辩论流。支持窗口**最大化/还原**，方便深度阅读。
- **📄 深度报告生成**：自动生成结构化的 HTML 议事报告，支持一键复制、**整合式下载菜单**（支持 HTML / 长图 / PDF）。
- **📊 本地图表渲染**：报告内置 ECharts（/static/vendor/echarts.min.js），避免 CDN/跟踪防护阻断，iframe 内可直接使用。
- **📜 历史管理**：完整的会话持久化，支持随时回溯、加载或删除历史议事记录。
- **💾 阵型预设**：支持保存、加载和管理常用的元老院配置（包括后端模型、议事轮数、智能体数量等），方便快速启动不同场景的议事。
- **✋ 用户介入**：支持在议事过程中随时输入指令，实时引导智能体的讨论方向。
- **📊 进度可视化**：实时显示当前议事轮数及详细状态。进度条逻辑经过优化，议事结束即达 100%，无需等待报告生成。
- **🤖 广泛的模型支持**：原生支持 DeepSeek、OpenAI、Aliyun (Qwen)、OpenRouter 及本地 Ollama 模型。

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
     - **OpenRouter**: 支持多种第三方模型
   - 点击「保存设置」

4. **开始议事**
   - 在主页输入您的议题（例如："如何提高团队协作效率？"）
   - 选择讨论轮数（建议从 1-2 轮开始）
   - 点击「🚀 开始议事」

5. **查看结果**
   - 实时查看各智能体的思考过程
   - 讨论结束后自动生成 HTML 报告
   - 支持导出为 **HTML / 截图 / PDF** 格式

#### ⚙️ 核心功能

- ✅ **单文件模式**: 无需安装 Python、依赖包、浏览器
- ✅ **内置 Playwright**: 支持高质量 PDF 导出（带超链接、图表）
- ✅ **自动配置**: 首次运行自动创建工作目录和配置文件
- ✅ **离线图表**: 内嵌 ECharts，报告可离线查看
- ✅ **多引擎搜索**: 支持 Baidu、Bing、Yahoo、Mojeek、DuckDuckGo
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
   DEEPSEEK_API_KEY = "您的密钥"
   OPENAI_API_KEY = "您的密钥"
   # ... 其他配置
   ```
或者您也可以在项目根目录下创建 `.env` 文件，程序会自动读取环境变量。

**【建议】或者您也可以在页面右上角的设置中进行配置。**

#### 5. 启动应用
```bash
python src/web/app.py
```
启动后，在浏览器访问 `http://127.0.0.1:5000` 即可开始议事。

### 6. 报告图表（ECharts）
- 已内置 ECharts 5.4.3：文件位于 `src/web/static/vendor/echarts.min.js`，报告中通过 `<script src="/static/vendor/echarts.min.js"></script>` 加载，离线和 iframe 场景均可用。
- 若文件缺失，可从 https://registry.npmmirror.com/echarts/5.4.3/files/dist/echarts.min.js 下载后保存到上述路径（也可使用 unpkg/cdnjs 备用源）。

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
- **搜索**: DrissionPage (自动化抓取), Requests + BeautifulSoup4 (轻量级抓取)
- **模型**: OpenAI API 兼容接口, Ollama (本地)

---

## 📂 项目结构

```text
AICouncil/
├── src/
│   ├── agents/          # 智能体核心逻辑与提示词模板
│   ├── web/             # Flask Web 服务与前端模板
│   ├── utils/           # 搜索、日志等工具类
│   └── config.py        # 全局配置文件
├── build/               # 构建工具与打包脚本
│   ├── build_config.py  # 构建配置
│   ├── path_manager.py  # 路径管理
│   └── config_manager.py # 配置管理
├── workspaces/          # 议事历史记录存储目录
├── tests/               # 单元测试
├── docs/                # 项目文档
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
- [x] **增强型搜索**：集成 DrissionPage 支持多引擎（Baidu, Bing, DuckDuckGo, Yahoo, Mojeek）并行搜索。
- [x] **UI 交互升级**：全站移除原生弹窗，采用 Tailwind CSS 自定义模态框。
- [x] **历史记录管理**：支持议事记录的持久化存储、回溯及物理删除。
- [x] **模型适配**：支持 DeepSeek, OpenAI, OpenRouter, Ollama 等主流模型。
- [x] **报告导出**：支持 HTML 报告生成、长图导出及 PDF 导出功能。
- [x] **用户介入模式**：允许用户在议事过程中随时"插话"，引导辩论方向。
- [x] **多语言支持**：实现前端界面的国际化 (i18n)。
- [x] **阵型预设**：支持保存和一键加载常用的议事配置（模型、轮数、人数）。
- [x] **多语言文档**：提供中英文双语 README。
- [x] **EXE 打包**：支持将应用打包为 Windows 可执行文件（双击即用，无需 Python）。

### 计划中
- [ ] **更多 Agent 类型**：增加经济学家、法律顾问、技术专家等垂直领域智能体。
- [ ] **本地知识库 (RAG)**：支持上传 PDF/Word/Markdown 等文档作为议事参考。
- [ ] **搜索源扩展**：接入 Google Search API 等专业搜索服务。
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
