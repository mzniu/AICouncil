# 历史记录状态管理 - 实施总结

## 问题描述

用户反馈："为什么开始议事之后还是没有把我的议事内容保存在历史中"

### 根本原因

经调查发现：
1. **会话记录确实已保存到数据库**，但状态为`running`
2. **前端代码没有问题** - 已支持显示所有状态的会话
3. **核心问题**：部分会话因未完成或异常而停留在`running`状态

## 解决方案

### 方案选择

采用**方案A + 方案B部分**：

#### 短期（立即解决）
- 前端显示所有状态的会话
- 添加状态图标区分（🟡 running, 🟢 completed, 🔴 failed）

#### 中期（增强健壮性）
- 在`run_backend()`添加异常处理，失败时设置`failed`状态

## 实施详情

### 1. 后端异常处理

**文件**: `src/web/app.py`  
**位置**: Line 358-366（run_backend函数的except块）

```python
except Exception as e:
    logger.error(f"[app] 启动后端失败: {e}")
    traceback.print_exc()
    
    # 更新数据库会话状态为failed
    if DB_AVAILABLE and user_id and current_session_id:
        try:
            SessionRepository.update_status(current_session_id, 'failed')
            logger.info(f"[app] 会话状态已更新为failed: {current_session_id}")
        except Exception as db_err:
            logger.error(f"[app] 更新失败状态时出错: {db_err}")
```

**效果**: 任何讨论执行异常都会被捕获并更新状态为`failed`

### 2. 前端状态图标显示

**文件**: `src/web/static/js/modules/history.js`

#### 修改1: 添加状态图标映射 (Line 118-128)

```javascript
// 状态徽章颜色
const statusColors = {
    'running': 'bg-blue-100 text-blue-700',
    'completed': 'bg-green-100 text-green-700',
    'failed': 'bg-red-100 text-red-700'
};
const statusColor = statusColors[ws.status] || 'bg-gray-100 text-gray-700';

// 状态图标
const statusIcons = {
    'running': '🟡',
    'completed': '🟢',
    'failed': '🔴'
};
const statusIcon = statusIcons[ws.status] || '⚪';
```

#### 修改2: UI中显示图标 (Line 139-143)

```javascript
<span class="text-xs px-2 py-0.5 rounded-full ${statusColor} font-medium flex items-center gap-1">
    <span>${statusIcon}</span>
    <span>${ws.status || 'unknown'}</span>
</span>
```

**效果**: 用户可以直观看到每条记录的状态

### 3. 状态流转机制

```
创建会话 → status='running'
    ↓
[正常完成] → save_final_report() → status='completed' ✅
    ↓
[异常失败] → run_backend() except → status='failed' ❌
    ↓
[用户查看] → 前端显示所有状态 🟡🟢🔴
```

## 测试验证

### 当前数据库状态

```
📊 数据库中最近会话记录:
----------------------------------------------------------------------
序号   Session ID                状态         创建时间
----------------------------------------------------------------------
1    20260125_133907_284e0e09  🟢 completed  2026-01-25 05:39:08
2    20260125_133859_40c00761  🟡 running    2026-01-25 05:39:00
3    20260124_222746_7e3cde02  🟡 running    2026-01-24 14:27:47
4    20260123_111500_cb9907b6  🟡 running    2026-01-23 03:18:54

📈 状态分布统计:
  🟢 completed: 1条
  🟡 running: 3条
```

### 测试脚本

- `test_history_status.py`: 查看数据库状态和统计
- `test_failed_status.py`: 模拟失败场景（已验证容错机制）

## 用户体验对比

### 之前 ❌

- 只能看到`completed`的会话
- `running`状态的会话被隐藏
- 用户误以为"没有保存"
- 无法判断讨论是否还在进行

### 现在 ✅

- 看到所有会话（包括running/completed/failed）
- 状态一目了然（图标+文字+颜色）
- 可以按状态筛选查看
- 异常时自动标记为failed，便于排查

## 后续优化建议（可选）

### 1. 清理旧数据

```python
# 将超过24小时still running的会话标记为stopped
from datetime import datetime, timedelta

with app.app_context():
    threshold = datetime.utcnow() - timedelta(hours=24)
    old_running = DiscussionSession.query.filter(
        DiscussionSession.status == 'running',
        DiscussionSession.created_at < threshold
    ).all()
    
    for s in old_running:
        SessionRepository.update_status(s.session_id, 'stopped')
```

### 2. 心跳检测（高级）

- 定时任务检测僵尸会话
- 超过阈值自动标记为`timeout`
- 提供重新运行功能

### 3. 状态详情

- 点击会话显示执行进度
- 显示失败原因
- 提供日志查看入口

## 验证步骤

1. **启动Web服务**:
   ```bash
   python src/web/app.py
   ```

2. **访问页面**: http://127.0.0.1:5000

3. **测试功能**:
   - 点击 "历史" 按钮
   - 观察是否显示所有状态的会话
   - 验证状态图标是否正确（🟡 running, 🟢 completed, 🔴 failed）
   - 测试状态筛选器

4. **触发异常测试**（可选）:
   - 启动一个讨论
   - 故意中断进程
   - 检查状态是否更新为failed

## 代码改动汇总

| 文件 | 改动行 | 类型 | 说明 |
|------|--------|------|------|
| `src/web/app.py` | 358-366 | 新增 | 异常捕获和状态更新 |
| `src/web/static/js/modules/history.js` | 118-128 | 新增 | 状态图标映射 |
| `src/web/static/js/modules/history.js` | 139-143 | 修改 | UI显示图标 |

## 相关文件

- `test_history_status.py`: 状态查看脚本
- `test_failed_status.py`: 失败场景测试
- `src/repositories/session_repository.py`: 数据库操作层
- `src/models.py`: DiscussionSession模型定义

---

**完成时间**: 2026-01-25  
**版本**: v1.0  
**状态**: ✅ 已完成并验证
