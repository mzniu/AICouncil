# AICouncil API 规范

## 概述

AICouncil 提供 RESTful API，供前端或外部系统调用议事功能。本文档定义核心 API 端点。

---

## 基础信息

- **Base URL**: `http://localhost:5000/api`
- **认证**: 本地部署无需认证，企业版可增加 Bearer Token
- **Content-Type**: `application/json`

---

## 端点列表

### 1. 系统状态

**接口**: `GET /api/status`

**说明**: 获取系统当前状态。

**响应**:

```json
{
  "is_running": false,
  "config": {
    "issue": "人工智能对传统教育的冲击与变革路径",
    "backend": "deepseek",
    "model": "deepseek-reasoner",
    "reasoning": true,
    "rounds": 3,
    "planners": 2,
    "auditors": 2
  },
  "browser_found": true
}
```

**字段说明**:

- `is_running`: 是否有讨论正在进行
- `config`: 当前/最近一次讨论配置
- `browser_found`: 是否找到浏览器（用于搜索功能）

---

### 2. 启动讨论

**接口**: `POST /api/start`

**说明**: 启动一次新的议事流程。

**请求体**:

```json
{
  "issue": "人工智能对传统教育的冲击与变革路径",
  "backend": "deepseek",
  "model": "deepseek-reasoner",
  "reasoning": true,
  "rounds": 3,
  "planners": 2,
  "auditors": 2,
  "agent_configs": {
    "leader": {"type": "openai", "model": "gpt-4"},
    "planner_1": {"type": "openrouter", "model": "google/gemini-pro"}
  }
}
```

**参数说明**:

| 参数            | 类型     | 必填 | 说明                                                         |
|---------------|--------|------|--------------------------------------------------------------|
| `issue`       | string | ✅    | 议题描述                                                      |
| `backend`     | string | ❌    | 后端模型（`deepseek`/`openrouter`/`openai`/`aliyun`/`ollama`），默认 `deepseek` |
| `model`       | string | ❌    | 全局模型名称（覆盖默认配置）                                    |
| `reasoning`   | bool/object | ❌ | 是否启用推理模式（DeepSeek R1）                               |
| `rounds`      | int    | ❌    | 讨论轮数，默认 3                                              |
| `planners`    | int    | ❌    | 策论家数量，默认 2                                            |
| `auditors`    | int    | ❌    | 监察官数量，默认 2                                            |
| `agent_configs` | object | ❌   | 为特定 agent 指定模型配置                                    |

**响应**:

- **成功 (200)**:

```json
{
  "status": "ok"
}
```

- **失败 (400)**:

```json
{
  "status": "error",
  "message": "议题不能为空"
}
```

或:

```json
{
  "status": "error",
  "message": "讨论正在进行中"
}
```

---

### 3. 停止讨论

**接口**: `POST /api/stop`

**说明**: 强制终止当前讨论流程。

**响应**:

- **成功 (200)**:

```json
{
  "status": "ok",
  "message": "已强制停止后台进程"
}
```

- **失败 (400)**:

```json
{
  "status": "error",
  "message": "没有正在运行的讨论"
}
```

---

### 4. 获取事件流

**接口**: `GET /api/events`

**说明**: 获取讨论过程中的所有事件、日志和最终报告。

**响应**:

```json
{
  "events": [
    {
      "type": "system_start",
      "issue": "AI 对教育的影响",
      "session_id": "20251229_101234_abc123"
    },
    {
      "type": "round_start",
      "round": 1
    },
    {
      "type": "agent_action",
      "agent_name": "策论家-1",
      "role_type": "planner",
      "content": "{...JSON...}",
      "chunk_id": "uuid-xxx"
    },
    {
      "type": "agent_thinking",
      "agent_name": "策论家-1",
      "thinking": "推理过程...",
      "chunk_id": "uuid-xxx"
    },
    {
      "type": "final_report",
      "content": "<html>...</html>"
    }
  ],
  "logs": [
    "[INFO] 系统启动",
    "[DEBUG] 加载配置"
  ],
  "final_report": "<html>...完整报告 HTML...</html>"
}
```

**事件类型**:

- `system_start`: 讨论启动
- `round_start`: 轮次开始
- `agent_action`: Agent 输出（JSON 结构）
- `agent_thinking`: 推理过程（DeepSeek R1 等模型）
- `final_report`: 最终报告生成
- `user_intervention`: 用户干预
- `search_triggered`: 触发搜索
- `error`: 错误消息

---

### 5. 更新事件（内部接口）

**接口**: `POST /api/update`

**说明**: 由后台进程调用，向前端推送事件更新（前端不应直接调用）。

**请求体**:

```json
{
  "type": "agent_action",
  "agent_name": "策论家-1",
  "role_type": "planner",
  "content": "...",
  "chunk_id": "uuid-xxx"
}
```

或:

```json
{
  "type": "log",
  "content": "[INFO] 完成第 1 轮讨论"
}
```

或:

```json
{
  "type": "final_report",
  "content": "<html>...</html>"
}
```

**响应**:

```json
{
  "status": "ok"
}
```

---

### 6. 干预讨论

**接口**: `POST /api/intervene`

**说明**: 在讨论中注入人工意见。

**请求体**:

```json
{
  "content": "请特别关注农村地区的教育数字化鸿沟问题"
}
```

**响应**:

- **成功 (200)**:

```json
{
  "status": "ok"
}
```

- **失败 (400)**:

```json
{
  "status": "error",
  "message": "没有正在进行的讨论"
}
```

或:

```json
{
  "status": "error",
  "message": "干预内容不能为空"
}
```

或:

```json
{
  "status": "error",
  "message": "工作区不存在"
}
```

---

### 7. 重新生成报告

**接口**: `POST /api/rereport`

**说明**: 使用不同模型重新生成最终报告。

**请求体**:

```json
{
  "backend": "openai"
}
```

**响应**:

- **成功 (200)**:

```json
{
  "status": "ok"
}
```

- **失败 (400)**:

```json
{
  "status": "error",
  "message": "讨论正在进行中，请稍后再试"
}
```

或:

```json
{
  "status": "error",
  "message": "未找到当前会话 ID"
}
```

或 (404):

```json
{
  "status": "error",
  "message": "工作区不存在: 20251229_101234_abc123"
}
```

---

### 8. 列出工作区

**接口**: `GET /api/workspaces`

**说明**: 列出所有历史讨论工作区。

**响应**:

```json
{
  "status": "success",
  "workspaces": [
    {
      "id": "20251229_101234_abc123",
      "issue": "AI 对教育的影响",
      "timestamp": "20251229"
    },
    {
      "id": "20251228_205612_a8309324",
      "issue": "未知议题",
      "timestamp": "20251228"
    }
  ]
}
```

**注意**: 按时间倒序排列（最新的在前）。

---

### 9. 加载工作区

**接口**: `GET /api/load_workspace/<session_id>`

**说明**: 加载指定工作区的历史讨论数据。

**路径参数**:

- `session_id`: 工作区 ID（如 `20251229_101234_abc123`）

**响应**:

- **成功 (200)**:

```json
{
  "status": "success",
  "issue": "AI 对教育的影响",
  "rounds": 3
}
```

- **失败 (404)**:

```json
{
  "status": "error",
  "message": "工作区不存在"
}
```

或 (500):

```json
{
  "status": "error",
  "message": "具体错误信息"
}
```

**副作用**: 加载成功后会自动填充 `discussion_events`、`final_report` 等全局状态。

---

### 10. 删除工作区

**接口**: `DELETE /api/delete_workspace/<session_id>`

**说明**: 删除指定工作区及其所有文件。

**路径参数**:

- `session_id`: 工作区 ID

**响应**:

- **成功 (200)**:

```json
{
  "status": "success",
  "message": "工作区已删除"
}
```

- **失败 (404)**:

```json
{
  "status": "error",
  "message": "工作区不存在"
}
```

或 (500):

```json
{
  "status": "error",
  "message": "删除失败: 具体原因"
}
```

---

### 11. 重置状态

**接口**: `POST /api/reset`

**说明**: 清空前端缓存的事件、日志、报告和配置。

**响应**:

```json
{
  "status": "success"
}
```

---

## 配置管理

### 获取配置

**接口**: `GET /api/config`

**说明**: 获取当前 API Key 和搜索配置（**注意安全风险**）。

**响应**:

```json
{
  "status": "success",
  "config": {
    "DEEPSEEK_API_KEY": "sk-xxx",
    "OPENAI_API_KEY": "sk-xxx",
    "OPENROUTER_API_KEY": "sk-xxx",
    "ALIYUN_API_KEY": "sk-xxx",
    "TAVILY_API_KEY": "tvly-xxx",
    "SEARCH_PROVIDER": "tavily",
    "BROWSER_PATH": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
  }
}
```

### 更新配置

**接口**: `POST /api/config`

**说明**: 更新 `config.py` 中的 API Key 配置。

**请求体**:

```json
{
  "DEEPSEEK_API_KEY": "sk-new-key",
  "SEARCH_PROVIDER": "duckduckgo",
  "BROWSER_PATH": ""
}
```

**响应**:

- **成功 (200)**:

```json
{
  "status": "success"
}
```

- **失败 (500)**:

```json
{
  "status": "error",
  "message": "具体错误信息"
}
```

**注意**: 此接口会直接修改 `src/config.py` 文件，并通过正则表达式替换 `os.getenv()` 的默认值。

---

## 预设管理

### 获取预设列表

**接口**: `GET /api/presets`

**说明**: 获取所有保存的议事配置预设。

**响应**:

```json
{
  "status": "success",
  "presets": {
    "快速测试": {
      "backend": "deepseek",
      "rounds": 1,
      "planners": 1,
      "auditors": 1
    },
    "深度分析": {
      "backend": "openai",
      "model": "gpt-4-turbo",
      "rounds": 5,
      "planners": 3,
      "auditors": 3
    }
  }
}
```

### 保存预设

**接口**: `POST /api/presets`

**说明**: 保存新的议事配置预设。

**请求体**:

```json
{
  "name": "快速测试",
  "config": {
    "backend": "deepseek",
    "rounds": 1,
    "planners": 1,
    "auditors": 1
  }
}
```

**响应**:

- **成功 (200)**:

```json
{
  "status": "success"
}
```

- **失败 (400)**:

```json
{
  "status": "error",
  "message": "名称和配置不能为空"
}
```

### 删除预设

**接口**: `DELETE /api/presets/<name>`

**说明**: 删除指定预设。

**路径参数**:

- `name`: 预设名称（如 `快速测试`）

**响应**:

- **成功 (200)**:

```json
{
  "status": "success"
}
```

- **失败 (404)**:

```json
{
  "status": "error",
  "message": "未找到该配置"
}
```

---

## 模型列表

### 获取 OpenRouter 模型

**接口**: `GET /api/openrouter/models`

**说明**: 获取 OpenRouter 支持的模型列表。

**响应**:

```json
[
  {
    "id": "openai/gpt-4-turbo",
    "name": "GPT-4 Turbo",
    "context_length": 128000,
    "pricing": {
      "prompt": "0.01",
      "completion": "0.03"
    }
  },
  {
    "id": "google/gemini-pro",
    "name": "Gemini Pro",
    "context_length": 32768
  }
]
```

### 获取 DeepSeek 模型

**接口**: `GET /api/deepseek/models`

**说明**: 获取 DeepSeek 支持的模型列表。

**响应**:

```json
[
  {
    "id": "deepseek-reasoner",
    "name": "DeepSeek Reasoner (R1)",
    "supports_reasoning": true
  },
  {
    "id": "deepseek-chat",
    "name": "DeepSeek Chat"
  }
]
```

---

## PDF 导出

### 检查 Playwright 状态

**接口**: `GET /api/playwright/status`

**说明**: 检查 Playwright 是否已安装及浏览器状态。

**响应**:

```json
{
  "status": "success",
  "data": {
    "installed": true,
    "auto_install_supported": true,
    "browser_installed": true
  }
}
```

### 安装 Playwright

**接口**: `POST /api/playwright/install`

**说明**: 自动安装 Playwright + Chromium 浏览器。

**响应**:

- **成功 (200)**:

```json
{
  "status": "success",
  "message": "Playwright 安装成功！",
  "logs": [
    "开始安装 Playwright...",
    "下载 Chromium...",
    "安装完成"
  ]
}
```

- **失败 (500)**:

```json
{
  "status": "error",
  "message": "Playwright 安装失败",
  "logs": ["错误详情..."]
}
```

### 检查 PDF 导出可用性

**接口**: `GET /api/pdf_available`

**说明**: 快速检查 PDF 导出功能是否可用。

**响应**:

```json
{
  "available": true,
  "message": "Playwright已安装"
}
```

或:

```json
{
  "available": false,
  "message": "需要安装Playwright: pip install playwright && playwright install chromium"
}
```

### 导出 PDF

**接口**: `POST /api/export_pdf`

**说明**: 使用 Playwright 将 HTML 报告导出为高质量 PDF（保留超链接）。

**请求体**:

```json
{
  "html": "<html>...完整报告 HTML...</html>",
  "filename": "report_20251229.pdf"
}
```

**参数说明**:

| 参数       | 类型   | 必填 | 说明                     |
|----------|--------|------|--------------------------|
| `html`   | string | ✅    | 完整的 HTML 报告内容      |
| `filename` | string | ❌  | 文件名，默认 `report.pdf` |

**响应**:

- **成功 (200)**: 返回 PDF 文件流（`application/pdf`）

- **失败 (400)**:

```json
{
  "status": "error",
  "message": "Playwright未安装。请点击【安装Playwright】按钮或运行: pip install playwright && playwright install chromium"
}
```

或:

```json
{
  "status": "error",
  "message": "HTML内容不能为空"
}
```

- **失败 (500)**:

```json
{
  "status": "error",
  "message": "PDF生成失败，请查看日志"
}
```

或:

```json
{
  "status": "error",
  "message": "导出失败: 具体错误原因"
}
```

---

## 错误代码

| HTTP 状态码 | 含义                |
|-----------|-------------------|
| 200       | 成功                |
| 400       | 请求参数错误          |
| 404       | 资源不存在            |
| 500       | 服务器内部错误        |

**标准错误响应**:

```json
{
  "status": "error",
  "message": "具体错误描述"
}
```

---

## 开发说明

### 身份认证

当前版本为本地部署，未实现身份认证。企业版建议使用：

- JWT Token
- API Key
- OAuth 2.0

### 速率限制

建议在生产环境添加：

- IP 级别限流（如 100 请求/分钟）
- 用户级别配额
- 讨论并发数限制

### 错误处理

所有接口遵循统一错误格式：

```json
{
  "status": "error",
  "message": "用户可读的错误描述"
}
```

### CORS 配置

如需跨域访问，需在 Flask 配置中添加：

```python
from flask_cors import CORS
CORS(app, origins=["http://localhost:3000"])
```
