# 角色设计师功能使用指南

## 功能概述

AI角色设计师是AICouncil的自动化角色创建工具，通过自然语言描述需求，AI将自动生成完整的角色配置，包括：
- 角色基本信息（名称、描述）
- 工作阶段定义（职责、思维方式、输出格式）
- 推荐人物原型

## 快速开始

### 1. 打开角色设计师

**方式一：通过高级配置**
1. 点击页面右上角"⚙️ 高级配置"按钮
2. 切换到"系统设置"标签页
3. 点击"✨ 创建新角色 (AI自动设计)"按钮

### 2. 描述需求（Step 1）

在需求描述框中输入您希望创建的角色功能和特点，例如：

```
我需要一个擅长数据分析的角色，能够处理统计分析、数据可视化和趋势预测任务。
这个角色应该具备批判性思维，输出结构化的分析报告。
```

**提示：详细描述以下内容**：
- 专业领域和核心能力
- 工作方式和思维风格
- 输出要求和格式

**示例需求：**
- 📊 市场调研员：收集行业数据、分析竞品策略、生成SWOT报告
- 💡 创意激发官：头脑风暴、跨领域联想、打破常规思维
- ⚠️ 风险评估师：识别潜在风险、评估影响程度、提出缓解措施

### 3. AI生成（Step 2）

点击"开始生成 →"按钮后：
- AI将分析您的需求
- 自动设计角色的阶段、职责、思维方式
- 推荐匹配的历史/虚构人物原型
- 预计耗时：30-60秒

### 4. 预览与保存（Step 3）

生成完成后，您可以：
- **预览基本信息**：技术名称、显示名称、角色描述
- **查看工作阶段**：每个阶段的职责、思维方式、输出格式
- **了解推荐人物**：参考人物的特质和推荐理由
- **编辑调整**：修改显示名称和描述（技术名称不可修改）
- **保存角色**：点击"保存角色"按钮完成创建

## 技术实现

### 后端架构

1. **Schema定义** ([src/agents/schemas.py](../src/agents/schemas.py))
   - `RoleDesignOutput`: 角色设计完整输出
   - `RoleStageDefinition`: 阶段定义
   - `FamousPersona`: 推荐人物

2. **RoleManager扩展** ([src/agents/role_manager.py](../src/agents/role_manager.py))
   - `generate_yaml_from_design()`: 从设计生成YAML配置
   - `generate_prompt_from_design()`: 从阶段生成Prompt模板
   - `create_new_role()`: 创建新角色（保存YAML + Prompt文件）

3. **API端点** ([src/web/app.py](../src/web/app.py))
   - `POST /api/roles/design`: 调用AI生成角色设计
   - `POST /api/roles`: 创建新角色

4. **LangChain集成** ([src/agents/langchain_agents.py](../src/agents/langchain_agents.py))
   - `call_role_designer()`: 调用DeepSeek Reasoner生成设计

### 前端实现

1. **3步向导Modal** ([src/web/templates/index.html](../src/web/templates/index.html))
   - Step 1: 需求输入界面（textarea + 示例）
   - Step 2: 生成加载界面（spinner + 状态更新）
   - Step 3: 预览编辑界面（基本信息 + 阶段 + 人物卡片）

2. **JavaScript函数**
   - `openRoleDesigner()`: 打开modal并重置状态
   - `updateDesignerStep()`: 更新步骤指示器和按钮
   - `designerNextStep()`: 处理"下一步"逻辑，调用API
   - `renderRolePreview()`: 渲染角色预览卡片
   - `saveNewRole()`: 保存角色到服务器

### Prompt设计

role_designer的prompt ([src/agents/roles/role_designer_generate.md](../src/agents/roles/role_designer_generate.md)) 包含：
- 系统架构说明（现有角色、讨论流程）
- 可用Schema列表
- 角色设计指导（命名、描述、阶段、人物）
- 集成考虑（插入点、协作方式）
- 输出格式要求（JSON Schema）
- 设计原则和示例

## 单元测试

### 测试覆盖

1. **Schema测试** ([tests/test_role_designer.py](../tests/test_role_designer.py))
   - `TestRoleDesignSchemas`: 6个测试（验证、缺失字段、无效命名等）

2. **RoleManager测试**
   - `TestRoleManagerDesigner`: 3个测试（YAML生成、创建成功、重名冲突）

3. **API测试**
   - `TestRoleDesignerAPI`: 3个测试（生成端点、创建端点、参数验证）

### 运行测试

```bash
# 运行所有角色设计师测试
pytest tests/test_role_designer.py -v

# 运行特定测试类
pytest tests/test_role_designer.py::TestRoleDesignSchemas -v

# 端到端测试（需要真实API调用）
python tests/test_e2e_role_designer.py
```

## 注意事项

### 角色命名规则
- **技术名称** (role_name): 必须是小写字母、数字、下划线组合，以字母开头
  - ✅ 有效: `data_analyst`, `market_researcher`, `risk_evaluator`
  - ❌ 无效: `数据分析师`, `Data-Analyst`, `123_role`

### Schema选择
- 优先复用现有Schema: `PlanSchema`, `AuditorSchema`, `LeaderSummary`
- 如需新Schema，在设计中说明理由，后续手动创建

### 文件保存位置
- 开发环境: `src/agents/roles/`
- 打包版: `%LOCALAPPDATA%\AICouncil\roles\` (Windows)
- 自动备份: `roles/backups/`

### 性能考虑
- AI生成耗时：30-60秒（取决于DeepSeek API响应速度）
- 推理强度：默认使用`deepseek-reasoner`（temperature=0.7）
- Token消耗：约2000-3000 tokens/次

## 故障排查

### 生成失败
- **症状**: Step 2显示"❌ 生成失败"
- **原因**: API密钥错误、网络问题、提示词解析失败
- **解决**: 检查`src/config.py`中的`DEEPSEEK_API_KEY`，查看日志`aicouncil.log`

### 创建失败
- **症状**: Step 3保存时提示"创建失败"
- **原因**: 角色名冲突、文件权限问题、YAML格式错误
- **解决**: 
  - 检查是否已存在同名角色
  - 确认roles目录有写权限
  - 验证生成的YAML格式

### 角色不显示
- **症状**: 创建成功但在角色列表中看不到
- **原因**: 角色标记为`hidden: true`或未重新加载
- **解决**: 刷新页面，检查YAML中的`ui.hidden`字段

## 扩展开发

### 添加新Schema
如果现有Schema不满足需求，需要：
1. 在`src/agents/schemas.py`定义新的Pydantic模型
2. 更新role_designer prompt中的"可用Schema"列表
3. 重新训练/调整prompt示例

### 自定义Prompt模板
修改`src/agents/roles/role_designer_generate.md`：
- 调整系统架构说明
- 添加更多设计原则
- 提供更多示例

### 支持多轮优化
当前版本是单次生成，如需支持迭代优化：
1. 添加Step 4: 用户反馈界面
2. 扩展`call_role_designer()`支持`previous_design`参数
3. 修改prompt支持"基于反馈修改设计"模式

## 更新日志

### v1.0.0 (2026-01-09)
- ✅ 实现基础角色设计功能
- ✅ 3步向导UI（需求 → 生成 → 预览）
- ✅ 自动生成YAML配置和Prompt文件
- ✅ 推荐人物原型功能
- ✅ 完整单元测试覆盖（12个测试）
- ✅ 端到端测试脚本

### 待实现功能 (Phase 3)
- 🔄 Prompt质量优化（多次迭代测试）
- 🔄 错误处理完善（重名冲突、生成超时）
- 🔄 多轮对话优化（用户反馈 → 修改设计）
- 🔄 角色预览沙盒（在创建前测试角色）

## 相关文档

- [架构设计](../docs/architecture.md)
- [API规范](../docs/api_spec.md)
- [Prompt模板](../docs/prompt_templates.md)
- [主README](../README.md)
