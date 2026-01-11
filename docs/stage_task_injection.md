# Stage任务指导注入功能

## 功能概述

在议事编排官的框架执行中，每个Stage现在能够将其具体任务描述传递给传统角色（planner/auditor），让Agent根据Stage的任务来讨论，而不仅仅是根据角色的通用定义。

## 实现原理

### 问题背景

在之前的实现中：
- **自定义角色**：能够接收`stage_description`和`stage_guidance`变量
- **传统角色（planner/auditor）**：只接收通用的`issue`变量，无法感知当前Stage的具体任务

这导致在框架执行时，传统角色无法针对Stage的特定目标进行讨论（例如Stage 1: 假设识别，Stage 2: 方案设计）。

### 解决方案

通过**增强`issue`内容**的方式，将Stage任务注入到传统角色的输入中：

```python
# framework_engine.py _build_agent_input()

# 为planner构建Stage任务
stage_task = ""
if stage.description:
    stage_task = f"\n\n【本Stage任务】：{stage.description}"
    if stage.prompt_suffix:
        stage_task += f"\n【任务要求】：{stage.prompt_suffix}"

enhanced_issue = self.user_requirement
if stage_task:
    enhanced_issue = f"{self.user_requirement}{stage_task}\n\n请围绕上述Stage任务提出方案。"

agent_input = {
    "planner_id": agent_id,
    "issue": enhanced_issue,  # ← 注入了Stage任务
    "previous_plan": previous_plan,
    "feedback": feedback
}
```

### 角色差异化

- **Planner**：使用"本Stage任务"和"任务要求"术语，提示"请围绕上述Stage任务提出方案"
- **Auditor**：使用"本Stage审查重点"和"审查要求"术语，提示"请围绕上述审查重点进行方案评估"

## 测试验证

### 测试场景

创建了一个"假设识别"Stage：
- `description`: "识别用户需求中的关键假设和前提条件"
- `prompt_suffix`: "请特别关注隐含假设和潜在风险"

### Planner输入示例

```
开发一个智能推荐系统

【本Stage任务】：识别用户需求中的关键假设和前提条件
【任务要求】：请特别关注隐含假设和潜在风险

请围绕上述Stage任务提出方案。
```

### Auditor输入示例

```
开发一个智能推荐系统

【本Stage审查重点】：识别用户需求中的关键假设和前提条件
【审查要求】：请特别关注隐含假设和潜在风险

请围绕上述审查重点进行方案评估。
```

### 测试结果

✅ **测试1: Planner输入构建** - Stage任务成功注入  
✅ **测试2: Auditor输入构建** - Stage审查重点成功注入  
✅ **兼容性**: 不影响自定义角色的`stage_description`机制

## 设计优势

### 1. 向后兼容
- 不修改任何现有的prompt模板
- 只在框架执行时增强输入内容
- 传统讨论模式不受影响

### 2. 清晰标记
使用中文标记（【本Stage任务】、【任务要求】）确保LLM能够理解任务指导的重要性。

### 3. 渐进式增强
- 如果Stage没有description或prompt_suffix，仍使用原始issue
- 只在有明确任务时才注入增强内容

### 4. 角色适配
针对不同角色使用不同的术语：
- Planner关注"提出方案"
- Auditor关注"审查评估"

## 使用示例

### 在议事编排官中定义Stage

```python
FrameworkStage(
    name="假设识别",
    description="识别用户需求中的关键假设和前提条件",
    roles=["planner", "auditor"],
    rounds=1,
    prompt_suffix="请特别关注隐含假设和潜在风险"
)
```

### 实际效果

- **Stage 1: 假设识别** - 所有Agent讨论关键假设和前提条件
- **Stage 2: 方案设计** - 所有Agent讨论具体的解决方案设计
- **Stage 3: 风险评估** - 所有Agent讨论潜在风险和缓解措施

每个Stage的Agent都能清晰理解当前阶段的目标，而不是仅按照角色的通用职责工作。

## 实现位置

- **主要代码**: [src/agents/framework_engine.py](../src/agents/framework_engine.py) Lines 490-570
- **测试脚本**: [tests/test_stage_task_injection.py](../tests/test_stage_task_injection.py)
- **Framework定义**: [src/agents/frameworks.py](../src/agents/frameworks.py) FrameworkStage类

## 未来改进

1. **提示词优化**: 可以在prompt模板中添加占位符`{stage_guidance}`，更灵活地控制注入位置
2. **多语言支持**: 根据用户语言动态生成"本Stage任务"或"Current Stage Task"
3. **可视化增强**: 在Web UI中高亮显示每个Stage的当前任务
4. **反馈机制**: 让Leader在综合时明确引用Stage的完成情况

## 结论

Stage任务注入功能成功实现了"让Agent根据Stage内容讨论"的目标，提升了框架执行的针对性和讨论质量。通过渐进式增强的方式，在不破坏现有架构的前提下，为传统角色提供了Stage级别的任务指导。
