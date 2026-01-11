# 议事编排官 Agent_Counts 不完整问题分析

## 问题现象

```
[meta_orchestrator] 匹配到的现有角色:
    • 辩论方法论分析专家 (debate_methodology_analyst): score=1.0, count=1
    • 策论家 (planner): score=0.8, count=1
    • 监察官 (auditor): score=0.7, count=1

[meta_orchestrator] agent_counts 配置: {'planner': 2, 'auditor': 1}
```

**问题**：
- 匹配了3个角色（1个专业角色 + 2个框架角色）
- 但 `agent_counts` 只包含2个（planner, auditor）
- **缺失**：leader（框架必需）、debate_methodology_analyst（专业角色）
- `role_stage_mapping` 为空

## 根本原因分析

### 1. LLM 不遵循 Prompt 规则

**证据**：
- 在 prompt 开头添加了🚨核心约束和📋检查清单
- 明确要求 agent_counts 必须包含三部分
- 但 LLM 依然输出不完整的配置

**可能原因**：
- **注意力衰减**：Prompt 太长（275行），LLM 可能忽略开头的约束
- **指令冲突**：后续的详细说明可能与开头约束产生矛盾
- **JSON 生成模式**：LLM 进入 JSON 输出模式后，可能不再参考约束
- **训练分布**：模型训练数据中，不完整配置可能是常见模式

### 2. 匹配结果和配置生成分离

**当前流程**：
```
Step 2: 调用 list_roles() 工具 → 获得匹配角色
↓
Step 4: 基于匹配结果生成 agent_counts
```

**问题**：
- 工具调用结果和最终配置之间缺乏强制约束
- LLM 需要"记住"工具返回的结果并正确映射到配置
- 这个"记忆+映射"过程容易出错

### 3. 输出验证缺失

**当前状态**：
- 只有 Pydantic schema 验证（类型检查）
- 没有业务逻辑验证（例如：是否包含所有匹配的角色）
- LLM 输出后直接使用，没有自动修正机制

## 解决方案对比

### 方案 A：后处理自动修正 ⭐⭐⭐⭐⭐

**实现位置**：`run_meta_orchestrator()` 解析 JSON 后

**核心逻辑**：
```python
# 1. 解析 LLM 输出
plan = schemas.OrchestrationPlan(**plan_dict)

# 2. 获取框架定义，识别必需角色
framework = get_framework(plan.framework_selection.framework_id)
required_roles = extract_required_roles(framework)  # planner, auditor, leader...

# 3. 自动修正 agent_counts
missing_framework_roles = [r for r in required_roles if r not in plan.execution_config.agent_counts]
for role in missing_framework_roles:
    plan.execution_config.agent_counts[role] = 1
    logger.warning(f"自动添加缺失的框架角色: {role}")

# 4. 添加匹配的专业角色
professional_roles = get_professional_roles(plan.role_planning.existing_roles)
for role_match in professional_roles:
    if role_match.name not in plan.execution_config.agent_counts:
        plan.execution_config.agent_counts[role_match.name] = role_match.assigned_count
        logger.warning(f"自动添加缺失的专业角色: {role_match.name}")

# 5. 修正 role_stage_mapping
if not plan.execution_config.role_stage_mapping:
    plan.execution_config.role_stage_mapping = {}
for role_match in professional_roles:
    if role_match.name not in plan.execution_config.role_stage_mapping:
        # 自动分配到合适的 stage
        suitable_stages = find_suitable_stages(role_match, framework)
        plan.execution_config.role_stage_mapping[role_match.name] = suitable_stages
        logger.warning(f"自动为 {role_match.name} 分配 stage: {suitable_stages}")
```

**优点**：
- ✅ **可靠性高**：不依赖 LLM 输出质量
- ✅ **实现简单**：纯 Python 逻辑，易于调试
- ✅ **向后兼容**：即使 prompt 优化后，这层保护依然有效
- ✅ **日志清晰**：每次修正都有明确日志

**缺点**：
- ❌ 绕过了 LLM 的"智能决策"（但这也是优点）
- ❌ 需要定义 `find_suitable_stages()` 的启发式规则

**实施成本**：⭐⭐（中等）

---

### 方案 B：简化 + 重构 Prompt

**策略 1：Three-Shot 提示**
```
你必须完成以下3步：

【第1步】输出框架必需角色
框架 "{framework_name}" 必需角色：{required_roles}
➜ 在 agent_counts 中必须包含：{required_roles}

【第2步】输出所有专业角色
工具返回的专业角色：{professional_roles}
➜ 在 agent_counts 中必须包含：{professional_roles}
➜ 在 role_stage_mapping 中必须为每个专业角色分配 stage

【第3步】输出完整 JSON
确保 agent_counts = {required_roles} + {professional_roles}
```

**策略 2：拆分为多次调用**
```
调用1：分析问题 + 选择框架
调用2：匹配/创建角色
调用3：生成配置（此时提供明确的角色列表，减少"记忆负担"）
```

**优点**：
- ✅ 更清晰的指令结构
- ✅ 减少 LLM "遗忘"的可能性

**缺点**：
- ❌ 可能依然无效（LLM 不听指令是根本问题）
- ❌ 多次调用增加延迟和成本

**实施成本**：⭐⭐⭐（较高）

---

### 方案 C：使用 Function Calling / Structured Output

**实现方式**：
```python
# 使用 OpenAI function calling 或类似机制
tools = [
    {
        "type": "function",
        "function": {
            "name": "configure_discussion",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_counts": {
                        "type": "object",
                        "description": "必须包含框架所有角色和所有匹配的专业角色",
                        "required": ["planner", "auditor", "leader"]  # 动态生成
                    },
                    "role_stage_mapping": {...}
                }
            }
        }
    }
]
```

**优点**：
- ✅ 更强的结构化约束
- ✅ 某些模型（如 GPT-4）对 function calling 的遵循度更高

**缺点**：
- ❌ **不适用于 DeepSeek**：DeepSeek Reasoner 不支持 function calling
- ❌ 限制了模型选择
- ❌ 增加了实现复杂度

**实施成本**：⭐⭐⭐⭐（高）

---

### 方案 D：两阶段验证 + 重试

**流程**：
```python
for retry in range(3):
    plan = call_meta_orchestrator_llm()
    
    # 验证 agent_counts 完整性
    if validate_agent_counts(plan, expected_roles):
        break  # 验证通过
    else:
        # 构造反馈 prompt，要求修正
        feedback = f"""
        你的输出有误：
        - 缺失的框架角色：{missing_framework_roles}
        - 缺失的专业角色：{missing_professional_roles}
        
        请修正 agent_counts，确保包含所有角色。
        """
        # 重新调用 LLM
```

**优点**：
- ✅ 利用 LLM 自我修正能力
- ✅ 保留"智能决策"空间

**缺点**：
- ❌ 增加延迟（多次调用）
- ❌ 增加成本
- ❌ 可能依然失败（3次后仍不正确）

**实施成本**：⭐⭐⭐（较高）

---

### 方案 E：混合方案（推荐）⭐⭐⭐⭐⭐

结合方案 A + 优化的 Prompt：

1. **优化 Prompt**（低成本尝试）
   - 在 Step 4 中明确列出"必须包含的角色列表"
   - 使用更直接的指令（减少描述性文字）

2. **后处理兜底**（方案 A）
   - 即使 prompt 优化无效，后处理确保正确性
   - 记录每次自动修正，用于后续 prompt 改进

3. **Fallback 机制**（已实现）
   - 当 role_stage_mapping 为空时自动创建专业分析 stage

**实施步骤**：
- [ ] Step 1：实现后处理逻辑（30分钟）
- [ ] Step 2：优化 prompt Step 4 指令（10分钟）
- [ ] Step 3：添加详细日志（5分钟）
- [ ] Step 4：测试验证（15分钟）

**总成本**：⭐⭐（低）

---

## 推荐方案：方案 E（混合方案）

### 为什么选择方案 E？

1. **实用主义**：
   - 不依赖 LLM 100% 遵守规则
   - 用确定性逻辑补偿 LLM 的不确定性

2. **渐进式改进**：
   - 后处理立即解决问题
   - Prompt 优化逐步提升 LLM 表现
   - 两者互不冲突

3. **低风险**：
   - 不改变核心架构
   - 不增加延迟或成本
   - 易于回滚

4. **可观测性**：
   - 详细日志记录每次自动修正
   - 数据驱动的 prompt 改进

### 实施优先级

**P0（立即实施）**：
- ✅ 后处理自动修正 agent_counts
- ✅ 后处理自动修正 role_stage_mapping
- ✅ 添加修正日志

**P1（短期优化）**：
- 📋 优化 Step 4 的 prompt 指令
- 📋 在输出示例中强化"完整性"要求

**P2（长期改进）**：
- 📊 收集修正数据，分析 LLM 常见错误模式
- 🔬 实验不同的 prompt 策略
- 🎯 针对特定模型（DeepSeek/OpenAI）定制 prompt

---

## 附录：代码实现草图

### A. 后处理修正逻辑

```python
def auto_fix_orchestration_plan(
    plan: OrchestrationPlan,
    framework: Framework
) -> OrchestrationPlan:
    """自动修正 OrchestrationPlan 的不完整配置"""
    
    # 1. 识别框架必需角色
    required_roles = set()
    for stage in framework.stages:
        required_roles.update(stage.roles)
    
    # 2. 识别专业角色
    framework_role_names = {"planner", "auditor", "leader", "devils_advocate", "reporter"}
    professional_roles = [
        role for role in plan.role_planning.existing_roles
        if role.name not in framework_role_names
    ]
    
    # 3. 修正 agent_counts
    modified = False
    
    # 3.1 添加缺失的框架角色
    for role in required_roles:
        if role not in plan.execution_config.agent_counts:
            plan.execution_config.agent_counts[role] = 1
            logger.warning(f"🔧 自动添加缺失的框架角色: {role}")
            modified = True
    
    # 3.2 添加缺失的专业角色
    for role_match in professional_roles:
        if role_match.name not in plan.execution_config.agent_counts:
            count = role_match.assigned_count or 1
            plan.execution_config.agent_counts[role_match.name] = count
            logger.warning(f"🔧 自动添加缺失的专业角色: {role_match.name} (count={count})")
            modified = True
    
    # 4. 修正 role_stage_mapping
    if not plan.execution_config.role_stage_mapping:
        plan.execution_config.role_stage_mapping = {}
    
    for role_match in professional_roles:
        if role_match.name not in plan.execution_config.role_stage_mapping:
            # 智能分配：匹配度最高的角色分配更重要的 stage
            suitable_stages = _find_suitable_stages(role_match, framework)
            plan.execution_config.role_stage_mapping[role_match.name] = suitable_stages
            logger.warning(f"🔧 自动为 {role_match.display_name} 分配 stage: {suitable_stages}")
            modified = True
    
    if modified:
        logger.info("✅ 已自动修正 OrchestrationPlan 配置")
    
    return plan

def _find_suitable_stages(role_match: RoleMatch, framework: Framework) -> List[str]:
    """为专业角色寻找合适的参与 stage"""
    
    # 策略1：如果匹配度很高(>0.9)，分配到更多 stage
    if role_match.match_score >= 0.9:
        # 分配到前2个非 leader 的 stage
        stages = [s.name for s in framework.stages if "leader" not in s.roles][:2]
        return stages if stages else [framework.stages[0].name]
    
    # 策略2：中等匹配度，分配到1个 stage
    else:
        # 选择中间的 stage（通常是讨论的核心阶段）
        mid_index = len(framework.stages) // 2
        return [framework.stages[mid_index].name]
```

### B. 优化的 Prompt Step 4

```markdown
## Step 4: 生成执行配置（关键步骤）

⚠️  **配置完整性要求**：

### 4.1 agent_counts 必须包含：

**第一部分：框架必需角色**
框架 "{framework_name}" 的 stages 中定义的所有角色：
{list_required_roles}
➜ 这些角色必须全部出现在 agent_counts 中

**第二部分：专业角色**
list_roles() 工具返回的专业角色（除 planner/auditor/leader/devils_advocate/reporter 外）：
{list_professional_roles}
➜ 这些角色必须全部出现在 agent_counts 中

**第三部分：新创建角色**
create_role() 创建的角色：
{list_new_roles}
➜ 这些角色必须全部出现在 agent_counts 中

### 4.2 role_stage_mapping 必须配置：

对于第二部分和第三部分的每个角色，必须在 role_stage_mapping 中指定其参与的 stage。

**示例**：
如果专业角色为 ["economist", "legal_expert"]，
则 role_stage_mapping 必须为：
{
  "economist": ["证据评估", "替代视角"],
  "legal_expert": ["逻辑推理"]
}

### 4.3 输出检查

在生成 JSON 前，请逐项检查：
□ agent_counts 是否包含框架的所有必需角色？
□ agent_counts 是否包含所有专业角色？
□ role_stage_mapping 是否为每个专业角色配置了 stage？
```

---

## 总结

**当前问题**：LLM 输出的 agent_counts 不完整，导致专业角色无法参与讨论。

**根本原因**：LLM 不可靠，即使有明确约束也可能输出错误配置。

**推荐方案**：混合方案（后处理自动修正 + prompt 优化）
- 立即实施后处理逻辑，确保配置完整性
- 渐进优化 prompt，提升 LLM 输出质量
- 保留 fallback 机制作为最后兜底

**预期效果**：
- ✅ 100% 保证配置完整性（后处理兜底）
- ✅ 逐步减少自动修正频率（prompt 优化）
- ✅ 专业角色能够正确参与讨论
