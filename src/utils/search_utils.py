import requests
import time
import os
import shutil
import tempfile
from bs4 import BeautifulSoup
from src import config_manager as config
from src.utils.logger import logger

def bing_search(query: str, max_results: int = 10, max_retries: int = 3) -> str:
    """使用 Bing 搜索。优先使用 requests，失败则回退到 DrissionPage。"""
    query = query.strip()
    # 清理 LLM 可能生成的冗余词汇
    clean_query = query.replace("内容", "").replace("汇总", "").replace("列表", "")
    import re
    clean_query = re.sub(r'\s+', ' ', clean_query)
    
    if len(clean_query) > 100:
        clean_query = clean_query[:100]
        
    logger.info(f"Attempting Bing search via requests for: {clean_query}")
    res = bing_search_requests(clean_query, max_results=max_results)
    
    # 检查结果相关性
    is_irrelevant = "失败" in res or "未找到结果" in res
    if not is_irrelevant:
        # 简单的相关性检查：如果结果中包含大量 World Economic Forum 且查询不是关于它的
        if "World Economic Forum" in res and "World Economic Forum" not in clean_query:
            logger.warning("Detected potentially irrelevant World Economic Forum results.")
            is_irrelevant = True
            
    if is_irrelevant:
        # 尝试优化查询：如果包含年份，尝试去掉年份再搜一次
        if re.search(r'202[45]', clean_query):
            optimized_query = re.sub(r'202[45]年?', '', clean_query).strip()
            logger.info(f"Retrying Bing search with optimized query: {optimized_query}")
            res = bing_search_requests(optimized_query, max_results=max_results)
            if "失败" not in res and "未找到结果" not in res:
                return res

    else:
        # 结果相关，直接返回
        logger.info("Bing search via requests succeeded.")
        return res

    logger.info("Bing search via requests failed or returned irrelevant results. Falling back to DrissionPage...")
        # ... (rest of the function)
    
    import random
    import urllib.parse
    from DrissionPage import ChromiumPage, ChromiumOptions
    
    encoded_query = urllib.parse.quote(query)
    results = []
    temp_dir = None

    try:
        # 增加随机延迟，避免并行启动时的资源竞争
        time.sleep(random.uniform(1.0, 3.0))
        
        logger.info(f"Performing Bing search via DrissionPage for: {query}")
        
        co = ChromiumOptions()
        co.headless(True)
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-dev-shm-usage')
        co.set_argument('--disable-blink-features=AutomationControlled')
        co.set_argument('--mute-audio')
        co.set_argument('--disable-extensions')
        co.set_argument('--disable-infobars')
        co.set_argument('--no-first-run')
        co.set_argument('--no-default-browser-check')
        # 设置超时时间
        co.set_timeouts(base=30)
        
        # 使用临时用户目录，避免多实例冲突
        temp_dir = tempfile.mkdtemp(prefix='bing_')
        co.set_user_data_path(temp_dir)
        
        # 如果配置了浏览器路径，则使用它
        browser_path = getattr(config, 'BROWSER_PATH', '')
        if browser_path:
            co.set_browser_path(browser_path)
            
        # 尝试初始化页面，增加重试机制
        page = None
        for attempt in range(2):
            try:
                # 强制使用新端口
                browser_port = random.randint(10000, 60000)
                co.set_local_port(browser_port)
                page = ChromiumPage(addr_or_opts=co)
                break
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"First attempt to start browser for Bing failed, retrying... Error: {e}")
                    time.sleep(3)
                else:
                    raise e

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
            if page:
                page.quit()
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass
    except Exception as e:
        logger.error(f"Bing search via DrissionPage failed: {e}")
        logger.info("Falling back to Bing search via requests...")
        return bing_search_requests(query, max_results=max_results)

    return "Bing 搜索失败或未找到结果。"

def bing_search_requests(query: str, max_results: int = 10, max_retries: int = 3) -> str:
    """使用 requests 进行 Bing 搜索的备选方案。"""
    # 使用 cn.bing.com 并配合特定的参数，通常在境内访问更稳定
    url = "https://cn.bing.com/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
        "Referer": "https://cn.bing.com/",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "Upgrade-Insecure-Requests": "1",
    }
    
    # 增加一些 Bing 搜索常用的参数，提高相关性
    params = {
        "q": query,
        "qs": "n",
        "form": "QBRE",
        "sp": "-1",
        "pq": query,
        "sc": "10-0",
        "sk": "",
        "cvid": "7B8B8B8B8B8B8B8B8B8B8B8B8B8B8B8B", # 随机 ID
        "mkt": "zh-CN",
        "setlang": "zh-hans",
    }
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Performing Bing search (requests) (attempt {attempt+1}/{max_retries}) for: {query}")
            session = requests.Session()
            # 先访问首页获取基础 Cookie，这对于 Bing 非常重要
            try:
                session.get("https://cn.bing.com/", headers=headers, timeout=5)
            except:
                pass
                
            response = session.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Bing response length: {len(response.text)}")
            if "在此处找不到任何结果" in response.text or "No results found" in response.text:
                logger.warning("Bing returned 'No results found' page.")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # 核心改进：更精确的选择器，并排除干扰项
            # Bing 的主结果通常在 ol#b_results 下的 li.b_algo
            items = soup.select('ol#b_results > li.b_algo')
            if not items:
                items = soup.select('li.b_algo')
            if not items:
                items = soup.select('.b_algo')
            
            logger.info(f"Found {len(items)} potential items in Bing response.")
            
            for item in items:
                if len(results) >= max_results:
                    break
                
                # 排除广告、相关搜索等干扰
                if item.select_one('.b_ad') or "b_ans" in item.get('class', []):
                    continue

                title_tag = item.select_one('h2 a') or item.select_one('h2')
                link_tag = item.select_one('a')
                # 摘要的选择器需要更精确
                snippet_tag = item.select_one('.b_caption p') or \
                             item.select_one('.b_algoSnippet') or \
                             item.select_one('.b_content p') or \
                             item.select_one('.b_caption')
                
                if title_tag:
                    href = link_tag.get('href', '') if link_tag else ''
                    # 过滤掉 Bing 内部链接
                    if href.startswith('http') and "bing.com/ck/ms" not in href and "microsoft.com" not in href:
                        title_text = title_tag.get_text().strip()
                        body_text = snippet_tag.get_text().strip() if snippet_tag else "无摘要"
                        
                        # 简单的相关性校验：如果标题太短或者包含明显的广告词，可以过滤
                        if len(title_text) < 2:
                            continue
                            
                        results.append({
                            "title": title_text,
                            "href": href,
                            "body": body_text
                        })
            
            if results:
                # 再次检查相关性：如果第一条结果完全不包含查询中的关键词，可能搜索被劫持或重定向了
                # 这里我们至少返回结果，但记录警告
                first_title = results[0]['title'].lower()
                keywords = [k for k in query.split() if len(k) > 1]
                match_count = sum(1 for k in keywords if k.lower() in first_title)
                if keywords and match_count == 0:
                    logger.warning(f"First result title '{first_title}' does not match any keywords from '{query}'")

                return format_search_results(results)
            
            if attempt < max_retries - 1:
                time.sleep(2)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                time.sleep(3)
                
    return f"Bing 搜索(Requests)失败: {str(last_exception)}" if last_exception else "Bing 搜索(Requests)未找到结果。"
                
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

def yahoo_search(query: str, max_results: int = 10, max_retries: int = 3) -> str:
    """使用 Yahoo 搜索（底层使用 Bing 引擎）。"""
    import urllib.parse
    import re
    
    query = query.strip()
    if len(query) > 200:
        query = query[:200]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "DNT": "1",
    }
    
    url = f"https://search.yahoo.com/search?p={urllib.parse.quote(query)}&n={max_results}"
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Performing Yahoo search (attempt {attempt+1}/{max_retries}) for: {query}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # 遍历搜索结果div
            for algo in soup.select('div.algo-sr'):
                if len(results) >= max_results:
                    break
                    
                # 获取标题
                h3 = algo.find('h3')
                if not h3:
                    continue
                
                title = h3.get_text().strip()
                if not title:
                    continue
                
                # 获取URL (从第一个有效的外部链接)
                result_url = None
                for a in algo.find_all('a', href=True):
                    href = a.get('href', '')
                    
                    # Yahoo重定向链接
                    if 'r.search.yahoo.com' in href:
                        match = re.search(r'/RU=([^/]+)/', href)
                        if match:
                            result_url = urllib.parse.unquote(match.group(1))
                            break
                    # 直接外部链接
                    elif href.startswith('http') and 'yahoo.com' not in href:
                        result_url = href
                        break
                
                if not result_url:
                    continue
                
                # 获取摘要
                snippet = "无摘要"
                for selector in ['span.fc-falcon', 'p.fz-ms', 'p', 'span.d-b']:
                    snippet_elem = algo.select_one(selector)
                    if snippet_elem:
                        text = snippet_elem.get_text().strip()
                        if len(text) > 20:
                            snippet = text
                            break
                
                results.append({
                    "title": title,
                    "href": result_url,
                    "body": snippet
                })
            
            if results:
                logger.info(f"Successfully retrieved {len(results)} results via Yahoo.")
                return format_search_results(results)
            
            if attempt < max_retries - 1:
                time.sleep(2)
                
        except Exception as e:
            last_exception = e
            logger.error(f"Yahoo search attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
    
    return f"Yahoo 搜索失败 (已重试 {max_retries} 次): {str(last_exception)}" if last_exception else "Yahoo 搜索未找到结果。"


def mojeek_search(query: str, max_results: int = 10, max_retries: int = 3) -> str:
    """使用 Mojeek 搜索（独立搜索引擎，不依赖 Google/Bing）。"""
    import urllib.parse
    
    query = query.strip()
    if len(query) > 200:
        query = query[:200]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    url = f"https://www.mojeek.com/search?q={urllib.parse.quote(query)}"
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Performing Mojeek search (attempt {attempt+1}/{max_retries}) for: {query}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            for item in soup.select('.results-standard li'):
                if len(results) >= max_results:
                    break
                    
                title_elem = item.find('a', class_='title')
                snippet_elem = item.find('p', class_='s')
                
                if title_elem:
                    title = title_elem.get_text().strip()
                    result_url = title_elem.get('href', '')
                    snippet = snippet_elem.get_text().strip() if snippet_elem else "无摘要"
                    
                    if title and result_url:
                        results.append({
                            "title": title,
                            "href": result_url,
                            "body": snippet
                        })
            
            if results:
                logger.info(f"Successfully retrieved {len(results)} results via Mojeek.")
                return format_search_results(results)
            
            if attempt < max_retries - 1:
                time.sleep(2)
                
        except Exception as e:
            last_exception = e
            logger.error(f"Mojeek search attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
    
    return f"Mojeek 搜索失败 (已重试 {max_retries} 次): {str(last_exception)}" if last_exception else "Mojeek 搜索未找到结果。"


def google_search_api(query: str, max_results: int = 10, max_retries: int = 3) -> str:
    """使用 Google Custom Search API 进行搜索（推荐方式）。
    
    优势：
    - 官方 API，无反爬问题
    - 速度快（~1秒）
    - 国内可访问（无需代理）
    - 稳定可靠
    
    配置：
    1. 访问 https://developers.google.com/custom-search/v1/overview
    2. 创建 API Key 和 Search Engine ID
    3. 在 config.py 中设置：
       GOOGLE_API_KEY = "your_api_key"
       GOOGLE_SEARCH_ENGINE_ID = "your_search_engine_id"
    
    限制：
    - 免费额度：100 次/天
    - 付费：$5/1000次查询
    """
    query = query.strip()
    if len(query) > 200:
        query = query[:200]
    
    # 检查配置
    api_key = config.GOOGLE_API_KEY
    search_engine_id = config.GOOGLE_SEARCH_ENGINE_ID
    
    if not api_key or not search_engine_id:
        logger.warning("GOOGLE_API_KEY or GOOGLE_SEARCH_ENGINE_ID not configured")
        return "搜索失败：未配置 Google API。请参考文档配置 GOOGLE_API_KEY 和 GOOGLE_SEARCH_ENGINE_ID。"
    
    url = "https://www.googleapis.com/customsearch/v1"
    
    last_exception = None
    for attempt in range(max_retries):
        try:
            logger.info(f"Performing Google Custom Search (attempt {attempt+1}/{max_retries}) for: {query}")
            
            params = {
                'key': api_key,
                'cx': search_engine_id,
                'q': query,
                'num': min(max_results, 10),  # API 限制单次最多 10 条
                'lr': 'lang_zh-CN',  # 语言限制
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 检查是否有错误
            if 'error' in data:
                error_msg = data['error'].get('message', 'Unknown error')
                logger.error(f"Google API error: {error_msg}")
                return f"Google API 错误: {error_msg}"
            
            # 提取搜索结果
            items = data.get('items', [])
            
            if not items:
                logger.info(f"No results found for query: {query}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return "未找到相关搜索结果。"
            
            logger.info(f"Successfully retrieved {len(items)} results via Google API.")
            
            # 格式化为统一格式
            results = []
            for item in items:
                results.append({
                    'title': item.get('title', '无标题'),
                    'href': item.get('link', '#'),
                    'body': item.get('snippet', '无摘要')
                })
            
            return format_search_results(results)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("Google API rate limit exceeded")
                return "Google API 配额已用尽。免费版限制 100 次/天。"
            last_exception = e
            logger.error(f"Google API attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
        except Exception as e:
            last_exception = e
            logger.error(f"Google API attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
    return f"Google API 搜索失败 (已重试 {max_retries} 次): {str(last_exception)}"


def google_search_playwright(query: str, max_results: int = 10, max_retries: int = 3, proxy: str = None) -> str:
    """使用 Playwright 执行 Google 搜索（需要访问 Google）。
    
    优势：
    - 真实浏览器环境，反爬能力强
    - 自动处理 JavaScript 渲染
    - 绕过部分反爬检测
    
    注意：
    - 国内需要代理
    - 启动速度较慢（~2-3秒）
    
    Args:
        query: 搜索关键词
        max_results: 最大结果数
        max_retries: 重试次数
        proxy: 代理服务器地址 (例如: "http://127.0.0.1:7890")
    """
    import asyncio
    import urllib.parse
    import random
    
    query = query.strip()
    if len(query) > 200:
        query = query[:200]
    
    async def _search():
        try:
            from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
            
            logger.info(f"Performing Google search via Playwright for: {query}")
            
            async with async_playwright() as p:
                # 启动浏览器配置 - 增强反检测
                launch_options = {
                    'headless': True,
                    'args': [
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-site-isolation-trials',
                        '--disable-web-security',
                        '--disable-features=BlockInsecurePrivateNetworkRequests',
                    ]
                }
                
                browser = await p.chromium.launch(**launch_options)
                
                # 上下文配置（包含代理和更多反检测特征）
                context_options = {
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    'locale': 'zh-CN',
                    'viewport': {'width': 1920, 'height': 1080},
                    'screen': {'width': 1920, 'height': 1080},
                    'device_scale_factor': 1,
                    'has_touch': False,
                    'is_mobile': False,
                    'extra_http_headers': {
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0',
                    }
                }
                
                if proxy:
                    context_options['proxy'] = {'server': proxy}
                    logger.info(f"Using proxy: {proxy}")
                
                context = await browser.new_context(**context_options)
                
                # 注入反检测脚本
                await context.add_init_script("""
                    // 删除 webdriver 标志
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // 修改 plugins 数量
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    
                    // 修改 languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['zh-CN', 'zh', 'en-US', 'en']
                    });
                    
                    // Chrome runtime
                    window.chrome = {
                        runtime: {}
                    };
                    
                    // Permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                """)
                
                page = await context.new_page()
                
                try:
                    # 先访问 Google 首页，建立 cookies
                    logger.info("Visiting Google homepage to establish cookies...")
                    try:
                        await page.goto('https://www.google.com', timeout=15000, wait_until='domcontentloaded')
                        await page.wait_for_timeout(random.randint(1000, 2000))
                    except:
                        pass  # 如果首页访问失败，继续尝试搜索
                    
                    # 访问 Google 搜索
                    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&hl=zh-CN&num={max_results}"
                    
                    try:
                        await page.goto(search_url, timeout=20000, wait_until='networkidle')
                    except PlaywrightTimeoutError:
                        # 降级为 domcontentloaded
                        await page.goto(search_url, timeout=20000, wait_until='domcontentloaded')
                    
                    # 模拟真实用户行为：随机等待
                    await page.wait_for_timeout(random.randint(1500, 3000))
                    
                    # 模拟滚动行为
                    try:
                        await page.evaluate('window.scrollTo(0, Math.random() * 500)')
                        await page.wait_for_timeout(random.randint(500, 1000))
                    except:
                        pass
                    
                    # 检查是否被 Google 阻止
                    page_content = await page.content()
                    if 'unusual traffic' in page_content.lower() or 'captcha' in page_content.lower():
                        await browser.close()
                        return "Google 检测到异常流量，需要人机验证。建议使用其他搜索引擎。"
                    
                    # 等待搜索结果加载（使用更通用的选择器）
                    try:
                        await page.wait_for_selector('div#search, div#rso, div#center_col', timeout=8000)
                    except PlaywrightTimeoutError:
                        # 检查是否是网络不可达
                        title = await page.title()
                        if not title or 'google' not in title.lower():
                            await browser.close()
                            return "无法访问 Google（可能需要代理）。"
                        logger.warning("Google search results selector timeout, trying alternative selectors...")
                    
                    # 额外等待确保内容加载
                    await page.wait_for_timeout(1500)
                    
                    # 提取搜索结果 - 使用多种选择器
                    results = []
                    
                    # 方法1: 标准搜索结果
                    search_items = await page.query_selector_all('div.g:not(.g-blk)')
                    
                    # 方法2: 如果方法1失败，尝试更宽泛的选择器
                    if len(search_items) == 0:
                        search_items = await page.query_selector_all('div[data-sokoban-container], div.Gx5Zad')
                    
                    # 方法3: 如果还是没有，尝试直接找 h3
                    if len(search_items) == 0:
                        logger.warning("Standard selectors failed, trying h3-based extraction...")
                        h3_elements = await page.query_selector_all('h3')
                        
                        for h3 in h3_elements[:max_results]:
                            try:
                                title = await h3.inner_text()
                                parent = await h3.evaluate_handle('el => el.closest("a")')
                                
                                if parent:
                                    href = await parent.get_attribute('href')
                                    
                                    if href and not any(x in href for x in ['google.com/search', 'accounts.google']):
                                        # 尝试获取摘要（在 h3 的父级元素中查找）
                                        grandparent = await h3.evaluate_handle('el => el.parentElement.parentElement')
                                        snippet = "无摘要"
                                        
                                        try:
                                            snippet_text = await grandparent.text_content()
                                            if snippet_text and len(snippet_text) > len(title):
                                                snippet = snippet_text.replace(title, '').strip()[:200]
                                        except:
                                            pass
                                        
                                        results.append({
                                            'title': title.strip(),
                                            'href': href,
                                            'body': snippet
                                        })
                            except Exception as e:
                                logger.debug(f"Failed to parse h3 item: {e}")
                                continue
                    else:
                        # 标准解析
                        for item in search_items[:max_results * 2]:  # 多抓一些，因为可能有广告
                            try:
                                # 提取标题
                                title_elem = await item.query_selector('h3')
                                if not title_elem:
                                    continue
                                title = await title_elem.inner_text()
                                
                                # 提取链接
                                link_elem = await item.query_selector('a')
                                if not link_elem:
                                    continue
                                href = await link_elem.get_attribute('href')
                                
                                # 过滤 Google 自身链接和广告
                                if not href or any(x in href for x in ['google.com/search', 'accounts.google', 'support.google']):
                                    continue
                                
                                # 提取摘要（多个可能的选择器）
                                snippet = "无摘要"
                                for selector in ['.VwiC3b', '.yXK7lf', 'div[data-sncf]', 'div[data-content-feature]', '.IsZvec', 'div.s', 'span.st']:
                                    snippet_elem = await item.query_selector(selector)
                                    if snippet_elem:
                                        text = await snippet_elem.inner_text()
                                        if len(text) > 20:
                                            snippet = text
                                            break
                                
                                # 如果还是没找到摘要，尝试从整个 item 中提取
                                if snippet == "无摘要":
                                    try:
                                        full_text = await item.inner_text()
                                        if full_text and len(full_text) > len(title):
                                            snippet = full_text.replace(title, '').strip()[:200]
                                    except:
                                        pass
                                
                                results.append({
                                    'title': title.strip(),
                                    'href': href,
                                    'body': snippet.strip()
                                })
                                
                                if len(results) >= max_results:
                                    break
                                    
                            except Exception as e:
                                logger.debug(f"Failed to parse Google search item: {e}")
                                continue
                    
                    await browser.close()
                    
                    if results:
                        logger.info(f"Successfully retrieved {len(results)} results via Google (Playwright).")
                        return format_search_results(results)
                    else:
                        return "Google 搜索未找到结果（可能需要代理或网络问题）。"
                        
                except PlaywrightTimeoutError:
                    await browser.close()
                    return "Google 搜索超时（可能需要代理或网络不稳定）。"
                except Exception as e:
                    await browser.close()
                    raise e
                    
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return "搜索失败：Playwright 未安装。"
        except Exception as e:
            logger.error(f"Google search via Playwright failed: {e}")
            import traceback
            traceback.print_exc()
            return f"Google 搜索失败: {str(e)}"
    
    # 运行异步搜索
    last_exception = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                logger.info(f"Retrying Google search (attempt {attempt+1}/{max_retries})...")
                time.sleep(2 * attempt)
            
            result = asyncio.run(_search())
            
            # 如果结果成功或明确提示需要代理/Playwright 未安装，直接返回
            if any(keyword in result for keyword in ["失败", "未找到结果", "超时", "异常流量", "未安装", "无法访问"]):
                if attempt < max_retries - 1 and "超时" in result:
                    last_exception = result
                    continue
                else:
                    return result
            else:
                return result
                
        except Exception as e:
            last_exception = e
            logger.error(f"Google search attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))
    
    return f"Google 搜索失败 (已重试 {max_retries} 次): {str(last_exception)}"


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

def baidu_search_requests(query: str, max_results: int = 10) -> str:
    """使用 requests 进行百度搜索的备选方案。"""
    import urllib.parse
    import random
    
    url = "https://www.baidu.com/s"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.baidu.com/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    results = []
    try:
        session = requests.Session()
        # 先访问首页获取基础 Cookie
        session.get("https://www.baidu.com/", headers=headers, timeout=10)
        
        # 百度每页 10 条
        pages_to_fetch = (max_results + 9) // 10
        
        for p in range(pages_to_fetch):
            pn = p * 10
            params = {
                "wd": query,
                "pn": pn,
                "ie": "utf-8",
                "rn": "10", # 每页记录数
            }
            
            logger.info(f"Baidu Requests Page {p+1}: {url}?wd={query}&pn={pn}")
            response = session.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"Baidu requests failed with status code: {response.status_code}")
                break
                
            # 检查是否被反爬
            if "安全验证" in response.text or "verify.baidu.com" in response.text:
                logger.warning("Baidu requests triggered captcha/security check.")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            # 百度搜索结果的多种可能选择器
            items = soup.select('.result.c-container')
            if not items:
                items = soup.select('div.result-op.xpath-log')
            if not items:
                items = soup.select('div[class*="result"]')
                
            for item in items:
                if len(results) >= max_results:
                    break
                try:
                    # 提取标题和链接
                    title_tag = item.select_one('h3 a') or item.select_one('h3')
                    link_tag = item.select_one('h3 a') or item.select_one('a')
                    
                    if not title_tag:
                        continue
                        
                    title = title_tag.get_text().strip()
                    href = link_tag.get('href', '') if link_tag else ''
                    
                    # 百度链接通常是加密的跳转链接，requests 方式下我们直接存这个链接
                    if href and href.startswith('/'):
                        href = "https://www.baidu.com" + href
                    elif href and not href.startswith('http'):
                        href = "https://www.baidu.com/s?wd=" + urllib.parse.quote(title)
                        
                    # 提取摘要
                    snippet_tag = item.select_one('.c-abstract') or \
                                 item.select_one('div[class*="content-"]') or \
                                 item.select_one('div[class*="c-span"]') or \
                                 item.select_one('.op-se-it-content')
                    
                    body = "无摘要"
                    if snippet_tag:
                        body = snippet_tag.get_text().strip()
                    else:
                        # 尝试从整个 item 中提取文本并排除标题
                        full_text = item.get_text(separator=' ', strip=True)
                        if title in full_text:
                            body = full_text.replace(title, '', 1).strip()
                            if len(body) > 200:
                                body = body[:200] + "..."
                    
                    if title and body != "无摘要":
                        results.append({
                            "title": title,
                            "href": href,
                            "body": body
                        })
                except Exception as e:
                    continue
            
            if len(results) >= max_results:
                break
            # 避免请求过快
            time.sleep(random.uniform(1.5, 3.0))
            
        if results:
            logger.info(f"Successfully retrieved {len(results)} results via Baidu requests.")
            return format_search_results(results)
    except Exception as e:
        logger.error(f"Baidu requests search failed: {e}")
        
    return "百度搜索(Requests)失败或未找到结果。"

def baidu_search(query: str, max_results: int = 10, max_retries: int = 3) -> str:
    """使用百度搜索。优先使用 requests，失败则回退到 DrissionPage。"""
    query = query.strip()
    if len(query) > 60:
        query = query[:60]
        
    logger.info(f"Attempting Baidu search via requests for: {query}")
    res = baidu_search_requests(query, max_results=max_results)
    
    # 检查相关性：如果第一条结果完全不包含查询中的关键词，或者包含明显的干扰项
    # 百度有时会返回大量广告或无关的热搜
    if "失败" not in res and "未找到结果" not in res:
        # 简单的相关性检查
        clean_query = query.strip()
        # 如果查询包含年份，且结果中出现了明显的无关内容（如百度热搜、广告等）
        if "202" in clean_query and ("百度热搜" in res or "广告" in res):
            # 尝试优化查询
            optimized_query = re.sub(r'202[45]年?', '', clean_query).strip()
            if optimized_query != clean_query:
                logger.info(f"Detected potential noise in Baidu results. Retrying with optimized query: {optimized_query}")
                res_opt = baidu_search_requests(optimized_query, max_results=max_results)
                if "失败" not in res_opt and "未找到结果" not in res_opt:
                    res = res_opt

        logger.info("Baidu search via requests succeeded.")
        return res
        
    logger.info("Baidu search via requests failed or returned no results. Falling back to DrissionPage...")
    
    import re
    import random
    import urllib.parse
    from DrissionPage import ChromiumPage, ChromiumOptions
    
    encoded_query = urllib.parse.quote(query)
    results = []
    temp_dir = None

    try:
        # 增加随机延迟，避免并行启动时的资源竞争
        time.sleep(random.uniform(1.0, 3.0))
        
        logger.info(f"Performing Baidu search via DrissionPage for: {query}")
        
        co = ChromiumOptions()
        co.headless(True)
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-dev-shm-usage')
        co.set_argument('--disable-blink-features=AutomationControlled')
        co.set_argument('--mute-audio')
        co.set_argument('--disable-extensions')
        co.set_argument('--disable-infobars')
        co.set_argument('--no-first-run')
        co.set_argument('--no-default-browser-check')
        co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        # 设置超时时间
        co.set_timeouts(base=30)
        
        # 使用临时用户目录，避免多实例冲突
        temp_dir = tempfile.mkdtemp(prefix='baidu_')
        co.set_user_data_path(temp_dir)
        
        # 如果配置了浏览器路径，则使用它
        browser_path = getattr(config, 'BROWSER_PATH', '')
        if browser_path:
            co.set_browser_path(browser_path)
            
        # 尝试初始化页面，增加重试机制
        page = None
        for attempt in range(2):
            try:
                # 强制使用新端口
                browser_port = random.randint(10000, 60000)
                co.set_local_port(browser_port)
                page = ChromiumPage(addr_or_opts=co)
                break
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"First attempt to start browser for Baidu failed, retrying... Error: {e}")
                    time.sleep(3)
                else:
                    raise e

        try:
            # 计算需要抓取的页数 (百度每页 10 条)
            pages_to_fetch = (max_results + 9) // 10
            
            for p in range(pages_to_fetch):
                pn = p * 10
                url = f"https://www.baidu.com/s?wd={encoded_query}&pn={pn}"
                logger.info(f"Baidu Search Page {p+1}: {url}")
                
                # 增加随机延迟
                time.sleep(random.uniform(1, 3))
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
            if page:
                page.quit()
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass
    except Exception as e:
        logger.error(f"Baidu search via DrissionPage failed: {e}")
        logger.info("Falling back to Baidu search via requests...")
        return baidu_search_requests(query, max_results=max_results)

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
            elif provider == "yahoo":
                return yahoo_search(query, max_results=max_res), provider
            elif provider == "mojeek":
                return mojeek_search(query, max_results=max_res), provider
            elif provider == "google":
                # Google 搜索 (仅 API 方式)
                return google_search_api(query, max_results=max_res), "google (API)"
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
