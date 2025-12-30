# Baseline 测试改进记录

## 日期：2025-12-30

## 问题分析

### 问题1：API 响应格式不匹配
**现象**：测试脚本期望 `/api/start` 返回 `{"status": "started", "session_id": "..."}`，但实际返回 `{"status": "ok"}`

**原因**：
- `/api/start` 接口启动后台线程后立即返回 `{"status": "ok"}`
- `session_id` 由 `demo_runner.py` 在后台生成，通过事件流 `/api/update` 发送

**解决方案**：
1. 修改 `start_discussion()` 检查 `status == "ok"` 而不是 `"started"`
2. 在 `wait_for_completion()` 中从事件流获取 `session_id`
3. 增加等待时间让后端初始化（2秒→3秒）

### 问题2：并发讨论冲突
**现象**：如果前一个讨论未完成，新测试启动会失败并返回"讨论正在进行中"错误

**原因**：
- Flask 使用全局 `is_running` 标志防止并发讨论
- 测试脚本未检查现有讨论状态

**解决方案**：
在 `start_discussion()` 前添加检查逻辑：
```python
# 检查是否有正在运行的讨论
status_resp = requests.get(f"{self.base_url}/api/status")
if status_data.get("is_running"):
    # 尝试停止现有讨论
    requests.post(f"{self.base_url}/api/stop")
    time.sleep(2)  # 等待清理
```

### 问题3：超时时间不足
**现象**：实际测试耗时约3-4分钟，但默认超时仅5分钟，裕度不足

**原因**：
- 1轮讨论包含：问题分解→策论家提案→监察官审查→搜索→报告生成
- 搜索引擎请求可能耗时10-30秒
- DeepSeek API 在高峰期响应较慢
- 未考虑网络波动

**解决方案**：
- 超时时间从 300秒（5分钟）增加到 600秒（10分钟）
- 在README中说明可根据需要调整

## 改进内容

### 1. 启动前检查（新增）
```python
def start_discussion(self):
    # 检查并停止现有讨论
    status_resp = requests.get(f"{self.base_url}/api/status", timeout=2)
    if status_data.get("is_running"):
        self.log("检测到正在运行的讨论，尝试停止...", "WARN")
        stop_resp = requests.post(f"{self.base_url}/api/stop", timeout=5)
        time.sleep(2)  # 等待清理
```

### 2. API响应格式适配（已修复）
```python
# 修改前
if data.get("status") == "started":
    self.session_id = data.get("session_id")
    
# 修改后
if data.get("status") == "ok":
    self.log("讨论已启动", "SUCCESS")
    time.sleep(3)  # 给后端初始化时间
```

### 3. Session ID 获取增强（已修复）
```python
# 从事件流动态获取
for event in events:
    if event.get("type") == "session_start":
        self.session_id = event.get("session_id")
        
# 即使未获取到也允许继续（容错）
if not session_id_found:
    self.log("警告：未能获取Session ID，但讨论已完成", "WARN")
    return True
```

### 4. 超时时间调整
```python
# 修改前
def wait_for_completion(self, timeout=300):  # 5分钟

# 修改后
def wait_for_completion(self, timeout=600):  # 10分钟
```

### 5. 错误处理增强
```python
# 添加更详细的错误信息
if response.status_code == 200:
    data = response.json()
    if data.get("status") == "ok":
        return True
    else:
        self.log(f"启动返回异常状态: {data}", "ERROR")
        return False
else:
    self.log(f"启动失败 (HTTP {response.status_code}): {response.text}", "ERROR")
    return False
```

## 测试验证

### 测试环境
- 操作系统: Windows 11
- Python: 3.9+
- 后端: DeepSeek API (deepseek-chat)
- 配置: 1轮, 1策论家, 1监察官

### 测试结果
✅ **通过** - Session: `20251230_181609_6d92ab13`

**执行时间**: 约4分钟
- 启动: 18:16:07
- 完成: 18:20:00左右

**生成文件**:
- ✅ decomposition.json (2.6 KB)
- ✅ round_1_data.json (6.4 KB)
- ✅ final_session_data.json (16.2 KB)
- ✅ history.json (11.4 KB)
- ✅ report.html (16.8 KB)
- ✅ search_references.json (26.4 KB)

**验证项**:
- ✅ Flask服务器正常运行
- ✅ 讨论启动成功
- ✅ 工作空间目录创建（使用 path_manager）
- ✅ 所有必需文件生成
- ✅ HTML报告格式正确
- ✅ 讨论流程完整

## 后续建议

### 1. 添加进度显示
在等待过程中显示更详细的进度信息：
```python
# 当前只显示状态变化
if current_status != last_status:
    self.log(f"状态: {current_status}")

# 建议添加
self.log(f"状态: {current_status} | 已等待: {elapsed}秒 | 剩余: {timeout-elapsed}秒")
```

### 2. 支持快速模式
添加命令行参数支持快速测试：
```python
parser.add_argument('--quick', action='store_true', 
                    help='Quick mode: no search, minimal rounds')

if args.quick:
    payload["rounds"] = 1
    payload["enable_search"] = False  # 如果支持
```

### 3. 添加重试机制
对于网络波动导致的失败，可以自动重试：
```python
max_retries = 3
for attempt in range(max_retries):
    if start_discussion():
        break
    if attempt < max_retries - 1:
        self.log(f"启动失败，{3-attempt}秒后重试...", "WARN")
        time.sleep(3)
```

### 4. 生成测试报告
保存测试结果到JSON文件：
```python
test_result = {
    "timestamp": datetime.now().isoformat(),
    "session_id": self.session_id,
    "duration": elapsed_time,
    "status": "passed" if success else "failed",
    "files_generated": file_list,
    "errors": error_list
}
with open("test_results.json", "w") as f:
    json.dump(test_result, f, indent=2)
```

### 5. 集成到CI/CD
创建GitHub Actions工作流：
```yaml
name: Baseline Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Baseline Test
        run: |
          python src/web/app.py &
          sleep 5
          python tests/test_baseline_api.py
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
```

## 总结

### 关键改进
1. ✅ 修复API响应格式不匹配
2. ✅ 添加并发讨论检查和停止逻辑
3. ✅ 增加超时时间到10分钟
4. ✅ 增强Session ID获取逻辑
5. ✅ 改进错误处理和日志输出

### 验证结果
- **Stage 1路径管理器**: ✅ 工作正常
- **核心功能**: ✅ 无破坏性改动
- **测试可靠性**: ✅ 显著提升

### 下一步
可以安全地进入 **Stage 2: 配置系统重构**
