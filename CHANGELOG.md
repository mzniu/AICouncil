# Changelog

All notable changes to AICouncil will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2026-01-15

### Fixed
- **报告加载优化**：移除 `handleFinalReport` 内部的早期校验逻辑，避免延迟加载时丢失 JS/配置
  - 在 WebSocket 事件流和 pollStatus 两个入口前置数据校验（`report_html.length > 100`）
  - 确保处理函数专注于转换逻辑，无防御性代码干扰
- **议事编排官议题传递**：修复从 `orchestration_result.json` 加载报告时使用错误字段的问题
  - 从 `problem_type`（"决策类"等分类标签）改为 `user_requirement`（实际议题内容）
  - 确保参考资料整理官收到正确的议题进行相关性过滤
  - 修复报告标题/内容显示分类标签而非实际议题的问题
- **用户数据库跟踪**：将 `data/users.db` 从 Git 跟踪中移除，避免敏感数据泄露

### Changed
- 优化控制台日志输出，区分 `console.error` 和 `console.warn` 的使用场景

## [2.0.0] - 2026-01-13

### Added

#### 🔐 企业级认证系统
- **用户注册与登录**：
  - 支持公开注册（可配置禁用）、密码强度策略（8位+大小写+数字）
  - 账户锁定机制（5次失败=5分钟锁定）
  - bcrypt 密码哈希（PBKDF2-HMAC-SHA256）
- **多因素认证 (MFA)**：
  - 基于 TOTP (RFC 6238) 的双因素认证
  - 支持 Google Authenticator / Microsoft Authenticator
  - QR码扫描快速配置
  - 每个用户 10 个一次性备份码（bcrypt 加密存储）
- **会话管理**：
  - "记住我"功能（30天持久化会话）
  - 会话版本控制（登出所有设备）
  - HttpOnly Cookies + SameSite=Lax 安全配置
- **审计日志**：
  - 完整登录历史记录（成功/失败/IP/User-Agent）
  - 支持安全审计与异常检测
- **用户管理**：
  - 用户设置界面（修改密码、管理 MFA、查看会话）
  - MFA 启用/禁用（需密码确认）
  - 密码修改后强制其他设备重新登录
- **数据库支持**：
  - SQLAlchemy ORM + Flask-Migrate 迁移系统
  - 支持 SQLite（开发）/ PostgreSQL（生产）
  - 用户表、登录历史表分离设计
- **完整文档**：
  - 认证系统文档（[docs/authentication.md](docs/authentication.md)）
  - 生产部署指南（[docs/production_deployment.md](docs/production_deployment.md)）
  - 42 个测试用例覆盖（41 passed, 1 skipped）

#### 🤖 议事编排官智能框架
- **自动需求分析**：根据问题类型推荐最优讨论策略
- **三大框架支持**：
  - 罗伯特议事规则（结构化决策与表决）
  - 图尔敏论证模型（深度论证与逻辑推理）
  - 批判性思维框架（风险识别与漏洞分析）
- **动态角色配置**：根据选定框架自动配置角色和流程
- **阶段化执行**：分阶段推进议事流程，确保深度讨论

#### 👹 质疑官（Devil's Advocate）闭环质疑机制
- 在议题拆解阶段和每轮总结后对议长输出进行严格审查，识别盲点与逻辑假设
- 三级严重度分类（Critical / Warning / Minor），按风险等级展示
- 强制修正流程：议长必须在下一轮中包含 `da_feedback_response` 字段回应质疑
- 结构化输出：使用 Pydantic 模型确保输出质量
- 专业化 UI：Tailwind CSS 卡片式渲染，颜色编码区分严重程度
- Reporter 集成：最终报告新增"质疑与修正"专栏
- 并行执行优化：与监察官同步运行，不影响整体性能

#### 🔄 用户参与式报告修订与版本管理
- 报告底部新增"💬 修订反馈"浮动面板，支持浏览器内提交修改要求
- 多版本保存（`report_v0.html` 原始版本，`v1/v2...` 为修订版）
- 报告标题栏提供版本选择下拉框
- `Report Auditor` 智能体自动处理用户反馈并生成修订建议

#### ✏️ 交互式报告编辑器 (MVP)
- 所见即所得编辑：直接在浏览器编辑报告内容
- 版本控制：自动创建快照，支持历史版本预览和恢复
- 自动保存：编辑模式下每 60 秒自动保存草稿
- 友好 UI：固定工具栏、状态指示器、通知消息、模态框
- 数据持久化：基于文件系统的版本管理，元数据存储在 `report_edits.json`
- REST API：完整的后端 API 支持
- 轻量实现：使用原生 ContentEditable API，无需 React/Vue
- 响应式设计：支持桌面和移动端编辑
- 安全防护：离开页面前自动提示未保存修改

#### 🔍 Google Custom Search API 集成
- 集成 Google Custom Search API，提供高质量搜索结果
- 国内可直接访问，无需代理或浏览器
- 响应速度 ~1 秒，显著优于浏览器自动化方案
- 免费配额：100 次/天；付费：$5/1000 次查询
- Web 配置页面支持直接设置 API Key 和 Search Engine ID

#### 📊 Mermaid 流程图支持
- 集成 Mermaid.js 10.9.5 实现丰富的图表渲染
- 支持 8 种图表类型：flowchart、sequenceDiagram、gantt、classDiagram、stateDiagram、erDiagram、journey、pie
- Reporter 智能体可根据内容自动生成合适的流程图
- 本地渲染，支持离线使用和 PDF 导出
- 修复常见语法问题（使用 `flowchart TD` 替代过时的 `graph TD`）

#### 📝 Markdown 格式导出
- 使用 BeautifulSoup4 智能解析 HTML 结构
- 自动转换标题、段落、列表、表格、链接、代码块
- 保留 Mermaid 流程图代码块（可在 Typora、VS Code、GitHub 中渲染）
- ECharts 图表转换为文字描述占位符
- 支持 CommonMark 标准，兼容主流 Markdown 编辑器
- 文件大小仅为 HTML 的 5-10%

#### 🔗 增强型信源引用与跳转链接解析
- 交互式引用预览：悬停显示标题、摘要和来源域名
- 跳转链接解析：自动解析搜索引擎跳转链接为实际目标 URL
- 并行解析引擎：使用多线程并行解析链接
- 百度验证码自动绕过：自动提取 backurl 中的原始地址
- 结构化搜索结果：搜索结果表格新增"来源"列
- 交互式 UI：使用原生 JS 和 CSS 实现轻量级 Tooltip

### Changed

- 📝 **Reporter 输出优化**：最终报告不再暴露内部角色讨论细节，将反馈自然整合为专业建议文本
- 🔧 **简化 Google 搜索实现**：
  - 移除 Playwright 浏览器自动化方案
  - 统一使用官方 API，代码更简洁、维护成本更低
  - 删除 `GOOGLE_SEARCH_PROXY` 配置项
  - 前端配置界面标注 Google 搜索为 "API" 方式
- ⚙️ **配置系统重构**：
  - 从 `src/config.py` 迁移到 `.env` 文件（更安全、更易管理）
  - 配置优先级：环境变量 > .env 文件 > config.py（向后兼容）> 默认值
  - 提供 `.env.example` 模板和 `scripts/validate_env.py` 验证工具
  - Web UI 支持直接配置并保存到 .env

### Fixed

- 🐛 修复报告修订时覆盖原始报告的问题（新增原始备份 `report_v0.html`）
- 🐛 修复历史工作区加载时版本选择下拉框不显示的问题
- 🐛 修复 MFA 设置页面 JavaScript DOM 错误（querySelector 重复调用）
- 🐛 修复 MFA 禁用时密码验证失败（改用 bcrypt.checkpw）
- 🐛 修复登录重定向 BuildError（login_manager.login_view 错误配置）
- 🐛 修复认证 API 404 错误（补充缺失的 /api/auth/mfa/setup/verify 端点）

### Removed

- ❌ 移除 `google_search_playwright()` 函数及相关 Playwright 依赖
- ❌ 移除 `tests/test_google_search.py` Playwright 测试文件
- ❌ 移除 Google 代理配置选项（不再需要）

### Security

- 🔒 **认证系统安全增强**：
  - bcrypt 密码哈希（PBKDF2-HMAC-SHA256）
  - TOTP 双因素认证（RFC 6238）
  - 会话版本控制防止会话固定攻击
  - HttpOnly Cookies + SameSite=Lax 防止 CSRF
  - 账户锁定机制防止暴力破解
- 🔒 **.env 配置文件保护**：
  - `.gitignore` 排除 `.env` 文件（防止密钥泄露）
  - 提供 `.env.example` 安全模板
  - 支持环境变量覆盖（生产环境推荐）

---

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
  - README.md - 项目概览与快速开始
  - docs/user_manual_exe.md - EXE 用户手册
  - docs/build_guide.md - 构建指南
  - docs/pdf_export_guide.md - PDF 导出说明
  - docs/architecture.md - 架构设计文档
  - docs/workflow.md - 工作流程图
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

[2.0.0]: https://github.com/mzniu/AICouncil/releases/tag/v2.0.0
[1.0.0]: https://github.com/mzniu/AICouncil/releases/tag/v1.0.0
