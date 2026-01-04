# Devil's Advocate 开发文档索引

本目录包含Devil's Advocate角色实施过程中的所有设计和开发文档。

## 📚 文档清单

### 核心设计文档

1. **[devils-advocate-implementation.md](./devils-advocate-implementation.md)**
   - 完整的技术实施方案
   - 架构设计和Schema定义
   - Prompt模板设计
   - 工作流程集成方案
   - UI/UX设计
   - 评估指标和风险分析

2. **[devils-advocate-todos.md](./devils-advocate-todos.md)**
   - 详细的开发任务列表
   - 按Phase分阶段实施计划
   - 每个任务的优先级、预计时间和依赖关系
   - 验收标准和检查清单
   - 进度追踪表

## 🎯 快速导航

### 如果你想了解：

- **"Devil's Advocate是什么？"** → 查看 [implementation.md](./devils-advocate-implementation.md) 的"角色定位"章节
- **"如何开始实施？"** → 查看 [todos.md](./devils-advocate-todos.md) 的 Phase 1
- **"Schema怎么设计？"** → 查看 [implementation.md](./devils-advocate-implementation.md) 的"Schema设计"章节
- **"Prompt怎么写？"** → 查看 [implementation.md](./devils-advocate-implementation.md) 的"Prompt模板设计"章节
- **"工作流程是什么？"** → 查看 [implementation.md](./devils-advocate-implementation.md) 的"工作流程集成"章节
- **"UI怎么展示？"** → 查看 [implementation.md](./devils-advocate-implementation.md) 的"UI/UX设计"章节
- **"当前进度如何？"** → 查看 [todos.md](./devils-advocate-todos.md) 的"进度追踪"章节

## 📊 项目概况

| 指标 | 值 |
|------|-----|
| **预计总工时** | 61小时 |
| **实施阶段** | 3个Phase |
| **核心文件改动** | 8个文件 |
| **新增Schema** | 5个类 |
| **新增函数** | 7个主要函数 |
| **预计完成时间** | 1-2周 |

## 🚀 实施路径

```
Phase 1 (1-2天): 最小可行版本
    ├── Schema定义 (Summary阶段)
    ├── Prompt设计
    ├── Chain实现
    ├── 流程集成
    └── 基础UI
    
Phase 2 (3-4天): 完整功能
    ├── 扩展到全阶段 (Decomposition + Synthesis + Summary)
    ├── 完整UI实现
    ├── 报告集成
    └── 测试覆盖
    
Phase 3 (1-2周): 质量优化
    ├── Prompt迭代优化
    ├── 性能优化
    ├── 高级UI特性
    └── 文档完善
```

## 📋 关键决策记录

### 为什么需要Devil's Advocate？

1. **信息过载问题**：Leader需要综合大量Planner和Auditor的输出
2. **盲点识别**：群体思维可能导致忽视关键问题
3. **质量保障**：缺乏系统化的验证机制
4. **风险评估**：需要专门角色识别潜在风险

### 为什么不质疑Leader权威？

1. 避免权力平衡混乱和无限递归
2. 通过"验证"而非"对抗"的方式提供第二意见
3. 保持Leader的决策权和流程收敛性

### 为什么分三个阶段执行？

1. **Decomposition阶段**：及早发现问题分解的缺陷
2. **Synthesis阶段**：挑战方案归纳和隐藏假设
3. **Summary阶段**：验证最终总结的完整性和一致性

## 🔄 开发流程

### 1. 开始新的Phase
```bash
# 查看当前Phase的任务
cat docs/dev/devils-advocate-todos.md | grep "Phase X"

# 创建feature分支
git checkout -b feature/devils-advocate-phase-X
```

### 2. 开发过程中
```bash
# 更新进度
# 编辑 docs/dev/devils-advocate-todos.md
# 标记完成的任务为 [x]

# 记录重要决策
# 在 docs/dev/devils-advocate-implementation.md 的"变更日志"中添加记录
```

### 3. Phase完成后
```bash
# 验收检查
# 对照 todos.md 中的"验收标准"逐项检查

# Code Review
# 对照 todos.md 中的"Code Review Checklist"

# 合并到主分支
git checkout main
git merge feature/devils-advocate-phase-X
```

## 📖 相关资源

### 内部文档
- [架构文档](../architecture.md) - 系统整体架构
- [工作流文档](../workflow.md) - Agent协作流程
- [Prompt模板文档](../prompt_templates.md) - 现有Prompt设计

### 外部参考
- Red Team thinking in AI systems
- Adversarial review processes
- Constitutional AI (Anthropic)

## 📝 文档维护

### 文档更新规范

1. **重要设计变更**：在 `devils-advocate-implementation.md` 的"变更日志"中记录
2. **任务状态更新**：实时更新 `devils-advocate-todos.md` 中的任务状态
3. **新增文档**：更新本 README.md 的文档清单

### 文档审核

- **技术审核**：每个Phase完成后由Tech Lead审核设计文档
- **用户文档审核**：Phase 3完成后由产品团队审核面向用户的文档

## ✅ Checklist：开始实施前

在开始Phase 1之前，请确认：

- [ ] 已阅读完整的 `devils-advocate-implementation.md`
- [ ] 理解Devil's Advocate的核心理念和工作范围
- [ ] 熟悉现有的Agent架构（Leader, Planner, Auditor, Reporter）
- [ ] 了解Schema设计和Prompt模板的基本原则
- [ ] 准备好开发环境（Python 3.10+, 依赖已安装）
- [ ] 确认API密钥配置正确（用于测试）
- [ ] 创建feature分支 `feature/devils-advocate-phase-1`

## 🤝 贡献指南

如果你要参与Devil's Advocate的开发：

1. **选择任务**：从 `todos.md` 中选择未完成的任务
2. **更新状态**：将任务状态改为"进行中"，并注明负责人
3. **开发**：按照 `implementation.md` 的设计规范实施
4. **测试**：编写相应的单元测试和集成测试
5. **文档**：更新代码注释和相关文档
6. **提交**：创建Pull Request，等待Code Review

## 📞 联系方式

如有问题或建议，请联系：
- **项目负责人**：[待分配]
- **技术讨论**：在GitHub Issue中提出
- **文档问题**：直接修改并提交PR

---

**最后更新**：2026-01-03  
**文档版本**：1.0

