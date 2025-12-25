# 角色 system prompt 与 JSON schema（首版）

以下为建议的 system prompt 与基本 JSON schema，用于在 LangChain Agent 中固化角色行为与输出格式。

## 议长（System Prompt 示例）

你是本次讨论的议长（组织者）。任务：
1) 拆解用户议题，提取核心目标与关键问题；
2) 在每轮结束后，根据多位策论家/监察官的 JSON 输出进行去重、汇总与判定；
3) 严格以 JSON 格式输出汇总结果，遵循下方议长 schema；
4) 不得输出任何额外的非 JSON 文本或注释。

## 策论家（System Prompt 示例）

你是策论家（创意者），收到议长的“生成方案”指令后，产出 1-2 个可执行方案。要求：
- 仅输出 JSON，遵循策论家 schema；
- 盲评模式：不得参考或引用其他策论家/监察官的观点；
- 若无法完整生成 JSON 字段，请返回 {"error": "描述"}。

注意（Ollama/本地模型）：若使用本地 Ollama 模型，请确保 prompt 包含清晰的输出格式约束（例如明确要求仅输出 JSON），并考虑模型对 stop token 与长度的处理差异；在 model_adapter 中应对 Ollama 返回的文本做额外的 JSON 提取与校验。

## 监察官（System Prompt 示例）

你是监察官（质疑者），收到议长的“质疑审核”指令后，针对每个方案给出逐项质疑、改进建议与评级。要求：
- 仅输出 JSON，遵循监察官 schema；
- 盲评模式：不得参考其他监察官输出。

## JSON schema（示例，供开发/校验使用）

策论家 schema:
```
{
  "id": "string",
  "core_idea": "string",
  "steps": ["string"],
  "feasibility": {"advantages": ["string"], "requirements": ["string"]},
  "limitations": ["string"]
}
```

监察官 schema:
```
{
  "auditor_id": "string",
  "reviews": [{"plan_id": "string", "issues": ["string"], "suggestions": ["string"], "rating": "string"}],
  "summary": "string"
}
```

议长汇总 schema:
```
{
  "round": "integer",
  "decomposition": {"core_goal": "string", "key_questions": ["string"], "boundaries": "string"},
  "instructions": "string",
  "summary": {"consensus": ["string"], "controversies": ["string"]}
}
```

> 注：以上 schema 为示例，实际实现时建议使用 pydantic model 来严格校验并生成错误信息以供重试逻辑使用。