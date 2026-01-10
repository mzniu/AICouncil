# 架构说明  元老院计划（MVP）

## 概览

系统采用前后端分离与分层架构，核心职责划分如下：

- **前端 (Web UI)**：议题输入、实时流式展示讨论过程、报告预览与导出（HTML/截图/PDF）。
- **后端服务层 (Flask)**：议题处理、角色调度、讨论规则引擎、报告生成、用户介入服务。
- **Agent 层**：基于 LangChain 的 Agent 实例（议长、策论家、监察官、质疑官、记录官），并行执行盲评，议长负责汇总。
- **模型适配层**：统一封装不同模型 API 的调用，支持 DeepSeek、OpenAI、Azure OpenAI、Anthropic Claude、Google Gemini、OpenRouter、Ollama 等多后端。
- **搜索增强层**：多引擎联网搜索（Baidu、Bing、Yahoo、Google API、Tavily、DuckDuckGo、Mojeek），支持 ``[SEARCH: query]`` 标签触发。
- **数据存储**：按 Workspace 目录存储议事记录（JSON）、报告（HTML），支持历史记录加载与报告重新生成。

## 组件与数据流

### 传统模式（固定流程）

```mermaid
graph TD
    subgraph Frontend ["前端 (Web UI)"]
        U[用户] -->|输入议题| FE(Flask 页面)
        FE -->|实时轮询| STATUS[/api/status]
    end

    subgraph Backend ["后端服务层"]
        API[Flask API] -->|启动讨论| RUNNER[demo_runner.py]
        RUNNER --> CYCLE[run_full_cycle]
    end

    subgraph AgentLayer ["Agent 协作层"]
        CYCLE --> LEADER_INIT[议长: 议题拆解]
        LEADER_INIT --> DA_DECOMP[质疑官: 拆解质疑]
        DA_DECOMP -->|有问题| LEADER_REVISE[议长: 修正拆解]
        DA_DECOMP -->|通过| PLANNERS
        LEADER_REVISE --> PLANNERS
        
        subgraph PLANNERS ["策论家群体 (并行)"]
            P1[策论家 1]
            P2[策论家 N]
        end
        
        PLANNERS --> AUDITORS
        
        subgraph AUDITORS ["监察官群体 (并行)"]
            A1[监察官 1]
            A2[监察官 N]
        end
        
        AUDITORS --> LEADER_SUM[议长: 汇总]
        LEADER_SUM --> DA_SUM[质疑官: 总结质疑]
        DA_SUM -->|继续迭代| PLANNERS
        DA_SUM -->|达成共识| LEADER_FINAL[议长: 最终汇总]
        LEADER_FINAL --> REPORTER[记录官: 生成报告]
    end

    subgraph SearchLayer ["搜索增强层"]
        SEARCH_DETECT["[SEARCH: query] 检测"]
        MULTI_ENGINE["多引擎并行搜索"]
        INJECT["结果注入上下文"]
        
        LEADER_INIT & P1 & P2 & A1 & A2 & DA_DECOMP & DA_SUM -.->|触发| SEARCH_DETECT
        SEARCH_DETECT --> MULTI_ENGINE
        MULTI_ENGINE --> INJECT
    end

    subgraph ModelAdapter ["模型适配层"]
        ADAPTER[AdapterLLM]
        DEEPSEEK[DeepSeek]
        OPENAI[OpenAI]
        AZURE[Azure OpenAI]
        ANTHROPIC[Anthropic]
        GEMINI[Google Gemini]
        OPENROUTER[OpenRouter]
        OLLAMA[Ollama]
        
        ADAPTER --> DEEPSEEK & OPENAI & AZURE & ANTHROPIC & GEMINI & OPENROUTER & OLLAMA
    end

    subgraph Storage ["数据存储"]
        WS[Workspace 目录]
        HISTORY[history.json]
        ROUND_DATA[round_N_data.json]
        REPORT_HTML[report.html]
        
        WS --> HISTORY & ROUND_DATA & REPORT_HTML
    end

    %% 连接关系
    FE -->|POST /api/start| API
    RUNNER -->|POST /api/update| STATUS
    REPORTER --> REPORT_HTML
    CYCLE --> WS
    AgentLayer --> ADAPTER

    %% 样式
    style Frontend fill:#e0f2fe,stroke:#0284c7
    style Backend fill:#fef3c7,stroke:#d97706
    style AgentLayer fill:#f0fdf4,stroke:#16a34a
    style SearchLayer fill:#fefce8,stroke:#ca8a04,stroke-dasharray: 5 5
    style ModelAdapter fill:#f3e8ff,stroke:#9333ea
    style Storage fill:#f1f5f9,stroke:#64748b
```

### Meta-Orchestrator 模式（智能编排）

**新增组件**：
- **Meta-Orchestrator Agent**：根据需求自动选择框架、配置角色
- **Frameworks 框架库**：预定义框架（罗伯特议事规则、图尔敏论证模型、批判性思维）
- **Meta Tools**：工具函数库（list_roles、create_role、select_framework）
- **FrameworkEngine**：框架执行引擎，逐 Stage 运行

```mermaid
graph TD
    subgraph Frontend ["前端 (Web UI)"]
        U[用户] -->|输入议题 + 启用Meta模式| FE(Flask 页面)
        FE -->|实时轮询| STATUS[/api/status]
        FE -->|查看规划| PLAN_VIEW[规划方案]
    end

    subgraph Backend ["后端服务层"]
        API[Flask API] -->|POST /api/orchestrate| META_RUNNER[run_meta_orchestrator_flow]
        META_RUNNER -->|mode=plan_only| RETURN_PLAN[返回规划方案]
        META_RUNNER -->|mode=plan_and_execute| EXECUTE[execute_orchestration_plan]
    end

    subgraph MetaLayer ["Meta-Orchestrator 层 (Stage 0)"]
        META[Meta-Orchestrator Agent]
        META --> ANALYSIS[需求分析]
        
        ANALYSIS -->|Function Calling| TOOLS[Meta Tools]
        
        subgraph TOOLS_DETAIL ["Meta Tools"]
            TOOL1[list_roles: 列出可用角色]
            TOOL2[create_role: 创建新角色]
            TOOL3[select_framework: 匹配框架]
        end
        
        TOOLS --> TOOL3
        TOOL3 --> FRAMEWORKS[Frameworks 框架库]
        
        subgraph FRAMEWORKS_DETAIL ["预定义框架"]
            FW1[罗伯特议事规则<br/>Roberts Rules of Order]
            FW2[图尔敏论证模型<br/>Toulmin Model]
            FW3[批判性思维框架<br/>Critical Thinking]
        end
        
        FRAMEWORKS --> FW1 & FW2 & FW3
        TOOL3 --> SELECTED_FW[选中的框架]
        
        ANALYSIS --> TOOLS
        TOOLS --> TOOL1
        TOOL1 --> ROLE_MATCH[匹配现有角色]
        TOOLS --> TOOL2
        TOOL2 --> ROLE_CREATE[创建新角色<br/>调用 Role Designer]
        
        ROLE_MATCH & ROLE_CREATE & SELECTED_FW --> ORCHESTRATION_PLAN[OrchestrationPlan]
        ORCHESTRATION_PLAN --> PLAN_VIEW
    end

    subgraph FrameworkExecution ["FrameworkEngine 执行 (Stage 1-N)"]
        ENGINE[FrameworkEngine]
        ORCHESTRATION_PLAN --> ENGINE
        
        ENGINE --> STAGE1[Stage 1: 议题提出]
        STAGE1 --> STAGE2[Stage 2: 开放讨论<br/>Planner + Auditor]
        STAGE2 --> STAGE3[Stage 3: 质疑与反驳<br/>Devil's Advocate]
        STAGE3 --> STAGE4[Stage 4: 方案总结<br/>Leader]
        STAGE4 --> STAGE5[Stage 5: Reporter 生成报告]
        
        STAGE5 --> MERMAID_CHART[生成 Mermaid 流程图<br/>展示框架执行过程]
    end

    subgraph AgentLayer ["Agent 协作层"]
        ROLE_POOL[角色池]
        LEADER_R[Leader]
        PLANNER_R[Planner]
        AUDITOR_R[Auditor]
        DA_R[Devil's Advocate]
        REPORTER_R[Reporter]
        CUSTOM_R[自定义角色]
        
        ROLE_POOL --> LEADER_R & PLANNER_R & AUDITOR_R & DA_R & REPORTER_R & CUSTOM_R
        ENGINE -.->|调用| ROLE_POOL
    end

    subgraph SearchLayer ["搜索增强层"]
        SEARCH_DETECT["[SEARCH: query] 检测"]
        MULTI_ENGINE["多引擎并行搜索"]
        
        AgentLayer -.->|触发| SEARCH_DETECT
        SEARCH_DETECT --> MULTI_ENGINE
    end

    subgraph ModelAdapter ["模型适配层"]
        ADAPTER[AdapterLLM + Function Calling]
        DEEPSEEK[DeepSeek]
        OPENAI[OpenAI]
        ANTHROPIC[Anthropic]
        GEMINI[Google Gemini]
        
        ADAPTER --> DEEPSEEK & OPENAI & ANTHROPIC & GEMINI
    end

    subgraph Storage ["数据存储"]
        WS[Workspace 目录]
        DECOMP[decomposition.json:<br/>Meta-Orchestrator 规划]
        HISTORY[history.json:<br/>完整对话历史]
        ROUND_DATA[round_N_data.json:<br/>每轮数据]
        REPORT_HTML[report.html:<br/>含 Mermaid 流程图]
        
        WS --> DECOMP & HISTORY & ROUND_DATA & REPORT_HTML
        ORCHESTRATION_PLAN --> DECOMP
    end

    %% 连接关系
    FE -->|POST /api/orchestrate| API
    RETURN_PLAN --> PLAN_VIEW
    EXECUTE -->|POST /api/update| STATUS
    STAGE5 --> REPORT_HTML
    MetaLayer & FrameworkExecution & AgentLayer --> ADAPTER

    %% 样式
    style Frontend fill:#e0f2fe,stroke:#0284c7
    style Backend fill:#fef3c7,stroke:#d97706
    style MetaLayer fill:#dbeafe,stroke:#3b82f6,stroke-width:3px
    style FrameworkExecution fill:#d1fae5,stroke:#10b981,stroke-width:3px
    style AgentLayer fill:#f0fdf4,stroke:#16a34a
    style SearchLayer fill:#fefce8,stroke:#ca8a04,stroke-dasharray: 5 5
    style ModelAdapter fill:#f3e8ff,stroke:#9333ea
    style Storage fill:#f1f5f9,stroke:#64748b
    
    style ORCHESTRATION_PLAN fill:#fbbf24,stroke:#f59e0b,stroke-width:2px
    style MERMAID_CHART fill:#34d399,stroke:#10b981,stroke-width:2px
```

### 关键流程对比

| 步骤 | 传统模式 | Meta-Orchestrator 模式 |
|-----|---------|----------------------|
| **1. 初始化** | 固定的 Leader-Planner-Auditor 流程 | Meta-Orchestrator 分析需求 |
| **2. 框架选择** | 无框架概念，固定流程 | 从 3 个预定义框架中选择最优方案 |
| **3. 角色配置** | 固定角色（Leader、Planner、Auditor、DA） | 自动匹配现有角色 + 创建新角色 |
| **4. 执行流程** | 单一流程：拆解 → 讨论 → 汇总 | 多阶段执行：Stage 1 → Stage N |
| **5. 报告生成** | 标准 HTML 报告 | 包含 Mermaid 流程图的增强报告 |

---

## 核心模块说明

## 主要设计要点

- **盲评隔离**：为每个并行 Agent 使用独立 ExecutionContext/Chain，保证不共享其他 Agent 输出。
- **格式强约束**：所有角色输出必须为 JSON，后端进行 Pydantic schema 校验并在失败时短重试（最多3次），若仍失败则返回标准错误 JSON。
- **质疑官闭环**：质疑官（Devil's Advocate）在拆解阶段和每轮汇总后进行批判性验证，确保方案经过充分质疑。
- **搜索增强**：Agent 可通过 ``[SEARCH: query]`` 标签触发多引擎并行搜索，结果自动注入上下文后重新生成。
- **流式输出**：支持 Reasoning（推理过程）和 Content 的实时流式展示，前端轮询 ``/api/status`` 获取更新。
- **多模型支持**：通过 ``ModelConfig`` 抽象支持多种后端，可按 Agent 角色分配不同模型。

## 可扩展点

- **模型切换**：在模型适配层配置，可按业务需要替换为高性能或低成本模型，支持按角色配置不同模型。
- **角色数量配置**：策论家和监察官数量可通过 Web UI 动态调整。
- **搜索引擎扩展**：在 ``search_utils.py`` 中添加新引擎实现即可。
- **监控与计量**：可接入 API 调用成本统计、轮次统计、错误率监控等。
