# Meta-Orchestrator 完整流程手动测试指南

## 测试目标

1. ✅ 验证专业角色能否正确参与讨论
2. ✅ 验证输出包含所有角色的发言
3. ✅ 测试多个专业角色的场景

## 前置条件

确保系统中已存在以下角色：
- `debate_methodology_analyst` (辩论方法论分析专家)
- 可选：其他专业角色用于多角色测试

## 测试场景1：单个专业角色

### 步骤

1. **启动Web界面**
   ```bash
   python src/web/app.py
   ```

2. **配置讨论参数**
   - 议题：`如何提高团队协作效率？这个问题涉及沟通方式、工具选择和团队文化等多个维度。`
   - 模型后端：`deepseek`
   - 讨论轮次：`1`（加快测试）
   - ✅ **开启"使用元调度器"**

3. **观察日志输出**

   在开始讨论后，控制台应输出：
   ```
   📊 角色规划详情:
     - 匹配的现有角色: X 个
       • 辩论方法论分析专家 (debate_methodology_analyst)
       • 策论家 (planner)
       • 监察官 (auditor)
       • 议长 (leader)
   
   🎯 Agent配置:
     - planner: 1
     - auditor: 1
     - leader: 1
     - debate_methodology_analyst: 1
   
   🔗 专业角色映射:
     - debate_methodology_analyst → 逻辑推理, 替代视角
   ```

4. **验证检查点**

   | 检查项 | 预期结果 | 实际结果 |
   |-------|---------|---------|
   | agent_counts 包含4个角色 | ✅ | [ ] |
   | agent_counts 包含 debate_methodology_analyst | ✅ | [ ] |
   | role_stage_mapping 不为空 | ✅ | [ ] |
   | debate_methodology_analyst 分配到至少1个stage | ✅ | [ ] |

5. **查看讨论过程**

   在Web界面的"议事过程"面板中，应看到：
   - 策论家的发言
   - 监察官的发言
   - **辩论方法论分析专家的发言**（关键验证点）
   - 议长的总结

6. **检查最终报告**

   报告中应包含：
   - 所有角色的观点
   - 辩论方法论分析专家的专业分析
   - 综合后的解决方案

### 预期输出示例

```json
{
  "framework_selection": {
    "selected_framework": "critical_thinking",
    "rationale": "团队协作问题需要系统性分析..."
  },
  "role_planning": {
    "existing_roles": [
      {
        "name": "debate_methodology_analyst",
        "display_name": "辩论方法论分析专家",
        "match_score": 0.95,
        "assigned_count": 1
      },
      {
        "name": "planner",
        "display_name": "策论家",
        "match_score": 0.7,
        "assigned_count": 1
      }
    ]
  },
  "execution_config": {
    "agent_counts": {
      "planner": 1,
      "auditor": 1,
      "leader": 1,
      "debate_methodology_analyst": 1
    },
    "role_stage_mapping": {
      "debate_methodology_analyst": ["逻辑推理", "替代视角"]
    }
  }
}
```

## 测试场景2：多个专业角色

### 步骤

1. **创建第二个专业角色**（如果不存在）

   在Web界面的"角色设计师"中创建：
   - 名称：`conflict_resolution_expert`
   - 显示名：`冲突解决专家`
   - 描述：`专注于团队冲突分析和解决方案设计`
   - 专长领域：`团队冲突`, `沟通协调`, `利益平衡`

2. **配置讨论参数**

   议题（设计为触发多个专业角色）：
   ```
   团队最近频繁发生意见分歧，影响项目进度。主要矛盾点在于：
   1. 技术方案选择上的争议
   2. 工作分配不均引发的不满
   3. 沟通方式导致的误解
   请提供系统性的改进建议。
   ```

3. **观察日志输出**

   应匹配到至少2个专业角色：
   ```
   📊 角色规划详情:
     - 匹配的现有角色: X 个
       • 辩论方法论分析专家 (debate_methodology_analyst)
       • 冲突解决专家 (conflict_resolution_expert)
       • 策论家 (planner)
       • 监察官 (auditor)
       • 议长 (leader)
   
   🎯 Agent配置:
     - planner: 1
     - auditor: 1
     - leader: 1
     - debate_methodology_analyst: 1
     - conflict_resolution_expert: 1
   
   🔗 专业角色映射:
     - debate_methodology_analyst → 逻辑推理
     - conflict_resolution_expert → 替代视角, 实践验证
   ```

4. **验证检查点**

   | 检查项 | 预期结果 | 实际结果 |
   |-------|---------|---------|
   | agent_counts 包含至少5个角色 | ✅ | [ ] |
   | 包含至少2个专业角色 | ✅ | [ ] |
   | 所有专业角色都有stage映射 | ✅ | [ ] |
   | 讨论中看到所有专业角色的发言 | ✅ | [ ] |

5. **查看角色发言分布**

   在Web界面中展开各个stage，确认：
   - 每个专业角色在其分配的stage中有发言
   - 发言内容与其专业领域相关

## 测试场景3：无匹配专业角色（Fallback测试）

### 步骤

1. **使用通用议题**

   ```
   如何提高代码质量？
   ```

2. **观察行为**

   - 如果没有匹配的专业角色，系统应：
     - 仅使用框架内置角色（planner, auditor, leader）
     - role_stage_mapping 为空
     - 正常完成讨论

3. **预期输出**

   ```json
   {
     "execution_config": {
       "agent_counts": {
         "planner": 2,
         "auditor": 2,
         "leader": 1
       },
       "role_stage_mapping": {}
     }
   }
   ```

## 问题排查

### 问题1：agent_counts 缺少专业角色

**症状**：
```
agent_counts: {'planner': 1, 'auditor': 1}
```

**检查**：
1. 查看日志中"匹配到的现有角色"是否包含专业角色
2. 检查 role_stage_mapping 是否为空
3. 查看 Meta-Orchestrator 的输出JSON是否完整

**解决方案**：
- 如果匹配到了但未添加到agent_counts → LLM输出问题，检查prompt约束
- 如果未匹配到 → 调整角色的expertise_areas或议题描述

### 问题2：role_stage_mapping 为空

**症状**：
```
⚠️ role_stage_mapping 为空或未设置
```

**检查**：
1. Meta-Orchestrator 是否在输出JSON中包含了role_stage_mapping
2. prompt中的检查清单是否被LLM遵循

**解决方案**：
- 强化prompt约束（已在开头添加核心约束）
- 考虑实现fallback机制（todo3）

### 问题3：专业角色未发言

**症状**：讨论中看不到专业角色的发言

**检查**：
1. agent_counts 是否包含该角色
2. role_stage_mapping 是否为该角色配置了stage
3. FrameworkEngine 日志中是否创建了该角色的chain

**解决方案**：
- 检查 `make_generic_role_chain()` 是否正确加载角色
- 检查 `_create_chains_for_stage()` 是否根据mapping添加角色

## 成功标准

测试通过的标准：

✅ **场景1（单专业角色）**：
- agent_counts 包含 debate_methodology_analyst
- role_stage_mapping 为该角色配置了stage
- 讨论中看到该角色的专业分析
- 报告中包含该角色的观点

✅ **场景2（多专业角色）**：
- agent_counts 包含所有匹配的专业角色
- 每个专业角色都有stage映射
- 讨论中看到所有专业角色的发言
- 各角色发言与其专长相关

✅ **场景3（无专业角色）**：
- 系统正常运行，使用框架角色
- 不报错，不崩溃

## 测试数据记录

| 测试时间 | 场景 | agent_counts | role_stage_mapping | 结果 | 备注 |
|---------|------|-------------|-------------------|------|------|
| YYYY-MM-DD HH:mm | 单专业角色 | { } | { } | ✅/❌ |  |
| YYYY-MM-DD HH:mm | 多专业角色 | { } | { } | ✅/❌ |  |
| YYYY-MM-DD HH:mm | 无专业角色 | { } | { } | ✅/❌ |  |
