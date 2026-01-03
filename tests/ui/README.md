# UI测试模块

本目录包含AICouncil的UI自动化测试。

## 目录结构

```
tests/ui/
├── conftest.py              # Pytest配置和全局Fixtures
├── pytest.ini               # Pytest配置文件
├── test_homepage.py         # 主页面功能测试
├── pages/                   # Page Object Model
│   ├── base_page.py        # 基础页面类
│   ├── home_page.py        # 主页面对象
│   └── __init__.py
├── fixtures/                # 测试数据和Mock
├── screenshots/             # 测试失败截图
├── videos/                  # 测试失败视频
└── reports/                 # HTML测试报告
```

## 快速开始

### 1. 安装依赖

```bash
pip install playwright pytest-playwright pytest-html
playwright install chromium
```

### 2. 运行测试

```bash
# 运行所有UI测试
pytest tests/ui/ -v

# 运行指定测试文件
pytest tests/ui/test_homepage.py -v

# 运行带标记的测试
pytest tests/ui/ -v -m smoke    # 只运行smoke测试
pytest tests/ui/ -v -m p0       # 只运行P0优先级测试

# 生成HTML报告
pytest tests/ui/ -v --html=tests/ui/reports/report.html --self-contained-html
```

### 3. 调试测试

```bash
# Headed模式（显示浏览器）
pytest tests/ui/ -v --headed

# 慢速模式（便于观察）
pytest tests/ui/ -v --slowmo=1000

# 运行单个测试并显示输出
pytest tests/ui/test_homepage.py::TestHomePage::test_page_loads_successfully -v -s
```

## 已实现的测试

### Phase 1: 基础架构（已完成）

- ✅ 环境准备和依赖安装
- ✅ Pytest配置文件
- ✅ Fixtures开发（flask_server, browser, page等）
- ✅ Page Object基础类
- ✅ 主页面Page Object
- ✅ 第一个测试用例（HP-001: 页面加载）

### 测试用例列表

| 用例ID | 用例名称 | 优先级 | 状态 |
|--------|---------|--------|------|
| HP-001 | test_page_loads_successfully | P0 | ✅ 已实现 |

## 下一步计划

参考 `docs/ui_testing_plan.md` 中的Phase 2任务清单。

## 常见问题

### Q: 测试运行很慢怎么办？
A: 使用`--headed=false`启用headless模式，或使用`-n auto`并行执行（需安装pytest-xdist）

### Q: 测试失败时如何调试？
A: 检查`tests/ui/screenshots/`目录下的失败截图，或使用`--headed`模式观察执行过程

### Q: Flask服务器启动失败怎么办？
A: 确保5000端口未被占用，或检查`conftest.py`中的服务器启动逻辑

## 贡献指南

添加新测试时请遵循：
1. 使用Page Object模式封装页面操作
2. 使用有意义的测试方法名（test_xxx_yyy）
3. 添加适当的pytest标记（@pytest.mark.smoke等）
4. 包含清晰的文档字符串说明测试目的
5. 使用断言方法提供友好的错误信息
