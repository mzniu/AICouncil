from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
b = p.chromium.launch(headless=False)
c = b.new_context()
page = c.new_page()

print("正在访问首页...")
page.goto('http://127.0.0.1:5000', wait_until='domcontentloaded')
time.sleep(2)

print("检查 #issue-input...")
el = page.query_selector('#issue-input')
print(f'Element found: {el is not None}')
if el:
    print(f'Visible: {el.is_visible()}')

print("检查 #start-btn...")
btn = page.query_selector('#start-btn')
print(f'Button found: {btn is not None}')
if btn:
    print(f'Visible: {btn.is_visible()}')
    print(f'Disabled: {btn.is_disabled()}')

input("按Enter继续...")
b.close()
p.stop()
