# 重新生成报告功能 400 错误修复

## 问题现象

```
POST http://127.0.0.1:5000/api/rereport 400 (BAD REQUEST)
```

用户点击"重新生成报告"按钮时，请求失败并返回 400 错误。

## 根本原因分析

### 1. 参数类型错误

**问题位置**: `src/web/app.py` Line 598

```python
# 错误代码
generate_report_from_workspace(workspace_path, model_cfg)
```

**问题**:
- `workspace_path` 是 `Path` 对象，但 `generate_report_from_workspace` 函数签名要求 `str` 类型
- 缺少第三个参数 `session_id`

**函数签名** (`src/agents/langchain_agents.py` Line 1029):
```python
def generate_report_from_workspace(workspace_path: str, model_config: Dict[str, Any], session_id: str = None) -> str:
```

### 2. 错误处理不完善

**问题**:
- 没有外层 try-catch 捕获异常
- 前端没有显示后端返回的具体错误消息
- 日志不够详细，难以定位问题

## 解决方案

### 修复 1: 修正函数调用参数

**文件**: `src/web/app.py`

```python
# 修复前
generate_report_from_workspace(workspace_path, model_cfg)

# 修复后
generate_report_from_workspace(str(workspace_path), model_cfg, current_session_id)
```

**改进**:
- ✅ 将 `Path` 对象转换为字符串
- ✅ 传入 `session_id` 参数确保正确性

### 修复 2: 增强错误处理和日志

**后端改进** (`src/web/app.py`):

1. **添加请求级别日志**:
```python
logger.info(f"[rereport] 开始重新生成报告，Session ID: {current_session_id}")
logger.info(f"[rereport] 配置: backend={selected_backend}, model={selected_model}, reasoning={reasoning}")
logger.info(f"[rereport] 工作区路径: {workspace_path}")
```

2. **添加外层异常捕获**:
```python
except Exception as e:
    logger.error(f"[rereport] 请求处理失败: {e}")
    traceback.print_exc()
    return jsonify({"status": "error", "message": str(e)}), 500
```

3. **增强内部函数日志**:
```python
logger.info(f"[rereport] 调用 generate_report_from_workspace，workspace={workspace_path}, session_id={current_session_id}")
generate_report_from_workspace(str(workspace_path), model_cfg, current_session_id)
logger.info(f"[rereport] 报告生成完成")
```

**前端改进** (`src/web/templates/index.html`):

1. **显示具体错误消息**:
```javascript
if (data.status !== 'ok') {
    const errorMsg = data.message || t('msg_request_failed');  // 显示后端返回的错误
    showAlert(errorMsg, t('title_error'), 'error');
    toggleReportLoading(false);  // 清除加载状态
    isReportingPhase = false;
}
```

2. **处理网络错误**:
```javascript
catch (error) {
    console.error('Re-report error:', error);
    showAlert(t('msg_request_failed'), t('title_error'), 'error');
    toggleReportLoading(false);  // 清除加载状态
    isReportingPhase = false;
}
```

## 测试验证

### 测试步骤

1. **启动应用**:
```bash
python src/web/app.py
```

2. **完成一次讨论**:
   - 输入议题
   - 开始讨论
   - 等待讨论完成并生成报告

3. **测试重新生成报告**:
   - 点击"重新生成报告"按钮
   - 观察控制台日志
   - 确认新报告正确生成

### 预期日志输出

```
[rereport] 开始重新生成报告，Session ID: 20260110_123456_abc123
[rereport] 配置: backend=deepseek, model=None, reasoning=None
[rereport] 工作区路径: D:\git\MyCouncil\workspaces\20260110_123456_abc123
[rereport] 调用 generate_report_from_workspace，workspace=D:\git\MyCouncil\workspaces\20260110_123456_abc123, session_id=20260110_123456_abc123
[report] 正在从工作区 D:\git\MyCouncil\workspaces\20260110_123456_abc123 重新生成报告（Session ID: 20260110_123456_abc123）...
[report] 正在调用模型生成最终报告 (尝试 1/3)...
[report] 报告生成成功！
[rereport] 报告生成完成
```

### 错误场景测试

1. **未完成讨论时点击重新生成**:
   - 预期: 400 错误，消息"未找到当前会话 ID"
   - 前端显示具体错误

2. **工作区被删除**:
   - 预期: 404 错误，消息"工作区不存在: {session_id}"
   - 前端显示具体错误

3. **模型配置错误**:
   - 预期: 500 错误，返回具体的异常信息
   - 前端显示错误并清除加载状态

## 其他改进建议

### P1（高优先级）

1. **添加重试机制**:
```python
max_retries = 3
for attempt in range(max_retries):
    try:
        generate_report_from_workspace(...)
        break
    except Exception as e:
        if attempt == max_retries - 1:
            raise
        time.sleep(2)
```

2. **添加进度反馈**:
```python
send_web_event("report_progress", message="正在生成报告...", progress=50)
```

### P2（中优先级）

1. **缓存最近的报告**:
   - 避免频繁重新生成
   - 提供"恢复上次报告"功能

2. **支持取消重新生成**:
   - 添加取消按钮
   - 中断后台线程

## 总结

**根本原因**: 函数调用参数类型不匹配（Path vs str）和缺少必需参数

**修复方案**:
- ✅ 修正参数类型和数量
- ✅ 增强错误处理和日志
- ✅ 改进前端错误显示

**预期效果**: 重新生成报告功能正常工作，错误信息清晰可见
