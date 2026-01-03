"""
主页面Page Object
封装AICouncil主页面的元素和操作
"""
from playwright.sync_api import Page
from .base_page import BasePage


class HomePage(BasePage):
    """
    主页面对象类
    
    封装主页面的所有元素选择器和操作方法
    """
    
    def __init__(self, page: Page, base_url: str = "http://127.0.0.1:5000"):
        super().__init__(page, base_url)
        
        # ==================== 选择器定义 ====================
        
        # 输入框和控制按钮
        self.issue_input = '#issue-input'
        self.backend_select = '#backend-select'
        self.global_model_input = '#global-model-input'
        self.rounds_input = '#rounds-input'
        self.planners_input = '#planners-input'
        self.auditors_input = '#auditors-input'
        self.start_btn = '#start-btn'
        self.stop_btn = '#stop-btn'
        self.advanced_toggle_btn = '#advanced-toggle-btn'
        
        # 状态指示器
        self.status_indicator = '#status-indicator'
        self.status_dot = '#status-dot'
        self.status_text = '#status-text'
        
        # 语言切换
        self.lang_zh_btn = '#lang-zh'
        self.lang_en_btn = '#lang-en'
        
        # 预设和历史
        self.presets_dropdown_btn = '#presets-dropdown-btn'
        self.presets_dropdown = '#presets-dropdown'
        self.history_btn = '#history-btn'
        
        # 讨论和报告区域
        self.discussion_section = '#discussion-section'
        self.report_section = '#report-section'
        self.report_iframe = '#report-iframe'
    
    # ==================== 导航方法 ====================
    
    def goto_home(self):
        """导航到主页"""
        self.goto("/")
        self.wait_for_load_state("networkidle")
    
    # ==================== 议题输入方法 ====================
    
    def fill_issue(self, issue_text: str):
        """
        填写议题
        
        Args:
            issue_text: 议题文本
        """
        self.fill_input(self.issue_input, issue_text)
    
    def get_issue_text(self) -> str:
        """
        获取议题输入框的文本
        
        Returns:
            str: 议题文本
        """
        return self.get_value(self.issue_input)
    
    # ==================== 配置选项方法 ====================
    
    def select_backend(self, backend: str):
        """
        选择模型后端
        
        Args:
            backend: 后端名称 (deepseek/openai/ollama等)
        """
        self.select_option(self.backend_select, backend)
    
    def get_selected_backend(self) -> str:
        """
        获取当前选中的后端
        
        Returns:
            str: 后端名称
        """
        return self.get_value(self.backend_select)
    
    def set_rounds(self, rounds: int):
        """
        设置讨论轮数
        
        Args:
            rounds: 轮数（1-10）
        """
        self.fill_input(self.rounds_input, str(rounds))
    
    def set_planners_count(self, count: int):
        """
        设置策论家数量
        
        Args:
            count: 数量（1-5）
        """
        self.fill_input(self.planners_input, str(count))
    
    def set_auditors_count(self, count: int):
        """
        设置监察官数量
        
        Args:
            count: 数量（1-5）
        """
        self.fill_input(self.auditors_input, str(count))
    
    def set_global_model(self, model_name: str):
        """
        设置全局模型
        
        Args:
            model_name: 模型名称
        """
        self.fill_input(self.global_model_input, model_name)
    
    # ==================== 控制按钮方法 ====================
    
    def start_discussion(self):
        """点击开始讨论按钮"""
        self.click(self.start_btn)
    
    def stop_discussion(self):
        """点击停止讨论按钮"""
        self.click(self.stop_btn)
    
    def toggle_advanced_settings(self):
        """切换高级设置显示/隐藏"""
        self.click(self.advanced_toggle_btn)
    
    # ==================== 状态检查方法 ====================
    
    def get_status_text(self) -> str:
        """
        获取状态文本
        
        Returns:
            str: 当前状态文本
        """
        return self.get_text(self.status_text)
    
    def wait_for_status(self, expected_text: str, timeout: int = 30000):
        """
        等待状态变化为指定文本
        
        Args:
            expected_text: 期望的状态文本
            timeout: 超时时间（毫秒）
        """
        self.page.wait_for_function(
            f"""() => {{
                const statusText = document.querySelector('{self.status_text}');
                return statusText && statusText.textContent.includes('{expected_text}');
            }}""",
            timeout=timeout
        )
    
    def is_start_button_enabled(self) -> bool:
        """
        判断开始按钮是否可用
        
        Returns:
            bool: 是否可用
        """
        return self.is_enabled(self.start_btn)
    
    def assert_button_enabled(self, button_selector: str):
        """
        断言按钮可用
        
        Args:
            button_selector: 按钮选择器
        """
        self.assert_enabled(button_selector, f"按钮 {button_selector} 应该可用")
    
    def assert_button_disabled(self, button_selector: str):
        """
        断言按钮禁用
        
        Args:
            button_selector: 按钮选择器
        """
        self.assert_disabled(button_selector, f"按钮 {button_selector} 应该禁用")
    
    # ==================== 语言切换方法 ====================
    
    def switch_to_english(self):
        """切换到英文"""
        self.click(self.lang_en_btn)
        self.wait_for_timeout(500)  # 等待翻译完成
    
    def switch_to_chinese(self):
        """切换到中文"""
        self.click(self.lang_zh_btn)
        self.wait_for_timeout(500)  # 等待翻译完成
    
    # ==================== 预设管理方法 ====================
    
    def open_presets_dropdown(self):
        """打开预设下拉菜单"""
        self.click(self.presets_dropdown_btn)
        self.wait_for_element(self.presets_dropdown, state='visible')
    
    def close_presets_dropdown(self):
        """关闭预设下拉菜单"""
        # 点击页面其他位置关闭
        self.page.click('body', position={'x': 10, 'y': 10})
    
    # ==================== 历史记录方法 ====================
    
    def open_history_modal(self):
        """打开历史记录模态框"""
        self.click(self.history_btn)
    
    # ==================== 报告相关方法 ====================
    
    def wait_for_report_generation(self, timeout: int = 300000):
        """
        等待报告生成完成
        
        Args:
            timeout: 超时时间（毫秒，默认5分钟）
        """
        # 等待iframe中加载了HTML内容
        self.page.wait_for_function(
            f"""() => {{
                const iframe = document.querySelector('{self.report_iframe}');
                return iframe && iframe.srcdoc && iframe.srcdoc.includes('<html');
            }}""",
            timeout=timeout
        )
    
    def is_report_generated(self) -> bool:
        """
        判断报告是否已生成
        
        Returns:
            bool: 是否已生成
        """
        try:
            srcdoc = self.get_attribute(self.report_iframe, 'srcdoc')
            return srcdoc and '<html' in srcdoc
        except:
            return False
    
    def get_report_iframe_content(self) -> str:
        """
        获取报告iframe的内容
        
        Returns:
            str: iframe的srcdoc内容
        """
        return self.get_attribute(self.report_iframe, 'srcdoc') or ""
    
    # ==================== 综合操作方法 ====================
    
    def configure_and_start_discussion(self, 
                                      issue: str,
                                      backend: str = "deepseek",
                                      rounds: int = 1,
                                      planners: int = 1,
                                      auditors: int = 1):
        """
        配置参数并启动讨论（一步到位）
        
        Args:
            issue: 议题文本
            backend: 模型后端
            rounds: 讨论轮数
            planners: 策论家数量
            auditors: 监察官数量
        """
        self.fill_issue(issue)
        self.select_backend(backend)
        self.set_rounds(rounds)
        self.set_planners_count(planners)
        self.set_auditors_count(auditors)
        self.start_discussion()
