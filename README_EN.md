# 🏛️ AICouncil

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)

[中文](README.md) | English

**AICouncil** is a multi-agent collaborative decision-making system based on Large Language Models (LLMs). It simulates the deliberation process of an ancient senate, using multiple AI agents with different responsibilities (Leader, Planner, Auditor, Reporter) to conduct multiple rounds of debate, questioning, and summarization, ultimately providing deep, objective, and multi-dimensional decision-making suggestions for complex issues.

---

## 🌟 Core Features

- **🔐 Enterprise-Grade Authentication System**:
  - **User Registration & Login**: Supports public registration (configurable), password strength policies, and account lockout mechanisms.
  - **Multi-Factor Authentication (MFA)**: TOTP-based (RFC 6238) two-factor authentication, compatible with Google Authenticator / Microsoft Authenticator.
  - **Backup Code System**: Generates 10 one-time backup codes per user for device loss scenarios.
  - **Session Management**: "Remember me" functionality, session versioning (logout all devices), secure cookie configuration.
  - **Audit Logs**: Comprehensive login history (success/failure/IP/User-Agent) for security audits.
  - **Documentation**: See [Authentication System Documentation](docs/authentication.md).
- **🎭 Multi-Role Collaboration**:
  - **Leader**: Responsible for issue decomposition, process guidance, and final report summarization.
  - **Planner**: Provides professional solutions and deep insights based on Retrieval-Augmented Generation (RAG).
  - **Auditor**: Conducts critical reviews of the Planner's solutions, pointing out potential risks and loopholes.
  - **Reporter**: Records the deliberation process in real-time to ensure no information is missed.
- **🔍 Enhanced Search**: Integrates multi-engine parallel search including **Google** (official API), Bing, Baidu, DuckDuckGo, Yahoo, and Mojeek. Features a **Requests-First** architecture for high performance, with **intelligent relevance validation** and **query optimization** (automatically bypassing irrelevant search engine noise). **Google Custom Search API** provides high-quality results with direct access from China (free tier: 100 queries/day). Yahoo, Mojeek, and Google are pure HTTP implementations requiring no browser dependencies for stable operation.

---
## 🚩 Highlights — 1.1.0

- 👹 **Devil's Advocate (closed-loop challenge)**:
   - The Devil's Advocate role issues structured challenges and blind-spot lists during the decomposition stage and after each round summary, labeled by severity (Critical / Warning / Minor). The `Leader` must explicitly respond in subsequent summaries.
   - A final-round forced revision is triggered when critical issues are present to ensure the delivered report has closed the loop and meets quality standards.

- 🔄 **User-driven report revision & versioning**:
   - A floating "💬 Revision Feedback" panel allows users to submit modification requests directly from the report view.
   - The system backs up the original report as `report_v0.html` before the first revision; subsequent revisions are saved as `report_v1.html`, `report_v2.html`, etc. A version selector is available in the report header for easy comparison and rollback.
   - A new `Report Auditor` agent analyzes feedback, drafts suggested revisions, and supports one-click apply & preview.

See `CHANGELOG.md` for full details.
- **💻 Real-time Monitoring Panel**: A Flask-based web interface that displays agent thinking processes, search progress, and debate flows in real-time. Supports **Maximize/Restore** for better readability.
- **📄 Deep Report Generation**: Automatically generates structured HTML deliberation reports, supporting one-click copy and a **consolidated download menu** (HTML / long image / PDF).
- **📊 Rich Chart Support**: Reports support **ECharts** data visualization (bar charts, pie charts, radar charts, etc.) and **Mermaid** diagrams (flowcharts, sequence diagrams, Gantt charts, class diagrams, state diagrams, etc.). All chart libraries are deployed locally (`/static/vendor/`), avoiding CDN dependencies and working in offline and iframe scenarios.
- **📜 History Management**: Complete session persistence, supporting anytime backtracking, loading, or deletion of historical records.
- **💾 Council Formations**: Supports saving, loading, and managing common council configurations (including backend models, rounds, agent counts) for quick startup in different scenarios.
- **✋ User Intervention**: Allows users to "intervene" at any time during the deliberation process to guide the direction of the debate.
- **📊 Progress Visualization**: Real-time display of current round and detailed agent status. Optimized progress logic reaches 100% immediately after the discussion ends.
- **🤖 Broad Model Support**: Native support for DeepSeek, OpenAI, Aliyun (Qwen), OpenRouter, and local Ollama models.

---

## 📸 UI Showcase

![AICouncil UI Showcase](assets/demo.png)

---

## 📅 TODOs

- [x] **Report Export Enhancement**: Support for PDF, Markdown exports.
- [ ] **Search Capability Upgrade**: Add Google Search support and more precise web content extraction.
- [ ] **Memory System**: Introduce long-term and short-term memory mechanisms for cross-session context.
- [ ] **Mobile Optimization**: Improve the user experience on mobile browsers.
- [ ] **Plugin System**: Support custom tools (e.g., calculator, code executor) for agents to call.

---

## 🚀 Quick Deployment

### 1. Prerequisites
- **Python**: Ensure your system has Python 3.9 or higher installed.
- **Browser**: **Google Chrome** or **Microsoft Edge** is recommended. Some search engines (Baidu/Bing) require a browser kernel for automated scraping. If no browser is installed, you can still use Yahoo, Mojeek, or DuckDuckGo for web search.

### 2. Clone the Project
```bash
git clone https://github.com/mzniu/AICouncil.git
cd AICouncil
```

### 3. Install Dependencies
It is recommended to use a virtual environment:
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.\.venv\Scripts\activate

# Activate virtual environment (Linux/macOS)
source .venv/bin/activate

# Install dependencies (recommended)
pip install -r requirements.txt

# Or minimal installation (for limited memory/disk environments)
pip install -r requirements-minimal.txt
# Optional: install enhancements as needed
pip install -r requirements-optional.txt
# If installing playwright, run: playwright install chromium
```

**Dependency Guide**:
- `requirements.txt`: Full dependencies (all features)
- `requirements-minimal.txt`: Core dependencies (basic features, smaller size)
- `requirements-optional.txt`: Optional enhancements (PDF/Markdown export, browser search)

### 4. Configure API Keys
1. Copy the configuration template file:
   ```bash
   cp src/config_template.py src/config.py
   ```
2. Edit `src/config.py` and fill in your API keys and related configurations:
   ```python
   DEEPSEEK_API_KEY = "your_key"
   OPENAI_API_KEY = "your_key"
   # ... other configs
   ```
Alternatively, you can create a `.env` file in the project root, and the program will automatically read environment variables. You can also configure them in the settings at the top right of the web page.

### 5. Start the Application
```bash
python src/web/app.py
```
After starting, visit `http://127.0.0.1:5000` in your browser to start deliberating.

### 6. Report Charts (ECharts)
- ECharts 5.4.3 is bundled at `src/web/static/vendor/echarts.min.js` and loaded via `<script src="/static/vendor/echarts.min.js"></script>`, so it works offline and inside iframes.
- If the file is missing, download it from https://registry.npmmirror.com/echarts/5.4.3/files/dist/echarts.min.js and place it at the path above (unpkg/cdnjs are optional mirrors).

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask, LangChain
- **Frontend**: Tailwind CSS, JavaScript (ES6+)
- **Search**: DrissionPage (Automation), Requests + BeautifulSoup4 (Lightweight Scraping)
- **Models**: OpenAI API compatible interfaces, Ollama (Local)

---

## 📂 Project Structure

```text
AICouncil/
├── src/
│   ├── agents/          # Agent core logic and prompt templates
│   ├── web/             # Flask Web service and frontend templates
│   ├── utils/           # Search, logging, and other utilities
│   └── config.py        # Global configuration file
├── workspaces/          # Directory for storing historical records
├── tests/               # Unit tests
├── requirements.txt     # Project dependencies
└── README.md            # Project documentation
```

---

## 📝 TODOs

### Completed
- [x] **Multi-Agent Architecture**: Implemented collaborative workflow for Leader, Planner, Auditor, and Reporter.
- [x] **Enhanced Search**: Integrated DrissionPage to support multi-engine (Baidu, Bing, DuckDuckGo, Yahoo, Mojeek) parallel search.
- [x] **UI Interaction Upgrade**: Replaced native alerts with Tailwind CSS custom modals.
- [x] **History Management**: Supported persistence, backtracking, and physical deletion of records.
- [x] **Model Adaptation**: Supported DeepSeek, OpenAI, OpenRouter, Ollama, etc.
- [x] **Report Export**: Supported HTML, PDF, Image, and Markdown format exports.
- [x] **User Intervention Mode**: Allows users to guide the debate direction at any time.
- [x] **Multi-language Support**: Implement internationalization (i18n) for the frontend interface.
- [x] **Council Formations**: Supports saving and one-click loading of common deliberation configurations (models, rounds, agent counts).
- [x] **Multi-language Documentation**: Provided bilingual README in Chinese and English.

### Planned
- [ ] **More Agent Types**: Add vertical domain agents like Economists, Legal Advisors, Technical Experts, etc.
- [ ] **Local Knowledge Base (RAG)**: Support uploading PDF/Word/Markdown documents as references.
- [x] **Export Format Extension**: Supports PDF and Markdown formats; Word export pending.
- [ ] **Search Source Expansion**: Integrate professional search services like Google Search API.

---

## 🤝 Contributing

We welcome any form of contribution! If you have good suggestions or found a bug, please submit an Issue or Pull Request.

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🏛️ Vision

Make AI more than just a simple Q&A tool, but a decision-making think tank capable of deep thinking and multi-dimensional debate.

---

## 📈 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=mzniu/AICouncil&type=Date)](https://star-history.com/#mzniu/AICouncil&Date)

---
*If this project is helpful to you, please give it a ⭐️ Star, it's our greatest support!*
