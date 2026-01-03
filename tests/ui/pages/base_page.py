"""
Page Object基础类
提供所有页面对象的通用方法和断言
"""
from playwright.sync_api import Page, expect
from typing import Optional, Union


class BasePage:
    """
    页面对象基类，提供通用的页面操作方法
    
    Attributes:
        page: Playwright页面对象
        base_url: 基础URL
    """
    
    def __init__(self, page: Page, base_url: str = "http://127.0.0.1:5000"):
        """
        初始化页面对象
        
        Args:
            page: Playwright页面对象
            base_url: 基础URL
        """
        self.page = page
        self.base_url = base_url
    
    # ==================== 导航方法 ====================
    
    def goto(self, path: str = "", **kwargs):
        """
        导航到指定路径
        
        Args:
            path: URL路径（相对于base_url）
            **kwargs: 传递给page.goto的额外参数
        """
        url = f"{self.base_url}{path}"
        self.page.goto(url, **kwargs)
    
    def reload(self):
        """刷新当前页面"""
        self.page.reload()
    
    # ==================== 元素查找方法 ====================
    
    def get_element(self, selector: str):
        """
        获取元素定位器
        
        Args:
            selector: CSS选择器或其他定位器
            
        Returns:
            Locator: 元素定位器
        """
        return self.page.locator(selector)
    
    def get_element_by_text(self, text: str, exact: bool = False):
        """
        通过文本内容查找元素
        
        Args:
            text: 要查找的文本
            exact: 是否精确匹配
            
        Returns:
            Locator: 元素定位器
        """
        return self.page.get_by_text(text, exact=exact)
    
    def get_element_by_role(self, role: str, **kwargs):
        """
        通过ARIA角色查找元素
        
        Args:
            role: ARIA角色 (button, textbox, link等)
            **kwargs: 额外的筛选参数
            
        Returns:
            Locator: 元素定位器
        """
        return self.page.get_by_role(role, **kwargs)
    
    # ==================== 等待方法 ====================
    
    def wait_for_element(self, selector: str, state: str = "visible", timeout: int = 30000):
        """
        等待元素出现/消失
        
        Args:
            selector: CSS选择器
            state: 等待状态 (visible/hidden/attached/detached)
            timeout: 超时时间（毫秒）
        """
        self.page.wait_for_selector(selector, state=state, timeout=timeout)
    
    def wait_for_url(self, url_pattern: Union[str, object], timeout: int = 30000):
        """
        等待URL变化
        
        Args:
            url_pattern: URL模式（字符串或正则表达式）
            timeout: 超时时间（毫秒）
        """
        self.page.wait_for_url(url_pattern, timeout=timeout)
    
    def wait_for_load_state(self, state: str = "networkidle", timeout: int = 30000):
        """
        等待页面加载状态
        
        Args:
            state: 加载状态 (load/domcontentloaded/networkidle)
            timeout: 超时时间（毫秒）
        """
        self.page.wait_for_load_state(state, timeout=timeout)
    
    def wait_for_timeout(self, timeout: int):
        """
        等待指定时间（谨慎使用，优先使用wait_for_element等方法）
        
        Args:
            timeout: 等待时间（毫秒）
        """
        self.page.wait_for_timeout(timeout)
    
    # ==================== 交互方法 ====================
    
    def click(self, selector: str, **kwargs):
        """
        点击元素
        
        Args:
            selector: CSS选择器
            **kwargs: 传递给click的额外参数
        """
        self.page.click(selector, **kwargs)
    
    def click_button(self, button_text: str = None, button_id: str = None):
        """
        点击按钮（通过文本或ID）
        
        Args:
            button_text: 按钮文本
            button_id: 按钮ID
        """
        if button_id:
            self.click(f"#{button_id}")
        elif button_text:
            self.page.get_by_role("button", name=button_text).click()
        else:
            raise ValueError("必须提供button_text或button_id")
    
    def fill_input(self, selector: str, value: str):
        """
        填写输入框
        
        Args:
            selector: CSS选择器
            value: 要填写的值
        """
        self.page.fill(selector, value)
    
    def select_option(self, selector: str, value: Union[str, list]):
        """
        选择下拉框选项
        
        Args:
            selector: CSS选择器
            value: 选项值（字符串或字符串列表）
        """
        self.page.select_option(selector, value)
    
    def check_checkbox(self, selector: str):
        """
        勾选复选框
        
        Args:
            selector: CSS选择器
        """
        self.page.check(selector)
    
    def uncheck_checkbox(self, selector: str):
        """
        取消勾选复选框
        
        Args:
            selector: CSS选择器
        """
        self.page.uncheck(selector)
    
    def type_text(self, selector: str, text: str, delay: int = 50):
        """
        逐字输入文本（模拟真实打字）
        
        Args:
            selector: CSS选择器
            text: 要输入的文本
            delay: 每个字符之间的延迟（毫秒）
        """
        self.page.type(selector, text, delay=delay)
    
    # ==================== 获取信息方法 ====================
    
    def get_text(self, selector: str) -> str:
        """
        获取元素文本内容
        
        Args:
            selector: CSS选择器
            
        Returns:
            str: 元素文本
        """
        return self.page.locator(selector).inner_text()
    
    def get_value(self, selector: str) -> str:
        """
        获取输入框的值
        
        Args:
            selector: CSS选择器
            
        Returns:
            str: 输入框的值
        """
        return self.page.locator(selector).input_value()
    
    def get_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """
        获取元素属性值
        
        Args:
            selector: CSS选择器
            attribute: 属性名
            
        Returns:
            str: 属性值
        """
        return self.page.locator(selector).get_attribute(attribute)
    
    def is_visible(self, selector: str) -> bool:
        """
        判断元素是否可见
        
        Args:
            selector: CSS选择器
            
        Returns:
            bool: 是否可见
        """
        return self.page.locator(selector).is_visible()
    
    def is_enabled(self, selector: str) -> bool:
        """
        判断元素是否可用
        
        Args:
            selector: CSS选择器
            
        Returns:
            bool: 是否可用
        """
        return self.page.locator(selector).is_enabled()
    
    def is_checked(self, selector: str) -> bool:
        """
        判断复选框/单选框是否被选中
        
        Args:
            selector: CSS选择器
            
        Returns:
            bool: 是否被选中
        """
        return self.page.locator(selector).is_checked()
    
    # ==================== 断言方法 ====================
    
    def assert_visible(self, selector: str, message: str = ""):
        """
        断言元素可见
        
        Args:
            selector: CSS选择器
            message: 断言失败时的消息
        """
        locator = self.page.locator(selector)
        expect(locator).to_be_visible()
        if message:
            print(f"✅ {message}")
    
    def assert_hidden(self, selector: str, message: str = ""):
        """
        断言元素隐藏
        
        Args:
            selector: CSS选择器
            message: 断言失败时的消息
        """
        locator = self.page.locator(selector)
        expect(locator).to_be_hidden()
        if message:
            print(f"✅ {message}")
    
    def assert_text_contains(self, selector: str, text: str, message: str = ""):
        """
        断言元素包含指定文本
        
        Args:
            selector: CSS选择器
            text: 期望的文本
            message: 断言失败时的消息
        """
        locator = self.page.locator(selector)
        expect(locator).to_contain_text(text)
        if message:
            print(f"✅ {message}")
    
    def assert_text_equals(self, selector: str, text: str, message: str = ""):
        """
        断言元素文本精确匹配
        
        Args:
            selector: CSS选择器
            text: 期望的文本
            message: 断言失败时的消息
        """
        locator = self.page.locator(selector)
        expect(locator).to_have_text(text)
        if message:
            print(f"✅ {message}")
    
    def assert_enabled(self, selector: str, message: str = ""):
        """
        断言元素可用
        
        Args:
            selector: CSS选择器
            message: 断言失败时的消息
        """
        locator = self.page.locator(selector)
        expect(locator).to_be_enabled()
        if message:
            print(f"✅ {message}")
    
    def assert_disabled(self, selector: str, message: str = ""):
        """
        断言元素禁用
        
        Args:
            selector: CSS选择器
            message: 断言失败时的消息
        """
        locator = self.page.locator(selector)
        expect(locator).to_be_disabled()
        if message:
            print(f"✅ {message}")
    
    def assert_has_class(self, selector: str, class_name: str, message: str = ""):
        """
        断言元素包含指定CSS类
        
        Args:
            selector: CSS选择器
            class_name: CSS类名
            message: 断言失败时的消息
        """
        locator = self.page.locator(selector)
        expect(locator).to_have_class(class_name)
        if message:
            print(f"✅ {message}")
    
    def assert_count(self, selector: str, count: int, message: str = ""):
        """
        断言元素数量
        
        Args:
            selector: CSS选择器
            count: 期望的元素数量
            message: 断言失败时的消息
        """
        locator = self.page.locator(selector)
        expect(locator).to_have_count(count)
        if message:
            print(f"✅ {message}")
    
    # ==================== 截图和调试方法 ====================
    
    def take_screenshot(self, path: str = None, full_page: bool = True):
        """
        截取页面截图
        
        Args:
            path: 保存路径（None则返回bytes）
            full_page: 是否截取整个页面
            
        Returns:
            bytes: 截图数据（如果path为None）
        """
        if path:
            self.page.screenshot(path=path, full_page=full_page)
            print(f"📸 截图已保存: {path}")
        else:
            return self.page.screenshot(full_page=full_page)
    
    def highlight_element(self, selector: str):
        """
        高亮显示元素（调试用）
        
        Args:
            selector: CSS选择器
        """
        self.page.locator(selector).highlight()
    
    def console_log(self, message: str):
        """
        在浏览器控制台输出日志
        
        Args:
            message: 日志消息
        """
        self.page.evaluate(f"console.log('{message}')")
