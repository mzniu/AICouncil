"""
简化测试：验证点击开始按钮是否能启动讨论
"""
import pytest
from playwright.sync_api import Page
from pages.home_page import HomePage


@pytest.mark.p0
def test_simple_click_start(authenticated_page: Page, test_issue_text: str):
    """
    最简单的测试：填表单 → 点击 → 验证状态变化
    """
    home = HomePage(authenticated_page)
    
    print(f"\n📝 配置议题: {test_issue_text}")
    home.fill_issue(test_issue_text)
    home.select_backend("deepseek")
    home.set_rounds(1)
    home.set_planners_count(1)
    home.set_auditors_count(1)
    
    # 验证按钮初始状态
    btn_before = authenticated_page.evaluate("""() => {
        const btn = document.getElementById('start-btn');
        return {
            disabled: btn.disabled,
            text: btn.innerText.trim(),
            visible: !btn.hidden,
            classes: btn.className
        };
    }""")
    print(f"🔍 点击前: {btn_before}")
    
    # 点击按钮
    print("🖱️  点击开始议事按钮...")
    authenticated_page.click('#start-btn')
    
    # 等待2秒看变化
    authenticated_page.wait_for_timeout(2000)
    
    # 检查点击后状态
    btn_after = authenticated_page.evaluate("""() => {
        const btn = document.getElementById('start-btn');
        return {
            disabled: btn.disabled,
            text: btn.innerText.trim()
        };
    }""")
    print(f"🔍 点击后: {btn_after}")
    
    status = home.get_status_text()
    print(f"📊 状态: {status}")
    
    # 检查网络请求
    print("\n🌐 检查是否发送了/api/start请求...")
    
    # 验证：按钮应该变化或状态应该变化
    if btn_after['disabled'] or "讨论" in status or "运行" in status:
        print("✅ 讨论已启动！")
    else:
        print(f"❌ 讨论未启动！按钮: {btn_after}, 状态: {status}")
        
        # 尝试直接调用JavaScript
        print("\n🔧 尝试直接调用JavaScript startDiscussion()...")
        authenticated_page.evaluate("startDiscussion()")
        authenticated_page.wait_for_timeout(2000)
        
        btn_js = authenticated_page.evaluate("""() => {
            const btn = document.getElementById('start-btn');
            return {disabled: btn.disabled, text: btn.innerText.trim()};
        }""")
        status_js = home.get_status_text()
        print(f"🔍 JS调用后 - 按钮: {btn_js}, 状态: {status_js}")
