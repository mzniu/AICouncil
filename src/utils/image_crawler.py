"""
Playwright 页面爬虫：从搜索结果页面提取图片

使用 Playwright 渲染页面（支持 JS），提取所有可见图片的：
- 实际 URL（src/currentSrc）
- 自然尺寸（naturalWidth/naturalHeight）
- 页面位置（用于判断是否在正文区域）
- alt 文本

相比 requests+BeautifulSoup 方案，能处理：
- 懒加载图片（JS 触发的 <img>）
- SPA/动态页面
- CSS background-image（可选）
"""

import asyncio
import hashlib
import re
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# ========== 常量 ==========

PAGE_TIMEOUT = 12000        # 单页加载超时（ms）
TOTAL_CRAWL_TIMEOUT = 40    # 总爬取超时（秒）
MAX_PAGES = 6               # 最多同时爬取页数
MAX_IMAGES_PER_PAGE = 8     # 每页最多提取图片数
VIEWPORT = {'width': 1280, 'height': 900}

# 广告/追踪域名
AD_DOMAINS = {
    'doubleclick.net', 'googlesyndication.com', 'googleadservices.com',
    'google-analytics.com', 'facebook.net', 'facebook.com',
    'twitter.com', 'linkedin.com', 'amazon-adsystem.com',
    'adnxs.com', 'adsrvr.org', 'criteo.com', 'outbrain.com',
    'taboola.com', 'moatads.com', 'quantserve.com', 'scorecardresearch.com',
    'bluekai.com', 'exelator.com', 'mathtag.com',
}

# 路径段黑名单
PATH_BLACKLIST = re.compile(
    r'/(ads?|banner|pixel|track|beacon|analytics|social|share|'
    r'icon|favicon|logo|sprite|emoji|avatar|badge|button|'
    r'loading|spinner|spacer|arrow|close|menu|nav|thumb_\d)/|'
    r'\.(gif)$',   # GIF 通常是动画/追踪
    re.IGNORECASE
)

# 文件名黑名单
FILENAME_BLACKLIST = re.compile(
    r'(logo|icon|avatar|badge|button|banner|ad[\-_]|pixel|tracker|'
    r'spacer|spinner|loading|arrow|close|menu|nav|emoji|favicon|'
    r'sprite|social|share|like|follow|play[\-_]|thumb_\d)',
    re.IGNORECASE
)


async def _crawl_single_page(
    browser,
    url: str,
    title: str = ""
) -> List[Dict]:
    """用 Playwright 爬取单个页面的图片
    
    Returns:
        [{url, alt, source_url, source_title, type, width, height, area, y_position}]
    """
    candidates = []
    context = None
    
    try:
        context = await browser.new_context(
            viewport=VIEWPORT,
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
            java_script_enabled=True,
            ignore_https_errors=True,
        )
        page = await context.new_page()
        
        # 阻止多媒体和字体加载（加速）
        await page.route("**/*.{mp4,webm,ogg,mp3,wav,flac,woff,woff2,ttf,eot}", 
                         lambda route: route.abort())
        
        await page.goto(url, wait_until='domcontentloaded', timeout=PAGE_TIMEOUT)
        
        # 等待图片懒加载触发
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
        await page.wait_for_timeout(800)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)
        
        # 提取 og:image / twitter:image
        meta_images = await page.evaluate("""() => {
            const results = [];
            const og = document.querySelector('meta[property="og:image"]');
            if (og && og.content) results.push({url: og.content, type: 'og'});
            const tw = document.querySelector('meta[name="twitter:image"]');
            if (tw && tw.content) results.push({url: tw.content, type: 'og'});
            return results;
        }""")
        
        for m in meta_images:
            if m['url'] and _is_valid_crawled_url(m['url'], url):
                candidates.append({
                    'url': m['url'],
                    'alt': title or '封面图',
                    'source_url': url,
                    'source_title': title,
                    'type': 'og',
                    'width': 0, 'height': 0,
                    'area': 0, 'y_position': 0,
                })
        
        # 提取所有可见 <img> 的详细信息
        img_data = await page.evaluate("""() => {
            const imgs = document.querySelectorAll('img');
            const results = [];
            for (const img of imgs) {
                const rect = img.getBoundingClientRect();
                // 跳过不可见的图片
                if (rect.width < 10 || rect.height < 10) continue;
                // 跳过 viewport 外的图片（太下方）
                if (rect.top > 4000) continue;
                
                results.push({
                    src: img.currentSrc || img.src || '',
                    alt: img.alt || img.title || '',
                    naturalWidth: img.naturalWidth || 0,
                    naturalHeight: img.naturalHeight || 0,
                    displayWidth: Math.round(rect.width),
                    displayHeight: Math.round(rect.height),
                    top: Math.round(rect.top),
                    area: Math.round(rect.width * rect.height),
                    // 检查是否在正文区域
                    inArticle: !!(img.closest('article') || img.closest('main') || 
                                  img.closest('[role="main"]') || img.closest('.content') ||
                                  img.closest('.post') || img.closest('.entry')),
                });
            }
            return results;
        }""")
        
        seen_urls = {c['url'] for c in candidates}
        
        for info in img_data:
            if len(candidates) >= MAX_IMAGES_PER_PAGE:
                break
            
            img_url = info['src']
            if not img_url or img_url.startswith('data:') or img_url in seen_urls:
                continue
            
            if not _is_valid_crawled_url(img_url, url):
                continue
            
            # 尺寸过滤（使用自然尺寸）
            nw = info['naturalWidth']
            nh = info['naturalHeight']
            if nw > 0 and nh > 0:
                if nw < 200 or nh < 150:
                    continue
                # 极端宽高比（横幅/条状广告）
                ratio = nw / nh
                if ratio > 5 or ratio < 0.2:
                    continue
            elif info['displayWidth'] < 150 or info['displayHeight'] < 100:
                continue
            
            seen_urls.add(img_url)
            candidates.append({
                'url': img_url,
                'alt': info['alt'][:120] or title or '内容图片',
                'source_url': url,
                'source_title': title,
                'type': 'content_article' if info['inArticle'] else 'content',
                'width': nw or info['displayWidth'],
                'height': nh or info['displayHeight'],
                'area': info['area'],
                'y_position': info['top'],
            })
        
        logger.info(f"[crawler] {urlparse(url).netloc}: {len(candidates)} 张图片")
        
    except Exception as e:
        logger.debug(f"[crawler] 爬取失败 {url}: {e}")
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
    
    return candidates


def _is_valid_crawled_url(img_url: str, page_url: str) -> bool:
    """检查爬取到的图片 URL 是否有效"""
    if not img_url or not img_url.startswith('http'):
        return False
    
    parsed = urlparse(img_url)
    
    # 域名黑名单
    netloc = parsed.netloc.lower()
    for ad in AD_DOMAINS:
        if ad in netloc:
            return False
    
    # 路径黑名单
    if PATH_BLACKLIST.search(parsed.path):
        return False
    
    # 文件名黑名单
    filename = parsed.path.rsplit('/', 1)[-1].lower()
    if FILENAME_BLACKLIST.search(filename):
        return False
    
    return True


async def _crawl_pages_async(pages: List[Dict]) -> List[Dict]:
    """异步并行爬取多个页面"""
    from playwright.async_api import async_playwright
    
    all_candidates = []
    start_time = time.time()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage'],
        )
        
        try:
            tasks = []
            for page_info in pages[:MAX_PAGES]:
                if time.time() - start_time > TOTAL_CRAWL_TIMEOUT:
                    break
                tasks.append(_crawl_single_page(browser, page_info['url'], page_info['title']))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for r in results:
                if isinstance(r, list):
                    all_candidates.extend(r)
                elif isinstance(r, Exception):
                    logger.debug(f"[crawler] 页面爬取异常: {r}")
        finally:
            await browser.close()
    
    # 去重
    seen = set()
    deduped = []
    for c in all_candidates:
        url_hash = hashlib.md5(c['url'].encode()).hexdigest()
        if url_hash not in seen:
            seen.add(url_hash)
            deduped.append(c)
    
    # 排序：og > content_article > content，同类按面积降序
    type_order = {'og': 0, 'content_article': 1, 'content': 2}
    deduped.sort(key=lambda x: (type_order.get(x['type'], 9), -x.get('area', 0)))
    
    return deduped


def crawl_images_from_urls(pages: List[Dict]) -> List[Dict]:
    """同步入口：使用 Playwright 从页面列表爬取图片
    
    Args:
        pages: [{"url": "...", "title": "..."}]
    
    Returns:
        候选图片列表（与 image_utils 格式兼容）
    """
    if not pages:
        return []
    
    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except ImportError:
        logger.info("[crawler] Playwright 未安装，跳过页面爬取")
        return []
    
    logger.info(f"[crawler] 开始 Playwright 爬取 {len(pages)} 个页面...")
    start = time.time()
    
    try:
        # 兼容已有事件循环的情况（如 Flask）
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # 在已有事件循环中，使用新线程
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _crawl_pages_async(pages))
                results = future.result(timeout=TOTAL_CRAWL_TIMEOUT + 10)
        else:
            results = asyncio.run(_crawl_pages_async(pages))
        
        elapsed = time.time() - start
        logger.info(f"[crawler] Playwright 爬取完成: {len(results)} 张图片, 耗时 {elapsed:.1f}s")
        return results
        
    except Exception as e:
        logger.warning(f"[crawler] Playwright 爬取失败: {e}")
        return []
