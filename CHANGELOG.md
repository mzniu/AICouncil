# Changelog

All notable changes to AICouncil will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- 🔍 **Google Custom Search API 集成**
  - 集成 Google Custom Search API，提供高质量搜索结果
  - 国内可直接访问，无需代理或浏览器
  - 响应速度 ~1 秒，显著优于浏览器自动化方案
  - 免费配额：100 次/天；付费：$5/1000 次查询
  - 支持在 Web 配置页面直接设置 API Key 和 Search Engine ID
  - 完整的测试套件和集成测试

### Changed

- 🔧 **简化 Google 搜索实现**
  - 移除 Playwright 浏览器自动化方案（复杂且不稳定）
  - 统一使用官方 API，代码更简洁、维护成本更低
  - 删除 `GOOGLE_SEARCH_PROXY` 配置项
  - 更新前端配置界面，Google 搜索标注为 "API" 方式

### Removed

- ❌ 移除 `google_search_playwright()` 函数及相关 Playwright 依赖
- ❌ 移除 `tests/test_google_search.py` Playwright 测试文件
- ❌ 移除 Google 代理配置选项（不再需要）

## [1.0.0] - 2025-12-31

### Added

#### 核心功能
- 🎭 多智能体协作决策系统
  - 议长（Leader）：议题拆解、流程引导、报告汇总
  - 策论家（Planner）：基于搜索增强（RAG）提供专业方案
  - 监察官（Auditor）：批判性审查，指出风险与漏洞
  - 记录员（Reporter）：实时记录议事过程
- 🔍 多引擎并行搜索系统
  - 集成 Google、Baidu、Bing、DuckDuckGo、Yahoo、Mojeek 搜索引擎
  - Requests-First 架构（Google/Yahoo/Mojeek 纯 HTTP 实现）
  - Google Custom Search API 提供高质量搜索（免费 100 次/天）
  - 智能相关性校验，自动过滤无关热点
  - 查询优化与去重机制
- 💻 Web 实时监控面板
  - 基于 Flask 的响应式界面
  - 实时展示智能体思考过程与搜索进度
  - 支持窗口最大化/还原，方便深度阅读
  - 进度可视化（讨论轮数、角色状态）
- 📄 深度报告生成
  - 结构化 HTML 议事报告
  - 内嵌 ECharts 图表（离线可用）
  - 整合式下载菜单（HTML / 长图 / PDF）
  - PDF 导出支持超链接和交互元素
- 📜 历史会话管理
  - 完整的会话持久化（history.json）
  - 支持回溯、加载、删除历史记录
  - 工作空间目录结构化存储
- 💾 阵型预设系统
  - 保存/加载常用元老院配置
  - 配置包括：后端模型、轮数、智能体数量等
  - JSON 格式持久化（council_presets.json）
- ✋ 用户实时介入
  - 议事过程中输入指令
  - 实时引导智能体讨论方向

#### 打包发布
- 📦 Windows 单文件 EXE 打包
  - 基于 PyInstaller 6.17.0 的 onefile 模式
  - 文件大小：342.73 MB
  - 集成 Playwright + Chromium（chromium_headless_shell-1200）
  - 无需 Python 环境，双击即用
  - 控制台模式支持实时日志输出
- 🏛️ 自定义应用图标
  - 元老院主题图标（🏛️）
  - 多尺寸优化（256/128/64/48/32/16）
  - 小图标使用几何图形（增强清晰度）
- 🔧 自动化构建系统
  - 一键构建脚本（build.py）
  - 依赖完整性检查
  - 自动浏览器路径检测
  - 构建日志与错误提示

#### 模型支持
- 🤖 多后端适配器
  - DeepSeek（deepseek-chat/deepseek-reasoner，推荐）
  - OpenAI（GPT-4/GPT-4-turbo 系列）
  - Aliyun DashScope（Qwen 系列）
  - OpenRouter（多种第三方模型）
  - Ollama（本地模型支持）
- 🧠 推理内容支持
  - DeepSeek R1 模型 `reasoning_content` 单独流式显示
  - 思考过程与最终输出分离展示

#### 文档与测试
- 📚 完善的项目文档
  - [README.md](README.md) - 项目概览与快速开始
  - [docs/user_manual_exe.md](docs/user_manual_exe.md) - EXE 用户手册
  - [docs/build_guide.md](docs/build_guide.md) - 构建指南
  - [docs/pdf_export_guide.md](docs/pdf_export_guide.md) - PDF 导出说明
  - [docs/architecture.md](docs/architecture.md) - 架构设计文档
  - [docs/workflow.md](docs/workflow.md) - 工作流程图
- 🧪 Baseline 测试框架
  - REST API 级别的功能测试
  - 完整议事流程验证（tests/test_baseline_api.py）
  - 一键运行脚本（tests/run_baseline_test.bat）

### Fixed

- 🐛 修复 Playwright 浏览器路径检测问题
  - 打包环境下自动设置 `PLAYWRIGHT_BROWSERS_PATH`
  - 支持 `chromium_headless_shell` 和 `chromium` 多版本回退
- 🐛 修复 ECharts 内联正则表达式错误
  - 使用 lambda 函数避免 `\d` 被解释为反向引用
  - 确保离线 PDF 中图表正常渲染
- 🐛 修复小图标显示为默认图标
  - 16x16/32x32 尺寸使用几何图形替代 emoji
  - 提升小尺寸下的图标清晰度
- 🐛 修复 PDF 导出内容截断问题
  - 使用 Playwright 替代 jsPDF
  - 保留超链接和交互元素
  - 自动展开折叠内容（collapsed/details/hidden）
- 🐛 修复 PDF 导出时 ECharts 图表分页截断
  - 注入 CSS 防止图表跨页（`page-break-inside: avoid`）
  - 图表 resize 后等待布局稳定（2s）

### Changed

- ♻️ 优化路径管理系统
  - 引入 `path_manager.py` 抽象层
  - 统一处理开发/打包环境路径差异
  - 支持 `sys._MEIPASS` 临时目录
- ♻️ 优化前端交互体验
  - 设置面板优化（模型配置、搜索引擎选择）
  - 下载菜单整合（HTML/截图/PDF）
  - 历史记录弹窗支持加载/删除操作
- ♻️ 优化构建配置
  - 排除不必要的依赖（torch/pandas/numpy/scipy/matplotlib）
  - 减小 EXE 体积（从 ~500MB 优化到 342MB）
  - 添加隐藏导入（playwright.async_api/sync_api/greenlet）
- ♻️ 优化搜索引擎集成
  - 统一搜索接口抽象
  - 多引擎并行执行与结果合并
  - 智能相关性检测（过滤热点干扰）

### Security

- 🔒 配置文件安全
  - `.gitignore` 排除 `src/config.py`（包含 API 密钥）
  - 提供 `config_template.py` 模板
  - 支持 `.env` 环境变量配置

### Infrastructure

- 🏗️ 构建系统
  - PyInstaller 6.17.0 集成
  - 自动化构建脚本（build.py）
  - 依赖分析与完整性检查
- 🏗️ 版本控制
  - 排除构建产物（build/、dist/）
  - Git tag 标记发布版本
  - GitHub Releases 发布流程

---

## [Unreleased]

### Planned Features
- 🚀 macOS/Linux 打包支持
- 🌐 国际化（i18n）支持
- 📱 移动端适配
- 🎨 主题切换功能
- 🔌 插件系统架构

---

[1.0.0]: https://github.com/mzniu/AICouncil/releases/tag/v1.0.0
