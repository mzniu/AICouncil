# AICouncil Development Guide

## Architecture Overview

AICouncil is a multi-agent deliberation system that simulates a council ("元老院") where AI agents debate complex issues through structured rounds. The architecture follows a strict **role-based blind evaluation** pattern:

- **Leader** (议长): Decomposes issues, orchestrates discussion flow, synthesizes final reports
- **Planners** (策论家): Generate solution proposals in parallel (blind evaluation - no cross-agent visibility)
- **Auditors** (监察官): Critically review planner proposals in parallel (blind evaluation)
- **Reporter** (记录员): Tracks and documents the entire deliberation process
- **Report Auditor** (报告审核官): Revises reports based on user feedback while maintaining factual accuracy

**Critical Design Principle**: Agents operate in **blind evaluation mode** - each agent cannot see outputs from other agents in the same role tier until the Leader synthesizes them. This is enforced through independent LangChain execution contexts.
**Critical Principle**: Don't commit and push the code.
## Core Workflow

1. **Planning Phase**: Leader decomposes issue into `key_questions` and designs report structure
2. **Iterative Discussion** (configurable rounds): 
   - Planners generate proposals → Auditors critique → Leader synthesizes
   - Each role tier executes in parallel using `ThreadPoolExecutor`
3. **Synthesis Phase**: Leader creates final summary → Reporter generates HTML report with embedded ECharts

**Search Integration**: Agents can trigger web searches mid-execution using `[SEARCH: query]` tags. The system detects these, fetches results via multi-engine search (Baidu/Bing/Yahoo/Mojeek/DuckDuckGo), and re-injects results into the agent's context for a second pass. Search is implemented as a **Requests-First architecture** (Yahoo/Mojeek use pure requests; Baidu/Bing fall back to DrissionPage for JavaScript rendering).

## Model Configuration

**Multi-Backend Support**: The system uses a unified `ModelConfig` abstraction ([src/agents/model_adapter.py](src/agents/model_adapter.py)) supporting:
- `deepseek`: DeepSeek API (default: deepseek-reasoner with thinking content support)
- `openai`: OpenAI/compatible APIs
- `openrouter`: OpenRouter with per-agent model selection
- `aliyun`: Aliyun DashScope (Qwen models)
- `ollama`: Local models via Ollama HTTP API

**Per-Agent Configuration**: You can override models for specific agents via `agent_configs` (e.g., use GPT-4 for Leader, Gemini for Planners). See [src/web/app.py](src/web/app.py) `/api/start` endpoint.

**Reasoning Content**: DeepSeek R1 models return `generation_info.reasoning` which is streamed separately to the UI. Handle this in [src/agents/langchain_llm.py](src/agents/langchain_llm.py) `AdapterLLM._stream` method.

## Key Code Patterns

### JSON Output Enforcement

All agents MUST output strict JSON matching Pydantic schemas ([src/agents/schemas.py](src/agents/schemas.py)). The system:
1. Cleans LLM output using `clean_json_string()` (strips markdown code fences)
2. Parses with Pydantic
3. Retries up to 2 times on validation failure
4. Returns error JSON if all retries fail

**Critical**: Prompts use multi-language instructions (Chinese + English) emphasizing "NO TEXT OUTSIDE JSON" to combat LLM verbosity.

### Streaming + Search Loop

See [src/agents/langchain_agents.py](src/agents/langchain_agents.py) `stream_agent_output()`:
- Streams LLM chunks to Web UI via `send_web_event()`
- Detects `[SEARCH:]` tags mid-stream
- Pauses generation, executes multi-engine parallel search
- Re-prompts agent with search results + "**严禁再次输出 [SEARCH:]**" instruction

### Web Interface Communication

Flask app ([src/web/app.py](src/web/app.py)) spawns discussion as subprocess (`demo_runner.py`). Agents POST events to `/api/update`:
```python
{"type": "agent_action", "agent_name": "策论家-1", "role_type": "planner", "content": "...", "chunk_id": "uuid"}
```
Frontend polls `/api/status` and displays real-time thinking process in collapsible panels.

## Development Workflows

### Running Locally
```bash
# Install dependencies (use venv)
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# Install Playwright browsers for PDF export (optional but recommended)
playwright install chromium

# Configure API keys
cp src/config_template.py src/config.py
# Edit src/config.py with your API keys

# Start web UI
python src/web/app.py  # Access http://127.0.0.1:5000

# OR run headless discussion
python src/agents/demo_runner.py --issue "你的议题" --backend deepseek --rounds 2
```

### Testing Search Engines
Test individual search providers in [tests/](tests/):
- `test_final_search.py`: Tests all search engines
- `verify_baidu_fix.py`: Validates Baidu HTML parsing

### Browser Dependencies
Baidu/Bing require Chrome or Edge for DrissionPage automation. Set `BROWSER_PATH` in [src/config.py](src/config.py) or let `browser_utils.find_browser_path()` auto-detect. Yahoo/Mojeek work without browsers.

## Project-Specific Conventions

### File Structure
- **Workspaces**: Each discussion creates `workspaces/{timestamp}_{uuid}/` with `history.json`, `round_N_data.json`, and `report.html`
- **Presets**: Council configurations saved to root `council_presets.json` (backend, rounds, agent counts)
- **Logs**: Main log at `aicouncil.log` (or `LOG_FILE` env var)

### HTML Reports
Reports are self-contained HTML with:
- Embedded ECharts 5.4.3 at `/static/vendor/echarts.min.js` (NO CDN dependency for iframe/offline support)
- Tailwind CSS classes for styling
- Export buttons supporting HTML/Screenshot/PDF formats

**PDF Export**: 
- **Primary method**: Server-side Playwright rendering (requires `pip install playwright && playwright install chromium`)
  - Preserves hyperlinks and interactive elements
  - Avoids content truncation with proper pagination
  - High-quality vector graphics rendering
  - **Auto-expands collapsed content**: All `.collapsed`, `details`, and `.hidden` elements are temporarily expanded before export, then restored
  - **ECharts support**: Automatically inlines ECharts library from local file to ensure charts render in offline PDFs
    - Forces `resize()` on all chart instances before PDF generation
    - Injects CSS to prevent charts from being split across pages (`page-break-inside: avoid`)
    - Waits for layout stabilization (2s) after resize
- **Fallback method**: Client-side `html2canvas` + `jsPDF` (legacy, has limitations)
  - Used when Playwright is not available
  - May truncate text/images at page boundaries
  - Hyperlinks rendered as plain text
  - Also auto-expands collapsed content before capture

**Implementation**: See [src/utils/pdf_exporter.py](src/utils/pdf_exporter.py) for server-side logic and `/api/export_pdf` endpoint in [src/web/app.py](src/web/app.py). Frontend logic in [index.html](src/web/templates/index.html) handles DOM manipulation to expand/restore collapsed elements.

### Error Handling
- Schema validation failures return `{"error": "description"}` JSON
- LLM API errors bubble up with `send_web_event("error", ...)` to frontend
- Browser automation failures (Baidu/Bing) fall back to Yahoo/Mojeek silently

## Integration Points

### Adding New Search Engines
Implement in [src/utils/search_utils.py](src/utils/search_utils.py) following the pattern:
1. Add `{engine}_search(query, max_results)` function
2. Return formatted string: `"# {engine} 搜索结果\n\n## {title}\n{snippet}\n{url}\n\n"`
3. Register in `SEARCH_PROVIDER` config and `search_if_needed()` router

### Adding New Agent Roles
1. Define Pydantic schema in [src/agents/schemas.py](src/agents/schemas.py)
2. Add prompt template in [src/agents/langchain_agents.py](src/agents/langchain_agents.py)
3. Update `run_full_cycle()` to orchestrate new role in parallel
4. Add frontend panel in [src/web/templates/index.html](src/web/templates/index.html)

### Model Adapter Extension
Add new backend in [src/agents/model_adapter.py](src/agents/model_adapter.py):
- Implement `call_model_with_retry()` case for new backend type
- Handle API-specific auth, endpoints, response formats
- Ensure JSON parsing with `clean_json_string()` compatibility

## Critical Files to Review

- [src/agents/langchain_agents.py](src/agents/langchain_agents.py): Core orchestration, search loop, prompt templates
- [src/agents/schemas.py](src/agents/schemas.py): Pydantic models for all agent outputs
- [src/web/app.py](src/web/app.py): Flask endpoints, subprocess management, SSE-like updates
- [src/utils/search_utils.py](src/utils/search_utils.py): Multi-engine search with relevance checking
- [src/config.py](src/config.py): All API keys and provider configurations
- [docs/workflow.md](docs/workflow.md): Mermaid diagram of agent collaboration flow

## Common Pitfalls

1. **Breaking Blind Evaluation**: Never pass one agent's output to another within the same tier (e.g., Planner-1 seeing Planner-2's output). Use independent `PromptTemplate` chains.

2. **Search Loop Infinite Loops**: Always inject "严禁再次输出 [SEARCH:]" instruction after providing search results. Some models ignore this - add explicit retry limits.

3. **JSON Parsing Failures**: LLMs often add commentary before/after JSON despite prompts. `clean_json_string()` uses bracket matching to extract valid JSON. Add retry logic for critical schemas.

4. **DrissionPage Hangs**: Use temporary user directories (`tempfile.mkdtemp()`) and random delays (`time.sleep(random.uniform(1, 3))`) to prevent browser instance conflicts in parallel searches.
laywright Installation**: PDF export requires Playwright browser automation. If not installed, system falls back to legacy jsPDF (with quality issues). Install via `pip install playwright && playwright install chromium`
5. **ECharts CDN Blocking**: Reports must use local `/static/vendor/echarts.min.js`. CDN links fail in tracking-protected browsers or offline contexts.

6. **PDF Export Quality**: jsPDF has limitations with complex layouts - text/images may be cut off at page boundaries, and hyperlinks are rendered as plain text. For production reports, recommend HTML export or canvas-based screenshots.

## Debugging Tips

- Enable verbose logging: `LOG_LEVEL=DEBUG` in [src/config.py](src/config.py)
- Inspect `workspaces/{session}/history.json` for full agent conversation history
- Use `/api/status` endpoint to check real-time discussion state
- Test search engines individually with `tests/test_final_search.py --engine baidu --query "测试"`
- For schema validation issues, check `discussion_events` array in frontend for raw LLM outputs

## Git Commit Guidelines
- Write clear, descriptive commit messages summarizing changes, only one sentence
- DON'T commit and push code without user's consent
- DON'T add before pushing

## Development Style & Collaboration Rules

### Communication Style
- **Language**: Use Chinese for all discussions and explanations
- **Concise Responses**: User prefers brief, direct answers; avoid unnecessary verbosity
- **Design-First**: Always discuss and compare design alternatives before implementation
- **Decision Format**: User typically responds with short phrases like "我倾向于A" to make decisions

### Design Discussion Pattern
When proposing a new feature or change:
1. **Present Multiple Options**: Provide 2-3 alternative approaches (方案A/B/C)
2. **Compare Trade-offs**: Use structured comparison with pros/cons, cost analysis, and complexity assessment
3. **Recommend**: Give a clear recommendation with reasoning
4. **Wait for Approval**: Don't start implementation until user confirms the approach

Example format:
```
## 方案A：[名称]
**优点**：✅ ...
**缺点**：❌ ...

## 方案B：[名称]
**优点**：✅ ...
**缺点**：❌ ...

## 💡 推荐：方案X，因为...
```

### Implementation Workflow
1. **Understand Requirements**: Clarify the goal before proposing solutions
2. **Design First**: Discuss architecture and approach
3. **Create Todo List**: Use `manage_todo_list` for multi-step tasks
4. **Implement Incrementally**: Complete one todo at a time, mark as completed immediately
5. **Verify**: Run tests or checks after each change
6. **Summarize**: Provide brief completion summary with key changes

### Quality Principles
- **Report Focus**: Final outputs should be polished solutions, not process records
- **Hide Internal Details**: Don't expose discussion process (e.g., "质疑官提出..." or "策论家认为...") in final deliverables
- **Closed-Loop Design**: Ensure feedback mechanisms complete the loop (e.g., DA feedback → Leader revision)
- **Graceful Degradation**: Always provide fallback behavior when operations fail

### Code Change Preferences
- **Minimal Changes**: Make targeted edits rather than rewriting large sections
- **Preserve Patterns**: Follow existing code style and conventions
- **Test After Edit**: Verify changes with syntax checks or unit tests
- **Clean Up**: Remove temporary files or scripts after use

## Coding Strategies
- Follow existing code patterns for consistency
- Write modular functions with single responsibilities
- Add comments for complex logic sections
- Write unit tests for new features or bug fixes
- Review changes before committing to avoid unintended modifications
- Use existing utility functions where applicable
- Feature level development should give the design and todos first

## Testing Strategies
- Run unit tests in `tests/` directory using `pytest`
- Run baseline tests after major changes to ensure no regressions
