# 元老院计划 (AICouncil) 议事流程图

本项目采用多智能体协作架构，通过 **Leader**、**Planner**、**Auditor**、**Devil's Advocate** 和 **Reporter** 五类 Agent 的协同工作，实现从议题拆解到深度调研，再到最终报告生成的全自动化流程。

## 核心协作流程

```mermaid
%%{init: {'themeVariables': { 'fontSize': '16px', 'fontFamily': 'Microsoft YaHei, Arial' }}}%%
graph TD
    subgraph Main_Chamber ["元老院议事厅 (The Main Chamber)"]
        direction TB

        subgraph Planning_Phase ["1. 规划阶段 (Decomposition)"]
            User_Input([用户输入议题])
            Leader_Init[议长 Leader]
            Decomposition{{"<b>议题拆解与<br/>报告设计</b>"}}
            DA_Decomp[质疑官 DA]
            DA_Challenge{{"<b>拆解质疑</b>"}}
            Leader_Revise[议长修正]
        end

        subgraph Execution_Phase ["2. 迭代讨论阶段 (Rounds 1~N)"]
            direction TB
            subgraph Planners ["策论家群体 (Parallel)"]
                P1[策论家 1]
                P2[策论家 N]
            end
            
            subgraph Auditors ["监察官群体 (Parallel)"]
                A1[监察官 1]
                A2[监察官 N]
            end
            
            Leader_Summary[议长汇总]
            DA_Summary[质疑官 DA]
            DA_Validate{{"<b>总结质疑</b>"}}
        end

        subgraph Search_Integration ["联网搜索 (所有Agent可用)"]
            direction LR
            SearchTag["[SEARCH: query]"]
            MultiEngine["多引擎搜索<br/>Baidu/Bing/Yahoo/Google/Tavily"]
            Results["结果注入"]
        end

        subgraph Synthesis_Phase ["3. 汇总阶段 (Synthesis)"]
            Leader_Final[议长最终汇总]
            Reporter[记录官 Reporter]
            Final_Report{{"<b>生成 HTML 报告</b>"}}
        end

        %% 规划阶段流程
        User_Input --> Leader_Init
        Leader_Init --> Decomposition
        Decomposition --> DA_Decomp
        DA_Decomp --> DA_Challenge
        DA_Challenge -->|有严重问题| Leader_Revise
        DA_Challenge -->|通过| P1 & P2
        Leader_Revise --> P1 & P2
        
        %% 迭代讨论循环
        P1 & P2 --> A1 & A2
        A1 & A2 --> Leader_Summary
        Leader_Summary --> DA_Summary
        DA_Summary --> DA_Validate
        DA_Validate -->|继续迭代| P1 & P2
        DA_Validate -->|达成共识| Leader_Final
        
        %% 搜索集成 (虚线表示可选触发)
        Leader_Init & P1 & P2 & A1 & A2 & DA_Decomp & DA_Summary <-.-> SearchTag
        SearchTag --> MultiEngine
        MultiEngine --> Results

        %% 汇总阶段
        Leader_Final --> Reporter
        Reporter --> Final_Report
        Final_Report --> Output([输出报告])
    end

    %% 全局连接线样式
    linkStyle default stroke:#0f172a,stroke-width:2px;

    %% 样式定义
    style Main_Chamber fill:#f8fafc,stroke:#e2e8f0,stroke-width:2px,color:#0f172a
    
    style User_Input fill:#10b981,stroke:#047857,stroke-width:2px,color:#ffffff,font-weight:bold
    style Output fill:#10b981,stroke:#047857,stroke-width:2px,color:#ffffff,font-weight:bold
    
    style Leader_Init fill:#d97706,stroke:#78350f,stroke-width:2px,color:#ffffff,font-weight:bold
    style Leader_Revise fill:#d97706,stroke:#78350f,stroke-width:2px,color:#ffffff,font-weight:bold
    style Leader_Summary fill:#d97706,stroke:#78350f,stroke-width:2px,color:#ffffff,font-weight:bold
    style Leader_Final fill:#d97706,stroke:#78350f,stroke-width:2px,color:#ffffff,font-weight:bold
    
    style P1 fill:#2563eb,stroke:#1e3a8a,stroke-width:2px,color:#ffffff,font-weight:bold
    style P2 fill:#2563eb,stroke:#1e3a8a,stroke-width:2px,color:#ffffff,font-weight:bold
    
    style A1 fill:#e11d48,stroke:#881337,stroke-width:2px,color:#ffffff,font-weight:bold
    style A2 fill:#e11d48,stroke:#881337,stroke-width:2px,color:#ffffff,font-weight:bold
    
    style DA_Decomp fill:#7c3aed,stroke:#4c1d95,stroke-width:2px,color:#ffffff,font-weight:bold
    style DA_Summary fill:#7c3aed,stroke:#4c1d95,stroke-width:2px,color:#ffffff,font-weight:bold
    
    style Reporter fill:#06b6d4,stroke:#0e7490,stroke-width:2px,color:#ffffff,font-weight:bold
    
    style SearchTag fill:#fbbf24,stroke:#b45309,stroke-width:2px,color:#0f172a,font-weight:bold
    style MultiEngine fill:#fef3c7,stroke:#b45309,stroke-width:1px,color:#78350f
    style Results fill:#fef3c7,stroke:#b45309,stroke-width:1px,color:#78350f
    
    style Decomposition fill:#f1f5f9,stroke:#0f172a,stroke-width:2px,color:#0f172a,font-weight:bold
    style DA_Challenge fill:#f3e8ff,stroke:#7c3aed,stroke-width:2px,color:#4c1d95,font-weight:bold
    style DA_Validate fill:#f3e8ff,stroke:#7c3aed,stroke-width:2px,color:#4c1d95,font-weight:bold
    style Final_Report fill:#059669,stroke:#064e3b,stroke-width:3px,color:#ffffff,font-weight:bold
    
    %% 子图样式
    classDef planStyle fill:#fffbeb,stroke:#fde68a,stroke-width:2px,color:#78350f,font-weight:bold,font-size:16px
    classDef execStyle fill:#eff6ff,stroke:#bfdbfe,stroke-width:2px,color:#1e3a8a,font-weight:bold,font-size:16px
    classDef synthStyle fill:#f0fdf4,stroke:#bbf7d0,stroke-width:2px,color:#166534,font-weight:bold,font-size:16px
    classDef searchStyle fill:#fefce8,stroke:#fde047,stroke-width:2px,stroke-dasharray: 5 5,color:#713f12,font-size:14px
    classDef innerStyle fill:#ffffff,stroke:#94a3b8,stroke-width:1px,color:#1e293b,font-size:14px

    class Planning_Phase planStyle
    class Execution_Phase execStyle
    class Synthesis_Phase synthStyle
    class Search_Integration searchStyle
    class Planners,Auditors innerStyle
```

## 详细步骤说明

1.  **议长 (Leader)**:
    *   **职责**: 负责全局视角的任务拆解与最终汇总。
    *   **动作**:
        *   **初始阶段**: 接收原始议题，将其分解为核心目标、关键问题，并设计报告结构（report_design）。
        *   **修正阶段**: 根据质疑官的反馈修正问题拆解（如存在严重问题）。
        *   **汇总阶段**: 收集策论家的方案与监察官的审计意见，判定是否达成共识或需要继续迭代。
        *   **最终阶段**: 综合所有讨论结果，输出最终共识方案。

2.  **策论家 (Planner)**:
    *   **职责**: 负责产出或迭代可执行方案。
    *   **动作**:
        *   **并行工作**: 系统通常启动多个策论家（P1, P2...PN）并行产出不同思路的方案。
        *   **思考 (Thinking)**: 使用 DeepSeek R1 等推理模型进行逻辑推理。
        *   **搜索 (Searching)**: 使用 `[SEARCH: query]` 指令获取行业背景或最新数据。
        *   **迭代**: 根据监察官的反馈和质疑官的挑战针对性修正方案。

3.  **监察官 (Auditor)**:
    *   **职责**: 负责对方案进行审计与评级。
    *   **动作**:
        *   **全量审计**: 每个监察官都会收到**所有**策论家的方案集，进行横向对比和深度审计。
        *   **审计**: 针对方案中的关键数据或技术路径进行搜索核实。
        *   **评级**: 给出"优秀/合格/需重构/不可行"的判定及具体建议。

4.  **质疑官 (Devil's Advocate)**:
    *   **职责**: 批判性思维专家，负责发现盲点和验证总结质量。
    *   **动作**:
        *   **拆解质疑**: 在议长完成问题拆解后，检查遗漏维度、隐含假设、替代框架和极端场景。
        *   **总结质疑**: 在每轮议长汇总后，验证推理链、检查证据质量、评估风险考量。
        *   **反馈闭环**: 质疑结果会反馈给议长和策论家，确保方案经过充分质疑和优化。

5.  **记录官 (Reporter)**:
    *   **职责**: 首席方案架构师，负责信息的整合与美化。
    *   **动作**: 汇总所有共识结论，按照议长设计的结构生成专业的 HTML 报告（含 ECharts 图表）。

6.  **联网搜索 (Search Integration)**:
    *   **触发方式**: 任何 Agent 输出中包含 `[SEARCH: 查询词]` 标签即触发。
    *   **多引擎支持**: Baidu、Bing、Yahoo、Google API、Tavily、DuckDuckGo、Mojeek。
    *   **处理流程**: 检测标签  并行多引擎搜索  结果注入上下文  Agent 重新生成。

7.  **Web UI (监控面板)**:
    *   **职责**: 实时展示上述所有过程。
    *   **特性**:
        *   实时流式展示思考过程（Reasoning）、搜索进度、任务状态。
        *   支持多模型后端配置（DeepSeek、OpenAI、Azure、Anthropic、Gemini、OpenRouter、Ollama）。
        *   报告导出支持 HTML、截图、PDF 格式。
