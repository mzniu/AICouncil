"""
Pytest配置和全局Fixtures
提供浏览器实例、Flask服务器、页面对象等测试基础设施
"""
import pytest
import subprocess
import time
import os
import sys
import shutil
import glob
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))
from report_generator import TestReportGenerator


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
    env['FLASK_DEBUG'] = '0'  # 禁用 debug 模式避免 reloader
    
    # 启动Flask服务器（不捕获输出避免管道阻塞）
    print("\n🚀 启动Flask测试服务器...")
    process = subprocess.Popen(
        ['python', 'src/web/app.py'],
        env=env,
        stdout=subprocess.DEVNULL,  # 直接丢弃输出
        stderr=subprocess.DEVNULL,
        cwd=os.getcwd()
    )
    
    # 等待服务器启动（增加到20秒，因为首次加载 Playwright 较慢）
    base_url = 'http://127.0.0.1:5000'
    max_retries = 20
    for i in range(max_retries):
        try:
            import requests
            response = requests.get(base_url, timeout=2)
            if response.status_code == 200:
                print(f"✅ Flask服务器启动成功: {base_url}")
                time.sleep(1)  # 额外等待确保完全就绪
                break
        except Exception as e:
            if i == max_retries - 1:
                print(f"❌ Flask服务器启动超时: {e}")
            time.sleep(1)
    else:
        process.terminate()
        raise RuntimeError("Flask服务器启动失败")
    
    yield base_url
    
    # 测试结束后关闭服务器
    print("\n🛑 关闭Flask测试服务器...")
    process.terminate()
    try:
        # 等待进程优雅退出
        process.wait(timeout=5)
        print("✅ Flask服务器已关闭")
    except subprocess.TimeoutExpired:
        print("⚠️ 强制终止Flask服务器")
        process.kill()
        process.wait()
    
    # 额外等待确保端口释放
    time.sleep(2)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()  # 强制终止


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
    
    # 简单清理：仅关闭页面（Flask服务器是session级别，无需每次停止讨论）
    # 测试失败时截图
    if hasattr(page, '_test_failed'):
        screenshot_path = f"tests/ui/screenshots/{page._test_name}.png"
        page.screenshot(path=screenshot_path)
        print(f"📸 测试失败截图: {screenshot_path}")
    
    page.close()


@pytest.fixture(scope="class")
def completed_discussion_page(browser_type, flask_server: str):
    """
    Class级别fixture：启动一次完整讨论并等待报告生成
    多个测试可以共享这个讨论结果，避免重复启动
    
    Args:
        browser_type: pytest-playwright提供的browser_type fixture
        flask_server: Flask服务器地址
    
    Returns:
        Page: 包含完整讨论结果的页面对象
    """
    from pages.home_page import HomePage
    import time
    
    test_issue = "如何提高UI测试的自动化覆盖率"  # 固定议题避免scope冲突
    
    print("\n🚀 [Class Fixture] 启动共享讨论会话...")
    
    # 使用browser_type创建browser、context和page
    browser = browser_type.launch(headless=False, slow_mo=50)
    context = playwright_browser.new_context()
    page = context.new_page()
    
    try:
        # 导航到首页
        page.goto(flask_server, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=10000)
        
        # 等待关键元素
        page.wait_for_selector('#issue-input', state='visible', timeout=10000)
        page.wait_for_selector('#start-btn', state='visible', timeout=5000)
        
        # 启动讨论
        home = HomePage(page)
        print(f"📝 [Class Fixture] 配置议题: {test_issue}")
        home.configure_and_start_discussion(
            issue=test_issue,
            backend="deepseek",
            rounds=1,
            planners=1,
            auditors=1
        )
        
        # 等待报告生成完成（完整流程）
        print("⏳ [Class Fixture] 等待讨论完成并生成报告（预计5-10分钟）...")
        page.wait_for_function(
            """() => {
                const reportIframe = document.getElementById('report-iframe');
                if (!reportIframe) return false;
                const iframeDoc = reportIframe.srcdoc;
                return iframeDoc && iframeDoc.length > 5000 && 
                       iframeDoc.includes('</html>') && 
                       iframeDoc.includes('<body');
            }""",
            timeout=600000  # 10分钟
        )
        print("✅ [Class Fixture] 讨论完成，报告已生成")
        
        # 返回页面对象供测试使用
        yield page
        
    finally:
        # 清理
        print("\n🧹 [Class Fixture] 清理共享会话...")
        try:
            import requests
            requests.post(f"{flask_server}/api/stop", timeout=3)
            time.sleep(2)
        except:
            pass
        
        page.close()
        context.close()
        browser.close()


@pytest.fixture
def stop_discussion_cleanup(flask_server: str):
    """
    提供讨论停止清理功能的fixture
    在测试结束后自动停止讨论并恢复UI状态
    
    Usage:
        def test_example(authenticated_page, stop_discussion_cleanup):
            # 测试代码...
            # 结束时自动调用清理
    """
    yield  # 测试执行
    
    # Teardown: 停止讨论
    import requests
    try:
        response = requests.post(f"{flask_server}/api/stop", timeout=3)
        if response.status_code == 200:
            print("🧹 清理：已停止讨论")
            time.sleep(2)  # 等待UI更新
    except Exception as e:
        print(f"⚠️ 清理失败: {e}")


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


@pytest.fixture(scope="class")
def test_issue_text():
    """
    提供测试用议题文本（class级别，可用于共享fixture）
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


# ==================== 测试报告生成 Hooks ====================

# 全局报告生成器实例
_report_generator = None


def pytest_configure(config):
    """Pytest配置钩子 - 初始化报告生成器"""
    global _report_generator
    _report_generator = TestReportGenerator()
    _report_generator.start_time = datetime.now()


def pytest_runtest_makereport(item, call):
    """
    测试执行后钩子 - 收集测试结果
    """
    global _report_generator
    
    if call.when == "call":  # 只在测试主体执行后收集
        outcome = "passed" if call.excinfo is None else "failed"
        
        # 收集测试信息
        result = {
            "name": item.nodeid,
            "status": outcome,
            "duration": call.duration,
            "markers": [m.name for m in item.iter_markers()]
        }
        
        # 如果测试失败，收集错误信息
        if call.excinfo:
            result["message"] = str(call.excinfo.value)
            result["traceback"] = str(call.excinfo.getrepr())
        
        # 收集截图和视频（如果存在）
        screenshots_dir = Path(__file__).parent / "screenshots"
        videos_dir = Path(__file__).parent / "videos"
        
        # 查找最新的截图（按修改时间）
        if screenshots_dir.exists():
            screenshots = list(screenshots_dir.glob("*.png"))
            if screenshots:
                latest_screenshot = max(screenshots, key=lambda p: p.stat().st_mtime)
                # 检查是否在测试执行期间创建
                if latest_screenshot.stat().st_mtime >= call.start:
                    result["screenshot"] = str(latest_screenshot)
        
        # 查找最新的视频
        if videos_dir.exists():
            videos = list(videos_dir.glob("*.webm"))
            if videos:
                latest_video = max(videos, key=lambda p: p.stat().st_mtime)
                if latest_video.stat().st_mtime >= call.start:
                    result["video"] = str(latest_video)
        
        if _report_generator:
            _report_generator.add_test_result(result)


def pytest_sessionfinish(session, exitstatus):
    """
    测试会话结束钩子 - 生成最终报告
    """
    global _report_generator
    
    if _report_generator:
        _report_generator.end_time = datetime.now()
        _report_generator.set_session_info(
            _report_generator.start_time,
            _report_generator.end_time
        )
        
        try:
            report_path = _report_generator.generate_html()
            print(f"\n" + "="*70)
            print(f"📊 测试报告: {report_path}")
            print(f"="*70)
        except Exception as e:
            print(f"\n❌ 生成测试报告失败: {e}")


# ==================== 优化测试 Fixtures ====================

@pytest.fixture(scope="class")
def class_shared_page(playwright_browser, flask_server: str):
    """
    提供class级别共享的page，用于优化测试（TestDiscussionOptimized使用）
    整个测试类只创建一次page，避免重复加载和关闭
    """
    context = playwright_browser.new_context()
    page = context.new_page()
    
    # 导航到Flask服务器
    page.goto(flask_server, wait_until="domcontentloaded")
    
    # 等待关键元素加载完成
    page.wait_for_selector('#issue-input', state='visible', timeout=10000)
    page.wait_for_selector('#start-btn', state='visible', timeout=5000)
    
    yield page
    
    # 测试类完成后清理
    try:
        import requests
        requests.post(f"{flask_server}/api/stop", timeout=2)
    except:
        pass
    
    page.close()
    context.close()


# ==================== 优化测试 Fixtures ====================

@pytest.fixture(scope="class")
def class_shared_page(playwright_browser, flask_server: str):
    """
    提供class级别共享的page，用于优化测试（TestDiscussionOptimized使用）
    整个测试类只创建一次page，避免重复加载和关闭
    """
    context = playwright_browser.new_context()
    page = context.new_page()
    
    # 导航到Flask服务器
    page.goto(flask_server, wait_until="domcontentloaded")
    
    # 等待关键元素加载完成
    page.wait_for_selector('#issue-input', state='visible', timeout=10000)
    page.wait_for_selector('#start-btn', state='visible', timeout=5000)
    
    yield page
    
    # 测试类完成后清理
    try:
        import requests
        requests.post(f"{flask_server}/api/stop", timeout=2)
    except:
        pass
    
    page.close()
    context.close()
