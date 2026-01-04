# Devil's Advocate (质疑官) 实施方案

## 📋 项目概述

**目标**：在元老院系统中增加Devil's Advocate角色，用于质疑和挑战讨论框架、假设和结论，提升讨论质量和深度。

**版本**：v1.0  
**创建日期**：2026-01-03  
**状态**：设计阶段

---

## 🎯 核心设计理念

### 角色定位

**Devil's Advocate（质疑官）** 是讨论流程中的"批判性思维引擎"：
- **不是对抗者**：目的是提升质量，而非否定
- **不是决策者**：提供质疑和替代视角，最终决策权仍在Leader
- **独立执行**：与其他Agent并行，避免影响正常流程

### 工作范围

Devil's Advocate将质疑三个层面：

1. **问题分解层**（Round 1）
   - 质疑Leader的初始议题分解
   - 识别遗漏的关键维度
   - 提出替代的分解框架

2. **方案讨论层**（Each Round）
   - 质疑Synthesizer的归纳是否全面
   - 挑战方案背后的隐含假设
   - 提出反例和极端场景

3. **总结验证层**（After Leader Summary）
   - 验证Leader总结的逻辑一致性
   - 识别遗漏的关键观点
   - 质疑结论的合理性

---

## 🏗️ 技术架构

### Schema设计

```python
# src/agents/schemas.py

class ChallengeItem(BaseModel):
    """单个质疑项"""
    target: str  # 质疑目标（假设/结论/分解维度等）
    challenge_type: str  # 类型：假设挑战/逻辑质疑/遗漏识别/反例/极端场景
    reasoning: str  # 质疑的推理过程
    alternative_perspective: str  # 提供的替代视角
    severity: str  # 严重程度：critical/important/minor

class DecompositionChallenge(BaseModel):
    """对问题分解的质疑"""
    missing_dimensions: List[str]  # 遗漏的关键维度
    alternative_frameworks: List[str]  # 替代的分解框架
    assumption_challenges: List[ChallengeItem]  # 对核心假设的质疑

class SynthesisChallenge(BaseModel):
    """对方案综合的质疑"""
    overlooked_patterns: List[str]  # 被忽视的模式
    hidden_assumptions: List[ChallengeItem]  # 隐藏的假设
    edge_cases: List[str]  # 边界情况和反例
    cross_cutting_risks: List[str]  # 跨方案的风险

class SummaryChallenge(BaseModel):
    """对总结的质疑"""
    logical_gaps: List[str]  # 逻辑跳跃或缺口
    missing_points: List[str]  # 遗漏的关键观点
    inconsistencies: List[str]  # 前后矛盾之处
    optimism_bias: Optional[str]  # 过度乐观/悲观的倾向

class DevilsAdvocateSchema(BaseModel):
    """Devil's Advocate完整输出"""
    round: int
    stage: str  # decomposition/synthesis/summary
    
    # 根据stage包含不同的字段
    decomposition_challenge: Optional[DecompositionChallenge]
    synthesis_challenge: Optional[SynthesisChallenge]
    summary_challenge: Optional[SummaryChallenge]
    
    overall_assessment: str  # 整体评价
    critical_issues: List[str]  # 必须解决的关键问题
    recommendations: List[str]  # 改进建议
```

### Prompt模板设计

#### 1. 问题分解阶段的Prompt

```python
DEVILS_ADVOCATE_DECOMPOSITION_PROMPT = """你是资深的批判性思维专家，专门发现问题分解中的盲点。

当前议题：
{issue}

议长的问题分解：
核心目标：{core_goal}
关键问题：{key_questions}
边界条件：{boundaries}

当前时间：{current_time}

你的任务：
1. **识别遗漏维度** - 哪些重要维度未被包含？
   - 时间维度（短期vs长期）
   - 利益相关方（谁受影响？）
   - 约束条件（资源、法规、技术）
   - 风险维度（what-if场景）

2. **质疑核心假设** - 分解背后的隐含假设是什么？这些假设可靠吗？
   - 例如："假设我们有足够的资源"
   - 例如："假设现状会持续"

3. **提供替代框架** - 是否有完全不同但可能更好的分解方式？
   - 例如：按时间线分解 vs 按利益相关方分解
   - 例如：自上而下 vs 自下而上

4. **极端场景测试** - 在极端情况下，这个分解框架是否仍然有效？

要求：
- 每个质疑都要有清晰的推理逻辑
- 提供建设性的替代视角，而非单纯否定
- 标注严重程度（critical/important/minor）
- 如果分解合理，也要明确说明

输出严格的JSON格式：
{schema}

记住：你的价值在于发现议长可能忽视的盲点，帮助完善问题框架。
"""
```

#### 2. 方案综合阶段的Prompt

```python
DEVILS_ADVOCATE_SYNTHESIS_PROMPT = """你是批判性思维大师，专门挑战常规假设和发现隐藏问题。

第{round}轮讨论 - 方案综合阶段

当前方案簇（Synthesizer归纳）：
{synthesis_clusters}

所有原始方案：
{all_plans}

所有审查意见：
{all_audits}

你的任务：
1. **挑战归纳完整性** - Synthesizer的归纳是否遗漏了关键模式？
   - 是否有方案被错误归类？
   - 是否有跨簇的重要联系未识别？

2. **识别隐藏假设** - 所有方案共同依赖的未明说的假设
   - 例如："大家都假设预算充足"
   - 例如："都假设用户会接受新技术"

3. **提出反例和边界情况** - 什么情况下这些方案会失效？
   - 极端市场条件
   - 技术突破或失败
   - 监管环境变化
   - 黑天鹅事件

4. **逆向思维** - 如果目标相反会怎样？是否有更简单的路径？
   - 例如：与其"增加功能"，能否"简化现有功能"？
   - 例如：与其"扩大市场"，能否"深耕细分市场"？

5. **跨方案风险** - 所有方案都忽视的共同风险

要求：
- 深入挖掘，不要重复Auditor已经提出的批评
- 每个质疑都要有具体例证或推理
- 既要指出问题，也要提供替代视角
- 标注严重程度

输出JSON格式：
{schema}

记住：群体思维会掩盖真正的问题，你的任务是打破这种一致性假象。
"""
```

#### 3. 总结验证阶段的Prompt

```python
DEVILS_ADVOCATE_SUMMARY_PROMPT = """你是逻辑严密性专家，负责验证议长总结的质量。

第{round}轮讨论 - 总结验证阶段

方案簇（Synthesizer归纳）：
{synthesis_clusters}

议长的总结：
{leader_summary}

历史讨论记录：
{history}

你的任务：
1. **逻辑一致性检查**
   - 总结中是否有前后矛盾？
   - 结论是否有逻辑跳跃（从A直接跳到C，缺少B）？
   - 因果关系是否成立？

2. **完整性检查**
   - Synthesizer识别的关键观点是否都在总结中体现？
   - 哪些重要内容被遗漏？
   - 是否平衡对待了所有方案簇？

3. **合理性检查**
   - 是否过度乐观（忽视风险）或过度悲观（忽视机会）？
   - 优先级判断是否合理？
   - 时间预估是否现实？

4. **一致性检查**
   - 本轮总结与上一轮是否矛盾？
   - 是否解决了之前识别的问题？

5. **决策支持性检查**
   - 总结是否提供了足够的信息供决策？
   - 是否明确了下一步行动？

要求：
- 对比总结与原始材料，识别偏差
- 明确指出哪些遗漏/矛盾是critical级别
- 如果总结质量高，也要明确肯定

输出JSON格式：
{schema}

记住：你不是挑剔，而是确保最终决策建立在可靠的基础上。
"""
```

---

## 🔄 工作流程集成

### 新的run_full_cycle流程

```python
def run_full_cycle(...):
    # 初始化
    session_id = ...
    workspace_path = ...
    
    # ========== 初始分解阶段 ==========
    # 1. Leader初始分解
    decomposition = run_leader_decomposition(issue_text)
    
    # 【新增】2. Devil's Advocate质疑分解
    devils_advocate_chain = make_devils_advocate_chain(model_config)
    da_decomp_challenge = run_devils_advocate_decomposition(
        devils_advocate_chain,
        issue_text,
        decomposition
    )
    
    # 3. Leader根据质疑调整（可选）
    # 如果有critical问题，可以让Leader重新分解
    if da_decomp_challenge.has_critical_issues():
        logger.warning("⚠️ Devil's Advocate发现分解的严重问题，建议调整")
        # 可选：触发重新分解
        # decomposition = run_leader_decomposition_v2(issue_text, da_decomp_challenge)
    
    # ========== 多轮讨论 ==========
    for r in range(1, max_rounds + 1):
        logger.info(f"=== 第 {r} 轮讨论 ===")
        
        # 4. Planners并行提案
        plans = parallel_run_planners(...)
        
        # 5. Auditors并行审查
        audits = parallel_run_auditors(plans, ...)
        
        # 【新增】6. Synthesizer归纳（新增的角色）
        synthesis = run_synthesizer(plans, audits, ...)
        
        # 【新增】7. Devil's Advocate质疑方案综合
        da_synthesis_challenge = run_devils_advocate_synthesis(
            devils_advocate_chain,
            r,
            synthesis,
            plans,
            audits
        )
        
        # 8. Leader综合总结（输入包含DA的质疑）
        leader_summary = run_leader_summary(
            r,
            synthesis,
            da_synthesis_challenge,  # ← 传入质疑内容
            history
        )
        
        # 【新增】9. Devil's Advocate验证总结
        da_summary_challenge = run_devils_advocate_summary(
            devils_advocate_chain,
            r,
            synthesis,
            leader_summary,
            history
        )
        
        # 10. 记录到history（包含所有DA的质疑）
        history.append({
            "round": r,
            "plans": plans,
            "audits": audits,
            "synthesis": synthesis,
            "da_synthesis_challenge": da_synthesis_challenge,
            "leader_summary": leader_summary,
            "da_summary_challenge": da_summary_challenge
        })
        
        # 保存本轮数据
        save_round_data(workspace_path, r, history[-1])
    
    # ========== 最终报告 ==========
    # 11. Reporter生成报告（包含DA的关键质疑）
    final_report = generate_report(
        issue_text,
        decomposition,
        history,
        include_devils_advocate=True  # 在报告中体现DA的关键发现
    )
    
    return {
        "session_id": session_id,
        "workspace": str(workspace_path),
        "final_report": final_report
    }
```

### 执行时机和并行策略

```
时序图：
┌─────────────────────────────────────────────────────┐
│ 初始化阶段                                           │
├─────────────────────────────────────────────────────┤
│ Leader分解 → DA质疑分解 → (可选)Leader调整          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 每轮讨论（重复max_rounds次）                         │
├─────────────────────────────────────────────────────┤
│ Planners(并行) ┐                                     │
│                ├→ Auditors(并行) ┐                   │
│                                  ├→ Synthesizer      │
│                                  ├→ DA质疑方案       │
│                                  │                   │
│ Leader总结 ← ───────────────────┘                   │
│    ↓                                                 │
│ DA验证总结                                           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 报告生成                                             │
├─────────────────────────────────────────────────────┤
│ Reporter生成HTML（包含DA关键发现）                   │
└─────────────────────────────────────────────────────┘
```

**并行优化**：
- Synthesizer和DA可以并行执行（都依赖plans+audits）
- DA验证总结必须在Leader总结之后

---

## 📁 文件改动清单

### 1. Schema定义
**文件**：`src/agents/schemas.py`
- [ ] 添加 `ChallengeItem`
- [ ] 添加 `DecompositionChallenge`
- [ ] 添加 `SynthesisChallenge`
- [ ] 添加 `SummaryChallenge`
- [ ] 添加 `DevilsAdvocateSchema`

### 2. Chain构建
**文件**：`src/agents/langchain_agents.py`
- [ ] 添加 `make_devils_advocate_chain()`
- [ ] 添加 `run_devils_advocate_decomposition()`
- [ ] 添加 `run_devils_advocate_synthesis()`
- [ ] 添加 `run_devils_advocate_summary()`
- [ ] 添加 Prompt模板常量

### 3. 核心流程
**文件**：`src/agents/langchain_agents.py`
- [ ] 修改 `run_full_cycle()` 集成DA
- [ ] 修改 `run_leader_summary()` 接收DA输入
- [ ] 更新 `save_round_data()` 保存DA数据

### 4. 报告生成
**文件**：`src/agents/langchain_agents.py`
- [ ] 修改 `generate_report_from_workspace()` 
- [ ] 在报告HTML中添加DA关键发现的展示区域
- [ ] 添加DA质疑的可折叠面板

### 5. Web界面
**文件**：`src/web/templates/index.html`
- [ ] 添加Devil's Advocate输出的显示区域
- [ ] 为DA质疑添加特殊样式（如红色边框、警告图标）
- [ ] 添加DA质疑的折叠/展开功能

### 6. API更新
**文件**：`src/web/app.py`
- [ ] 确保DA的输出能通过 `/api/update` 发送到前端
- [ ] 更新状态轮询逻辑

### 7. 配置
**文件**：`src/config_template.py`
- [ ] 添加 `ENABLE_DEVILS_ADVOCATE` 开关
- [ ] 添加DA专用模型配置（可选）

### 8. 文档
- [ ] 更新 `README.md` 介绍DA角色
- [ ] 更新 `docs/architecture.md`
- [ ] 更新 `docs/workflow.md` Mermaid图

---

## 🧪 测试策略

### 单元测试
**文件**：`tests/test_devils_advocate.py`
- [ ] 测试 `make_devils_advocate_chain()` 
- [ ] 测试Schema解析
- [ ] 测试各阶段的prompt模板

### 集成测试
- [ ] 测试完整流程（issue → 带DA的讨论 → 报告）
- [ ] 测试DA在关键场景下的质疑质量
  - 测试用例1：明显错误的分解（应识别critical问题）
  - 测试用例2：忽略风险的方案（应识别遗漏）
  - 测试用例3：逻辑不一致的总结（应识别矛盾）

### UI测试
**文件**：`tests/ui/test_discussion.py`
- [ ] 验证DA输出在Web界面正确显示
- [ ] 验证DA质疑的折叠/展开功能
- [ ] 验证报告中DA部分的渲染

---

## 🎨 UI/UX设计

### Web界面展示

```html
<!-- Devil's Advocate输出区域 -->
<div class="devils-advocate-section">
    <div class="section-header" style="background: #dc2626;">
        <i class="fas fa-user-secret"></i>
        <span>质疑官 (Devil's Advocate)</span>
        <span class="badge">批判性思维</span>
    </div>
    
    <!-- 分解阶段质疑 -->
    <div class="challenge-decomposition" v-if="decompositionChallenge">
        <h4>⚠️ 对问题分解的质疑</h4>
        <div class="critical-issues" v-if="decompositionChallenge.critical_issues.length">
            <span class="badge badge-danger">严重问题</span>
            <ul>
                <li v-for="issue in decompositionChallenge.critical_issues">
                    {{ issue }}
                </li>
            </ul>
        </div>
        <details>
            <summary>查看详细质疑</summary>
            <!-- 详细内容 -->
        </details>
    </div>
    
    <!-- 方案阶段质疑 -->
    <div class="challenge-synthesis">
        <h4>🔍 对方案综合的质疑</h4>
        <!-- ... -->
    </div>
    
    <!-- 总结验证 -->
    <div class="challenge-summary">
        <h4>✓ 对总结的验证</h4>
        <!-- ... -->
    </div>
</div>
```

### 报告展示

在HTML报告中添加专门的"批判性分析"章节：

```html
<section id="devils-advocate-insights">
    <h2>🔍 批判性分析</h2>
    <p class="description">
        以下是质疑官(Devil's Advocate)在整个讨论过程中发现的关键问题和替代视角。
        这些质疑有助于全面理解方案的风险和局限性。
    </p>
    
    <!-- 按轮次展示关键质疑 -->
    <div class="round-challenges">
        <h3>第1轮关键质疑</h3>
        <ul class="critical-challenges">
            <li class="challenge-item critical">
                <span class="challenge-type">逻辑缺口</span>
                <p>总结中假设用户会接受新UI，但未提供用户调研数据支持</p>
            </li>
        </ul>
    </div>
    
    <!-- 总结所有被识别但未解决的问题 -->
    <div class="unresolved-issues">
        <h3>⚠️ 未完全解决的问题</h3>
        <ul>
            <!-- ... -->
        </ul>
    </div>
</section>
```

---

## 📊 评估指标

实施DA后，如何衡量效果？

### 定量指标
1. **质疑覆盖率**
   - 每轮DA提出的质疑数量
   - critical/important/minor的分布

2. **问题识别准确率**
   - DA识别的问题中，有多少在后续被验证为真实问题
   - 需要人工标注ground truth

3. **质量改进**
   - Leader总结的修订次数（因DA质疑而修改）
   - 最终报告的完整性评分（对比无DA的baseline）

### 定性指标
1. **深度**：DA是否发现了其他Agent未发现的深层问题？
2. **建设性**：DA的质疑是否提供了可行的替代视角？
3. **独立性**：DA是否避免了重复Auditor的批评？

---

## 🚀 实施里程碑

### Phase 1: 最小可行版本（1-2天）
- [ ] 实现基础Schema
- [ ] 实现单一阶段的DA（推荐：summary阶段）
- [ ] 集成到run_full_cycle
- [ ] 基础UI展示
- [ ] 验证可用性

**成功标准**：能在一个完整讨论中看到DA的输出，质疑内容有意义

### Phase 2: 完整功能（3-4天）
- [ ] 实现所有三个阶段的DA
- [ ] 优化Prompt质量（迭代测试）
- [ ] 完整的UI展示
- [ ] 报告集成
- [ ] 单元测试和集成测试

**成功标准**：DA在各阶段都能提供有价值的质疑，UI完整展示

### Phase 3: 质量优化（1-2周）
- [ ] 根据实际使用反馈优化Prompt
- [ ] 添加DA专用的搜索功能（验证事实性声明）
- [ ] 性能优化（并行执行）
- [ ] 高级UI（可折叠、可标记、可导出）
- [ ] 完整的测试覆盖

**成功标准**：DA成为系统的核心质量保障机制，用户明显感知到讨论质量提升

---

## 🔒 风险和缓解

### 风险1：DA质疑过于消极
**缓解**：
- Prompt中明确要求"建设性质疑"
- 要求提供替代视角，而非单纯否定
- 设置质疑的严重程度分级，避免小题大做

### 风险2：DA增加计算成本
**缓解**：
- 提供配置开关 `ENABLE_DEVILS_ADVOCATE`
- DA与Synthesizer并行执行
- 仅对critical轮次启用DA（如最后一轮）

### 风险3：DA质疑质量不高
**缓解**：
- 迭代优化Prompt（基于真实案例）
- 考虑为DA使用更强的模型（如GPT-4）
- 添加Few-shot examples展示期望的质疑风格

### 风险4：Leader忽视DA的质疑
**缓解**：
- 在Reporter报告中显著展示DA的critical发现
- 如果有critical问题，触发警告或额外讨论轮
- 记录DA质疑的采纳率，作为系统优化指标

---

## 📖 参考资源

### 理论基础
- Red Team thinking in AI systems
- Adversarial review processes in scientific publishing
- Pre-mortem analysis techniques

### 类似实现
- OpenAI的Constitutional AI
- Anthropic的debate-based alignment
- 学术界的peer review系统

---

## 📝 变更日志

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|---------|------|
| 2026-01-03 | 1.0 | 初始设计文档 | AI Council Team |

---

## ✅ 审批记录

- [ ] 技术方案审批
- [ ] 资源分配审批
- [ ] 开始实施

