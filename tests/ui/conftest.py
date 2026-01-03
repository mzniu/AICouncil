"""
Pytest配置和全局Fixtures
提供浏览器实例、Flask服务器、页面对象等测试基础设施
"""
import pytest
import subprocess
import time
import os
import shutil
import glob
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext


# ==================== Flask服务器 Fixture ====================

@pytest.fixture(scope="session")
def flask_server():
    """
    启动Flask服务器（session级别，整个测试会话共享）
    
    Returns:
        str: Flask服务器URL (http://127.0.0.1:5000)
    """
    # 设置测试环境变量
    env = os.environ.copy()
    env['FLASK_ENV'] = 'testing'
    env['TESTING'] = 'true'
    
    # 启动Flask服务器
    print("\n🚀 启动Flask测试服务器...")
    process = subprocess.Popen(
        ['python', 'src/web/app.py'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.getcwd()
    )
    
    # 等待服务器启动（最多10秒）
    base_url = 'http://127.0.0.1:5000'
    for i in range(10):
        try:
            import requests
            response = requests.get(base_url, timeout=1)
            if response.status_code == 200:
                print(f"✅ Flask服务器启动成功: {base_url}")
                break
        except Exception:
            time.sleep(1)
    else:
        process.terminate()
        raise RuntimeError("Flask服务器启动失败")
    
    yield base_url
    
    # 测试结束后关闭服务器
    print("\n🛑 关闭Flask测试服务器...")
    process.terminate()
    process.wait(timeout=5)


# ==================== 浏览器 Fixtures ====================

@pytest.fixture(scope="session")
def browser_context_args():
    """
    浏览器上下文参数配置
    可在测试中覆盖以自定义设置
    """
    return {
        "viewport": {"width": 1920, "height": 1080},
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
    }


@pytest.fixture(scope="session")
def playwright_browser():
    """
    提供Playwright浏览器实例（session级别，复用以提高性能）
    
    Returns:
        Browser: Chromium浏览器实例
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # 设为True可无头模式运行
            slow_mo=50,      # 减慢操作速度便于观察（调试时使用）
        )
        yield browser
        browser.close()


@pytest.fixture
def context(playwright_browser: Browser, browser_context_args):
    """
    提供浏览器上下文（function级别，每个测试独立）
    
    Args:
        playwright_browser: 浏览器实例
        browser_context_args: 上下文配置参数
        
    Returns:
        BrowserContext: 浏览器上下文
    """
    context = playwright_browser.new_context(**browser_context_args)
    
    # 配置视频录制（仅在测试失败时保存）
    # context.tracing.start(screenshots=True, snapshots=True)
    
    yield context
    
    # 清理上下文
    # context.tracing.stop(path="tests/ui/traces/trace.zip")
    context.close()


@pytest.fixture
def page(context: BrowserContext, flask_server: str):
    """
    提供页面实例（function级别，每个测试独立页面）
    
    Args:
        context: 浏览器上下文
        flask_server: Flask服务器URL
        
    Returns:
        Page: Playwright页面对象
    """
    page = context.new_page()
    
    # 导航到主页
    page.goto(flask_server, wait_until="domcontentloaded")
    
    # 等待页面加载完成
    page.wait_for_load_state("networkidle", timeout=10000)
    
    yield page
    
    # 测试失败时截图
    if hasattr(page, '_test_failed'):
        screenshot_path = f"tests/ui/screenshots/{page._test_name}.png"
        page.screenshot(path=screenshot_path)
        print(f"📸 测试失败截图: {screenshot_path}")
    
    page.close()


@pytest.fixture
def authenticated_page(page: Page, flask_server: str):
    """
    提供已完成初始化的页面（等待关键元素加载）
    并确保没有运行中的讨论会话
    
    Args:
        page: 页面实例
        flask_server: Flask服务器URL
        
    Returns:
        Page: 已初始化的页面对象
    """
    # 等待关键元素加载完成
    page.wait_for_selector('#issue-input', state='visible', timeout=10000)
    page.wait_for_selector('#start-btn', state='visible', timeout=5000)
    page.wait_for_selector('#backend-select', state='visible', timeout=5000)
    
    # 检查是否有运行中的讨论，如果有则通过API停止
    try:
        is_running = page.evaluate("""() => {
            const startBtn = document.getElementById('start-btn');
            return startBtn && startBtn.disabled === true;
        }""")
        
        if is_running:
            print("⚠️ 检测到运行中的讨论，通过API停止...")
            # 直接调用停止API
            import requests
            import time
            try:
                response = requests.post(f"{flask_server}/api/stop", timeout=5)
                if response.status_code == 200:
                    print("✅ API停止命令已发送")
                    
                    # 等待后端状态更新（最多5秒）
                    max_wait = 5
                    for i in range(max_wait):
                        status_response = requests.get(f"{flask_server}/api/status", timeout=2)
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            if not status_data.get('is_running', False):
                                print("✅ 后端状态已更新为停止")
                                break
                        time.sleep(1)
                    
                    # 等待前端按钮恢复可用（最多20秒）
                    try:
                        page.wait_for_function(
                            """() => {
                                const startBtn = document.getElementById('start-btn');
                                return startBtn && startBtn.disabled === false;
                            }""",
                            timeout=20000
                        )
                        print("✅ 讨论已停止，按钮已恢复可用")
                    except Exception as wait_error:
                        print(f"⚠️ 等待按钮恢复超时，尝试刷新页面")
                        page.reload(wait_until="domcontentloaded")
                        page.wait_for_load_state("networkidle", timeout=5000)
                        print("✅ 页面已刷新")
                else:
                    print(f"⚠️ API停止返回非200状态: {response.status_code}")
            except Exception as api_error:
                print(f"⚠️ API停止失败: {api_error}")
                # 如果API失败，尝试刷新页面作为fallback
                try:
                    page.reload(wait_until="domcontentloaded")
                    page.wait_for_load_state("networkidle", timeout=5000)
                    print("✅ 页面已刷新作为fallback")
                except:
                    pass
    except Exception as e:
        print(f"⚠️ 清理讨论状态失败: {e}")
    
    return page


# ==================== 测试数据清理 Fixtures ====================

@pytest.fixture(autouse=True)
def cleanup_test_workspaces():
    """
    自动清理测试工作区（每个测试后执行）
    删除 workspaces/test_* 目录
    """
    yield
    
    # 测试后清理
    test_workspaces = glob.glob('workspaces/test_*')
    for workspace in test_workspaces:
        try:
            shutil.rmtree(workspace)
            print(f"🧹 清理测试工作区: {workspace}")
        except Exception as e:
            print(f"⚠️  清理失败 {workspace}: {e}")


@pytest.fixture(autouse=True)
def cleanup_test_reports():
    """
    自动清理旧的测试报告（session开始前执行）
    """
    # 在测试开始前清理超过7天的测试报告
    reports_dir = Path('tests/ui/reports')
    if reports_dir.exists():
        import time
        current_time = time.time()
        for report_file in reports_dir.glob('*.html'):
            file_age_days = (current_time - report_file.stat().st_mtime) / 86400
            if file_age_days > 7:
                report_file.unlink()
                print(f"🗑️  删除旧报告: {report_file.name}")
    
    yield


# ==================== Pytest Hooks ====================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook: 捕获测试结果，用于在测试失败时截图
    """
    outcome = yield
    rep = outcome.get_result()
    
    # 只处理测试执行阶段（不包括setup/teardown）
    if rep.when == "call":
        # 获取page fixture（如果存在）
        if "page" in item.fixturenames:
            page = item.funcargs.get("page")
            if page and rep.failed:
                page._test_failed = True
                page._test_name = item.nodeid.replace("::", "_").replace("/", "_")


def pytest_configure(config):
    """
    Hook: Pytest配置初始化
    """
    # 确保必要的目录存在
    Path('tests/ui/screenshots').mkdir(parents=True, exist_ok=True)
    Path('tests/ui/videos').mkdir(parents=True, exist_ok=True)
    Path('tests/ui/reports').mkdir(parents=True, exist_ok=True)
    Path('tests/ui/traces').mkdir(parents=True, exist_ok=True)


# ==================== 辅助Fixtures ====================

@pytest.fixture
def mock_api_responses(page: Page):
    """
    Mock API响应（用于快速测试，无需等待真实API）
    
    使用示例:
        def test_with_mock(mock_api_responses):
            # 所有API调用都会被Mock
            pass
    """
    # Mock启动讨论API
    page.route('**/api/start', lambda route: route.fulfill(
        status=200,
        content_type='application/json',
        body='{"session_id": "test_mock_123", "status": "ok"}'
    ))
    
    # Mock状态查询API - 返回运行中状态
    page.route('**/api/status', lambda route: route.fulfill(
        status=200,
        content_type='application/json',
        body='{"is_running": true, "progress": 50, "current_stage": "讨论中", "status": "running"}'
    ))
    
    # Mock更新事件API
    page.route('**/api/update', lambda route: route.fulfill(
        status=200,
        content_type='application/json',
        body='{"status": "ok"}'
    ))
    
    # Mock报告编辑API
    page.route('**/api/report/edit/*', lambda route: route.fulfill(
        status=200,
        content_type='application/json',
        body='{"success": true, "version": "v1"}'
    ))
    
    return page


@pytest.fixture
def test_issue_text():
    """
    提供测试用议题文本
    """
    return "如何提高UI测试的自动化覆盖率"


@pytest.fixture
def test_config():
    """
    提供测试配置参数
    """
    return {
        "backend": "deepseek",
        "rounds": 1,
        "planners": 1,
        "auditors": 1,
    }
