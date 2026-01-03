"""
报告编辑器页面对象
处理报告编辑器的所有交互操作
"""
from playwright.sync_api import Page
from .base_page import BasePage


class EditorPage(BasePage):
    """报告编辑器页面对象类"""
    
    def __init__(self, page: Page):
        """
        初始化编辑器页面对象
        
        Args:
            page: Playwright页面实例
        """
        super().__init__(page)
        
        # ==================== 选择器定义 ====================
        
        # 编辑器容器和按钮
        self.editor_container = "#editor-container"
        self.editor_modal = "#editor-modal"
        self.editor_overlay = ".editor-overlay"
        self.edit_button = "button:has-text('编辑报告')"
        self.close_editor_btn = "#close-editor-btn"
        self.save_editor_btn = "#save-editor-btn"
        
        # 编辑器工具栏
        self.editor_toolbar = ".editor-toolbar"
        self.undo_btn = "button[title*='撤销'], button[title*='Undo']"
        self.redo_btn = "button[title*='重做'], button[title*='Redo']"
        self.bold_btn = "button[title*='粗体'], button[title*='Bold']"
        self.italic_btn = "button[title*='斜体'], button[title*='Italic']"
        self.version_btn = "button:has-text('版本历史'), button:has-text('Version History')"
        
        # 编辑区域
        self.editor_title_input = "#editor-title"
        self.editor_content_area = "#editor-content"
        self.editor_preview = "#editor-preview"
        
        # 版本历史
        self.version_list = "#version-list"
        self.version_item = ".version-item"
        self.restore_version_btn = "button:has-text('恢复此版本'), button:has-text('Restore')"
        
        # 状态提示
        self.save_status = "#save-status"
        self.save_success_msg = ".save-success"
        self.save_error_msg = ".save-error"
    
    # ==================== 编辑器打开/关闭操作 ====================
    
    def open_editor(self):
        """
        打开报告编辑器
        """
        self.click(self.edit_button)
        self.wait_for_element(self.editor_modal, state='visible', timeout=5000)
        print("✅ 编辑器已打开")
    
    def close_editor(self):
        """
        关闭报告编辑器
        """
        self.click(self.close_editor_btn)
        self.wait_for_element(self.editor_modal, state='hidden', timeout=5000)
        print("✅ 编辑器已关闭")
    
    def is_editor_open(self) -> bool:
        """
        检查编辑器是否打开
        
        Returns:
            bool: 编辑器是否可见
        """
        return self.is_visible(self.editor_modal)
    
    # ==================== 内容编辑操作 ====================
    
    def get_title(self) -> str:
        """
        获取编辑器中的标题
        
        Returns:
            str: 当前标题文本
        """
        return self.get_value(self.editor_title_input)
    
    def set_title(self, title: str):
        """
        设置报告标题
        
        Args:
            title: 新标题文本
        """
        self.clear_input(self.editor_title_input)
        self.fill_input(self.editor_title_input, title)
        print(f"✅ 标题已设置: {title}")
    
    def get_content(self) -> str:
        """
        获取编辑器中的内容
        
        Returns:
            str: 当前内容文本
        """
        return self.get_text(self.editor_content_area)
    
    def set_content(self, content: str):
        """
        设置报告内容
        
        Args:
            content: 新内容文本
        """
        # 清空内容区域
        self.page.evaluate(f"""() => {{
            const editor = document.querySelector('{self.editor_content_area}');
            if (editor) editor.textContent = '';
        }}""")
        
        # 填充新内容
        self.fill_input(self.editor_content_area, content)
        print(f"✅ 内容已设置 ({len(content)} 字符)")
    
    def append_content(self, content: str):
        """
        在当前内容末尾追加文本
        
        Args:
            content: 要追加的文本
        """
        current = self.get_content()
        self.set_content(current + content)
    
    # ==================== 工具栏操作 ====================
    
    def click_bold(self):
        """点击粗体按钮"""
        self.click(self.bold_btn)
        print("✅ 已点击粗体按钮")
    
    def click_italic(self):
        """点击斜体按钮"""
        self.click(self.italic_btn)
        print("✅ 已点击斜体按钮")
    
    def click_undo(self):
        """点击撤销按钮"""
        self.click(self.undo_btn)
        print("✅ 已点击撤销按钮")
    
    def click_redo(self):
        """点击重做按钮"""
        self.click(self.redo_btn)
        print("✅ 已点击重做按钮")
    
    def is_undo_enabled(self) -> bool:
        """
        检查撤销按钮是否可用
        
        Returns:
            bool: 撤销按钮是否可点击
        """
        return self.is_enabled(self.undo_btn)
    
    def is_redo_enabled(self) -> bool:
        """
        检查重做按钮是否可用
        
        Returns:
            bool: 重做按钮是否可点击
        """
        return self.is_enabled(self.redo_btn)
    
    # ==================== 保存操作 ====================
    
    def save_changes(self):
        """
        保存编辑的修改
        """
        self.click(self.save_editor_btn)
        print("✅ 已点击保存按钮")
    
    def wait_for_save_success(self, timeout: int = 10000):
        """
        等待保存成功提示
        
        Args:
            timeout: 超时时间（毫秒）
        """
        self.wait_for_element(self.save_success_msg, state='visible', timeout=timeout)
        print("✅ 保存成功")
    
    def get_save_status(self) -> str:
        """
        获取保存状态文本
        
        Returns:
            str: 状态文本
        """
        return self.get_text(self.save_status)
    
    # ==================== 版本历史操作 ====================
    
    def open_version_history(self):
        """
        打开版本历史面板
        """
        self.click(self.version_btn)
        self.wait_for_element(self.version_list, state='visible', timeout=5000)
        print("✅ 版本历史已打开")
    
    def get_version_count(self) -> int:
        """
        获取版本历史中的版本数量
        
        Returns:
            int: 版本数量
        """
        count = self.page.locator(self.version_item).count()
        print(f"📝 版本数量: {count}")
        return count
    
    def select_version(self, index: int = 0):
        """
        选择指定版本
        
        Args:
            index: 版本索引（0为最新）
        """
        versions = self.page.locator(self.version_item)
        if index < versions.count():
            versions.nth(index).click()
            print(f"✅ 已选择版本 {index}")
        else:
            raise ValueError(f"版本索引 {index} 超出范围")
    
    def restore_version(self):
        """
        恢复选中的版本
        """
        self.click(self.restore_version_btn)
        print("✅ 版本已恢复")
    
    # ==================== 预览操作 ====================
    
    def get_preview_content(self) -> str:
        """
        获取预览区域的HTML内容
        
        Returns:
            str: 预览HTML
        """
        return self.page.evaluate(f"""() => {{
            const preview = document.querySelector('{self.editor_preview}');
            return preview ? preview.innerHTML : '';
        }}""")
    
    def is_preview_visible(self) -> bool:
        """
        检查预览区域是否可见
        
        Returns:
            bool: 预览是否可见
        """
        return self.is_visible(self.editor_preview)
    
    # ==================== 验证方法 ====================
    
    def assert_editor_open(self):
        """断言编辑器已打开"""
        self.assert_visible(self.editor_modal, "编辑器应该打开")
    
    def assert_editor_closed(self):
        """断言编辑器已关闭"""
        assert not self.is_visible(self.editor_modal), "编辑器应该关闭"
    
    def assert_title_equals(self, expected_title: str):
        """
        断言标题等于预期值
        
        Args:
            expected_title: 预期标题
        """
        actual_title = self.get_title()
        assert actual_title == expected_title, f"标题不匹配: 期望'{expected_title}'，实际'{actual_title}'"
        print(f"✅ 标题验证通过: {actual_title}")
    
    def assert_content_contains(self, expected_text: str):
        """
        断言内容包含指定文本
        
        Args:
            expected_text: 预期包含的文本
        """
        content = self.get_content()
        assert expected_text in content, f"内容未包含'{expected_text}'"
        print(f"✅ 内容包含验证通过: {expected_text}")
    
    def assert_save_successful(self):
        """断言保存成功"""
        self.assert_visible(self.save_success_msg, "应显示保存成功提示")
