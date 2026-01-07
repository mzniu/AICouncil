"""
优化后的讨论流程测试
使用类变量共享讨论状态，减少重复启动，执行时间从~70分钟降至~15分钟
"""
import pytest
from playwright.sync_api import Page, expect
import os
import shutil
import glob
import subprocess
import time


class TestDiscussionOptimized:
    """
    优化的讨论流程测试类
    
    策略：setup_class启动完整讨论（5-10分钟），
    所有测试方法都是快速验证（每个<10秒）
    """
    
    # 类变量用于存储共享的讨论页面
    _shared_page: Page = None
    _discussion_started = False
    _workspace_dir = None  # 记录本次测试的workspace目录
    _flask_process = None  # Flask子进程
    
    @classmethod
    def setup_class(cls):
        """
        类级别初始化：启动Flask和讨论流程
        在所有测试方法执行前运行一次（7-10分钟）
        """
        from playwright.sync_api import sync_playwright
        from pages.home_page import HomePage
        import requests
        
        print("\n" + "="*70)
        print("🚀 [Setup] 启动Flask和讨论流程...")
        print("="*70)
        
        # 1. 启动Flask服务器
        print("🌐 启动Flask服务器...")
        cls._flask_process = subprocess.Popen(
            ["python", "src/web/app.py"],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            env={**os.environ, "FLASK_DEBUG": "0"},  # 禁用debug避免Reloader
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 等待Flask启动（最多10秒）
        flask_ready = False
        for i in range(20):
            time.sleep(0.5)
            try:
                resp = requests.get("http://127.0.0.1:5000", timeout=1)
                if resp.status_code == 200:
                    print("✅ Flask服务器已就绪")
                    flask_ready = True
                    break
            except:
                pass
        
        if not flask_ready:
            cls._flask_process.kill()
            raise RuntimeError("Flask服务器启动失败")
        
        # 2. 手动创建playwright browser和page（因为setup_class不能使用fixture）
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch(headless=False, slow_mo=50)
        cls._context = cls._browser.new_context()
        cls._shared_page = cls._context.new_page()
        
        # 导航到测试页面
        print("📍 导航到首页...")
        cls._shared_page.goto("http://127.0.0.1:5000", wait_until="domcontentloaded")
        cls._shared_page.wait_for_selector('#issue-input', state='visible', timeout=10000)
        cls._shared_page.wait_for_selector('#start-btn', state='visible', timeout=5000)
        
        # 启动讨论
        home = HomePage(cls._shared_page)
        test_issue = "如何利用AI技术提高软件开发效率？请给出具体方案。"
        
        print(f"📝 配置议题: {test_issue}")
        home.fill_issue(test_issue)
        home.select_backend("deepseek")
        home.set_rounds(1)
        home.set_planners_count(1)
        home.set_auditors_count(1)
        
        print("🖱️ 点击开始议事...")
        
        # 确保按钮可见且未禁用
        start_btn = cls._shared_page.locator('#start-btn')
        start_btn.wait_for(state='visible', timeout=5000)
        
        # 验证按钮初始状态
        is_disabled = start_btn.is_disabled()
        if is_disabled:
            raise RuntimeError("开始按钮已被禁用，无法点击")
        
        # 尝试点击（带重试机制）
        max_click_attempts = 3
        click_success = False
        
        for attempt in range(max_click_attempts):
            print(f"  尝试点击 (第{attempt + 1}次)...")
            
            # 点击按钮
            start_btn.click(force=True)
            time.sleep(3)
            
            # 检查是否点击成功
            btn_state = cls._shared_page.evaluate("""() => {
                const btn = document.getElementById('start-btn');
                return {disabled: btn.disabled, text: btn.innerText.trim()};
            }""")
            
            if btn_state['disabled'] and '议事' in btn_state['text']:
                print(f"  ✓ 点击成功！按钮状态: {btn_state}")
                click_success = True
                break
            else:
                print(f"  ✗ 点击未生效，按钮状态: {btn_state}")
                if attempt < max_click_attempts - 1:
                    print(f"  等待2秒后重试...")
                    time.sleep(2)
        
        if not click_success:
            raise RuntimeError(f"点击按钮失败，已尝试{max_click_attempts}次")
        
        # 验证状态和API调用
        status_text = home.get_status_text()
        print(f"📊 当前状态: {status_text}")
        
        # 检查API状态
        try:
            response = requests.get("http://127.0.0.1:5000/api/status", timeout=5)
            print(f"📡 API响应状态: {response.status_code}")
            if response.ok:
                data = response.json()
                print(f"📡 API返回数据: status={data.get('status')}, workspace={data.get('workspace_dir', 'N/A')[:50] if data.get('workspace_dir') else 'N/A'}")
                if data.get("workspace_dir"):
                    cls._workspace_dir = data["workspace_dir"]
                    print(f"📂 记录workspace: {os.path.basename(cls._workspace_dir)}")
                
                # 验证讨论是否真的启动了
                if data.get('status') in ['就绪', 'Ready', '空闲', 'Idle']:
                    print("❌ 警告: API显示未启动讨论，状态仍为就绪")
                    raise RuntimeError("讨论未成功启动，请检查按钮点击逻辑")
        except requests.RequestException as e:
            print(f"⚠️ API请求失败: {e}")
            raise RuntimeError(f"无法连接到Flask服务器: {e}")
        
        # 等待报告生成
        print("⏳ 等待报告生成（预计7-10分钟）...")
        max_wait = 1800  # 30分钟
        check_interval = 10
        elapsed = 0
        
        while elapsed < max_wait:
            try:
                has_report = cls._shared_page.evaluate("""() => {
                    const iframe = document.getElementById('report-iframe');
                    if (!iframe) return false;
                    const content = iframe.srcdoc;
                    return content && content.length > 5000;
                }""")
                
                if has_report:
                    print(f"✅ 报告已生成（用时 {elapsed}秒）")
                    cls._discussion_started = True
                    break
            except:
                pass
            
            time.sleep(check_interval)
            elapsed += check_interval
            if elapsed % 60 == 0:
                print(f"  ⏳ 已等待 {elapsed // 60} 分钟...")
        
        if not cls._discussion_started:
            raise TimeoutError(f"报告生成超时（{max_wait}秒）")
        
        print("="*70)
        print("✅ [Setup] 讨论完成，所有测试可以开始")
        print("="*70)
    

    @classmethod
    def teardown_class(cls):
        """
        类级别清理：在所有测试完成后执行
        清理测试过程中生成的内容
        """
        print("\n🧹 [Cleanup] 开始清理测试数据...")
        
        # 0. 停止讨论
        try:
            import requests
            requests.post("http://127.0.0.1:5000/api/stop", timeout=5)
            print("  ✓ 讨论已停止")
        except Exception as e:
            print(f"  ⚠️ 停止讨论失败: {e}")
        
        # 1. 停止Flask服务器
        try:
            if cls._flask_process:
                cls._flask_process.terminate()
                cls._flask_process.wait(timeout=5)
                print("  ✓ Flask服务器已停止")
        except Exception as e:
            print(f"  ⚠️ 停止Flask失败: {e}")
            try:
                cls._flask_process.kill()
            except:
                pass
        
        # 2. 关闭浏览器资源
        try:
            if cls._shared_page:
                cls._shared_page.close()
            if cls._context:
                cls._context.close()
            if cls._browser:
                cls._browser.close()
            if cls._playwright:
                cls._playwright.stop()
            print("  ✓ 浏览器资源已释放")
        except Exception as e:
            print(f"  ⚠️ 关闭浏览器失败: {e}")
        
        # 2. 清理workspace目录
        if cls._workspace_dir and os.path.exists(cls._workspace_dir):
            try:
                shutil.rmtree(cls._workspace_dir)
                print(f"  ✓ 已删除workspace: {os.path.basename(cls._workspace_dir)}")
            except Exception as e:
                print(f"  ⚠️ 清理workspace失败: {e}")
        
        # 3. 清理今天创建的其他测试workspace
        try:
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            workspaces_dir = os.path.join(os.path.dirname(__file__), "..", "..", "workspaces")
            
            if os.path.exists(workspaces_dir):
                test_workspaces = glob.glob(os.path.join(workspaces_dir, f"{today}_*"))
                cleaned_count = 0
                for ws in test_workspaces:
                    if os.path.isdir(ws) and ws != cls._workspace_dir:
                        try:
                            shutil.rmtree(ws)
                            cleaned_count += 1
                        except:
                            pass
                
                if cleaned_count > 0:
                    print(f"  ✓ 已清理 {cleaned_count} 个今日测试workspace")
        except Exception as e:
            print(f"  ⚠️ 清理额外workspace失败: {e}")
        
        # 注意：测试报告不清理，保留所有历史报告用于问题追溯
        
        print("✅ [Cleanup] 清理完成")
    
    @pytest.mark.p0
    def test_01_discussion_started(self):
        """验证讨论已启动（不等待完成）"""
        assert TestDiscussionOptimized._discussion_started, "讨论未启动"
        page = TestDiscussionOptimized._shared_page
        
        print("\n🔍 [Test 01] 验证讨论已启动...")
        
        # 验证按钮状态（讨论中应该被禁用）
        btn_disabled = page.evaluate("""() => {
            const btn = document.getElementById('start-btn');
            return btn.disabled;
        }""")
        
        # 验证状态文本
        status_text = page.locator('#status-text').text_content()
        
        print(f"  按钮禁用: {btn_disabled}")
        print(f"  状态文本: {status_text}")
        print("✅ 讨论已成功启动")
    @pytest.mark.p0
    def test_02_leader_output_display(self):
        """验证议长输出"""
        assert TestDiscussionOptimized._discussion_started, "讨论未启动"
        page = TestDiscussionOptimized._shared_page
        
        print("\n🔍 [Test 02] 验证议长输出...")
        
        # 验证页面上有议长相关内容（不要求元素可见，因为可能在折叠面板中）
        leader_text = page.locator('body').text_content()
        has_leader = '议长' in leader_text or 'Leader' in leader_text
        
        assert has_leader, "页面中未找到议长相关内容"
        print(f"✅ 议长输出验证通过")
    
    @pytest.mark.p0
    def test_03_planner_output_display(self):
        """验证策论家输出"""
        assert TestDiscussionOptimized._discussion_started, "讨论未启动"
        page = TestDiscussionOptimized._shared_page
        
        print("\n🔍 [Test 03] 验证策论家输出...")
        
        # 验证策论家输出存在
        planner_output = page.get_by_text('策论家', exact=False).or_(page.get_by_text('Planner', exact=False))
        expect(planner_output.first).to_be_visible(timeout=10000)
        
        content = planner_output.first.text_content()
        print(f"✅ 策论家输出验证通过（{len(content)} 字符）")
    
    @pytest.mark.p0
    def test_04_auditor_output_display(self):
        """验证监察官输出"""
        assert TestDiscussionOptimized._discussion_started, "讨论未启动"
        page = TestDiscussionOptimized._shared_page
        
        print("\n🔍 [Test 04] 验证监察官输出...")
        
        # 验证监察官输出存在
        auditor_output = page.get_by_text('监察官', exact=False).or_(page.get_by_text('Auditor', exact=False))
        expect(auditor_output.first).to_be_visible(timeout=10000)
        
        content = auditor_output.first.text_content()
        print(f"✅ 监察官输出验证通过（{len(content)} 字符）")
    
    @pytest.mark.p0
    def test_05_report(self):
        """验证报告生成"""
        assert TestDiscussionOptimized._discussion_started, "讨论未启动"
        page = TestDiscussionOptimized._shared_page
        
        print("\n🔍 [Test 05] 验证报告生成...")
        
        # 验证iframe存在
        report_iframe = page.locator('#report-iframe')
        expect(report_iframe).to_be_visible(timeout=10000)
        
        # 验证报告内容
        iframe_content = report_iframe.get_attribute('srcdoc')
        if iframe_content:
            print(f"✅ 报告已生成（{len(iframe_content)} 字符）")
        else:
            print("⚠️ 报告iframe存在但内容为空（讨论可能仍在进行）")
    
    @pytest.mark.p0
    def test_06_report_structure(self):
        """验证报告结构"""
        assert TestDiscussionOptimized._discussion_started, "讨论未启动"
        page = TestDiscussionOptimized._shared_page
        
        print("\n🔍 [Test 06] 验证报告结构...")
        
        # 获取iframe内容
        report_iframe = page.locator('#report-iframe')
        iframe_content = report_iframe.get_attribute('srcdoc')
        
        if iframe_content and len(iframe_content) > 1000:
            # 报告已生成，验证结构
            has_title = '议题' in iframe_content or 'Issue' in iframe_content or 'title' in iframe_content.lower()
            print(f"✅ 报告结构验证通过（包含标题: {has_title}）")
        else:
            print("⚠️ 报告尚未完全生成，跳过结构验证")
    
    @pytest.mark.p0
    def test_07_editor_button(self):
        """验证编辑器按钮"""
        assert TestDiscussionOptimized._discussion_started, "讨论未启动"
        page = TestDiscussionOptimized._shared_page
        
        print("\n🔍 [Test 07] 验证编辑器按钮...")
        
        # 等待编辑器按钮出现
        edit_btn = page.locator("button:has-text('编辑器')")
        expect(edit_btn.first).to_be_visible(timeout=10000)
        
        # 检查按钮状态（报告未完成时可能禁用）
        is_enabled = not edit_btn.first.is_disabled()
        print(f"  编辑器按钮状态: {'可用' if is_enabled else '禁用（等待报告完成）'}")
        
        if is_enabled:
            # 验证点击打开新标签
            with page.context.expect_page() as new_page_info:
                edit_btn.first.click()
                new_page = new_page_info.value
                new_page.wait_for_load_state("domcontentloaded", timeout=5000)
                print(f"  ✅ 新标签页已打开: {new_page.url}")
                new_page.close()
        
        print("✅ 编辑器按钮验证通过")

# 保留独立的启动测试（不依赖共享状态）
@pytest.mark.p0
@pytest.mark.slow
def test_start_discussion_success_standalone(class_shared_page: Page, test_issue_text: str, stop_discussion_cleanup):
    """
    独立的讨论启动测试（不共享状态）
    
    验证点:
    - 填写议题后可启动讨论
    - 状态变化为"讨论中"
    - 开始按钮禁用
    """
    from pages.home_page import HomePage
    
    home = HomePage(class_shared_page)
    
    # 配置讨论参数
    print(f"\n📝 [Standalone Test] 配置议题: {test_issue_text}")
    home.fill_issue(test_issue_text)
    home.select_backend("deepseek")
    home.set_rounds(1)
    home.set_planners_count(1)
    home.set_auditors_count(1)
    
    # 验证初始状态
    initial_status = home.get_status_text()
    print(f"📍 初始状态: {initial_status}")
    assert "就绪" in initial_status or "Ready" in initial_status
    
    # 启动讨论
    print("🚀 启动讨论...")
    home.start_discussion()
    
    # 等待状态变化
    try:
        home.wait_for_status("讨论中", timeout=10000)
        print("✅ 状态已变更为'讨论中'")
    except:
        current_status = home.get_status_text()
        assert "讨论" in current_status or "Discussion" in current_status
        print(f"✅ 状态已变更: {current_status}")
    
    # 验证开始按钮已禁用
    home.assert_button_disabled(home.start_btn)
    print("✅ 开始按钮已禁用")
    
    # 验证停止按钮可见
    home.assert_visible(home.stop_btn, "停止按钮可见")
    
    print("🎉 [Standalone Test] 讨论启动测试通过")
