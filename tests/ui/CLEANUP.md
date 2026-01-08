# 测试清理机制说明

## 概述

`test_discussion_optimized.py` 中实现了完整的测试数据清理机制，在所有测试完成后自动清理生成的临时文件。

## 清理内容

### 1. **Workspace目录清理**
- 删除本次测试生成的workspace目录（`workspaces/YYYYMMDD_HHMMSS_UUID/`）
- 清理今天创建的其他测试workspace（避免历史测试数据堆积）

### 2. **测试报告清理**
- 保留最近3个测试报告（`tests/ui/reports/test_report_*.html`）
- 自动删除更早的历史报告

### 3. **进程清理**
- 通过`stop_discussion_cleanup` fixture确保讨论进程正常停止
- Flask服务器在测试结束后自动关闭（session级fixture）

## 实现方式

```python
@classmethod
def teardown_class(cls):
    """类级别清理：在所有测试完成后执行"""
    # 1. 清理本次测试的workspace
    # 2. 清理今日其他测试workspace
    # 3. 清理旧测试报告（保留最近3个）
```

## 触发时机

- **teardown_class**: 在`TestDiscussionOptimized`类的所有测试方法执行完成后自动触发
- **执行顺序**: test_01 → test_02 → ... → test_07 → teardown_class → cleanup

## Workspace路径获取

在test_01中通过API获取当前讨论的workspace路径：

```python
response = requests.get("http://127.0.0.1:5000/api/status")
data = response.json()
TestDiscussionOptimized._workspace_dir = data["workspace_dir"]
```

## 保护机制

- 使用try-except包裹所有清理操作，避免清理失败影响测试结果
- 保留最近3个报告便于问题追溯
- 只清理今天创建的workspace，避免误删历史重要数据

## 手动清理

如需手动清理所有测试数据：

```powershell
# 清理所有workspace
Remove-Item workspaces/* -Recurse -Force

# 清理所有测试报告
Remove-Item tests/ui/reports/*.html -Force
```

## 清理日志

清理过程会输出详细日志：

```
🧹 [Cleanup] 开始清理测试数据...
  ✓ 已删除workspace: 20260106_180624_abc123
  ✓ 已清理 2 个今日测试workspace
  ✓ 已清理 5 个旧测试报告
✅ [Cleanup] 清理完成
```
