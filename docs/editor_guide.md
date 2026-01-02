# 交互式报告编辑器使用指南

## 功能概述

AICouncil 的交互式报告编辑器允许您直接在浏览器中编辑生成的报告，支持版本控制、自动保存等功能。

## 快速开始

### 1. 生成报告

首先通过 AICouncil 生成一份报告：

```bash
python src/agents/demo_runner.py --backend deepseek --rounds 1 --issue "您的议题"
```

### 2. 查看报告

报告会保存在 `workspaces/{session_id}/report.html`，直接用浏览器打开即可。

### 3. 进入编辑模式

打开报告后，页面右上角会显示编辑工具栏：

```
┌─────────────────────────────────────┐
│ [编辑报告] [版本历史] [查看模式]   │
└─────────────────────────────────────┘
```

点击 **[编辑报告]** 按钮即可进入编辑模式。

## 核心功能

### 📝 文本编辑

**进入编辑模式后：**
- 所有文本区域会显示虚线边框（悬停时）
- 直接点击任意文本即可编辑
- 支持基础格式：加粗、斜体、链接等
- 实时显示"未保存的修改"状态

**支持编辑的内容：**
- ✅ 标题和副标题
- ✅ 段落内容
- ✅ 列表项
- ✅ 数据点和注释
- ❌ 图表（需专门的图表编辑器 - Phase 2）
- ❌ 引用列表（需专门的引用管理器 - Phase 2）

### 💾 保存与自动保存

**手动保存：**
1. 编辑完成后点击 **[保存]** 按钮
2. 输入本次修改的简要说明（可选）
3. 系统会创建版本快照并保存

**自动保存：**
- 编辑模式下每 60 秒自动保存草稿
- 草稿保存在 `workspaces/{session_id}/report_draft.html`
- 不会覆盖正式版本

**保存后的文件：**
```
workspaces/{session_id}/
├── report.html                    # 当前版本
├── report_draft.html             # 自动保存的草稿
├── report_edits.json            # 版本元数据
└── versions/                     # 历史版本
    ├── v1_20260102_140530.html
    ├── v2_20260102_145620.html
    └── ...
```

### 🕐 版本历史

点击 **[版本历史]** 按钮可查看所有历史版本：

```
┌────────────────────────────────────┐
│ 版本历史                            │
├────────────────────────────────────┤
│ [当前版本]                          │
│ 2026-01-02 14:56                   │
│ 修改了市场分析章节                  │
├────────────────────────────────────┤
│ [v2]                               │
│ 2026-01-02 14:05                   │
│ 用户手动编辑                        │
│ [预览] [恢复此版本]                 │
├────────────────────────────────────┤
│ [v1]                               │
│ 2026-01-02 13:40                   │
│ 初始生成的报告                      │
│ [预览] [恢复此版本]                 │
└────────────────────────────────────┘
```

**版本操作：**
- **预览**：在新窗口查看该版本内容
- **恢复此版本**：将报告恢复到该版本（当前未保存的修改会丢失）

### ⚠️ 取消编辑

点击 **[取消]** 按钮可放弃当前所有修改，恢复到编辑前的状态。

**注意：** 如果有未保存的修改，系统会弹出确认对话框。

## API 端点

编辑器通过以下 API 与后端通信：

### 保存编辑

```
POST /api/report/edit/{workspace_id}

Request Body:
{
  "html_content": "<完整的HTML内容>",
  "sections": [...],
  "citations": [...],
  "metadata": {
    "last_edited": "2026-01-02T14:56:00",
    "edit_summary": "用户输入的修改说明"
  }
}

Response:
{
  "status": "success",
  "version": "v2",
  "message": "保存成功"
}
```

### 自动保存草稿

```
POST /api/report/draft/{workspace_id}

Request Body:
{
  "html_content": "<完整的HTML内容>",
  "metadata": {
    "last_saved": "2026-01-02T14:55:30",
    "is_draft": true
  }
}

Response:
{
  "status": "success",
  "message": "草稿已保存"
}
```

### 获取版本列表

```
GET /api/report/versions/{workspace_id}

Response:
[
  {
    "id": "current",
    "timestamp": "2026-01-02T14:56:00",
    "changes_summary": "当前版本",
    "file_path": "report.html"
  },
  {
    "id": "v2",
    "timestamp": "2026-01-02T14:05:30",
    "changes_summary": "用户手动编辑",
    "file_path": "versions/v2_20260102_140530.html"
  },
  ...
]
```

### 获取版本内容

```
GET /api/report/version/{workspace_id}/{version_id}

Response: HTML content
```

### 恢复版本

```
POST /api/report/restore/{workspace_id}/{version_id}

Response:
{
  "status": "success",
  "message": "已恢复到版本 v2"
}
```

### 获取编辑历史

```
GET /api/report/history/{workspace_id}

Response:
{
  "status": "success",
  "history": [...],
  "current_version": "v2"
}
```

## 实现细节

### 前端架构

**文件结构：**
```
src/web/static/
├── js/
│   └── report-editor.js      # 编辑器核心逻辑
└── css/
    └── editor.css             # 编辑器样式
```

**核心类：`ReportEditor`**

```javascript
class ReportEditor {
    constructor(workspaceId)
    
    // 初始化
    init()
    createToolbar()
    bindEvents()
    
    // 编辑模式
    enterEditMode()
    exitEditMode()
    toggleEditMode()
    
    // 保存操作
    saveReport()
    autoSave()
    cancelEdit()
    
    // 数据提取
    extractReportData()
    
    // 版本管理
    loadEditHistory()
    showVersionHistory()
    previewVersion(versionId)
    restoreVersion(versionId)
    
    // UI更新
    updateStatus(text, type)
    showNotification(message, type, duration)
}
```

### ContentEditable 实现

编辑器使用浏览器原生的 `contenteditable` 属性：

```javascript
// 进入编辑模式
const textElements = el.querySelectorAll('p, h2, h3, li, .data-point');
textElements.forEach(textEl => {
    textEl.setAttribute('contenteditable', 'true');
    textEl.classList.add('editable-active');
});
```

**样式控制：**

```css
[contenteditable="true"]:hover {
    outline: 2px dashed #93c5fd;
    background-color: rgba(147, 197, 253, 0.05);
}

[contenteditable="true"]:focus {
    outline: 2px solid #3b82f6;
    background-color: rgba(59, 130, 246, 0.05);
}
```

### 版本控制策略

**版本命名：**
- `v1`, `v2`, `v3`... 按顺序递增
- 文件名：`{version_id}_{timestamp}.html`
- 例如：`v2_20260102_140530.html`

**元数据存储：**

```json
{
  "current_version": "v2",
  "versions": [
    {
      "id": "v1",
      "timestamp": "20260102_133531",
      "changes_summary": "初始生成的报告",
      "file_path": "versions/v1_20260102_133531.html"
    },
    {
      "id": "v2",
      "timestamp": "20260102_140530",
      "changes_summary": "编辑了技术对比章节",
      "file_path": "versions/v2_20260102_140530.html"
    }
  ]
}
```

## 使用场景

### 场景 1：修正报告中的错误

1. 打开报告 → 点击"编辑报告"
2. 找到错误内容并直接修改
3. 点击"保存"并输入"修正了XXX错误"
4. 确认保存成功后退出编辑模式

### 场景 2：添加自定义内容

1. 进入编辑模式
2. 在需要添加内容的位置直接输入
3. 使用浏览器的格式化快捷键（如 Ctrl+B 加粗）
4. 保存修改

### 场景 3：回滚到之前的版本

1. 点击"版本历史"
2. 找到需要恢复的版本
3. 点击"预览"确认内容
4. 点击"恢复此版本"
5. 确认操作后页面会自动刷新

### 场景 4：对比不同版本

1. 打开版本历史
2. 点击版本的"预览"按钮在新窗口打开
3. 并排对比当前版本和历史版本
4. 根据需要决定是否恢复

## 常见问题

### Q: 为什么有些区域无法编辑？

A: 以下区域暂不支持直接编辑：
- 图表（ECharts/Mermaid）
- 引用列表
- 报告标题栏
- 工具栏

这些功能将在后续版本（Phase 2）中通过专门的编辑器实现。

### Q: 自动保存的草稿在哪里？

A: 草稿保存在 `workspaces/{session_id}/report_draft.html`，不会覆盖正式版本。您可以手动打开该文件查看。

### Q: 版本历史会占用很多空间吗？

A: 是的，每个版本都会完整保存 HTML 文件。建议定期清理旧版本，或者只保留关键版本。

### Q: 编辑器是否支持协作编辑？

A: 当前版本（MVP）不支持多人实时协作。如果多人同时编辑，后保存的会覆盖先保存的内容。协作功能计划在 Phase 3 实现。

### Q: 如何导出编辑后的报告？

A: 编辑并保存后，使用报告页面原有的导出功能（HTML/Screenshot/PDF）即可导出最新版本。

## 后续计划

### Phase 2（增强功能）

- [ ] 图表编辑器（修改图表数据和样式）
- [ ] 引用管理器（添加/删除/编辑引用）
- [ ] 浮动工具栏（选中文字时显示格式化选项）
- [ ] 版本对比视图（并排对比差异）

### Phase 3（高级功能）

- [ ] AI 辅助改写（选中段落后调用 LLM 优化）
- [ ] 协作批注（多人异步评论）
- [ ] 自定义样式主题
- [ ] 导出增强（Word 格式、定制 PDF 模板）

## 开发者指南

### 扩展编辑功能

如需添加新的编辑功能，参考以下流程：

1. **前端**：在 `report-editor.js` 中添加方法
2. **后端**：在 `app.py` 中添加对应的 API 端点
3. **样式**：在 `editor.css` 中添加相关样式
4. **提示词**：更新 `langchain_agents.py` 中的 Reporter 提示词，确保生成的 HTML 包含必要的数据属性

### 测试编辑器

```bash
# 1. 生成测试报告
python src/agents/demo_runner.py --backend deepseek --rounds 1 --issue "测试议题"

# 2. 找到生成的报告路径
# 输出示例：workspaces/20260102_133531_b7c03beb/report.html

# 3. 用浏览器打开报告并测试编辑功能

# 4. 检查版本文件
ls workspaces/20260102_133531_b7c03beb/versions/
```

## 技术栈

- **前端**：原生 JavaScript + ContentEditable API
- **后端**：Flask REST API
- **存储**：文件系统（HTML + JSON 元数据）
- **样式**：CSS Grid + Flexbox

## 许可与贡献

本编辑器是 AICouncil 项目的一部分，遵循项目整体许可协议。

欢迎提交 Issue 和 Pull Request！
