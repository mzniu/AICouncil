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
- **🔍 增强型搜索**：集成 Bing、Baidu、DuckDuckGo 等多引擎并行搜索。采用 **Requests-First** 架构，优先通过轻量级请求获取数据，并具备**智能相关性校验**与**查询优化**功能（自动识别并规避搜索引擎的无关热点干扰）。
- **💻 实时监控面板**：基于 Flask 的 Web 界面，实时展示智能体思考过程、搜索进度及辩论流。支持窗口**最大化/还原**，方便深度阅读。
- **📄 深度报告生成**：自动生成结构化的 HTML 议事报告，支持一键复制、**整合式下载菜单**（支持 HTML 或导出为长图）。
- **📜 历史管理**：完整的会话持久化，支持随时回溯、加载或删除历史议事记录。
- **✋ 用户介入**：支持在议事过程中随时输入指令，实时引导智能体的讨论方向。
- **📊 进度可视化**：实时显示当前议事轮数及详细状态。进度条逻辑经过优化，议事结束即达 100%，无需等待报告生成。
- **🤖 广泛的模型支持**：原生支持 DeepSeek、OpenAI、Aliyun (Qwen)、OpenRouter 及本地 Ollama 模型。

---

## 📸 界面展示

![AI 元老院界面展示](assets/demo.png)

---

## 🚀 快速部署

### 1. 环境准备
- **Python**: 确保您的系统已安装 Python 3.9 或更高版本。
- **浏览器**: 建议安装 **Google Chrome** 或 **Microsoft Edge**。联网搜索功能（Baidu/Bing）需要调用浏览器内核进行自动化抓取。

### 2. 克隆项目
```bash
git clone https://github.com/mzniu/AICouncil.git
cd AICouncil
```

### 3. 安装依赖
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

# 安装依赖
pip install -r requirements.txt
```

### 4. 配置 API 密钥
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

### 5. 启动应用
```bash
python src/web/app.py
```
启动后，在浏览器访问 `http://127.0.0.1:5000` 即可开始议事。

---

## 🛠️ 技术栈

- **后端**: Python, Flask, LangChain
- **前端**: Tailwind CSS, JavaScript (ES6+)
- **搜索**: DrissionPage (自动化抓取), BeautifulSoup4
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
├── workspaces/          # 议事历史记录存储目录
├── tests/               # 单元测试
├── requirements.txt     # 项目依赖
└── README.md            # 项目说明文档
```

---

## 📝 TODOs

### 已完成
- [x] **多智能体架构**：实现议长、策论家、监察官、记录员的协同工作流。
- [x] **增强型搜索**：集成 DrissionPage 支持多引擎（Baidu, Bing, DuckDuckGo）并行搜索。
- [x] **UI 交互升级**：全站移除原生弹窗，采用 Tailwind CSS 自定义模态框。
- [x] **历史记录管理**：支持议事记录的持久化存储、回溯及物理删除。
- [x] **模型适配**：支持 DeepSeek, OpenAI, OpenRouter, Ollama 等主流模型。
- [x] **报告导出**：支持 HTML 报告生成及长图导出功能。
- [x] **用户介入模式**：允许用户在议事过程中随时“插话”，引导辩论方向。
- [x] **多语言支持**：实现前端界面的国际化 (i18n)。
- [x] **多语言文档**：提供中英文双语 README。

### 计划中
- [ ] **更多 Agent 类型**：增加经济学家、法律顾问、技术专家等垂直领域智能体。
- [ ] **本地知识库 (RAG)**：支持上传 PDF/Word/Markdown 等文档作为议事参考。
- [ ] **导出格式扩展**：支持导出为 PDF、Markdown 或 Word 文档。
- [ ] **搜索源扩展**：接入 Google Search API 等专业搜索服务。

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
