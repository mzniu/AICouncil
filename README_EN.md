# 🏛️ AICouncil

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)

[中文](README.md) | English

**AICouncil** is a multi-agent collaborative decision-making system based on Large Language Models (LLMs). It simulates the deliberation process of an ancient senate, using multiple AI agents with different responsibilities (Leader, Planner, Auditor, Reporter) to conduct multiple rounds of debate, questioning, and summarization, ultimately providing deep, objective, and multi-dimensional decision-making suggestions for complex issues.

---

## 🌟 Core Features

- **🎭 Multi-Role Collaboration**:
  - **Leader**: Responsible for issue decomposition, process guidance, and final report summarization.
  - **Planner**: Provides professional solutions and deep insights based on Retrieval-Augmented Generation (RAG).
  - **Auditor**: Conducts critical reviews of the Planner's solutions, pointing out potential risks and loopholes.
  - **Reporter**: Records the deliberation process in real-time to ensure no information is missed.
- **🔍 Enhanced Search**: Integrates multi-engine parallel search (Bing, Baidu, DuckDuckGo), supporting multi-page scraping to ensure AI gets the latest and most comprehensive information.
- **💻 Real-time Monitoring Panel**: A Flask-based web interface that displays agent thinking processes, search progress, and debate flows in real-time.
- **📄 Deep Report Generation**: Automatically generates structured HTML deliberation reports, supporting one-click copy, HTML download, or export as a long image.
- **📜 History Management**: Complete session persistence, supporting anytime backtracking, loading, or deletion of historical records.
- **✋ User Intervention**: Allows users to "intervene" at any time during the deliberation process to guide the direction of the debate.
- **📊 Progress Visualization**: Real-time display of current round (Round X / Y) and detailed agent status.
- **🤖 Broad Model Support**: Native support for DeepSeek, OpenAI, Aliyun (Qwen), OpenRouter, and local Ollama models.

---

## � UI Showcase

![AICouncil UI Showcase](assets/demo.png)

---

## 📅 TODOs

- [ ] **Report Export Enhancement**: Support for PDF export.
- [ ] **Search Capability Upgrade**: Add Google Search support and more precise web content extraction.
- [ ] **Memory System**: Introduce long-term and short-term memory mechanisms for cross-session context.
- [ ] **Mobile Optimization**: Improve the user experience on mobile browsers.
- [ ] **Plugin System**: Support custom tools (e.g., calculator, code executor) for agents to call.

---

## 🚀 Quick Deployment

### 1. Prerequisites
Ensure your system has Python 3.9 or higher installed.

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

# Install dependencies
pip install -r requirements.txt
```

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

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask, LangChain
- **Frontend**: Tailwind CSS, JavaScript (ES6+)
- **Search**: DrissionPage (Automation), BeautifulSoup4
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
- [x] **Enhanced Search**: Integrated DrissionPage to support multi-engine (Baidu, Bing, DuckDuckGo) parallel search.
- [x] **UI Interaction Upgrade**: Replaced native alerts with Tailwind CSS custom modals.
- [x] **History Management**: Supported persistence, backtracking, and physical deletion of records.
- [x] **Model Adaptation**: Supported DeepSeek, OpenAI, OpenRouter, Ollama, etc.
- [x] **Report Export**: Supported HTML report generation and long image export.
- [x] **User Intervention Mode**: Allows users to guide the debate direction at any time.
- [x] **Multi-language Documentation**: Provided bilingual README in Chinese and English.

### Planned
- [ ] **More Agent Types**: Add vertical domain agents like Economists, Legal Advisors, Technical Experts, etc.
- [ ] **Local Knowledge Base (RAG)**: Support uploading PDF/Word/Markdown documents as references.
- [ ] **Multi-language Support**: Implement internationalization (i18n) for the frontend interface.
- [ ] **Export Format Extension**: Support exporting to PDF, Markdown, or Word documents.
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
