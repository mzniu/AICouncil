# 元老院计划 (AICouncil) 议事流程图

本项目采用多智能体协作架构，通过 **Leader**、**Planner**、**Councilor** 和 **Reporter** 四类 Agent 的协同工作，实现从议题拆解到深度调研，再到最终报告生成的全自动化流程。

## 核心协作流程

```mermaid
%%{init: {'themeVariables': { 'fontSize': '16px', 'fontFamily': 'Microsoft YaHei, Arial' }}}%%
graph TD
    subgraph Main_Chamber ["元老院议事厅 (The Main Chamber)"]
        direction TB

        subgraph Planning_Phase ["1. 规划阶段"]
            Leader_Init[议长 Leader]
            Decomposition{{"<b>议题拆解与<br/>报告设计</b>"}}
        end

        subgraph Middle_Part [" "]
            direction LR
            subgraph Execution_Phase ["2. 迭代讨论阶段"]
                direction TB
                subgraph Planners ["策论家群体 (Parallel)"]
                    P1[策论家 1]
                    P2[策论家 N]
                end
                
                subgraph Auditors ["监察官群体 (Parallel)"]
                    A1[监察官 1]
                    A2[监察官 N]
                end
            end

            subgraph Search_Loop ["联网搜索循环"]
                direction TB
                SearchTag["检测到 [SEARCH: query]"]
                Tavily[Tavily 搜索引擎]
                Results["注入搜索结果并重试"]
            end
        end

        subgraph Synthesis_Phase ["3. 汇总阶段"]
            Leader_Final[议长 Leader]
            Reporter[记录官 Reporter]
            Final_Report{{"<b>生成最终报告</b>"}}
        end

        %% 流程连接
        User_Input([用户输入议题]) --> Leader_Init
        Leader_Init --> Decomposition
        Decomposition --> P1 & P2
        
        %% 讨论循环
        P1 & P2 <--> A1 & A2
        
        %% 搜索循环 (连接到执行阶段)
        Leader_Init & P1 & P2 & A1 & A2 & Leader_Final <-.-> Search_Loop
        SearchTag --> Tavily
        Tavily --> Results

        %% 汇总
        A1 & A2 --> Leader_Final
        Leader_Final --> Reporter
        Reporter --> Final_Report
        Final_Report --> Output([输出报告])
    end

    %% 全局连接线样式 (更粗、更黑)
    linkStyle default stroke:#0f172a,stroke-width:3px;

    %% 样式定义 (高对比度/大字体)
    style Main_Chamber fill:#f8fafc,stroke:#e2e8f0,stroke-width:2px,color:#0f172a
    
    style Leader_Init fill:#d97706,stroke:#78350f,stroke-width:2px,color:#ffffff,font-weight:bold
    style Leader_Final fill:#d97706,stroke:#78350f,stroke-width:2px,color:#ffffff,font-weight:bold
    
    style P1 fill:#2563eb,stroke:#1e3a8a,stroke-width:2px,color:#ffffff,font-weight:bold
    style P2 fill:#2563eb,stroke:#1e3a8a,stroke-width:2px,color:#ffffff,font-weight:bold
    
    style A1 fill:#e11d48,stroke:#881337,stroke-width:2px,color:#ffffff,font-weight:bold
    style A2 fill:#e11d48,stroke:#881337,stroke-width:2px,color:#ffffff,font-weight:bold
    
    style Reporter fill:#7c3aed,stroke:#4c1d95,stroke-width:2px,color:#ffffff,font-weight:bold
    
    style Search_Loop fill:#ffffff,stroke:#475569,stroke-width:2px,stroke-dasharray: 5 5
    style Decomposition fill:#f1f5f9,stroke:#0f172a,stroke-width:3px,color:#0f172a,font-weight:bold
    style Final_Report fill:#059669,stroke:#064e3b,stroke-width:4px,color:#ffffff,font-weight:bold
    style Middle_Part fill:none,stroke:none
    
    %% 子图样式 (各阶段区分颜色)
    classDef planStyle fill:#fffbeb,stroke:#fde68a,stroke-width:2px,color:#78350f,font-weight:bold,font-size:18px
    classDef execStyle fill:#eff6ff,stroke:#bfdbfe,stroke-width:2px,color:#1e3a8a,font-weight:bold,font-size:18px
    classDef synthStyle fill:#f5f3ff,stroke:#ddd6fe,stroke-width:2px,color:#4c1d95,font-weight:bold,font-size:18px
    classDef innerStyle fill:#ffffff,stroke:#94a3b8,stroke-width:1px,color:#1e293b,font-size:16px

    class Planning_Phase planStyle
    class Execution_Phase execStyle
    class Synthesis_Phase synthStyle
    class Planners,Auditors,Search_Loop innerStyle
```

## 详细步骤说明

1.  **议长 (Leader)**:
    *   **职责**: 负责全局视角的任务拆解与最终汇总。
    *   **动作**: 
        *   **初始阶段**: 接收原始议题，将其分解为核心目标、关键问题，并设计报告结构（report_design）。
        *   **汇总阶段**: 收集策论家的方案与监察官的审计意见，判定是否达成共识或需要继续迭代。

2.  **策论家 (Planner)**:
    *   **职责**: 负责产出或迭代可执行方案。
    *   **动作**: 
        *   **并行工作**: 系统通常启动多个策论家（P1, P2...PN）并行产出不同思路的方案。
        *   **思考 (Thinking)**: 使用 DeepSeek R1 进行逻辑推理。
        *   **搜索 (Searching)**: 优先使用 `[SEARCH]` 指令获取行业背景或最新数据。
        *   **迭代**: 根据监察官的反馈针对性修正方案。

3.  **监察官 (Auditor)**:
    *   **职责**: 负责对方案进行质疑、审计与评级。
    *   **动作**: 
        *   **全量审计**: 每个监察官都会收到**所有**策论家的方案集，进行横向对比和深度审计。
        *   **审计**: 针对方案中的关键数据或技术路径进行搜索核实。
        *   **评级**: 给出“优秀/合格/需重构/不可行”的判定。

4.  **报告者 (Reporter)**:
    *   **职责**: 首席方案架构师，负责信息的整合与美化。
    *   **动作**: 汇总所有共识结论，按照议长设计的结构生成专业的 HTML 报告。

4.  **Web UI (监控面板)**:
    *   **职责**: 实时展示上述所有过程。
    *   **特性**: 实时流式展示思考过程、搜索进度、任务状态及最终报告。
