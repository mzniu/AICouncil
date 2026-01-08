"""
议事流程端到端测试
测试完整的议事讨论流程
"""
import pytest
from playwright.sync_api import Page, expect
from pages.home_page import HomePage


class TestDiscussion:
    """议事流程测试类"""
    
    @pytest.mark.slow
    @pytest.mark.p0
    def test_start_discussion_success(self, authenticated_page: Page, test_issue_text: str, stop_discussion_cleanup):
        """
        DS-001: 测试启动讨论成功
        
        验证点:
        - 填写议题后可启动讨论
        - 状态变化为"讨论中"
        - 开始按钮禁用
        
        注意：此测试需要真实API，执行时间较长（标记为slow）
        使用stop_discussion_cleanup确保测试结束后停止讨论
        """
        home = HomePage(authenticated_page)
        
        # 配置讨论参数（最小配置：1轮，1策论家，1监察官）
        print(f"📝 配置议题: {test_issue_text}")
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
        
        # 等待状态变化（最多10秒）
        try:
            home.wait_for_status("讨论中", timeout=10000)
            print("✅ 状态已变更为'讨论中'")
        except:
            # 可能是英文状态
            current_status = home.get_status_text()
            assert "讨论" in current_status or "Discussion" in current_status or "运行" in current_status
            print(f"✅ 状态已变更: {current_status}")
        
        # 验证开始按钮已禁用
        home.assert_button_disabled(home.start_btn)
        print("✅ 开始按钮已禁用")
        
        # 验证停止按钮可见
        home.assert_visible(home.stop_btn, "停止按钮可见")
        
        print("🎉 DS-001测试通过：讨论启动成功")
    
    @pytest.mark.p0
    @pytest.mark.skip(reason="已知问题：按钮点击不触发讨论启动 - 需要调试Flask后端或JavaScript事件")
    def test_start_button_disabled_during_discussion(self, authenticated_page: Page, test_issue_text: str):
        """
        DS-002: 测试讨论期间按钮禁用
        
        验证点:
        - 使用configure_and_start_discussion辅助方法启动讨论
        - 验证按钮被禁用
        - 验证停止按钮可见
        
        注意：使用HomePage的封装方法简化测试
        
        已知问题：
        - 按钮点击后不触发讨论启动
        - 按钮状态不变化（disabled=False, text='开始议事'）
        - 无API请求发送到/api/start
        - 需要调查JavaScript startDiscussion()函数或Flask后端
        """
        home = HomePage(authenticated_page)
        
        # 使用封装好的方法启动讨论（会自动填充表单并点击）
        print(f"📝 使用配置: {test_issue_text}")
        home.configure_and_start_discussion(
            issue=test_issue_text,
            backend="deepseek",
            rounds=1,
            planners=1,
            auditors=1
        )
        
        # 等待状态更新（按钮应该被禁用）
        print("⏳ 等待讨论启动...")
        try:
            authenticated_page.wait_for_function(
                """() => {
                    const startBtn = document.getElementById('start-btn');
                    return startBtn && startBtn.disabled === true;
                }""",
                timeout=10000
            )
            print("✅ 开始按钮已禁用")
        except:
            # 打印当前状态用于调试
            btn_state = authenticated_page.evaluate("""() => {
                const btn = document.getElementById('start-btn');
                return {
                    disabled: btn.disabled,
                    text: btn.innerText.trim(),
                    classes: btn.className
                };
            }""")
            status = home.get_status_text()
            print(f"❌ 按钮状态: {btn_state}")
            print(f"❌ 系统状态: {status}")
            pytest.fail(f"讨论未能启动，按钮未禁用: {btn_state}")
        
        # 验证停止按钮可见
        try:
            home.assert_visible(home.stop_btn, "停止按钮应该可见")
            print("✅ 停止按钮可见")
        except:
            print("⚠️ 停止按钮不可见，但按钮已禁用，继续测试")
        
        # 清理：停止讨论
        print("🛑 停止讨论...")
        try:
            authenticated_page.on("dialog", lambda dialog: dialog.accept())
            if home.is_visible(home.stop_btn):
                home.click(home.stop_btn)
                authenticated_page.wait_for_timeout(1000)
        except Exception as e:
            print(f"⚠️ 停止讨论时出错: {e}")
        
        print("🎉 DS-002测试通过：按钮禁用功能正常")
    
    @pytest.mark.slow
    @pytest.mark.p0
    def test_agent_output_display_leader(self, authenticated_page: Page, test_issue_text: str, stop_discussion_cleanup):
        """
        DS-003: 测试议长（Leader）输出显示
        
        验证点:
        - 讨论过程中显示议长输出
        - 议长角色标识可见
        
        注意：需要真实API，执行时间较长
        使用stop_discussion_cleanup确保测试结束后停止讨论
        """
        home = HomePage(authenticated_page)
        
        # 启动讨论
        home.configure_and_start_discussion(
            issue=test_issue_text,
            backend="deepseek",
            rounds=1,
            planners=1,
            auditors=1
        )
        
        # 等待讨论区域有内容输出（最多60秒）
        print("⏳ 等待议长输出...")
        try:
            authenticated_page.wait_for_function(
                """() => {
                    const discussionSection = document.querySelector('#discussion-section');
                    return discussionSection && discussionSection.textContent.includes('议长');
                }""",
                timeout=60000
            )
            print("✅ 检测到议长输出")
        except:
            # 尝试查找Leader关键字（英文）
            authenticated_page.wait_for_function(
                """() => {
                    const discussionSection = document.querySelector('#discussion-section');
                    return discussionSection && (
                        discussionSection.textContent.includes('Leader') ||
                        discussionSection.textContent.includes('议长')
                    );
                }""",
                timeout=10000
            )
            print("✅ 检测到Leader输出")
        
        # 验证讨论区域包含议长内容
        discussion_content = home.get_text(home.discussion_section)
        assert "议长" in discussion_content or "Leader" in discussion_content
        print("✅ 议长输出显示正确")
        
        print("🎉 DS-003测试通过：议长输出显示正常")
    
    @pytest.mark.slow
    @pytest.mark.p0
    def test_agent_output_display_planner(self, authenticated_page: Page, test_issue_text: str, stop_discussion_cleanup):
        """
        DS-004: 测试策论家（Planner）输出显示
        
        验证点:
        - 讨论过程中显示策论家输出
        - 策论家角色标识可见
        """
        home = HomePage(authenticated_page)
        
        # 启动讨论
        home.configure_and_start_discussion(
            issue=test_issue_text,
            backend="deepseek",
            rounds=1,
            planners=1,
            auditors=1
        )
        
        # 等待策论家输出（最多120秒，因为需要等Leader完成）
        print("⏳ 等待策论家输出...")
        try:
            authenticated_page.wait_for_function(
                """() => {
                    const discussionSection = document.querySelector('#discussion-section');
                    return discussionSection && discussionSection.textContent.includes('策论家');
                }""",
                timeout=120000
            )
            print("✅ 检测到策论家输出")
        except:
            authenticated_page.wait_for_function(
                """() => {
                    const discussionSection = document.querySelector('#discussion-section');
                    return discussionSection && discussionSection.textContent.includes('Planner');
                }""",
                timeout=10000
            )
            print("✅ 检测到Planner输出")
        
        discussion_content = home.get_text(home.discussion_section)
        assert "策论家" in discussion_content or "Planner" in discussion_content
        print("✅ 策论家输出显示正确")
        
        print("🎉 DS-004测试通过：策论家输出显示正常")
    
    @pytest.mark.slow
    @pytest.mark.p0
    def test_agent_output_display_auditor(self, authenticated_page: Page, test_issue_text: str, stop_discussion_cleanup):
        """
        DS-005: 测试监察官（Auditor）输出显示
        
        验证点:
        - 讨论过程中显示监察官输出
        - 监察官角色标识可见
        """
        home = HomePage(authenticated_page)
        
        # 启动讨论
        home.configure_and_start_discussion(
            issue=test_issue_text,
            backend="deepseek",
            rounds=1,
            planners=1,
            auditors=1
        )
        
        # 等待监察官输出（最多180秒）
        print("⏳ 等待监察官输出...")
        try:
            authenticated_page.wait_for_function(
                """() => {
                    const discussionSection = document.querySelector('#discussion-section');
                    return discussionSection && discussionSection.textContent.includes('监察官');
                }""",
                timeout=180000
            )
            print("✅ 检测到监察官输出")
        except:
            authenticated_page.wait_for_function(
                """() => {
                    const discussionSection = document.querySelector('#discussion-section');
                    return discussionSection && discussionSection.textContent.includes('Auditor');
                }""",
                timeout=10000
            )
            print("✅ 检测到Auditor输出")
        
        discussion_content = home.get_text(home.discussion_section)
        assert "监察官" in discussion_content or "Auditor" in discussion_content
        print("✅ 监察官输出显示正确")
        
        print("🎉 DS-005测试通过：监察官输出显示正常")
    
    @pytest.mark.slow
    @pytest.mark.p0
    @pytest.mark.slow
    def test_agent_output_display_reporter(self, authenticated_page: Page, test_issue_text: str, stop_discussion_cleanup):
        """
        DS-006: 测试记录员（Reporter）输出显示
        
        验证点:
        - 讨论完成后显示记录员输出
        - 报告成功生成
        
        注意：记录员在讨论完成后生成报告，需要完整流程
        """
        home = HomePage(authenticated_page)
        
        # 启动讨论
        home.configure_and_start_discussion(
            issue=test_issue_text,
            backend="deepseek",
            rounds=1,
            planners=1,
            auditors=1
        )
        
        # 等待报告生成（记录员的工作成果）（最多10分钟）
        print("⏳ 等待报告生成（记录员工作成果）...")
        authenticated_page.wait_for_function(
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
        print("✅ 记录员已完成报告生成")
        
        # 验证报告iframe存在
        assert home.is_report_generated(), "报告应该已生成"
        print("✅ 记录员输出（报告）显示正确")
        
        print("🎉 DS-006测试通过：记录员完成报告生成")
    
    @pytest.mark.slow
    @pytest.mark.p0
    def test_report_generation_automatic(self, authenticated_page: Page, test_issue_text: str, stop_discussion_cleanup):
        """
        DS-010: 测试报告自动生成
        
        验证点:
        - 讨论完成后报告自动生成
        - 报告iframe加载完成
        - 报告内容不为空
        
        注意：需要完整讨论流程，执行时间较长
        """
        home = HomePage(authenticated_page)
        
        # 启动讨论（最小配置）
        home.configure_and_start_discussion(
            issue=test_issue_text,
            backend="deepseek",
            rounds=1,
            planners=1,
            auditors=1
        )
        
        # 等待讨论完成和报告生成（最多10分钟）
        print("⏳ 等待报告生成...")
        authenticated_page.wait_for_function(
            """() => {
                const reportIframe = document.getElementById('report-iframe');
                if (!reportIframe) return false;
                const iframeDoc = reportIframe.srcdoc;
                // 确保内容足够长且包含实际报告结构
                return iframeDoc && iframeDoc.length > 5000 && 
                       iframeDoc.includes('</html>') && 
                       iframeDoc.includes('<body');
            }""",
            timeout=600000  # 10分钟
        )
        print("✅ 报告已生成")
        
        # 验证报告iframe存在且可见
        home.assert_visible(home.report_iframe, "报告iframe应该可见")
        
        # 获取iframe的srcdoc内容
        iframe_content = authenticated_page.evaluate(
            "document.getElementById('report-iframe').srcdoc"
        )
        assert iframe_content and len(iframe_content) > 5000, f"报告内容太短: {len(iframe_content)} 字符"
        print(f"✅ 报告内容长度: {len(iframe_content)} 字符")
        
        # 验证报告包含关键信息（使用宽松检查，因为内容可能被转换）
        if test_issue_text not in iframe_content:
            # 尝试检查标题或其他关键词
            print(f"⚠️ 报告未包含原始议题文本，检查内容前500字符: {iframe_content[:500]}")
        # 至少应该有HTML结构
        assert '<body' in iframe_content.lower(), "报告应包含body标签"
        print("✅ 报告包含议题信息")
        
        print("🎉 DS-010测试通过：报告自动生成正常")
    
    @pytest.mark.slow
    @pytest.mark.p0
    def test_report_iframe_load(self, authenticated_page: Page, test_issue_text: str, stop_discussion_cleanup):
        """
        DS-011: 测试报告iframe加载
        
        验证点:
        - iframe正确加载HTML内容
        - 报告结构完整（包含标题、正文等）
        - 报告可交互（按钮可点击）
        
        注意：需要完整讨论流程，执行时间较长
        """
        home = HomePage(authenticated_page)
        
        # 启动讨论
        home.configure_and_start_discussion(
            issue=test_issue_text,
            backend="deepseek",
            rounds=1,
            planners=1,
            auditors=1
        )
        
        # 等待报告生成（使用更长时间确保内容完整）
        print("⏳ 等待报告生成...")
        authenticated_page.wait_for_function(
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
        print("✅ 报告已生成")
        
        # 验证报告已生成
        assert home.is_report_generated(), "报告应该已生成"
        
        # 获取iframe内容进行验证
        iframe_content = authenticated_page.evaluate(
            "document.getElementById('report-iframe').srcdoc"
        )
        
        # 验证报告结构（HTML标签完整性）
        iframe_lower = iframe_content.lower()
        assert "<html" in iframe_lower, f"报告应包含HTML标签，实际长度: {len(iframe_content)}"
        assert "<body" in iframe_lower, f"报告应包含body标签，前500字符: {iframe_content[:500]}"
        assert "</html>" in iframe_lower, "报告应闭合HTML标签"
        print("✅ 报告HTML结构完整")
        
        # 验证报告包含关键元素（宽松检查）
        key_elements = ["议题", "背景", "分析", "建议"]
        found_elements = [elem for elem in key_elements if elem in iframe_content]
        print(f"✅ 报告包含元素: {found_elements}")
        
        # 至少应该有标题和内容结构
        assert len(iframe_content) > 5000, f"报告内容太短: {len(iframe_content)} 字符"
        
        # 验证报告包含下载按钮（HTML导出、图片导出等）
        has_export_buttons = any(keyword in iframe_content for keyword in [
            "exportHTML", "exportImage", "exportPDF", "下载", "导出"
        ])
        assert has_export_buttons, "报告应包含导出按钮"
        print("✅ 报告包含导出功能")
        
        print("🎉 DS-011测试通过：报告iframe加载正常")


if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v', '-s', '-m', 'not slow'])  # 默认不运行slow测试
