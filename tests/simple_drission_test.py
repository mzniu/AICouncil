import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DrissionPage import ChromiumPage, ChromiumOptions
import time

def test():
    from src.utils.browser_utils import find_browser_path
    browser_path = find_browser_path()
    print(f"Using browser path: {browser_path}")
    
    co = ChromiumOptions()
    if browser_path:
        co.set_browser_path(browser_path)
    co.headless(True)
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_timeouts(base=30)
    # 使用当前目录下的 tmp 文件夹
    tmp_path = os.path.join(os.getcwd(), 'drission_tmp')
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    co.set_user_data_path(tmp_path)
    
    print("Starting browser...")
    try:
        page = ChromiumPage(addr_or_opts=co)
        print("Browser started. Navigating to Baidu Search...")
        page.get('https://www.baidu.com/s?wd=MCP%20%E6%A8%A1%E5%9E%8B%E4%B8%8A%E4%B8%8B%E6%96%87%E5%8D%8F%E8%AE%AE')
        page.wait.load_start()
        print(f"Title: {page.title}")
        html = page.html
        print(f"HTML length: {len(html)}")
        time.sleep(5)
        page.quit()
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test()
