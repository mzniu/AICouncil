# 数据库优先存储架构 - 修改方案

## 概述
当前系统使用**双写模式**（文件+数据库），本方案将改为**数据库优先模式**，文件系统仅作为备份和降级方案。

## 当前状态分析

### 1. 数据写入位置

#### A. `src/agents/langchain_agents.py` (核心讨论逻辑)

**文件写入**：
- 第961行：`decomposition.json`
- 第1017行：`decomposition_challenge.json`  
- 第1063行：`decomposition_revised.json`
- 第1199行：`round_{r}_data.json`
- 第1364行：`history.json` ✅ **已同步到数据库**
- 第1452行：`final_session_data.json` ✅ **已同步到数据库**
- 第1464行：`search_references.json` ✅ **已同步到数据库**

**数据库同步状态**：
- ✅ `decomposition` - Line 967: `SessionRepository.update_decomposition()`
- ✅ `history` - Line 1370: `SessionRepository.update_history()`
- ✅ `final_session_data` - Line 1458: `SessionRepository.update_final_session_data()`
- ✅ `search_references` - Line 1470: `SessionRepository.update_search_references()`
- ✅ `report_html` - Line 1480+: `SessionRepository.save_final_report()`

**结论**：**✅ 核心数据已全部同步到数据库**

#### B. `src/agents/framework_engine.py`

**文件写入**：
- 第157行：`stage_{index}_{name}.json` - 每个stage的执行结果

**数据库同步**：❌ **未同步**

**建议**：这些是中间过程数据，可以：
1. 暂时保留文件写入（调试用）
2. 或合并到 `final_session_data.json` 中

#### C. `src/agents/langchain_agents.py` - `execute_orchestration_plan()`

**文件写入**：
- `orchestration_result.json` - 完整的编排结果
- `search_references.json` - 搜索引用

**数据库同步**：❌ **未同步**  

**建议**：添加到 `final_session_data` 字段

#### D. `src/agents/demo_runner.py`

**文件写入**：
- 第198行：`report.html`

**数据库同步**：✅ **已在 langchain_agents.py 中同步**

### 2. 数据读取位置

#### A. `src/web/app.py` - `/api/load_workspace`

**当前逻辑**（第869-1050行）：
1. 检查 workspace 目录是否存在
2. 从文件读取：
   - `report.html`
   - `history.json` 或 `final_session_data.json` 或 `orchestration_result.json`
3. 重建 `discussion_events`

**问题**：
- ❌ 完全依赖文件系统
- ❌ 未使用数据库中的数据
- ❌ 删除文件后无法加载

**修改方案**：
```python
# 优先从数据库加载
if DB_AVAILABLE and current_user.is_authenticated:
    session = SessionRepository.get_session_by_id(session_id)
    if session:
        # 从数据库字段加载所有数据
        discussion_events = reconstruct_events_from_history(session.history)
        final_report = session.report_html
        config = session.config
        # ...
        return jsonify({...,"source": "database"})

# 降级：从文件系统加载
workspace_path = get_workspace_dir() / session_id
if workspace_path.exists():
    # 保持原有文件读取逻辑
    # ...
    return jsonify({...,"source": "filesystem"})
    
return jsonify({"error": "Session not found"}), 404
```

#### B. `src/agents/langchain_agents.py` - `generate_report_from_workspace()`

**当前逻辑**（第1500-1550行）：
1. 尝试读取 `orchestration_result.json`
2. 降级读取 `final_session_data.json`
3. 再降级读取 `history.json`

**问题**：
- ❌ 完全依赖文件系统
- ❌ 报告生成时无法使用数据库数据

**修改方案**：
```python
def generate_report_from_workspace(workspace_path, model_config, session_id):
    # 优先从数据库加载
    if DB_AVAILABLE and SessionRepository:
        session = SessionRepository.get_session_by_id(session_id)
        if session and session.final_session_data:
            final_data = session.final_session_data
            # 使用数据库数据生成报告
            # ...
            return report_html
    
    # 降级：从文件加载（向后兼容）
    # ... 保持原有逻辑
```

### 3. 报告相关功能

#### `src/web/app.py` - 报告相关端点

**需要修改的端点**：
- `/api/rereport` (Line 640+)：重新生成报告
- `/report/<workspace_id>` (Line 2230+)：查看报告
- `/api/download_report` (Line 1810+)：下载报告
- `/api/report_content/<workspace_id>` (Line 1840+)：获取报告内容
- `/api/save_report` (Line 2270+)：保存编辑后的报告

**当前逻辑**：都是从文件系统读写 `report.html`

**修改方案**：
- 读取：优先从 `session.report_html` 字段
- 写入：同时更新数据库和文件

## 实施计划

### 阶段1：核心读取改为数据库优先（高优先级）

1. **修改 `load_workspace`**
   - ✅ 优先从数据库加载
   - ✅ 文件系统作为降级

2. **修改 `generate_report_from_workspace`**
   - ✅ 优先从数据库读取 `final_session_data`
   - ✅ 降级从文件读取

3. **修改报告查看端点**
   - ✅ `/report/<workspace_id>` 从数据库读取
   - ✅ `/api/report_content` 从数据库读取

### 阶段2：完善数据库写入（中优先级）

1. **Framework Engine 数据同步**
   - 将 stage 结果合并到 `final_session_data`
   - 或添加新的 `stage_results` JSON 字段

2. **Orchestration 结果同步**
   - `execute_orchestration_plan` 写入数据库
   - 保存到 `final_session_data` 或新字段

### 阶段3：移除文件依赖（低优先级）

1. **配置开关**
   - 添加 `FILE_BACKUP_ENABLED` 环境变量
   - 默认值：`False`（不写文件）
   - 调试时设为 `True`

2. **清理文件写入代码**
   - 保留关键位置的文件写入（可配置）
   - 移除冗余的中间文件

## 代码修改示例

### 示例1：修改 load_workspace

```python
@app.route('/api/load_workspace/<session_id>', methods=['GET'])
@login_required
def load_workspace(session_id):
    global discussion_events, backend_logs, final_report, current_session_id, current_config
    
    # 权限检查
    if DB_AVAILABLE and current_user.is_authenticated:
        if not SessionRepository.check_user_permission(current_user.id, session_id):
            return jsonify({"status": "error", "message": "无权限"}), 403
    
    # 优先从数据库加载
    if DB_AVAILABLE:
        session = SessionRepository.get_session_by_id(session_id)
        if session:
            # 重建事件
            discussion_events = []
            for entry in (session.history or []):
                discussion_events.append({
                    "type": "agent_action",
                    "agent_name": entry.get("agent", "未知"),
                    "role_type": entry.get("role", "unknown"),
                    "content": entry.get("output", ""),
                })
            
            final_report = session.report_html or ""
            current_session_id = session_id
            current_config = {
                "issue": session.issue,
                "backend": session.backend,
                "model": session.model,
                **session.config
            }
            
            return jsonify({
                "status": "success",
                "events": discussion_events,
                "final_report": final_report,
                "config": current_config,
                "source": "database"
            })
    
    # 降级：文件系统
    workspace_path = get_workspace_dir() / session_id
    if not workspace_path.exists():
        return jsonify({"status": "error", "message": "工作区不存在"}), 404
    
    # ... 保持原有文件读取逻辑 ...
    return jsonify({..., "source": "filesystem"})
```

### 示例2：修改 generate_report_from_workspace

```python
def generate_report_from_workspace(workspace_path, model_config, session_id):
    # 优先从数据库加载
    if DB_AVAILABLE and SessionRepository:
        try:
            session = SessionRepository.get_session_by_id(session_id)
            if session and session.final_session_data:
                logger.info(f"[report] 从数据库加载数据生成报告")
                final_data = session.final_session_data
                # 使用数据库数据
                issue = final_data.get("issue", "")
                decomposition = final_data.get("decomposition", {})
                # ... 生成报告逻辑 ...
                return report_html
        except Exception as e:
            logger.warning(f"[report] 数据库加载失败，降级到文件: {e}")
    
    # 降级：从文件读取
    logger.info(f"[report] 从文件系统加载数据生成报告")
    # ... 保持原有逻辑 ...
```

### 示例3：配置文件备份开关

```python
# src/config.py
FILE_BACKUP_ENABLED = os.getenv('FILE_BACKUP_ENABLED', 'false').lower() == 'true'

# 在写入文件的地方添加判断
if FILE_BACKUP_ENABLED:
    with open(os.path.join(workspace_path, "history.json"), "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)
```

## 总结

### 已完成
- ✅ 核心数据（decomposition, history, final_data, search_refs, report）已同步到数据库
- ✅ 双写模式运行正常

### 待完成（本次任务）
1. **修改 `load_workspace`** - 优先从数据库读取
2. **修改 `generate_report_from_workspace`** - 优先从数据库读取
3. **修改报告查看端点** - 从数据库读取
4. **添加数据库优先的测试**

### 可选后续
- Framework Engine stage 结果同步
- Orchestration 结果同步
- 添加文件备份开关
- 完全移除文件依赖（可选）

## 兼容性

**向后兼容**：保留文件系统降级方案，确保：
1. 历史会话（文件系统）仍可访问
2. 数据库故障时可降级
3. 迁移过程平滑
