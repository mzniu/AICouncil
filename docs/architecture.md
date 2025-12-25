# 架构说明 — 元老院计划（MVP）

## 概览

系统采用前后端分离与分层架构，核心职责划分如下：

- 前端：议题输入、用户介入弹窗、报告预览（MVP 可省略前端日志展示）。
- 后端服务层：议题处理、角色调度、讨论规则引擎、报告生成、用户介入服务。
- Agent 层：基于 LangChain 的 Agent 实例（议长、策论家、监察官），并行执行盲评，议长负责汇总。
- 模型适配层：统一封装不同模型 API 的调用（demo 中使用模拟适配器）。
- 模型适配层：统一封装不同模型 API 的调用（demo 中使用模拟适配器）。支持远程闭源模型（如 OpenAI）以及本地模型（如 Ollama 本地运行模型）。
- 数据存储：MVP 阶段默认按“最大记录保留”，管理员可配置清理策略（MongoDB 建议）。

## 组件与数据流（简要）

```mermaid
graph TD
  U[用户] -->|提交议题| FE(前端)
  FE -->|POST /issue| BE[后端讨论服务]
  BE --> AG(议长 Agent)
  AG -->|下达指令| CA[策论家 Agents (并行)]
  CA --> AG
  AG -->|汇总| AU[监察官 Agents (并行)]
  AU --> AG
  AG --> BE
  BE --> DB[(数据存储)]
  BE -->|生成报告| REPORT[报告存储/导出]
```

## 主要设计要点

- 盲评隔离：为每个并行 Agent 使用独立 ExecutionContext/Chain，保证不共享其他 Agent 输出。
- 格式强约束：所有角色输出必须为 JSON，后端进行 schema 校验并在失败时短重试（最多2次），若仍失败则返回标准错误 JSON 以供人工/系统处理。
- 状态机驱动：角色调度使用状态机（WAIT -> SPEAKING -> DONE）来管理并发与超时（默认超时 30s）。
- 最小可运行：仓库包含本地 demo（不依赖真实模型 API）用于验证流程逻辑与 schema 校验。

- 本地模型支持（Ollama）：架构中模型适配层应提供统一接口（call_model(role, content, model_config)），当 model_config.type=="ollama" 时，通过本地 HTTP API 或 CLI 调用 Ollama 模型，并在后端进行 JSON 解析与 schema 校验。

## 可扩展点

- 支持模型切换（在模型适配层配置），可按业务需要替换为高性能或低成本模型。
- 后续可开放角色数量配置与自定义提示。
- 可接入监控与计量（API 调用成本、轮次统计、错误率等）。
