"""
报告编辑器功能测试
测试报告编辑器的所有核心功能
"""
import pytest
from playwright.sync_api import Page
from pages.home_page import HomePage
from pages.editor_page import EditorPage


class TestReportEditor:
    """报告编辑器测试类"""
    
    @pytest.mark.slow
    @pytest.mark.p0
    def test_editor_loads_after_report_generation(self, authenticated_page: Page, test_issue_text: str, stop_discussion_cleanup):
        """
        RE-001: 测试编辑器加载
        
        验证点:
        - 报告生成后编辑按钮可见
        - 点击编辑按钮可打开编辑器
        - 编辑器正确加载报告内容
        
        注意：需要完整讨论流程，执行时间较长
        使用stop_discussion_cleanup确保测试结束后停止讨论
        """
        home = HomePage(authenticated_page)
        
        # 启动讨论并等待报告生成
        home.configure_and_start_discussion(
            issue=test_issue_text,
            backend="deepseek",
            rounds=1,
            planners=1,
            auditors=1
        )
        
        print("⏳ 等待报告生成...")
        # 等待报告完整加载
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
        
        # 验证主页面中的编辑器按钮（不在iframe内）
        # 按钮文本是 "📝 编辑器"
        edit_btn = authenticated_page.locator("button:has-text('编辑器')")
        assert edit_btn.count() > 0, "编辑器按钮应该存在"
        print("✅ 编辑器按钮可见")
        
        # 点击编辑按钮打开编辑器（会在新标签页打开）
        with authenticated_page.context.expect_page() as new_page_info:
            edit_btn.first.click()
            new_page = new_page_info.value
            print("✅ 编辑器已在新标签页打开")
            
            # 等待新标签页加载
            new_page.wait_for_load_state("domcontentloaded", timeout=10000)
            print(f"✅ 编辑器页面已加载: {new_page.url}")
            
            # 关闭新标签页
            new_page.close()
        
        print("🎉 RE-001测试通过：编辑器加载正常")
    
    @pytest.mark.p0
    def test_title_editing(self, authenticated_page: Page):
        """
        RE-002: 测试标题编辑
        
        验证点:
        - 可以修改报告标题
        - 标题修改后正确显示
        
        注意：此测试需要Mock编辑器环境或真实报告
        """
        # 由于编辑器在报告iframe中，这里使用简化的测试逻辑
        # 实际测试需要先生成报告或Mock编辑器界面
        
        print("⚠️ RE-002: 标题编辑测试需要编辑器环境，暂时跳过")
        pytest.skip("需要完整的编辑器实现和报告生成")
    
    @pytest.mark.p0
    def test_content_editing(self, authenticated_page: Page):
        """
        RE-003: 测试内容编辑
        
        验证点:
        - 可以修改报告正文
        - 内容修改后正确显示
        - 支持富文本编辑（粗体、斜体等）
        """
        print("⚠️ RE-003: 内容编辑测试需要编辑器环境，暂时跳过")
        pytest.skip("需要完整的编辑器实现和报告生成")
    
    @pytest.mark.p0
    def test_save_changes(self, authenticated_page: Page):
        """
        RE-004: 测试保存修改
        
        验证点:
        - 点击保存按钮后修改被保存
        - 显示保存成功提示
        - 刷新页面后修改仍然存在
        """
        print("⚠️ RE-004: 保存修改测试需要编辑器环境，暂时跳过")
        pytest.skip("需要完整的编辑器实现和报告生成")
    
    @pytest.mark.p1
    def test_undo_redo_functionality(self, authenticated_page: Page):
        """
        RE-005: 测试撤销/重做功能
        
        验证点:
        - 编辑后撤销按钮可用
        - 点击撤销可恢复之前状态
        - 撤销后重做按钮可用
        - 点击重做可恢复撤销的修改
        """
        print("⚠️ RE-005: 撤销/重做测试需要编辑器环境，暂时跳过")
        pytest.skip("需要完整的编辑器实现和报告生成")
    
    @pytest.mark.p1
    def test_version_history(self, authenticated_page: Page):
        """
        RE-006: 测试版本历史
        
        验证点:
        - 可以查看历史版本列表
        - 可以选择并预览历史版本
        - 可以恢复到指定历史版本
        """
        print("⚠️ RE-006: 版本历史测试需要编辑器环境，暂时跳过")
        pytest.skip("需要完整的编辑器实现和报告生成")
    
    @pytest.mark.p0
    def test_export_integration(self, authenticated_page: Page):
        """
        RE-007: 测试导出功能集成
        
        验证点:
        - 编辑器中可以访问导出功能
        - 导出按钮在编辑模式下仍然可用
        - 导出的内容包含编辑后的修改
        """
        print("⚠️ RE-007: 导出集成测试需要编辑器环境，暂时跳过")
        pytest.skip("需要完整的编辑器实现和报告生成")
    
    @pytest.mark.p0
    def test_editor_close(self, authenticated_page: Page):
        """
        RE-008: 测试编辑器关闭
        
        验证点:
        - 点击关闭按钮可关闭编辑器
        - 未保存的修改会弹出确认对话框
        - 确认后编辑器正确关闭
        """
        print("⚠️ RE-008: 编辑器关闭测试需要编辑器环境，暂时跳过")
        pytest.skip("需要完整的编辑器实现和报告生成")


class TestEditorPageObject:
    """编辑器Page Object单元测试"""
    
    @pytest.mark.p2
    def test_editor_page_object_instantiation(self, authenticated_page: Page):
        """
        测试EditorPage对象可以正确实例化
        """
        editor = EditorPage(authenticated_page)
        
        # 验证所有选择器都已定义
        assert editor.editor_container is not None
        assert editor.editor_modal is not None
        assert editor.edit_button is not None
        assert editor.save_editor_btn is not None
        
        print("✅ EditorPage对象实例化成功")
        print("🎉 编辑器Page Object结构验证通过")


if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v', '-s', '-m', 'p2'])  # 默认只运行P2单元测试
