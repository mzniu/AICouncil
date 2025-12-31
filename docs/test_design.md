# 测试设计文档

版本：v1.0.0

本文档总结了针对 AICouncil 项目的测试策略与实施建议，包含单元测试（UT）、API 测试与 UI/E2E 测试三类，以及配套的夹具、CI、覆盖率和防止不稳定的实践。目标是建立可复现、可自动化、低脆弱性的测试体系，支持 PR 校验与定期回归。

## 1 目标与原则
- 可重复：测试在本地与 CI 上能一致运行。
- 可隔离：外部依赖（网络、浏览器、OS 文件）使用 mock 或本地替代。
- 快速反馈：单元测试快速，E2E 放到更少频率或并行化执行。
- 可诊断：失败时收集日志、截图、HTML 快照和覆盖报告。

## 2 单元测试（Unit Tests）

目标：验证模块内部逻辑、边界条件和错误处理，不触发真实网络/浏览器。

- 框架：`pytest`，扩展 `pytest-cov`, `pytest-xdist`, `pytest-mock`。
- 目录：`tests/unit/`，命名：`test_<module>.py`。
- 覆盖点：
  - `src/agents/`：prompt 构建、JSON 清洗/解析、retry 逻辑。
  - `src/utils/`：`search_utils.py`、`pdf_exporter.py`（核心算法部分用 mock 隔离 I/O）。
  - `src/web/app.py`：路由处理器的纯逻辑（不启动服务器时测试）。
- Mock：
  - 网络请求：`requests` 用 `responses` 或 `requests-mock`。
  - Playwright/drission：替换为 stub，断言调用参数。
  - 文件系统：`tmp_path` fixture 或 `pyfakefs`（如需）。
- 用例类型：正常路径、边界值、异常/抛错路径。
- 参数化：`@pytest.mark.parametrize` 覆盖输入矩阵。
- 依赖项安装示例：

```bash
pip install pytest pytest-cov pytest-xdist pytest-mock
pytest tests/unit -q
```

## 3 API 测试

目标：验证 HTTP 接口契约、状态码、错误响应、认证与主要业务场景。

- 框架：`pytest` + `httpx`（或 Flask 自带的 test client）。
- 目录：`tests/api/`。
- 测试要点：
  - 响应字段与数据结构（成功 / 4xx / 5xx）。
  - 权限与认证（模拟 token/无 token）。
  - 输入校验与错误信息。
  - 重要流程（创建会话、运行讨论、导出报告）。
- 隔离与数据：使用 `testing` 配置、内存 sqlite 或临时工作区（`workspaces/temp_test/`），并在每个用例前后清理。
- 合约测试（可选）：若有 OpenAPI，使用 `schemathesis` 做 fuzz/contract 测试。

示例运行：

```bash
pytest tests/api -q
```

## 4 UI / E2E 测试（Playwright）

目标：覆盖关键用户流程（启动会话、策论家/监察官周期、导出 PDF、搜索循环），在真实浏览器环境下验证交互与集成点。

- 工具：Playwright（优先）或 `pytest-playwright`。Playwright 已用于项目中，推荐复用相同 runner。
- 目录：`tests/e2e/`。
- 核心场景：
  - 启动应用并访问首页加载资源。
  - 创建并运行讨论会（带多轮）、等待并断言最终报告生成。
  - PDF 导出：触发 Playwright 导出并检查返回文件 / 内容是否包含关键文本与图表。
  - 搜索循环：模拟模型输出包含 `[SEARCH:]` 的流程，确保系统执行搜索并继续。
- 稳定性实践：
  - 用 `start_server` fixture 在 headless 模式下启动本地服务（随机端口）。
  - 使用 `await page.wait_for_selector()` 等就绪条件替代固定 sleep。
  - 失败时保存截图、录屏与 HTML（CI artifact）。
  - 对关键页面使用视觉回归（Playwright snapshot）。
- 并发与跨平台：在 CI 上 headless Linux 运行所有 E2E；在 Windows 做一次烟雾测试以覆盖平台特异问题。

示例运行：

```bash
pip install playwright pytest-playwright
playwright install
pytest tests/e2e -q
```

## 5 测试夹具与辅助工具

- `tests/conftest.py`：提供全局 fixtures：`app`, `client`, `db_session`, `temp_workspace`, `start_server`, `playwright_page`。
- 工厂：使用 `factory_boy` 或手写 builder 以便快速构建测试对象。
- 记录/回放：对第三方 API 使用 `vcrpy` 或 `requests-mock` 来记录和回放网络交互，避免外部依赖导致不稳定。

## 6 CI 集成（GitHub Actions 推荐）

- 基本流程：
  1. Checkout
  2. Setup Python
  3. Cache pip
  4. Install deps
  5. `playwright install --with-deps`
  6. Run `pytest`（按标记将 E2E 与单元分开）
  7. Upload artifacts（失败时的 screenshots、videos、coverage）
- 建议分流：PR 中仅运行单元与 API 测试；在 `main` 或 nightly 运行 E2E。
- 例：`.github/workflows/tests.yml` 包含 matrix（python 版本）、artifact 上传与 coverage badge 发布步骤。

## 7 覆盖率与质量门槛

- 使用 `pytest-cov` 输出 `coverage.xml` 与终端报告。
- 初始目标：80% 覆盖率（可针对核心模块要求更高）。
- 结合 `ruff`/`flake8` 和 `mypy`（可选）做静态质量检测。

## 8 防止脆弱性与维护策略

- 避免时间敏感断言（如固定 sleep）。
- 对 flaky 测试开启短期重试并记录为 artifact，后续分析并根治。
- 将慢速 E2E 标记 `@pytest.mark.e2e` 并在 CI 中单独调度。

## 9 性能与安全测试（可选）

- 负载测试：`locust` 或 `k6` 针对关键 API（生成会话、导出报告）做小规模压测。
- 安全扫描：`bandit`、依赖漏洞扫描（Dependabot / GitHub security alerts）。

## 10 快速上手命令汇总

```bash
# 安装基础测试依赖
pip install -r requirements.txt
pip install pytest pytest-cov pytest-xdist pytest-mock pytest-playwright
playwright install

# 运行单元测试
pytest tests/unit -q

# 运行 API 测试
pytest tests/api -q

# 运行 E2E（本地）
pytest tests/e2e -q

# 运行全部并生成覆盖率
pytest --cov=src --cov-report=xml --cov-report=term
```

## 11 后续工作建议（优先级）
1. 编写 `tests/conftest.py` 与 1-2 个示例单元 / API 测试（门槛最低）。
2. 添加 CI 流水线，使 PR 自动运行单元与 API 测试。
3. 逐步补充 E2E 场景并在夜间构建中运行。
4. 为关键失败采集 artifacts（截图、视频、coverage），并添加失败通知。

---
如需，我可以：
- 在仓库中生成 `tests/conftest.py`、若干示例测试文件与 `.github/workflows/tests.yml` 的初始实现；
- 或仅生成模板与示例以供你手动审阅。请选择要我执行的下一步。
