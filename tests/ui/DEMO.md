# 测试优化演示

## 快速验证

验证新的优化测试是否正确配置：

```bash
# 1. 查看测试收集（不执行）
python -m pytest tests/ui/test_discussion_optimized.py --collect-only

# 预期输出：
# - TestDiscussionOptimized 类（6个测试）
# - test_start_discussion_success_standalone（独立测试）
# 共7个测试
```

## 执行测试

### 选项1：只运行优化测试（推荐）
```bash
# 使用辅助脚本
python tests/ui/run_optimized_tests.py

# 或直接用pytest
pytest tests/ui/test_discussion_optimized.py::TestDiscussionOptimized -v -m p0
```

**预期结果**：
- ✅ 6个测试按顺序执行
- ⏱️ 总耗时约10-15分钟
- 📊 生成HTML测试报告

### 选项2：运行所有P0测试
```bash
pytest tests/ui/ -v -m p0
```

**包含**：
- Homepage测试（3个）~30秒
- 优化讨论测试（6个）~10分钟
- 独立启动测试（1个）~5分钟
- 总耗时约15-20分钟

### 选项3：性能对比（警告：耗时很长）
```bash
python tests/ui/run_optimized_tests.py --compare
```

**对比内容**：
- 旧测试：test_agent_output_display_* 3个测试 ~30分钟
- 新测试：TestDiscussionOptimized 6个测试 ~10分钟
- 总耗时约40分钟

## 验证要点

### 1. Fixture共享验证
观察日志输出，应该只看到一次：
```
🚀 [Class Fixture] 启动共享讨论会话...
📝 [Class Fixture] 配置议题: ...
⏳ [Class Fixture] 等待讨论完成并生成报告...
✅ [Class Fixture] 讨论完成，报告已生成
```

### 2. 测试顺序验证
测试应该按编号顺序执行：
```
🔍 [Test 01] 验证议长输出...
✅ 议长输出验证通过

🔍 [Test 02] 验证策论家输出...
✅ 策论家输出验证通过

🔍 [Test 03] 验证监察官输出...
✅ 监察官输出验证通过

... 依此类推
```

### 3. 清理验证
所有测试完成后应该看到一次清理：
```
🧹 [Class Fixture] 清理共享会话...
```

## 调试技巧

### 查看完整日志
```bash
pytest tests/ui/test_discussion_optimized.py::TestDiscussionOptimized -v -s
```

`-s` 参数显示所有print输出

### 只运行特定测试
```bash
# 只运行前3个测试
pytest tests/ui/test_discussion_optimized.py::TestDiscussionOptimized::test_01_leader_output_display -v
pytest tests/ui/test_discussion_optimized.py::TestDiscussionOptimized::test_02_planner_output_display -v
pytest tests/ui/test_discussion_optimized.py::TestDiscussionOptimized::test_03_auditor_output_display -v
```

**注意**：如果只运行部分测试，fixture仍会完整执行一次讨论

### 查看浏览器操作（非headless）
Fixture已配置为 `headless=False`，可以看到浏览器自动化过程

## 故障排查

### 问题1：Fixture启动失败
**症状**：所有6个测试都显示 SKIPPED 或 ERROR

**解决**：
1. 检查Flask服务器是否正常启动
2. 查看日志中的错误信息
3. 确认议题文本正确配置

### 问题2：报告生成超时
**症状**：Fixture在"等待讨论完成"阶段超时（10分钟）

**解决**：
1. 检查DeepSeek API是否可用
2. 确认网络连接正常
3. 查看src/config.py中的API密钥配置

### 问题3：测试验证失败
**症状**：Fixture成功但某个测试失败

**排查**：
1. 查看失败测试的断言信息
2. 确认元素选择器是否正确
3. 检查报告内容是否完整

## 对比原始测试

### 原始测试特点
- **文件**：`tests/ui/test_discussion.py`
- **模式**：每个测试独立启动讨论
- **优点**：测试完全隔离，互不影响
- **缺点**：执行时间长，资源浪费

### 优化测试特点
- **文件**：`tests/ui/test_discussion_optimized.py`
- **模式**：共享一次讨论，多个验证
- **优点**：执行时间短，效率高
- **缺点**：测试间有依赖（必须按顺序）

### 何时使用哪种？

**使用优化测试**（推荐）：
- ✅ 日常开发测试
- ✅ CI/CD流水线
- ✅ 快速验证功能

**使用原始测试**：
- ✅ 调试特定功能
- ✅ 验证测试隔离性
- ✅ 排查偶发问题

## 后续优化建议

### 1. 增加测试配置变体
创建多个fixture支持不同配置：
- `completed_discussion_single_round` （当前）
- `completed_discussion_multi_round` （3轮）
- `completed_discussion_complex` （多智能体）

### 2. 并行执行
使用pytest-xdist在多CPU上并行运行：
```bash
pytest tests/ui/ -n auto -m p0
```

**注意**：class级别fixture仍会在每个worker中执行一次

### 3. 缓存讨论结果
对于真正不变的测试场景，可以缓存讨论结果到文件：
- 第一次运行生成并保存
- 后续运行直接加载
- 需要时可以强制重新生成

## 相关文档

- [完整优化方案](OPTIMIZATION.md)
- [Pytest Fixture文档](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [Playwright Python文档](https://playwright.dev/python/docs/test-runners)
