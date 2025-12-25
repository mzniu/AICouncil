import sys
import os
import time
import random
from bs4 import BeautifulSoup

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import logger

def test_bing_search_logic(query: str, max_results: int = 5):
    """测试 Bing 搜索逻辑，模拟 search_utils.py 中的实现"""
    try:
        from DrissionPage import ChromiumPage, ChromiumOptions
        print(f"\n[Test] 正在搜索: {query}")
        
        co = ChromiumOptions()
        co.set_argument('--headless')
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        
        # 模拟多实例端口分配
        browser_port = random.randint(10000, 60000)
        co.set_local_port(browser_port)
        
        print(f"[Test] 启动浏览器，端口: {browser_port}")
        page = ChromiumPage(addr_or_opts=co)
        
        try:
            url = f"https://cn.bing.com/search?q={query}"
            print(f"[Test] 访问 URL: {url}")
            page.get(url)
            
            print("[Test] 等待页面加载完成...")
            # 使用更稳健的等待方式：等待页面停止加载，而不是直接等待元素
            page.wait.load_start()
            
            # 循环检查元素是否存在，而不是使用 ele_displayed (它会频繁调用 JS 导致失效)
            found = False
            for _ in range(15):
                if page.ele('css:li.b_algo'):
                    found = True
                    break
                time.sleep(1)
            
            if found:
                print("[Test] 元素已找到，等待 2 秒让动态内容加载完毕...")
                time.sleep(2)
                
                print("[Test] 抓取页面 HTML 快照...")
                # 直接获取 HTML 字符串，不经过元素对象
                page_html = page.html
                print(f"[Test] HTML 抓取成功，长度: {len(page_html)}")

                soup = BeautifulSoup(page_html, 'html.parser')
                items = soup.select('li.b_algo')
                print(f"[Test] 找到 {len(items)} 个搜索条目")
                
                results = []
                for i, item in enumerate(items[:max_results]):
                    title_tag = item.select_one('h2 a') or item.select_one('h2')
                    link_tag = item.select_one('a')
                    snippet_tag = item.select_one('.b_caption p, .b_linehighlight, .b_algoSlug, .b_content p, .b_algoSnippet')
                    
                    if title_tag and link_tag:
                        href = link_tag.get('href', '')
                        if href.startswith('http'):
                            results.append({
                                "title": title_tag.get_text().strip(),
                                "href": href,
                                "body": snippet_tag.get_text().strip() if snippet_tag else "无摘要"
                            })
                            print(f"  {i+1}. {results[-1]['title'][:50]}...")
                
                if results:
                    print(f"\n[Success] 成功获取 {len(results)} 条结果！")
                    return True
                else:
                    print("\n[Fail] 未能解析出有效结果。")
            else:
                print("\n[Fail] 超时未找到搜索结果元素。")
                # 打印当前页面标题辅助调试
                print(f"[Debug] 页面标题: {page.title}")
                if "验证" in page.html or "Captcha" in page.html:
                    print("[Debug] 检测到验证码拦截！")
        finally:
            page.quit()
            print("[Test] 浏览器已关闭")
            
    except Exception as e:
        print(f"\n[Error] 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
    
    return False

if __name__ == "__main__":
    test_cases = [
        {
            "name": "过度拆分关键词测试",
            "query": "北京 2025年 最新 房地产 政策 调整 内容",
            "expect_results": True
        },
        {
            "name": "普通政策查询",
            "query": "2025年北京房地产政策",
            "expect_results": True
        },
        {
            "name": "技术架构查询",
            "query": "DeepSeek R1 技术架构原理",
            "expect_results": True
        },
        {
            "name": "长查询/复杂查询",
            "query": "北京市关于进一步优化调整房地产政策更好满足居民家庭多样化住房需求的通知 2025",
            "expect_results": True
        },
        {
            "name": "英文查询",
            "query": "OpenAI Sora technical report summary",
            "expect_results": True
        },
        {
            "name": "可能触发百科的查询",
            "query": "北京 房地产",
            "expect_results": True
        },
        {
            "name": "无结果查询",
            "query": "asdfghjkl1234567890qwertyuiop",
            "expect_results": False
        }
    ]
    
    summary = []
    for case in test_cases:
        print(f"\n{'='*20} 测试场景: {case['name']} {'='*20}")
        start_time = time.time()
        success = test_bing_search_logic(case['query'])
        duration = time.time() - start_time
        
        status = "PASS" if success == case['expect_results'] else "FAIL"
        summary.append(f"| {case['name']} | {case['query'][:30]}... | {status} | {duration:.2f}s |")
        time.sleep(3) # 避免请求过快被封
    
    print("\n" + "="*50)
    print("测试汇总报告:")
    print("| 场景名称 | 查询语句 | 状态 | 耗时 |")
    print("|---|---|---|---|")
    for line in summary:
        print(line)
    print("="*50)
