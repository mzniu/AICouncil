# AICouncil Baseline Test

## 概述

Baseline 测试用于验证 EXE 打包改动（阶段1：路径抽象层）后，核心议事流程是否仍能正常运行。

## 测试配置

- **讨论轮数**: 1轮
- **策论家数量**: 1个
- **监察官数量**: 1个
- **测试议题**: "如何提高团队协作效率"
- **模型后端**: deepseek-chat

## 测试内容

### 1. 服务器检查
- 验证 Flask 服务器在 `http://127.0.0.1:5000` 运行

### 2. 讨论启动
- 通过 `/api/start` 接口启动讨论
- 验证返回的 Session ID

### 3. 流程监控
- 轮询 `/api/status` 接口
- 监控讨论进度
- 等待完成（最长10分钟，适应不同模型响应速度）

### 4. 结果验证
- **工作空间目录**: 验证 `workspaces/{session_id}/` 创建成功
- **必要文件**: 检查以下文件存在
  - `history.json` - 完整历史记录
  - `decomposition.json` - 问题分解结果
  - `round_1_data.json` - 第1轮讨论数据
  - `final_session_data.json` - 最终会话数据
- **角色完整性**: 验证所有角色出现
  - Leader（议长）
  - Planner（策论家）
  - Auditor（监察官）
  - Reporter（记录员）
- **报告生成**: 验证 HTML 报告生成且格式正确

## 使用方法

### 方法一：自动运行（推荐）

Windows 双击运行：
```bash
tests\run_baseline_test.bat
```

该脚本会：
1. 检查 Flask 服务器状态
2. 如未运行，自动启动服务器
3. 运行 Baseline 测试
4. 显示测试结果

### 方法二：手动运行

**步骤1：启动 Flask 服务器**
```bash
python src\web\app.py
```

**步骤2：运行测试**（新开终端）
```bash
python tests\test_baseline_api.py
```

### 方法三：PowerShell 运行

```powershell
# 启动服务器（后台）
Start-Process python -ArgumentList "src\web\app.py" -WindowStyle Hidden

# 等待5秒
Start-Sleep -Seconds 5

# 运行测试
python tests\test_baseline_api.py
```

## 前置条件

1. **Python 环境**
   - Python 3.9+
   - 已安装 `requirements.txt` 依赖

2. **API 密钥配置**
   - `src/config.py` 中配置 `DEEPSEEK_API_KEY`
   - 或设置环境变量 `DEEPSEEK_API_KEY`

3. **网络连接**
   - 能够访问 DeepSeek API

## 预期输出

### 成功示例

```
============================================================
  AICouncil Baseline Test - REST API
============================================================

[18:00:00] ✅ 服务器运行正常

[18:00:01] ℹ️ 启动讨论：如何提高团队协作效率
[18:00:02] ✅ 讨论已启动，Session ID: 20251230_180002_a1b2c3d4

[18:00:03] ⏳ 等待讨论完成（最长 600 秒）...
[18:00:05] ℹ️ 状态: 议长正在分解问题...
[18:00:20] ℹ️ 状态: 策论家正在提供方案...
[18:00:45] ℹ️ 状态: 监察官正在审查...
[18:01:10] ℹ️ 状态: 生成最终报告...
[18:01:30] ✅ 讨论已完成

[18:01:31] ℹ️ 验证讨论结果...
[18:01:31] ✅ 工作空间目录存在: D:\git\MyCouncil\workspaces\20251230_180002_a1b2c3d4
[18:01:31] ✅ 文件存在: history.json
[18:01:31] ✅ 文件存在: decomposition.json
[18:01:31] ✅ 文件存在: round_1_data.json
[18:01:31] ✅ 文件存在: final_session_data.json
[18:01:31] ✅ 历史记录包含 25 条事件
[18:01:31] ✅ 所有角色都已出现: leader, planner, auditor, reporter
[18:01:32] ✅ 报告已生成（长度: 15234 字符）
[18:01:32] ✅ 报告格式正确（包含 HTML）

============================================================
[18:01:32] ✅ 🎉 Baseline 测试通过！
============================================================

[18:01:32] ℹ️ 保留测试数据: 20251230_180002_a1b2c3d4
[18:01:32] ℹ️ 如需删除，请访问 Web UI 或手动删除工作空间目录
```

### 失败示例

如果测试失败，会显示具体错误：

```
[18:00:00] ❌ 服务器未运行！请先启动: python src/web/app.py
```

或：

```
[18:01:30] ❌ 缺失文件: final_session_data.json
[18:01:30] ❌ Baseline 测试失败！
```

## 故障排查

### 1. 服务器未运行

**错误**: `服务器未运行！请先启动...`

**解决**:
```bash
python src\web\app.py
```

### 2. API 密钥未配置

**错误**: 讨论启动后立即失败，日志显示 API 错误

**解决**: 编辑 `src/config.py`
```python
DEEPSEEK_API_KEY = "your-api-key-here"
```

### 3. 端口被占用

**错误**: Flask 启动失败，提示 5000 端口已被占用

**解决**:
```bash
# 查找占用进程
netstat -ano | findstr :5000

# 结束进程
taskkill /F /PID <进程ID>
```

### 4. 超时

**错误**: `超时！讨论未在 600 秒内完成`

**可能原因**:
- 网络问题（无法访问 DeepSeek API）
- API 响应慢（高峰期）
- 模型配置错误
- 讨论轮数或agent数量过多

**解决**:
- 检查网络连接
- 检查 API 密钥是否有效
- 减少讨论轮数或agent数量
- 如有必要可增加超时时间（修改测试脚本中的 timeout 参数）

### 5. 路径错误

**错误**: `工作空间目录不存在`

**可能原因**: 路径管理器配置问题

**解决**:
```bash
# 验证路径管理器
python -c "from src.utils.path_manager import print_environment_info; print_environment_info()"
```

## 测试数据清理

测试完成后，数据会保留在 `workspaces/` 目录。

**手动删除**:
```bash
# PowerShell
Remove-Item -Recurse workspaces\20251230_180002_*

# CMD
rmdir /s /q workspaces\20251230_180002_*
```

**通过 Web UI 删除**:
1. 访问 http://127.0.0.1:5000
2. 点击"历史记录"
3. 找到对应 Session
4. 点击"删除"

## 集成到 CI/CD

可以将此测试集成到自动化流程：

```yaml
# GitHub Actions 示例
- name: Run Baseline Test
  run: |
    python src/web/app.py &
    sleep 5
    python tests/test_baseline_api.py
  env:
    DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
```

## 扩展测试

如需更复杂的测试，可以修改脚本：

```python
# 修改测试配置
payload = {
    "issue": "你的测试议题",
    "backend": "openai",  # 切换模型
    "model": "gpt-4",
    "rounds": 2,          # 增加轮数
    "planners": 2,        # 增加策论家数量
    "auditors": 2         # 增加监察官数量
}
```

## 相关文件

- `tests/test_baseline_api.py` - 测试脚本
- `tests/run_baseline_test.bat` - 自动运行脚本
- `src/utils/path_manager.py` - 路径管理器（被测试模块）
- `src/web/app.py` - Flask 应用（被测试API）
- `src/agents/langchain_agents.py` - 核心逻辑（被测试流程）

## 版本历史

- **v1.0.0** (2025-12-30) - 初始版本
  - 基本 REST API 测试
  - 验证路径管理器集成
  - 验证工作空间创建
  - 验证报告生成
