# UI测试报告生成器

自动为 AICouncil UI 测试生成精美的 HTML 报告。

## 功能特性

✅ **精美界面**
- 与 AICouncil 主项目风格一致
- 使用 Tailwind CSS + ECharts
- 响应式设计，支持移动端

✅ **丰富的可视化**
- 测试状态分布饼图
- 执行时长排行柱状图
- 统计卡片和趋势分析

✅ **详细测试信息**
- 测试用例状态和耗时
- 失败原因和堆栈信息
- 截图和视频回放（内嵌 base64）
- 测试标记（markers）展示

✅ **交互功能**
- 实时搜索测试用例
- 按状态过滤
- 折叠/展开详情
- 一键查看截图/视频

## 使用方法

### 1. 运行测试并生成报告

```bash
# 运行所有UI测试（自动生成报告）
pytest tests/ui/ -v

# 运行指定测试文件
pytest tests/ui/test_homepage.py -v

# 运行带标记的测试
pytest tests/ui/ -v -m smoke
```

### 2. 查看报告

报告会自动生成到 `tests/ui/reports/` 目录：

- `test_report_YYYYMMDD_HHMMSS.html` - 带时间戳的报告
- `latest.html` - 最新报告的快捷方式

用浏览器打开即可查看：

```bash
# Windows
start tests/ui/reports/latest.html

# macOS
open tests/ui/reports/latest.html

# Linux
xdg-open tests/ui/reports/latest.html
```

## 报告内容

### 统计概览
- 总测试数
- 通过/失败/跳过/错误数量
- 通过率
- 总耗时

### 图表分析
- **状态分布饼图**：直观展示测试结果比例
- **执行时长排行**：识别慢速测试用例（Top 15）

### 测试详情
每个测试用例显示：
- 状态徽章（Passed/Failed/Skipped/Error）
- 执行时长
- 测试标记（如 `@pytest.mark.smoke`）
- 失败原因和堆栈信息
- 失败时的截图
- 测试过程视频

### 搜索和过滤
- 按测试名称搜索
- 按状态过滤（All/Passed/Failed/Skipped/Error）

## 自定义配置

### 修改报告输出目录

在 `conftest.py` 中修改：

```python
def pytest_configure(config):
    global _report_generator
    output_dir = Path("custom/report/path")
    _report_generator = TestReportGenerator(output_dir=output_dir)
    _report_generator.start_time = datetime.now()
```

### 自定义报告模板

编辑 `tests/ui/templates/report_template.html` 修改：
- 颜色主题
- 图表样式
- 布局结构

### 禁用截图/视频嵌入

如果报告文件过大，可以在 `report_generator.py` 中禁用文件嵌入：

```python
# 在 generate_html() 方法中注释掉这段
# for result in self.test_results:
#     if "screenshot" in result and result["screenshot"]:
#         result["screenshot_data"] = self.embed_file(...)
```

## 技术架构

### 核心组件

1. **report_generator.py** - 报告生成核心
   - `TestReportGenerator` 类
   - 收集测试结果
   - 生成图表数据
   - 渲染 HTML

2. **conftest.py** - Pytest 钩子集成
   - `pytest_configure` - 初始化报告生成器
   - `pytest_runtest_makereport` - 收集单个测试结果
   - `pytest_sessionfinish` - 生成最终报告

3. **report_template.html** - HTML 模板
   - Tailwind CSS 样式
   - ECharts 图表
   - 交互式 JavaScript

### 数据流

```
测试执行 → pytest hooks → TestReportGenerator → 收集结果
                                                    ↓
                                            生成图表数据
                                                    ↓
                                            渲染 HTML 模板
                                                    ↓
                                            写入文件系统
```

## 故障排除

### 报告未生成

检查是否正确导入：
```python
from .report_generator import TestReportGenerator
```

### 截图/视频未显示

确保 Playwright 配置正确：
```python
@pytest.fixture(scope="function")
def context(browser):
    context = browser.new_context(
        record_video_dir="tests/ui/videos",
        record_video_size={"width": 1280, "height": 720}
    )
    yield context
    context.close()
```

### 图表未渲染

检查 ECharts CDN 是否可访问，或使用本地版本：
```html
<!-- 替换为本地文件 -->
<script src="/static/vendor/echarts.min.js"></script>
```

## 示例报告

查看 `tests/ui/reports/` 目录下的示例报告了解完整功能。

## 更新日志

### v1.0.0 (2026-01-05)
- ✅ 初始版本
- ✅ 基础报告生成
- ✅ ECharts 图表集成
- ✅ 截图/视频嵌入
- ✅ 搜索和过滤功能
