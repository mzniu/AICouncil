# API 规范（最小可用）

说明：以下为 MVP 的最小 REST API 设计示例，后续可扩展为 GraphQL/Socket 等。

## 环境说明
- 所有请求/响应均使用 JSON。
- 身份认证与权限暂略（MVP 内部使用或通过简单 API Key）。

## 1. 提交议题

POST /api/v1/issues

请求体：
{
  "user_id": "string",
  "original_issue": "string",
  "constraints": "string (optional)"
}

返回：
{
  "issue_id": "string",
  "status": "accepted|error",
  "message": "string"
}

## 2. 查询讨论状态

GET /api/v1/issues/{issue_id}/status

返回：
{
  "issue_id": "string",
  "round": 1,
  "roles": [{"role":"策论家1","status":"DONE"}, ...],
  "progress": "string"
}

## 3. 获取报告

GET /api/v1/issues/{issue_id}/report

返回：
{
  "issue_id": "string",
  "report": { ... 议长汇总的 JSON 报告 ... }
}

## 4. 用户介入指令

POST /api/v1/issues/{issue_id}/intervene

请求体：
{
  "user_id": "string",
  "command": "string",
  "notes": "string (optional)"
}

返回：
{
  "issue_id": "string",
  "status": "accepted|rejected",
  "message": "string"
}

## 错误响应
统一返回：
{
  "error_code": "string",
  "message": "string",
  "details": {}
}


注：此规范为最小可用示例，实际实现时建议：
- 增加认证（JWT/API Key）
- 增加分页与查询过滤
- 增加速率限制与配额控制
