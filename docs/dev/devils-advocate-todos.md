# Devil's Advocate Implementation - TODOs

**项目**: 增强版Devil's Advocate实施  
**状态**: ✅ Phase 1 完成 + Decomposition阶段扩展  
**预计完成时间**: Phase 1 (2天) + Phase 2 (4天) + Phase 3 (1-2周)

---

## 🎯 Phase 1: 最小可行版本 (MVP) - ✅ 完成

**目标**: 实现两个阶段的DA，验证基本可行性  
**预计时间**: 1-2天
**实际时间**: 1天
**状态**: ✅ 全部完成

### 重要扩展：Decomposition阶段质疑 ✅

**用户反馈**: "议长在第一轮开始之前对议题的拆解是不是也应该接受DA的质疑？"  
**实施结果**: ✅ 已完成

- [x] 添加 `DecompositionChallenge` Schema（包含4个质疑维度）
- [x] 更新 `DevilsAdvocateSchema` 支持多阶段（decomposition/summary）
- [x] 实现 Decomposition 阶段的 Prompt 模板
- [x] 创建两个独立的 chain：
  - `devils_advocate_decomposition_chain` - 质疑问题拆解
  - `devils_advocate_summary_chain` - 质疑总结
- [x] 在 `run_full_cycle` 初始拆解后调用 DA
- [x] 保存拆解质疑结果到 `decomposition_challenge.json`
- [x] 添加单元测试（9/9 tests passing）

**质疑内容**:
1. 识别遗漏维度（时间、利益相关方、约束、风险）
2. 质疑核心假设
3. 提供替代拆解框架
4. 极端场景测试

---

## 🎯 Phase 1: 最小可行版本 (MVP)

**目标**: 实现单一阶段的DA，验证基本可行性  
**预计时间**: 1-2天

### Step 1: Schema定义 (2小时) ✅ 完成

- [x] **Task 1.1**: 在 `src/agents/schemas.py` 添加基础Schema
  - [x] 定义 `ChallengeItem` 类
  - [x] 定义 `SummaryChallenge` 类（Phase 1只实现summary阶段）
  - [x] 定义 `DevilsAdvocateSchema` 类（简化版）
  ```python
  # 优先级：P0
  # 预计时间：1小时
  # 依赖：无
  # 状态：✅ 已完成
  ```

- [x] **Task 1.2**: 编写Schema单元测试
  - [x] 测试Schema解析
  - [x] 测试JSON序列化/反序列化
  - [x] 测试字段验证
  ```python
  # 优先级：P1
  # 预计时间：30分钟
  # 依赖：Task 1.1
  # 状态：✅ 已完成 (8/8 tests passing)
  ```

### Step 2: Prompt设计 (3小时) ✅ 完成

- [x] **Task 2.1**: 编写Summary阶段的Prompt模板
  - [x] 定义 `DEVILS_ADVOCATE_SUMMARY_PROMPT` 常量
  - [x] 包含明确的输出格式要求
  - [x] 添加Few-shot示例（可选）
  ```python
  # 优先级：P0
  # 预计时间：2小时
  # 依赖：Task 1.1
  # 状态：✅ 已完成
  ```

- [x] **Task 2.2**: Prompt质量验证
  - [x] 手动测试Prompt（使用API直接调用）
  - [x] 验证输出格式正确性
  - [x] 调整措辞以确保质疑质量
  ```python
  # 优先级：P0
  # 预计时间：1小时
  # 依赖：Task 2.1
  # 状态：✅ 已完成 (通过实际集成测试验证)
  ```

### Step 3: Chain实现 (2小时) ✅ 完成

- [x] **Task 3.1**: 实现 `make_devils_advocate_chain()`
  - [x] 创建LangChain的PromptTemplate
  - [x] 配置AdapterLLM
  - [x] 返回可执行的chain
  ```python
  # 优先级：P0
  # 预计时间：1小时
  # 依赖：Task 2.1
  # 文件：src/agents/langchain_agents.py
  # 状态：✅ 已完成
  ```

- [x] **Task 3.2**: 实现 `run_devils_advocate_summary()`
  - [x] 调用chain并处理流式输出
  - [x] 解析JSON输出
  - [x] 错误处理和重试逻辑
  - [x] 发送Web事件
  ```python
  # 优先级：P0
  # 预计时间：1小时
  # 依赖：Task 3.1
  # 状态：✅ 已完成 (集成在 run_full_cycle 中)
  ```

### Step 4: 流程集成 (2小时) ✅ 完成

- [x] **Task 4.1**: 修改 `run_full_cycle()`
  - [x] 在Leader总结后添加DA调用
  - [x] 将DA输出保存到history
  - [x] 更新 `save_round_data()` 包含DA数据
  ```python
  # 优先级：P0
  # 预计时间：1.5小时
  # 依赖：Task 3.2
  # 文件：src/agents/langchain_agents.py
  # 状态：✅ 已完成
  ```

- [ ] **Task 4.2**: 测试端到端流程
  - [ ] 运行完整的讨论测试
  - [ ] 验证DA在正确时机执行
  - [ ] 检查保存的JSON数据完整性
  ```python
  # 优先级：P0
  # 预计时间：30分钟
  # 依赖：Task 4.1
  ```

### Step 5: 基础UI展示 (3小时) ✅ 完成 + 高级可视化扩展

- [x] **Task 5.1**: 修改前端接收DA事件
  - [x] 更新 `index.html` 的事件处理逻辑
  - [x] 添加DA专用的显示区域
  - [x] 基础样式（红色边框、警告图标）
  - [x] **扩展**: 实现与其他Agent相同的可视化效果
  ```html
  # 优先级：P1
  # 预计时间：2小时
  # 依赖：Task 4.1
  # 文件：src/web/templates/index.html
  # 状态：✅ 已完成（包括高级可视化）
  
  可视化特性：
  - 根据严重程度动态调整颜色（Critical=红色，Warning=琥珀色）
  - 分类展示质疑内容（逻辑缺口、遗漏维度、矛盾等）
  - 图标标识不同质疑类型
  - 结构化卡片布局
  - 阴影和边框增强视觉层次
  ```

- [x] **Task 5.2**: 验证实时显示
  - [x] 运行讨论并观察前端
  - [x] 确认DA输出正确显示
  - [x] 调整样式以提高可读性
  ```html
  # 优先级：P1
  # 预计时间：1小时
  # 依赖：Task 5.1
  ```

### Phase 1 验收标准

- [ ] ✅ 能在讨论的summary阶段看到DA输出
- [ ] ✅ DA质疑内容有意义（不是空洞或重复）
- [ ] ✅ Web界面正确显示DA输出
- [ ] ✅ 数据正确保存到workspace JSON
- [ ] ✅ 没有崩溃或错误

---

## 🚀 Phase 2: 完整功能实现

**目标**: 实现所有三个阶段的DA，完善UI和报告  
**预计时间**: 3-4天

### Step 6: 扩展到全阶段 (4小时)

- [ ] **Task 6.1**: 添加完整的Schema定义
  - [ ] 定义 `DecompositionChallenge`
  - [ ] 定义 `SynthesisChallenge`
  - [ ] 更新 `DevilsAdvocateSchema` 支持三个阶段
  ```python
  # 优先级：P0
  # 预计时间：1小时
  # 依赖：Task 1.1完成
  ```

- [ ] **Task 6.2**: 编写Decomposition阶段Prompt
  - [ ] 定义 `DEVILS_ADVOCATE_DECOMPOSITION_PROMPT`
  - [ ] 测试和优化Prompt质量
  ```python
  # 优先级：P0
  # 预计时间：1.5小时
  # 依赖：Task 6.1
  ```

- [ ] **Task 6.3**: 编写Synthesis阶段Prompt
  - [ ] 定义 `DEVILS_ADVOCATE_SYNTHESIS_PROMPT`
  - [ ] 测试和优化Prompt质量
  ```python
  # 优先级：P0
  # 预计时间：1.5小时
  # 依赖：Task 6.1
  ```

### Step 7: 实现额外的执行函数 (3小时)

- [ ] **Task 7.1**: 实现 `run_devils_advocate_decomposition()`
  - [ ] 调用chain处理初始分解
  - [ ] 解析和验证输出
  - [ ] 发送Web事件
  ```python
  # 优先级：P0
  # 预计时间：1.5小时
  # 依赖：Task 6.2
  ```

- [ ] **Task 7.2**: 实现 `run_devils_advocate_synthesis()`
  - [ ] 调用chain处理方案综合
  - [ ] 解析和验证输出
  - [ ] 发送Web事件
  ```python
  # 优先级：P0
  # 预计时间：1.5小时
  # 依赖：Task 6.3
  ```

### Step 8: 完整流程集成 (3小时)

- [ ] **Task 8.1**: 更新 `run_full_cycle()` 完整集成
  - [ ] 在Leader分解后添加DA质疑
  - [ ] 在每轮的方案综合后添加DA质疑
  - [ ] 确保DA数据在所有阶段都被保存
  ```python
  # 优先级：P0
  # 预计时间：2小时
  # 依赖：Task 7.1, 7.2
  ```

- [ ] **Task 8.2**: 处理Critical问题的响应逻辑
  - [ ] 如果DA发现critical问题，记录警告
  - [ ] 可选：触发Leader重新分解/总结
  - [ ] 在报告中高亮critical问题
  ```python
  # 优先级：P1
  # 预计时间：1小时
  # 依赖：Task 8.1
  ```

### Step 9: 完整UI实现 (4小时)

- [ ] **Task 9.1**: 实现三个阶段的UI展示
  - [ ] Decomposition质疑的显示
  - [ ] Synthesis质疑的显示
  - [ ] Summary质疑的显示
  - [ ] 按严重程度分类显示（critical/important/minor）
  ```html
  # 优先级：P0
  # 预计时间：2.5小时
  # 依赖：Task 8.1
  ```

- [ ] **Task 9.2**: 添加可折叠功能
  - [ ] 使用 `<details>` 标签或JavaScript
  - [ ] 默认展开critical级别，折叠其他
  - [ ] 添加展开/折叠全部按钮
  ```html
  # 优先级：P1
  # 预计时间：1.5小时
  # 依赖：Task 9.1
  ```

### Step 10: 报告集成 (3小时)

- [ ] **Task 10.1**: 修改 `generate_report_from_workspace()`
  - [ ] 从history中提取DA的关键发现
  - [ ] 添加"批判性分析"章节到HTML模板
  - [ ] 汇总所有critical和important问题
  ```python
  # 优先级：P0
  # 预计时间：2小时
  # 依赖：Task 8.1
  # 文件：src/agents/langchain_agents.py
  ```

- [ ] **Task 10.2**: 设计报告中DA部分的样式
  - [ ] 添加专门的CSS类
  - [ ] 使用不同颜色区分严重程度
  - [ ] 添加图标和视觉提示
  ```css
  # 优先级：P1
  # 预计时间：1小时
  # 依赖：Task 10.1
  ```

### Step 11: 测试覆盖 (4小时)

- [ ] **Task 11.1**: 编写单元测试
  - [ ] 测试所有Schema类
  - [ ] 测试chain构建函数
  - [ ] 测试DA执行函数
  ```python
  # 优先级：P1
  # 预计时间：2小时
  # 依赖：Phase 2所有功能完成
  # 文件：tests/test_devils_advocate.py
  ```

- [ ] **Task 11.2**: 编写集成测试
  - [ ] 测试完整流程（带DA）
  - [ ] 测试critical问题的处理
  - [ ] 测试报告生成包含DA内容
  ```python
  # 优先级：P1
  # 预计时间：2小时
  # 依赖：Task 11.1
  ```

### Phase 2 验收标准

- [ ] ✅ DA在所有三个阶段都能正常工作
- [ ] ✅ Web界面完整展示所有DA输出
- [ ] ✅ 报告中包含DA的批判性分析章节
- [ ] ✅ Critical问题被高亮显示
- [ ] ✅ 单元测试和集成测试覆盖率 > 80%
- [ ] ✅ 至少完成3个真实案例的测试

---

## 🎨 Phase 3: 质量优化和高级特性

**目标**: 根据反馈优化，添加高级功能  
**预计时间**: 1-2周

### Step 12: Prompt优化迭代 (持续)

- [ ] **Task 12.1**: 收集真实案例反馈
  - [ ] 记录DA质疑质量的用户评价
  - [ ] 识别常见的质量问题（过于消极/不够深入等）
  - [ ] 建立Prompt优化的反馈循环
  ```
  # 优先级：P0
  # 预计时间：持续进行
  ```

- [ ] **Task 12.2**: 添加Few-shot Examples
  - [ ] 收集高质量的DA输出示例
  - [ ] 在Prompt中添加2-3个示例
  - [ ] A/B测试对比效果
  ```
  # 优先级：P1
  # 预计时间：4小时
  ```

- [ ] **Task 12.3**: 多模型实验
  - [ ] 测试不同模型作为DA（GPT-4, Claude, DeepSeek等）
  - [ ] 对比质疑深度和准确性
  - [ ] 选择最佳默认模型
  ```
  # 优先级：P2
  # 预计时间：3小时
  ```

### Step 13: 搜索增强 (可选)

- [ ] **Task 13.1**: 为DA添加事实核查功能
  - [ ] 识别可验证的声明
  - [ ] 调用搜索API验证
  - [ ] 在质疑中引用验证结果
  ```python
  # 优先级：P2
  # 预计时间：6小时
  # 文件：src/agents/langchain_agents.py
  ```

### Step 14: 性能优化

- [ ] **Task 14.1**: 并行执行优化
  - [ ] DA与Synthesizer并行运行
  - [ ] 优化大规模讨论的执行时间
  ```python
  # 优先级：P1
  # 预计时间：3小时
  ```

- [ ] **Task 14.2**: 添加配置开关
  - [ ] 在 `config_template.py` 添加 `ENABLE_DEVILS_ADVOCATE`
  - [ ] 支持仅在特定轮次启用DA
  - [ ] 添加DA模型的单独配置
  ```python
  # 优先级：P1
  # 预计时间：1小时
  ```

### Step 15: 高级UI特性

- [ ] **Task 15.1**: DA质疑的标记功能
  - [ ] 用户可以标记质疑为"有用/无用"
  - [ ] 收集反馈用于Prompt优化
  ```javascript
  # 优先级：P2
  # 预计时间：3小时
  ```

- [ ] **Task 15.2**: DA质疑的导出功能
  - [ ] 单独导出DA的批判性分析
  - [ ] 支持Markdown和JSON格式
  ```javascript
  # 优先级：P2
  # 预计时间：2小时
  ```

### Step 16: 文档和示例

- [ ] **Task 16.1**: 更新用户文档
  - [ ] 更新 `README.md` 介绍DA功能
  - [ ] 添加DA使用指南
  - [ ] 提供示例案例
  ```markdown
  # 优先级：P1
  # 预计时间：2小时
  ```

- [ ] **Task 16.2**: 更新架构文档
  - [ ] 更新 `docs/architecture.md`
  - [ ] 更新 `docs/workflow.md` 的Mermaid图
  - [ ] 添加DA的技术设计文档
  ```markdown
  # 优先级：P1
  # 预计时间：2小时
  ```

### Step 17: UI测试

- [ ] **Task 17.1**: 添加UI自动化测试
  - [ ] 测试DA输出在Web界面的显示
  - [ ] 测试折叠/展开功能
  - [ ] 测试报告中DA部分的渲染
  ```python
  # 优先级：P1
  # 预计时间：3小时
  # 文件：tests/ui/test_discussion.py
  ```

### Phase 3 验收标准

- [ ] ✅ Prompt质量经过至少10个真实案例验证
- [ ] ✅ DA质疑的准确率和深度符合预期
- [ ] ✅ 性能优化后，DA不显著增加执行时间
- [ ] ✅ 用户文档完整，新用户能快速理解DA功能
- [ ] ✅ UI测试覆盖所有DA相关功能

---

## 📊 进度追踪

### 当前进度

| Phase | 状态 | 完成度 | 预计完成日期 |
|-------|------|--------|-------------|
| Phase 1: MVP | 🔴 未开始 | 0% | - |
| Phase 2: 完整功能 | 🔴 未开始 | 0% | - |
| Phase 3: 优化 | 🔴 未开始 | 0% | - |

### 工时统计

| Phase | 预计工时 | 实际工时 | 偏差 |
|-------|---------|---------|------|
| Phase 1 | 12小时 | - | - |
| Phase 2 | 21小时 | - | - |
| Phase 3 | 28小时 | - | - |
| **总计** | **61小时** | **-** | **-** |

---

## ⚠️ 风险和依赖

### 阻塞问题
- [ ] 无当前阻塞

### 外部依赖
- [ ] Synthesizer实现（Phase 2依赖）
  - 如果没有Synthesizer，DA在synthesis阶段的质疑会受限
  - 可以先跳过synthesis阶段，只实现decomposition和summary

### 技术风险
- [ ] LLM输出质量不稳定
  - 缓解：增加重试逻辑，优化Prompt
- [ ] JSON解析失败率较高
  - 缓解：使用 `clean_json_string()` 预处理，增加错误处理

---

## 📞 联系和协作

### 负责人
- **Tech Lead**: [待分配]
- **QA**: [待分配]
- **UI/UX**: [待分配]

### Code Review
- 每个Phase完成后需要Code Review
- Review checklist:
  - [ ] 代码符合项目规范
  - [ ] 有足够的单元测试
  - [ ] Prompt质量经过验证
  - [ ] UI展示清晰易懂
  - [ ] 文档已更新

---

## ✅ 最终检查清单

### 代码质量
- [ ] 所有新代码有类型注解
- [ ] 所有函数有docstring
- [ ] 代码通过Lint检查
- [ ] 单元测试覆盖率 > 80%

### 功能完整性
- [ ] 所有三个阶段的DA正常工作
- [ ] Web界面完整展示
- [ ] 报告正确生成
- [ ] 配置开关工作正常

### 用户体验
- [ ] UI清晰易懂
- [ ] 报告中DA部分有价值
- [ ] 性能影响可接受（< 20%额外时间）
- [ ] 文档完善，用户能快速上手

### 测试验证
- [ ] 单元测试全部通过
- [ ] 集成测试全部通过
- [ ] UI测试全部通过
- [ ] 至少5个真实案例验证

---

## 📝 更新日志

| 日期 | 更新内容 | 更新人 |
|------|---------|--------|
| 2026-01-03 | 创建初始TODO列表 | AI Council Team |

