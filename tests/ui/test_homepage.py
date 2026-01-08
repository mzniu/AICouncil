"""
主页面功能测试
测试AICouncil主页的基础功能
"""
import pytest
from playwright.sync_api import Page, expect
from pages.home_page import HomePage


class TestHomePage:
    """主页面测试类"""
    
    @pytest.mark.smoke
    @pytest.mark.p0
    def test_page_loads_successfully(self, authenticated_page: Page):
        """
        HP-001: 测试页面加载成功
        
        验证点:
        - 页面标题正确
        - 核心元素可见（输入框、按钮、下拉菜单）
        """
        home = HomePage(authenticated_page)
        
        # 验证页面标题（标题可能包含"AI Council"或"实时讨论视图"）
        title = authenticated_page.title()
        assert "AI Council" in title or "AICouncil" in title, f"页面标题不正确: {title}"
        print(f"✅ 页面标题验证通过: {title}")
        
        # 验证议题输入框可见
        home.assert_visible(home.issue_input, "议题输入框可见")
        
        # 验证开始按钮可见且可用
        home.assert_visible(home.start_btn, "开始按钮可见")
        home.assert_button_enabled(home.start_btn)
        
        # 验证模型后端选择器可见
        home.assert_visible(home.backend_select, "模型后端选择器可见")
        
        # 验证轮数、策论家、监察官输入框可见
        home.assert_visible(home.rounds_input, "讨论轮数输入框可见")
        home.assert_visible(home.planners_input, "策论家数量输入框可见")
        home.assert_visible(home.auditors_input, "监察官数量输入框可见")
        
        # 验证状态指示器可见
        home.assert_visible(home.status_indicator, "状态指示器可见")
        status_text = home.get_status_text()
        # 接受多种状态（可能是就绪/Ready，也可能刚停止后还显示其他状态）
        # 只要不是Error/错误状态即可
        assert not any(error in status_text for error in ["错误", "Error", "失败", "Failed"]), \
            f"状态不应显示错误: {status_text}"
        print(f"✅ 状态文本: {status_text}")
        
        print("🎉 HP-001测试通过：页面加载成功，所有核心元素正常显示")
    
    @pytest.mark.p0
    def test_backend_selection(self, authenticated_page: Page):
        """
        HP-004: 测试模型后端选择功能
        
        验证点:
        - 后端下拉菜单可选择不同选项
        - 选择后值正确保存
        - 常见后端选项存在（deepseek/openai/ollama等）
        """
        home = HomePage(authenticated_page)
        
        # 验证后端选择器可见
        home.assert_visible(home.backend_select, "模型后端选择器可见")
        
        # 获取初始选中的后端
        initial_backend = home.get_selected_backend()
        print(f"📝 初始后端: {initial_backend}")
        
        # 测试选择deepseek
        home.select_backend("deepseek")
        selected = home.get_selected_backend()
        assert selected == "deepseek", f"选择deepseek失败，当前值: {selected}"
        print("✅ deepseek后端选择成功")
        
        # 测试选择openai
        home.select_backend("openai")
        selected = home.get_selected_backend()
        assert selected == "openai", f"选择openseek失败，当前值: {selected}"
        print("✅ openai后端选择成功")
        
        # 验证选择器仍然可用
        home.assert_enabled(home.backend_select, "后端选择器保持可用")
        
        print("🎉 HP-004测试通过：模型后端选择功能正常")
    
    @pytest.mark.p0
    def test_start_button_state_during_discussion(self, authenticated_page: Page, test_issue_text: str, stop_discussion_cleanup):
        """
        HP-005 (原DS-002): 测试讨论启动后按钮状态
        
        验证点:
        - 使用configure_and_start_discussion启动讨论
        - 验证按钮被禁用
        
        注意：使用stop_discussion_cleanup确保测试结束后停止讨论
        """
        home = HomePage(authenticated_page)
        
        print(f"📝 配置讨论: {test_issue_text}")
        
        # 使用封装方法启动讨论
        home.configure_and_start_discussion(
            issue=test_issue_text,
            backend="deepseek",
            rounds=1,
            planners=1,
            auditors=1
        )
        
        # 等待讨论启动（按钮应被禁用）
        print("⏳ 等待讨论启动...")
        try:
            authenticated_page.wait_for_function(
                """() => {
                    const btn = document.getElementById('start-btn');
                    return btn && btn.disabled === true;
                }""",
                timeout=10000
            )
            print("✅ 开始按钮已禁用")
        except:
            btn_state = authenticated_page.evaluate("""() => {
                const btn = document.getElementById('start-btn');
                return {disabled: btn.disabled, text: btn.innerText.trim()};
            }""")
            pytest.fail(f"按钮应被禁用，实际状态: {btn_state}")
        
        # 清理：停止讨论
        try:
            authenticated_page.on("dialog", lambda dialog: dialog.accept())
            if home.is_visible(home.stop_btn):
                home.click(home.stop_btn)
        except:
            pass
        
        print("🎉 HP-005测试通过：按钮状态正确")


if __name__ == '__main__':
    # 运行单个测试
    pytest.main([__file__, '-v', '-s'])
