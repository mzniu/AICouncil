# 会话记录预创建机制 - 改进说明

## 问题分析

用户提出："是不是应该在用户点击开始议事就把议事内容开始储存到数据库中了？"

### 之前的流程问题

```
用户点击"开始议事" 
  → POST /api/start
  → 启动后台线程 run_backend()
  → 调用 run_full_cycle()
  → 【才在这里创建数据库记录】 ❌
```

**问题**：
1. 如果线程启动失败 → 数据库中没有记录
2. 如果参数验证失败 → 数据库中没有记录
3. 如果在创建记录前出错 → 用户看不到任何痕迹

### 改进后的流程

```
用户点击"开始议事"
  → POST /api/start
  → 【立即创建数据库记录】 ✅ (status='running')
  → 启动后台线程 run_backend(session_id)
  → 调用 run_full_cycle(session_id)
  → 完成时更新状态为'completed'
  → 失败时更新状态为'failed'
```

**优势**：
1. ✅ 用户点击即刻保存，数据不丢失
2. ✅ 即使后续失败，历史中也有记录
3. ✅ 可以追溯所有尝试（包括失败的）
4. ✅ 更符合用户预期："点了就应该保存"

## 实施细节

### 1. 修改 `/api/start` 端点

**文件**: `src/web/app.py`  
**位置**: Line 257-294

#### 改动说明

在启动后台线程**之前**，立即创建数据库记录：

```python
# ===【改进】在启动线程前立即创建数据库记录===
session_id = None
if DB_AVAILABLE and user_id:
    from datetime import datetime
    import uuid
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
    
    config_data = {
        "backend": backend,
        "model": model,
        "rounds": rounds,
        "planners": planners,
        "auditors": auditors,
        "reasoning": reasoning,
        "agent_configs": agent_configs,
        "use_meta_orchestrator": use_meta_orchestrator
    }
    
    try:
        db_session = SessionRepository.create_session(
            user_id=user_id,
            session_id=session_id,
            issue=issue,
            config=config_data,
            tenant_id=tenant_id
        )
        if db_session:
            logger.info(f"[start_discussion] ✅ 会话记录已创建: {session_id}")
        else:
            logger.warning(f"[start_discussion] ⚠️ 会话记录创建失败: {session_id}")
    except Exception as e:
        logger.error(f"[start_discussion] ❌ 创建会话记录时出错: {e}")
        session_id = None  # 创建失败，清空session_id

# 启动后台线程时传递session_id
thread = threading.Thread(
    target=run_backend, 
    args=(issue, backend, model, rounds, planners, auditors, 
          agent_configs, reasoning, use_meta_orchestrator, 
          user_id, tenant_id, session_id)  # 新增参数
)
thread.daemon = True
thread.start()

return jsonify({"status": "ok", "session_id": session_id})  # 返回session_id
```

### 2. 修改 `run_backend` 函数

**文件**: `src/web/app.py`  
**位置**: Line 301

#### 改动说明

接收并保存session_id到全局变量：

```python
def run_backend(issue, backend, model, rounds, planners, auditors, 
                agent_configs=None, reasoning=None, use_meta_orchestrator=False, 
                user_id=None, tenant_id=None, session_id=None):  # 新增参数
    global is_running, current_process, current_session_id
    
    # 保存session_id到全局变量（用于异常处理时更新状态）
    current_session_id = session_id
    
    try:
        # ... 调用 run_full_cycle 时传递 session_id
        result = run_full_cycle(
            issue=issue,
            model_config=model_cfg, 
            max_rounds=rounds,
            num_planners=planners,
            num_auditors=auditors,
            agent_configs=agent_configs,
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id  # 传递预创建的session_id
        )
```

### 3. 修改 `run_full_cycle` 函数

**文件**: `src/agents/langchain_agents.py`  
**位置**: Line 909

#### 改动说明

接收可选的session_id参数，如果已存在则使用，否则生成新的：

```python
def run_full_cycle(issue_text: str, model_config: Dict[str, Any] = None, 
                   max_rounds: int = 3, num_planners: int = 2, num_auditors: int = 2, 
                   agent_configs: Dict[str, Any] = None, 
                   user_id: Optional[int] = None, tenant_id: Optional[int] = None, 
                   session_id: Optional[str] = None) -> Dict[str, Any]:  # 新增参数
    """
    Args:
        ...
        session_id: 预创建的会话ID（可选，如果提供则使用，否则生成新的）
    """
    
    # 1. 初始化 Session 和 Workspace
    # 如果提供了session_id则使用，否则生成新的
    if not session_id:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
    
    workspace_path = get_workspace_dir() / session_id
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    # 2. 数据库会话记录处理
    # 如果session_id是预创建的，则不需要重新创建
    if DB_AVAILABLE and user_id and SessionRepository:
        from src.web.app import app
        
        try:
            with app.app_context():
                from src.models import DiscussionSession
                existing = DiscussionSession.query.filter_by(session_id=session_id).first()
                
                if existing:
                    logger.info(f"[cycle] 使用预创建的会话记录: {session_id}")
                else:
                    # 向后兼容：直接调用run_full_cycle时仍可创建记录
                    logger.info(f"[cycle] 创建新的会话记录: {session_id}")
                    # ... 创建逻辑
```

## 向后兼容性

这个改进保持了向后兼容：

1. **通过Web API调用**：使用预创建的session_id
2. **直接调用 `run_full_cycle()`**：如果没有提供session_id，会自动生成新的并创建记录

## 测试验证

### 测试脚本

运行 `test_session_precreate.py`：

```bash
python test_session_precreate.py
```

### 测试结果

```
✅ 会话记录创建成功
   Session ID: 20260125_134613_a1eafaf1
   状态: running
   创建时间: 2026-01-25 05:46:13.579310

✅ 在数据库中找到记录
   议题: 测试议题：验证会话记录预创建机制
   状态: running
   用户ID: 1
   租户ID: 1
   后端: deepseek
   模型: deepseek-chat

✅ 所有字段验证通过
```

## 用户体验提升

### 之前 ❌

```
用户: 点击"开始议事"
系统: 启动线程...
[如果失败]
用户: 去历史页面查看 → "咦？没有记录？是不是没保存？"
```

### 现在 ✅

```
用户: 点击"开始议事"
系统: ✅ 立即保存到数据库 (status='running')
系统: 启动线程...
[无论成功失败]
用户: 去历史页面查看 → 看到记录！
  - 成功: 🟢 completed
  - 进行中: 🟡 running
  - 失败: 🔴 failed
```

## 优势总结

1. **数据不丢失**
   - 用户点击即保存
   - 即使系统崩溃也有记录

2. **可追溯性**
   - 所有尝试都有痕迹
   - 便于调试和分析

3. **符合直觉**
   - 用户期望："点了就应该保存"
   - 更好的用户体验

4. **错误可见**
   - 失败的尝试也会显示
   - 用户知道"确实执行了，只是失败了"

## 代码改动总结

| 文件 | 函数/位置 | 改动类型 | 说明 |
|------|-----------|----------|------|
| `src/web/app.py` | `start_discussion()` Line 257-294 | 新增 | 启动线程前创建记录 |
| `src/web/app.py` | `run_backend()` Line 301 | 修改 | 接收并保存session_id |
| `src/agents/langchain_agents.py` | `run_full_cycle()` Line 909 | 修改 | 接收可选session_id |

## 相关文件

- `test_session_precreate.py`: 测试脚本
- `docs/history_status_fix.md`: 历史状态显示改进文档

---

**完成时间**: 2026-01-25  
**版本**: v2.0  
**状态**: ✅ 已完成并测试通过
