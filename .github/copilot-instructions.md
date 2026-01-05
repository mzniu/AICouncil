# AICouncil 开发指南

## 架构概览

AICouncil 是一个多智能体协商系统，模拟一个"元老院"，AI 智能体通过结构化的轮次辩论复杂议题。架构遵循严格的**基于角色的盲评模式**：

- **议长** (Leader): 分解议题、编排讨论流程、综合最终报告。根据轮次上下文（中间轮次 vs 最终轮次）调整策略
- **策论家** (Planners): 并行生成解决方案提案（盲评 - 无跨智能体可见性）
- **监察官** (Auditors): 并行批判性审查策论家的提案（盲评）
- **质疑官** (Devil's Advocate): 通过批判性分析挑战议长的分解和总结，识别逻辑缺陷、缺失视角和潜在偏见。当发现严重问题时触发议长修订
- **记录员** (Reporter): 从讨论结果生成精美的 HTML 报告。自然地整合质疑官的反馈到解决方案中，而不暴露内部讨论过程

**核心设计原则**：智能体以**盲评模式**运行 - 每个智能体在议长综合之前无法看到同一角色层级中其他智能体的输出。这通过独立的 LangChain 执行上下文来强制执行。
**关键原则**：未经用户同意，不要提交和推送代码。

## 核心工作流

1. **规划阶段**：议长将议题分解为 `key_questions` 并设计报告结构
   - 质疑官挑战分解方案
   - 如果发现严重问题，议长进行修订（闭环）
2. **迭代讨论**（可配置轮次）：
   - 策论家生成提案 → 监察官批评 → 议长综合
   - 质疑官每轮挑战议长的总结
   - 每个角色层级使用 `ThreadPoolExecutor` 并行执行
3. **最终轮次特殊处理**：
   - 议长使用 `is_final_round=True` 提示词（聚焦全局综合，而非下一轮方向）
   - 质疑官提供最终挑战
   - **强制最终修订**：议长必须在生成报告前基于质疑官反馈修订总结
4. **综合阶段**：议长的修订总结 → 记录员生成带嵌入式 ECharts 的 HTML 报告
   - 记录员自然地整合质疑官的见解，而不暴露讨论过程

**搜索集成**：智能体可以在执行过程中使用 `[SEARCH: query]` 标签触发网络搜索。系统检测到这些标签后，通过多引擎搜索（百度/必应/雅虎/Mojeek/DuckDuckGo）获取结果，并将结果重新注入智能体的上下文进行第二次处理。搜索实现为**请求优先架构**（雅虎/Mojeek 使用纯 requests；百度/必应回退到 DrissionPage 进行 JavaScript 渲染）。

## 模型配置

**多后端支持**：系统使用统一的 `ModelConfig` 抽象（[src/agents/model_adapter.py](src/agents/model_adapter.py)）支持：
- `deepseek`: DeepSeek API（默认：deepseek-reasoner，支持思考内容）
- `openai`: OpenAI/兼容 API
- `openrouter`: OpenRouter，支持按智能体选择模型
- `aliyun`: 阿里云 DashScope（Qwen 模型）
- `ollama`: 通过 Ollama HTTP API 使用本地模型

**按智能体配置**：你可以通过 `agent_configs` 为特定智能体覆盖模型（例如，议长使用 GPT-4，策论家使用 Gemini）。参见 [src/web/app.py](src/web/app.py) 的 `/api/start` 端点。

**推理内容**：DeepSeek R1 模型返回 `generation_info.reasoning`，它会单独流式传输到 UI。在 [src/agents/langchain_llm.py](src/agents/langchain_llm.py) 的 `AdapterLLM._stream` 方法中处理。

## 关键代码模式

### JSON 输出强制

所有智能体必须输出严格匹配 Pydantic schemas 的 JSON（[src/agents/schemas.py](src/agents/schemas.py)）。系统：
1. 使用 `clean_json_string()` 清理 LLM 输出（删除 markdown 代码围栏）
2. 使用 Pydantic 解析
3. 验证失败时最多重试 2 次
4. 所有重试失败后返回错误 JSON

**关键**：提示词使用多语言指令（中文+英文）强调"JSON 外不要任何文本"以对抗 LLM 冗长。

### 流式传输 + 搜索循环

参见 [src/agents/langchain_agents.py](src/agents/langchain_agents.py) 的 `stream_agent_output()`：
- 通过 `send_web_event()` 将 LLM 块流式传输到 Web UI
- 在流中检测 `[SEARCH:]` 标签
- 暂停生成，执行多引擎并行搜索
- 使用搜索结果 + "**严禁再次输出 [SEARCH:]**" 指令重新提示智能体

### Web 界面通信

Flask 应用（[src/web/app.py](src/web/app.py)）将讨论作为子进程（`demo_runner.py`）生成。智能体向 `/api/update` POST 事件：
```python
{"type": "agent_action", "agent_name": "策论家-1", "role_type": "planner", "content": "...", "chunk_id": "uuid"}
```
前端轮询 `/api/status` 并在可折叠面板中显示实时思考过程。

## 开发工作流

### 本地运行
```bash
# 安装依赖（使用 venv）
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# 安装 Playwright 浏览器用于 PDF 导出（可选但推荐）
playwright install chromium

# 配置 API 密钥
cp src/config_template.py src/config.py
# 编辑 src/config.py 填入你的 API 密钥

# 启动 Web UI
python src/web/app.py  # 访问 http://127.0.0.1:5000

# 或运行无头讨论
python src/agents/demo_runner.py --issue "你的议题" --backend deepseek --rounds 2
```

### 测试搜索引擎
在 [tests/](tests/) 中测试单个搜索提供商：
- `test_final_search.py`: 测试所有搜索引擎
- `verify_baidu_fix.py`: 验证百度 HTML 解析

### 浏览器依赖
百度/必应需要 Chrome 或 Edge 用于 DrissionPage 自动化。在 [src/config.py](src/config.py) 中设置 `BROWSER_PATH` 或让 `browser_utils.find_browser_path()` 自动检测。雅虎/Mojeek 无需浏览器。

## 项目特定约定

### 文件结构
- **Workspaces**: 每次讨论创建 `workspaces/{timestamp}_{uuid}/` 目录，包含 `history.json`、`round_N_data.json` 和 `report.html`
- **Presets**: 元老院配置保存到根目录 `council_presets.json`（后端、轮次、智能体数量）
- **Logs**: 主日志位于 `aicouncil.log`（或 `LOG_FILE` 环境变量）

### HTML 报告
报告是自包含的 HTML，包含：
- 嵌入的 ECharts 5.4.3，位于 `/static/vendor/echarts.min.js`（无 CDN 依赖，支持 iframe/离线）
- Tailwind CSS 类用于样式
- 导出按钮支持 HTML/截图/PDF 格式

**PDF 导出**：
- **主要方法**：服务器端 Playwright 渲染（需要 `pip install playwright && playwright install chromium`）
  - 保留超链接和交互元素
  - 通过适当的分页避免内容截断
  - 高质量矢量图形渲染
  - **自动展开折叠内容**：导出前临时展开所有 `.collapsed`、`details` 和 `.hidden` 元素，然后恢复
  - **ECharts 支持**：自动从本地文件内联 ECharts 库，确保图表在离线 PDF 中渲染
    - 在 PDF 生成前对所有图表实例强制执行 `resize()`
    - 注入 CSS 防止图表跨页分割（`page-break-inside: avoid`）
    - 调整大小后等待布局稳定（2 秒）
- **回退方法**：客户端 `html2canvas` + `jsPDF`（旧版，有限制）
  - 当 Playwright 不可用时使用
  - 可能在页面边界处截断文本/图像
  - 超链接渲染为纯文本
  - 同样在捕获前自动展开折叠内容

**实现**：参见 [src/utils/pdf_exporter.py](src/utils/pdf_exporter.py) 的服务器端逻辑和 [src/web/app.py](src/web/app.py) 中的 `/api/export_pdf` 端点。[index.html](src/web/templates/index.html) 中的前端逻辑处理 DOM 操作以展开/恢复折叠元素。

### 错误处理
- Schema 验证失败返回 `{"error": "description"}` JSON
- LLM API 错误通过 `send_web_event("error", ...)` 冒泡到前端
- 浏览器自动化失败（百度/必应）静默回退到雅虎/Mojeek

## 集成点

### 添加新搜索引擎
在 [src/utils/search_utils.py](src/utils/search_utils.py) 中按照以下模式实现：
1. 添加 `{engine}_search(query, max_results)` 函数
2. 返回格式化字符串：`"# {engine} 搜索结果\n\n## {title}\n{snippet}\n{url}\n\n"`
3. 在 `SEARCH_PROVIDER` 配置和 `search_if_needed()` 路由中注册

### 添加新智能体角色
1. 在 [src/agents/schemas.py](src/agents/schemas.py) 中定义 Pydantic schema
2. 在 [src/agents/langchain_agents.py](src/agents/langchain_agents.py) 中添加提示词模板
3. 更新 `run_full_cycle()` 以并行编排新角色
4. 在 [src/web/templates/index.html](src/web/templates/index.html) 中添加前端面板

### 质疑官集成模式
质疑官角色遵循**挑战 → 修订闭环**：
1. **分解阶段**：`make_devils_advocate_chain(cfg, stage="decomposition")` → 挑战议长的议题分解
2. **总结阶段**：`make_devils_advocate_chain(cfg, stage="summary")` → 挑战每轮的综合
3. **修订触发**：如果 `critical_issues` 非空或 `overall_assessment` 中包含"严重"，议长必须修订
4. **最终轮次**：无论严重程度如何都强制修订（确保报告质量）

### 议长轮次感知提示
议长根据轮次上下文调整行为：
- `make_leader_chain(cfg, is_final_round=False)`: 中间轮次 - 包含 `next_round_focus` 字段
- `make_leader_chain(cfg, is_final_round=True)`: 最终轮次 - 聚焦全局综合，`next_round_focus=null`

### 模型适配器扩展
在 [src/agents/model_adapter.py](src/agents/model_adapter.py) 中添加新后端：
- 为新后端类型实现 `call_model_with_retry()` case
- 处理 API 特定的认证、端点、响应格式
- 确保 JSON 解析与 `clean_json_string()` 兼容

## 需要审查的关键文件

- [src/agents/langchain_agents.py](src/agents/langchain_agents.py): 核心编排、搜索循环、提示词模板
- [src/agents/schemas.py](src/agents/schemas.py): 所有智能体输出的 Pydantic 模型
- [src/web/app.py](src/web/app.py): Flask 端点、子进程管理、SSE 类更新
- [src/utils/search_utils.py](src/utils/search_utils.py): 多引擎搜索与相关性检查
- [src/config.py](src/config.py): 所有 API 密钥和提供商配置
- [docs/workflow.md](docs/workflow.md): 智能体协作流程的 Mermaid 图

## 常见陷阱

1. **破坏盲评**：永远不要在同一层级内将一个智能体的输出传递给另一个（例如，策论家-1 看到策论家-2 的输出）。使用独立的 `PromptTemplate` 链。

2. **搜索循环无限循环**：在提供搜索结果后始终注入"严禁再次输出 [SEARCH:]"指令。某些模型会忽略此指令 - 添加显式重试限制。

3. **JSON 解析失败**：尽管有提示，LLM 经常在 JSON 前后添加注释。`clean_json_string()` 使用括号匹配来提取有效 JSON。为关键 schema 添加重试逻辑。

4. **DrissionPage 挂起**：使用临时用户目录（`tempfile.mkdtemp()`）和随机延迟（`time.sleep(random.uniform(1, 3))`）以防止并行搜索中的浏览器实例冲突。

5. **Playwright 安装**：PDF 导出需要 Playwright 浏览器自动化。如果未安装，系统会回退到旧版 jsPDF（有质量问题）。通过 `pip install playwright && playwright install chromium` 安装

6. **ECharts CDN 阻塞**：报告必须使用本地 `/static/vendor/echarts.min.js`。CDN 链接在跟踪保护的浏览器或离线环境中会失败。

7. **PDF 导出质量**：jsPDF 对复杂布局有限制 - 文本/图像可能在页面边界处被截断，超链接被渲染为纯文本。对于生产报告，建议 HTML 导出或基于画布的截图。

## 调试技巧

- 启用详细日志：在 [src/config.py](src/config.py) 中设置 `LOG_LEVEL=DEBUG`
- 检查 `workspaces/{session}/history.json` 以查看完整的智能体对话历史
- 使用 `/api/status` 端点检查实时讨论状态
- 使用 `tests/test_final_search.py --engine baidu --query "测试"` 单独测试搜索引擎
- 对于 schema 验证问题，检查前端的 `discussion_events` 数组以查看原始 LLM 输出

## Git 提交指南
- 编写清晰、描述性的提交消息总结更改，只用一句话
- 未经用户同意不要提交和推送代码
- 推送前不要添加

## 开发风格与协作规则

### 沟通风格
- **语言**：所有讨论和解释使用中文
- **简洁回应**：用户偏好简短、直接的答案；避免不必要的冗长
- **设计优先**：在实现前始终讨论和比较设计方案
- **决策格式**：用户通常用"我倾向于A"这样的短语做决定

### 设计讨论模式
提出新功能或更改时：
1. **提供多个选项**：提供 2-3 个替代方案（方案A/B/C）
2. **比较权衡**：用优缺点、成本分析和复杂度评估进行结构化比较
3. **推荐**：给出明确的推荐和理由
4. **等待批准**：在用户确认方案前不要开始实现

示例格式：
```
## 方案A：[名称]
**优点**：✅ ...
**缺点**：❌ ...

## 方案B：[名称]
**优点**：✅ ...
**缺点**：❌ ...

## 💡 推荐：方案X，因为...
```

### 实现工作流
1. **理解需求**：在提出解决方案前澄清目标
2. **设计优先**：讨论架构和方法
3. **创建待办列表**：对多步骤任务使用 `manage_todo_list`
4. **增量实现**：一次完成一个待办，立即标记为已完成
5. **验证**：每次更改后运行测试或检查
6. **总结**：提供简要的完成总结和关键更改

### 质量原则
- **报告焦点**：最终输出应该是精美的解决方案，而非过程记录
- **隐藏内部细节**：不要在最终交付物中暴露讨论过程（例如"质疑官提出..."或"策论家认为..."）
- **闭环设计**：确保反馈机制完成循环（例如，质疑官反馈 → 议长修订）
- **优雅降级**：操作失败时始终提供回退行为

### 代码更改偏好
- **最小化更改**：进行有针对性的编辑而非重写大段代码
- **保留模式**：遵循现有代码风格和约定
- **编辑后测试**：通过语法检查或单元测试验证更改
- **清理**：使用后删除临时文件或脚本

## 编码策略
- 遵循现有代码模式以保持一致性
- 编写单一职责的模块化函数
- 为复杂逻辑部分添加注释
- 为新功能或错误修复编写单元测试
- 提交前审查更改以避免意外修改
- 在适用的地方使用现有工具函数
- 功能级开发应首先给出设计和待办事项

## 测试策略
- 使用 `pytest` 运行 `tests/` 目录中的单元测试
- 在重大更改后运行基线测试以确保无回归
