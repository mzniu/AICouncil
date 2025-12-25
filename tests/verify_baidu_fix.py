import sys
import os
import time
import random
from bs4 import BeautifulSoup

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_baidu_snippet_logic(query: str):
    try:
        from DrissionPage import ChromiumPage, ChromiumOptions
        print(f"\n[Test] 正在测试百度摘要抓取: {query}")
        
        co = ChromiumOptions()
        co.set_argument('--headless')
        browser_port = random.randint(10000, 60000)
        co.set_local_port(browser_port)
        
        page = ChromiumPage(addr_or_opts=co)
        try:
            url = f"https://www.baidu.com/s?wd={query}"
            page.get(url)
            page.wait.load_start()
            
            time.sleep(3) # 给更多时间加载
            page_html = page.html
            soup = BeautifulSoup(page_html, 'html.parser')
            items = soup.select('.result.c-container')
            
            print(f"[Test] 找到 {len(items)} 个条目")
            for i, item in enumerate(items[:3]):
                title_tag = item.select_one('h3 a') or item.select_one('h3')
                
                # 模拟新逻辑
                snippet_tag = item.select_one('.c-abstract') or \
                             item.select_one('div[class*="content-"]') or \
                             item.select_one('div[class*="c-span"]') or \
                             item.select_one('.op-se-it-content')
                
                body = "无摘要"
                if snippet_tag:
                    body = snippet_tag.get_text().strip()
                else:
                    full_text = item.get_text(separator=' ', strip=True)
                    title_text = title_tag.get_text(strip=True) if title_tag else ""
                    body = full_text.replace(title_text, '', 1).strip()
                
                print(f"\n--- 结果 {i+1} ---")
                print(f"标题: {title_tag.get_text().strip() if title_tag else 'N/A'}")
                print(f"摘要: {body[:100]}...")
                
        finally:
            page.quit()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_baidu_snippet_logic("北京发布楼市新政")
