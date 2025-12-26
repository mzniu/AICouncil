import requests
import time
from bs4 import BeautifulSoup
from src import config
from src.utils import logger

def bing_search(query: str, max_results: int = 10, max_retries: int = 3) -> str:
    """使用 Bing 搜索。支持多页抓取。"""
    import re
    import random
    import urllib.parse
    from DrissionPage import ChromiumPage, ChromiumOptions
    
    query = query.strip()
    query = query.replace("内容", "").replace("汇总", "").replace("列表", "")
    query = re.sub(r'\s+', ' ', query)
    
    if len(query) > 60:
        query = query[:60]
    
    encoded_query = urllib.parse.quote(query)
    results = []

    try:
        import random
        # 增加微小随机延迟，避免并行启动时的资源竞争
        time.sleep(random.uniform(0.1, 0.5))
        
        co = ChromiumOptions()
        co.set_argument('--headless')
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        
        # 如果配置了浏览器路径，则使用它
        browser_path = getattr(config, 'BROWSER_PATH', '')
        if browser_path:
            co.set_browser_path(browser_path)
            
        browser_port = random.randint(10000, 60000)
        co.set_local_port(browser_port)
        
        page = ChromiumPage(addr_or_opts=co) 
        try:
            # 计算需要抓取的页数 (Bing 每页约 10 条)
            pages_to_fetch = (max_results + 9) // 10
            
            for p in range(pages_to_fetch):
                first_index = p * 10 + 1
                url = f"https://cn.bing.com/search?q={encoded_query}&first={first_index}&mkt=zh-CN&setlang=zh-hans"
                logger.info(f"Bing Search Page {p+1}: {url}")
                
                page.get(url)
                page.wait.load_start()
                
                # 等待结果加载
                found = False
                for _ in range(8):
                    if page.ele('css:li.b_algo'):
                        found = True
                        break
                    time.sleep(1)
                
                if not found:
                    break
                
                time.sleep(1.5)
                page_html = page.html
                soup = BeautifulSoup(page_html, 'html.parser')
                items = soup.select('li.b_algo')
                
                for item in items:
                    if len(results) >= max_results:
                        break
                    try:
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
                    except:
                        continue
                
                if len(results) >= max_results:
                    break
                
            if results:
                logger.info(f"Successfully retrieved {len(results)} results via Bing.")
                return format_search_results(results)
                
        finally:
            page.quit()
    except Exception as e:
        logger.error(f"Bing search failed: {e}")

    return "Bing 搜索失败或未找到结果。"

def bing_search_requests(query: str, max_results: int = 5, max_retries: int = 3) -> str:
    """使用 requests 进行 Bing 搜索的备选方案。"""
    url = "https://cn.bing.com/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Referer": "https://cn.bing.com/",
    }
    
    params = {
        "q": query,
        "form": "QBRE",
        "mkt": "zh-CN",
        "setlang": "zh-hans",
        "cc": "CN",
        "cvid": "9EC267FFF1EF46A6927986217CF9B9E3"
    }
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Performing Bing search (requests) (attempt {attempt+1}/{max_retries}) for: {query}")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            items = soup.select('li.b_algo') or soup.select('.b_algo')
            
            for item in items[:max_results]:
                title_tag = item.select_one('h2 a')
                snippet_tag = item.select_one('.b_caption p, .b_linehighlight, .b_algoSlug, .b_content p, .b_algoSnippet')
                
                if title_tag:
                    results.append({
                        "title": title_tag.get_text(),
                        "href": title_tag.get('href'),
                        "body": snippet_tag.get_text() if snippet_tag else "无摘要"
                    })
            
            if results:
                return format_search_results(results)
            
            if attempt < max_retries - 1:
                time.sleep(2)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                time.sleep(3)
                
    return f"Bing 搜索失败: {str(last_exception)}"

def format_search_results(results: list) -> str:
    """将搜索结果列表格式化为 Markdown 表格。"""
    table_header = "| # | 标题 | 摘要 |\n|---|---|---|\n"
    table_rows = []
    for i, res in enumerate(results, 1):
        title = res.get('title', '无标题').replace('|', '\\|')
        content = res.get('body', '无内容').replace('|', '\\|').replace('\n', ' ')
        url_link = res.get('href', '#')
        table_rows.append(f"| {i} | [{title}]({url_link}) | {content[:200]}... |")
    return table_header + "\n".join(table_rows)

def duckduckgo_search(query: str, max_results: int = 5, max_retries: int = 3) -> str:
    """使用 DuckDuckGo 进行免费联网搜索，带重试机制。"""
    # 如果查询太长，截断它以避免 API 错误
    if len(query) > 200:
        logger.warning(f"Search query too long ({len(query)} chars), truncating for stability.")
        query = query[:200]

    last_exception = None
    for attempt in range(max_retries):
        try:
            from duckduckgo_search import DDGS
            logger.info(f"Performing DuckDuckGo search (attempt {attempt+1}/{max_retries}) for: {query}")
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(query, max_results=max_results)]
                
            if not results:
                logger.info(f"No results found for query: {query}")
                # 如果没找到结果，可能是网络抖动或频率限制，增加延迟后重试
                if attempt < max_retries - 1:
                    sleep_time = (attempt + 1) * 3
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    continue
                return "未找到相关搜索结果。"
                
            logger.info(f"Successfully retrieved {len(results)} search results for: {query}")
            
            # 构建 Markdown 表格
            table_header = "| # | 标题 | 摘要 |\n|---|---|---|\n"
            table_rows = []
            for i, res in enumerate(results, 1):
                title = res.get('title', '无标题').replace('|', '\\|')
                content = res.get('body', '无内容').replace('|', '\\|').replace('\n', ' ')
                url = res.get('href', '#')
                table_rows.append(f"| {i} | [{title}]({url}) | {content[:200]}... |")
                
            return table_header + "\n".join(table_rows)
        except Exception as e:
            last_exception = e
            logger.error(f"DuckDuckGo search attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                sleep_time = (attempt + 1) * 5 # 报错时延迟更久一点
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            
    return f"DuckDuckGo 搜索失败 (已重试 {max_retries} 次): {str(last_exception)}"

def tavily_search(query: str, max_results: int = 5, max_retries: int = 3) -> str:
    """使用 Tavily API 进行联网搜索，带重试机制。"""
    if not config.TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set, skipping search.")
        return "搜索失败：未配置 TAVILY_API_KEY。"

    # 截断过长查询
    if len(query) > 200:
        query = query[:200]

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": config.TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results
    }
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Performing Tavily search (attempt {attempt+1}/{max_retries}) for: {query}")
            response = requests.post(url, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if not results:
                logger.info(f"No results found for query: {query}")
                if attempt < max_retries - 1:
                    sleep_time = (attempt + 1) * 2
                    time.sleep(sleep_time)
                    continue
                return "未找到相关搜索结果。"
                
            logger.info(f"Successfully retrieved {len(results)} search results for: {query}")
            
            # 构建 Markdown 表格
            table_header = "| # | 标题 | 摘要 |\n|---|---|---|\n"
            table_rows = []
            for i, res in enumerate(results, 1):
                title = res.get('title', '无标题').replace('|', '\\|')
                content = res.get('content', '无内容').replace('|', '\\|').replace('\n', ' ')
                url = res.get('url', '#')
                table_rows.append(f"| {i} | [{title}]({url}) | {content[:200]}... |")
                
            return table_header + "\n".join(table_rows)
        except Exception as e:
            last_exception = e
            logger.error(f"Tavily search attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                sleep_time = (attempt + 1) * 4
                time.sleep(sleep_time)
            
    return f"Tavily 搜索失败 (已重试 {max_retries} 次): {str(last_exception)}"

def baidu_search(query: str, max_results: int = 10, max_retries: int = 3) -> str:
    """使用百度搜索。支持多页抓取。"""
    import re
    import random
    import urllib.parse
    from DrissionPage import ChromiumPage, ChromiumOptions
    
    query = query.strip()
    if len(query) > 60:
        query = query[:60]
    
    encoded_query = urllib.parse.quote(query)
    results = []

    try:
        import random
        # 增加微小随机延迟，避免并行启动时的资源竞争
        time.sleep(random.uniform(0.1, 0.5))
        
        logger.info(f"Performing Baidu search via DrissionPage for: {query}")
        
        co = ChromiumOptions()
        co.set_argument('--headless')
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        
        # 如果配置了浏览器路径，则使用它
        browser_path = getattr(config, 'BROWSER_PATH', '')
        if browser_path:
            co.set_browser_path(browser_path)
            
        browser_port = random.randint(10000, 60000)
        co.set_local_port(browser_port)
        
        page = ChromiumPage(addr_or_opts=co) 
        try:
            # 计算需要抓取的页数 (百度每页 10 条)
            pages_to_fetch = (max_results + 9) // 10
            
            for p in range(pages_to_fetch):
                pn = p * 10
                url = f"https://www.baidu.com/s?wd={encoded_query}&pn={pn}"
                logger.info(f"Baidu Search Page {p+1}: {url}")
                
                page.get(url)
                page.wait.load_start()
                
                found = False
                for _ in range(8):
                    if page.ele('css:.result.c-container'):
                        found = True
                        break
                    time.sleep(1)
                
                if not found:
                    break
                
                time.sleep(2)
                page_html = page.html
                soup = BeautifulSoup(page_html, 'html.parser')
                items = soup.select('.result.c-container')
                
                for item in items:
                    if len(results) >= max_results:
                        break
                    try:
                        title_tag = item.select_one('h3 a') or item.select_one('h3')
                        link_tag = item.select_one('h3 a') or item.select_one('a')
                        
                        snippet_tag = item.select_one('.c-abstract') or \
                                     item.select_one('div[class*="content-"]') or \
                                     item.select_one('div[class*="c-span"]') or \
                                     item.select_one('.op-se-it-content')
                        
                        if title_tag:
                            href = link_tag.get('href', '') if link_tag else ''
                            body = "无摘要"
                            if snippet_tag:
                                body = snippet_tag.get_text().strip()
                            else:
                                full_text = item.get_text(separator=' ', strip=True)
                                title_text = title_tag.get_text(strip=True)
                                if title_text in full_text:
                                    body = full_text.replace(title_text, '', 1).strip()
                                    if len(body) > 200:
                                        body = body[:200] + "..."
                            
                            results.append({
                                "title": title_tag.get_text().strip(),
                                "href": href,
                                "body": body if body else "无摘要"
                            })
                    except:
                        continue
                
                if len(results) >= max_results:
                    break
                    
            if results:
                logger.info(f"Successfully retrieved {len(results)} results via Baidu.")
                return format_search_results(results)
            
        finally:
            page.quit()
    except Exception as e:
        logger.error(f"Baidu search failed: {e}")

    return "百度搜索失败或未找到结果。"

def search_if_needed(text: str) -> str:
    """
    简单的启发式搜索：如果文本中包含特定的搜索指令，则执行搜索。
    支持多个搜索指令，并支持多供应商并行搜索。
    """
    import re
    from concurrent.futures import ThreadPoolExecutor
    
    queries = re.findall(r'\[SEARCH:\s*(.*?)\]', text)
    if not queries:
        return ""
    
    # 获取供应商列表，支持逗号分隔的多选
    provider_str = getattr(config, "SEARCH_PROVIDER", "bing").lower()
    providers = [p.strip() for p in provider_str.split(',') if p.strip()]
    if not providers:
        providers = ["bing"]
    
    all_results = []
    
    def perform_single_search(query, provider):
        query = query.strip()
        # 默认获取 10 条结果，如果需要更多可以从这里调整
        max_res = 10
        try:
            if provider == "tavily":
                return tavily_search(query, max_results=max_res), provider
            elif provider == "bing":
                return bing_search(query, max_results=max_res), provider
            elif provider == "baidu":
                return baidu_search(query, max_results=max_res), provider
            elif provider == "duckduckgo":
                res = duckduckgo_search(query, max_results=max_res)
                if "搜索失败" in res:
                    logger.info(f"DuckDuckGo failed, falling back to Bing for: {query}")
                    return bing_search(query, max_results=max_res), "bing (fallback)"
                return res, provider
            else:
                return bing_search(query, max_results=max_res), "bing (default)"
        except Exception as e:
            logger.error(f"Search failed for {query} on {provider}: {e}")
            return f"搜索出错: {str(e)}", provider

    # 使用线程池并行执行所有查询和供应商的组合
    search_tasks = []
    for query in queries:
        for provider in providers:
            search_tasks.append((query, provider))
            
    logger.info(f"Starting parallel search: {len(search_tasks)} tasks across {len(providers)} providers.")
    
    with ThreadPoolExecutor(max_workers=min(len(search_tasks), 10)) as executor:
        futures = [executor.submit(perform_single_search, q, p) for q, p in search_tasks]
        
        # 按顺序收集结果
        for i, future in enumerate(futures):
            query, provider = search_tasks[i]
            res, actual_provider = future.result()
            all_results.append(f"### 搜索查询: {query} (来源: {actual_provider})\n\n{res}")
    
    return "\n\n---\n\n".join(all_results)
