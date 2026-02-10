"""
图片处理工具：下载、压缩、Base64 编码

为报告生成提供图片素材支持。
从搜索结果页面提取 og:image 和正文图片，
下载后压缩为适合嵌入 HTML 报告的 Base64 Data URI。
"""

import base64
import io
import re
import time
import hashlib
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# ========== 常量 ==========

# 下载限制
DOWNLOAD_TIMEOUT = 8          # 单张图片下载超时（秒）
TOTAL_TIMEOUT = 45            # 总图片处理超时（秒）
MAX_DOWNLOAD_SIZE = 5 * 1024 * 1024  # 最大下载尺寸 5MB（原始）

# 压缩参数
MAX_WIDTH = 800               # 最大宽度（像素）
JPEG_QUALITY = 75             # JPEG 压缩质量
MAX_ENCODED_SIZE = 150 * 1024 # 单张 Base64 前最大 150KB

# 池大小限制
MAX_IMAGES_PER_PAGE = 5       # 每个页面最多提取的图片数
MAX_TOTAL_IMAGES = 12         # 总候选图片上限
MAX_FINAL_IMAGES = 8          # 最终传给 Reporter 的上限
MAX_TOTAL_BASE64_SIZE = 1.5 * 1024 * 1024  # 总 Base64 上限 1.5MB

# 图片过滤规则
MIN_IMAGE_DIMENSION = 200     # 最小宽/高（像素）
BLACKLIST_PATTERNS = re.compile(
    r'(logo|icon|avatar|badge|button|banner|ad[_\-]|pixel|tracker|'
    r'spacer|spinner|loading|arrow|close|menu|nav|thumb_\d|emoji|'
    r'favicon|sprite|social|share|like|follow)',
    re.IGNORECASE
)
BLACKLIST_DOMAINS = {
    'doubleclick.net', 'googlesyndication.com', 'googleadservices.com',
    'facebook.com', 'twitter.com', 'linkedin.com', 'analytics.',
    'pixel.', 'beacon.', 'track.', 'count.'
}

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
}


# ========== 图片提取（从页面 HTML）==========

def extract_images_from_url(url: str, page_title: str = "") -> List[Dict]:
    """从单个 URL 提取 og:image + 正文图片
    
    Args:
        url: 页面 URL
        page_title: 页面标题（用于图片描述）
    
    Returns:
        [{url, alt, source_url, source_title, type:'og'|'content', width, height}]
    """
    candidates = []
    
    try:
        resp = requests.get(url, headers={
            'User-Agent': HEADERS['User-Agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }, timeout=DOWNLOAD_TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        
        # 限制 HTML 大小（避免解析巨大页面）
        if len(resp.content) > 2 * 1024 * 1024:
            logger.debug(f"[image] 页面过大，跳过: {url}")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        seen_urls = set()
        
        # 1. 提取 og:image（最高优先级）
        og_tags = soup.find_all('meta', property='og:image')
        for tag in og_tags:
            img_url = tag.get('content', '').strip()
            if img_url:
                img_url = urljoin(url, img_url)
                if img_url not in seen_urls and _is_valid_image_url(img_url):
                    seen_urls.add(img_url)
                    candidates.append({
                        'url': img_url,
                        'alt': page_title or '封面图',
                        'source_url': url,
                        'source_title': page_title,
                        'type': 'og',
                        'width': 0, 'height': 0,  # 稍后填充
                    })
        
        # 2. 提取 twitter:image
        tw_tags = soup.find_all('meta', attrs={'name': 'twitter:image'})
        for tag in tw_tags:
            img_url = tag.get('content', '').strip()
            if img_url:
                img_url = urljoin(url, img_url)
                if img_url not in seen_urls and _is_valid_image_url(img_url):
                    seen_urls.add(img_url)
                    candidates.append({
                        'url': img_url,
                        'alt': page_title or '封面图',
                        'source_url': url,
                        'source_title': page_title,
                        'type': 'og',
                        'width': 0, 'height': 0,
                    })
        
        # 3. 提取正文 <img> 标签（Phase B）
        # 优先选择在 article/main/content 区域中的图片
        content_areas = soup.find_all(['article', 'main']) or [soup.find('body')]
        content_area = content_areas[0] if content_areas else soup
        
        if content_area:
            img_tags = content_area.find_all('img', src=True)
            for img in img_tags:
                if len(candidates) >= MAX_IMAGES_PER_PAGE:
                    break
                    
                img_url = img.get('src', '').strip()
                if not img_url or img_url.startswith('data:'):
                    continue
                    
                img_url = urljoin(url, img_url)
                if img_url in seen_urls or not _is_valid_image_url(img_url):
                    continue
                
                # 检查 HTML 属性中的尺寸提示
                width = _parse_dimension(img.get('width', ''))
                height = _parse_dimension(img.get('height', ''))
                
                # 跳过明显的小图标
                if width and width < MIN_IMAGE_DIMENSION and height and height < MIN_IMAGE_DIMENSION:
                    continue
                
                alt_text = img.get('alt', '').strip() or img.get('title', '').strip() or ''
                
                seen_urls.add(img_url)
                candidates.append({
                    'url': img_url,
                    'alt': alt_text or page_title or '内容图片',
                    'source_url': url,
                    'source_title': page_title,
                    'type': 'content',
                    'width': width or 0,
                    'height': height or 0,
                })
        
        logger.info(f"[image] 从 {urlparse(url).netloc} 提取 {len(candidates)} 张候选图片")
        
    except requests.RequestException as e:
        logger.debug(f"[image] 获取页面失败 {url}: {e}")
    except Exception as e:
        logger.debug(f"[image] 解析页面失败 {url}: {e}")
    
    return candidates


def extract_images_from_search_results(
    search_refs: List[str],
    max_pages: int = 8
) -> List[Dict]:
    """从搜索引用列表（Markdown 表格字符串）中并行提取图片
    
    Args:
        search_refs: all_search_references 列表，每个元素是 Markdown 表格
        max_pages: 最多访问的页面数
    
    Returns:
        去重后的候选图片列表
    """
    # 1. 从 Markdown 表格中解析 URL 和标题
    pages = _parse_urls_from_refs(search_refs)
    pages = pages[:max_pages]
    
    if not pages:
        logger.info("[image] 无搜索引用可提取图片")
        return []
    
    logger.info(f"[image] 开始从 {len(pages)} 个页面提取图片...")
    
    # 2. 并行提取
    all_candidates = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=min(len(pages), 6)) as executor:
        futures = {
            executor.submit(extract_images_from_url, p['url'], p['title']): p
            for p in pages
        }
        for future in as_completed(futures):
            if time.time() - start_time > TOTAL_TIMEOUT:
                logger.warning("[image] 图片提取总超时，中止剩余任务")
                break
            try:
                candidates = future.result(timeout=DOWNLOAD_TIMEOUT + 2)
                all_candidates.extend(candidates)
            except Exception as e:
                page = futures[future]
                logger.debug(f"[image] 提取失败 {page['url']}: {e}")
    
    # 3. 去重（基于 URL 哈希）
    seen = set()
    deduped = []
    for c in all_candidates:
        url_hash = hashlib.md5(c['url'].encode()).hexdigest()
        if url_hash not in seen:
            seen.add(url_hash)
            deduped.append(c)
    
    # 4. 排序：og > content，同类内按来源顺序
    deduped.sort(key=lambda x: (0 if x['type'] == 'og' else 1))
    
    deduped = deduped[:MAX_TOTAL_IMAGES]
    logger.info(f"[image] 共获取 {len(deduped)} 张候选图片（去重后）")
    
    return deduped


# ========== 图片下载与压缩 ==========

def download_and_encode_image(img_info: Dict) -> Optional[Dict]:
    """下载单张图片，压缩后编码为 Base64 Data URI
    
    Args:
        img_info: 候选图片 dict（含 url, alt, source_url 等）
    
    Returns:
        增强后的 dict（新增 data_uri, encoded_size），或 None（失败/不符合条件）
    """
    url = img_info['url']
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=DOWNLOAD_TIMEOUT, 
                          stream=True, allow_redirects=True)
        resp.raise_for_status()
        
        # 检查 Content-Type
        content_type = resp.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            logger.debug(f"[image] 非图片响应: {content_type} - {url}")
            return None
        
        # 检查大小
        content_length = int(resp.headers.get('Content-Length', 0))
        if content_length > MAX_DOWNLOAD_SIZE:
            logger.debug(f"[image] 图片过大 ({content_length} bytes): {url}")
            return None
        
        # 读取数据
        data = resp.content
        if len(data) < 1000:  # 太小的可能是占位符
            return None
        
        # 压缩图片
        compressed_data, mime_type, width, height = _compress_image(data)
        if not compressed_data:
            return None
        
        # 尺寸检查
        if width < MIN_IMAGE_DIMENSION and height < MIN_IMAGE_DIMENSION:
            logger.debug(f"[image] 图片太小 ({width}x{height}): {url}")
            return None
        
        # Base64 编码
        b64 = base64.b64encode(compressed_data).decode('ascii')
        data_uri = f"data:{mime_type};base64,{b64}"
        
        encoded_size = len(compressed_data)
        if encoded_size > MAX_ENCODED_SIZE:
            logger.debug(f"[image] 压缩后仍过大 ({encoded_size} bytes): {url}")
            return None
        
        result = dict(img_info)
        result.update({
            'data_uri': data_uri,
            'encoded_size': encoded_size,
            'width': width,
            'height': height,
            'mime_type': mime_type,
        })
        
        logger.debug(f"[image] ✅ 下载成功: {width}x{height}, {encoded_size//1024}KB - {urlparse(url).netloc}")
        return result
        
    except requests.RequestException as e:
        logger.debug(f"[image] 下载失败 {url}: {e}")
        return None
    except Exception as e:
        logger.debug(f"[image] 处理失败 {url}: {e}")
        return None


def build_image_pool(
    candidates: List[Dict],
    max_images: int = MAX_FINAL_IMAGES
) -> List[Dict]:
    """并行下载候选图片，构建最终图片池
    
    Args:
        candidates: extract_images_from_search_results 返回的候选列表
        max_images: 最终保留的图片数量上限
    
    Returns:
        包含 data_uri 的图片列表，按优先级排序
    """
    if not candidates:
        return []
    
    logger.info(f"[image] 开始下载 {len(candidates)} 张候选图片...")
    start_time = time.time()
    
    pool = []
    total_size = 0
    
    with ThreadPoolExecutor(max_workers=min(len(candidates), 6)) as executor:
        futures = {
            executor.submit(download_and_encode_image, c): c 
            for c in candidates
        }
        for future in as_completed(futures):
            if time.time() - start_time > TOTAL_TIMEOUT:
                logger.warning("[image] 下载总超时，中止")
                break
            
            try:
                result = future.result(timeout=DOWNLOAD_TIMEOUT + 2)
                if result:
                    # 检查总大小限制
                    if total_size + result['encoded_size'] > MAX_TOTAL_BASE64_SIZE:
                        logger.info(f"[image] 达到总大小限制 ({total_size//1024}KB)，停止添加")
                        break
                    
                    pool.append(result)
                    total_size += result['encoded_size']
                    
                    if len(pool) >= max_images:
                        break
            except Exception as e:
                logger.debug(f"[image] 处理异常: {e}")
    
    # 排序：og > content
    pool.sort(key=lambda x: (0 if x['type'] == 'og' else 1))
    pool = pool[:max_images]
    
    logger.info(f"[image] 图片池构建完成: {len(pool)} 张，总大小 {total_size//1024}KB")
    return pool


def format_image_pool_for_prompt(pool: List[Dict]) -> str:
    """将图片池格式化为 Reporter prompt 可用的文本
    
    Reporter LLM 不直接看到 base64，而是得到图片编号列表及描述信息。
    实际 base64 在 post-processing 阶段注入。
    
    Args:
        pool: build_image_pool 返回的图片列表
    
    Returns:
        描述性文本，供 Reporter 决定图片放置位置
    """
    if not pool:
        return ""
    
    lines = ["可用配图素材（请根据内容相关性选择合适的图片插入报告中，使用 IMG_N 标记）："]
    for i, img in enumerate(pool, 1):
        source_domain = urlparse(img['source_url']).netloc if img.get('source_url') else '未知'
        
        # 优先使用多模态分析结果
        description = img.get('description', '') or img.get('alt', '未知图片')
        category = img.get('category', '')
        relevance = img.get('relevance', 0)
        suggested = img.get('suggested_section', '')
        
        info_parts = [f"IMG_{i}:"]
        info_parts.append(f"[{description[:80]}]")
        info_parts.append(f"({img['width']}x{img['height']}")
        if category:
            info_parts[-1] += f", {category}"
        info_parts[-1] += f", 来源: {source_domain})"
        if relevance:
            info_parts.append(f"相关度: {relevance}/5")
        if suggested:
            info_parts.append(f"建议放置: {suggested}")
        
        lines.append("  " + " ".join(info_parts))
    
    lines.append("")
    lines.append("图片使用说明：")
    lines.append("- 在报告HTML中需要插入图片的位置，使用标记：<!-- IMG_N --> （N为图片编号）")
    lines.append("- 每张图片最多使用一次，选择与上下文最相关的图片")
    lines.append("- 优先使用相关度 4-5 的图片，相关度 3 的可选用")
    lines.append("- 参考「建议放置」位置，将图片放在对应章节")
    lines.append("- 推荐使用 3-6 张图片，不必全部使用")
    lines.append("- 图片标记会在后处理阶段替换为实际的 <img> 标签")
    
    return "\n".join(lines)


def inject_images_into_html(html: str, pool: List[Dict]) -> str:
    """将 <!-- IMG_N --> 标记替换为实际的 <img> 标签（含 Base64 Data URI）
    
    Args:
        html: Reporter 生成的 HTML
        pool: 图片池列表
    
    Returns:
        注入图片后的 HTML
    """
    if not pool:
        return html
    
    injected_count = 0
    for i, img in enumerate(pool, 1):
        marker = f"<!-- IMG_{i} -->"
        if marker in html:
            alt = img['alt'].replace('"', '&quot;')[:100]
            source = img.get('source_title', '').replace('"', '&quot;')[:60]
            source_url = img.get('source_url', '#')
            
            img_tag = (
                f'<figure style="margin: 20px 0; text-align: center; page-break-inside: avoid;">'
                f'<img src="{img["data_uri"]}" alt="{alt}" '
                f'style="max-width: 100%; height: auto; border-radius: 8px; '
                f'box-shadow: 0 2px 8px rgba(0,0,0,0.1);" loading="lazy">'
                f'<figcaption style="margin-top: 8px; font-size: 12px; color: #64748b;">'
                f'{alt}'
                f'{f" — <a href=\"{source_url}\" target=\"_blank\" style=\"color: #94a3b8;\">{source}</a>" if source else ""}'
                f'</figcaption>'
                f'</figure>'
            )
            html = html.replace(marker, img_tag, 1)
            injected_count += 1
    
    if injected_count > 0:
        logger.info(f"[image] 已注入 {injected_count} 张图片到报告中")
    
    # 清除未使用的标记
    html = re.sub(r'<!-- IMG_\d+ -->', '', html)
    
    return html


# ========== 内部辅助函数 ==========

def _is_valid_image_url(url: str) -> bool:
    """检查图片 URL 是否有效（排除广告、追踪像素等）"""
    if not url or not url.startswith('http'):
        return False
    
    parsed = urlparse(url)
    
    # 域名黑名单
    for bd in BLACKLIST_DOMAINS:
        if bd in parsed.netloc:
            return False
    
    # 路径黑名单
    path_lower = parsed.path.lower()
    if BLACKLIST_PATTERNS.search(path_lower):
        return False
    
    # 扩展名检查（允许无扩展名，因为 CDN 通常不带扩展名）
    valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg', '.bmp'}
    ext = parsed.path.rsplit('.', 1)[-1].lower() if '.' in parsed.path.split('/')[-1] else ''
    if ext and f'.{ext}' not in valid_exts:
        return False
    
    return True


def _parse_dimension(value: str) -> int:
    """解析 HTML width/height 属性值"""
    if not value:
        return 0
    try:
        # 去除 px, %, em 等
        num = re.match(r'(\d+)', str(value))
        return int(num.group(1)) if num else 0
    except (ValueError, AttributeError):
        return 0


def _compress_image(data: bytes) -> Tuple[Optional[bytes], str, int, int]:
    """压缩图片到目标大小
    
    Returns:
        (compressed_bytes, mime_type, width, height) 或 (None, '', 0, 0)
    """
    try:
        from PIL import Image
        
        img = Image.open(io.BytesIO(data))
        
        # 跳过动画 GIF
        if getattr(img, 'is_animated', False):
            return None, '', 0, 0
        
        width, height = img.size
        
        # 转换模式
        if img.mode in ('RGBA', 'LA', 'PA'):
            # 有透明通道，保存为 PNG
            if width > MAX_WIDTH:
                ratio = MAX_WIDTH / width
                height = int(height * ratio)
                width = MAX_WIDTH
                img = img.resize((width, height), Image.LANCZOS)
            
            buf = io.BytesIO()
            img.save(buf, format='PNG', optimize=True)
            return buf.getvalue(), 'image/png', width, height
        
        # 其他模式转 RGB → JPEG
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 缩放
        if width > MAX_WIDTH:
            ratio = MAX_WIDTH / width
            height = int(height * ratio)
            width = MAX_WIDTH
            img = img.resize((width, height), Image.LANCZOS)
        
        # JPEG 压缩
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        compressed = buf.getvalue()
        
        # 如果还是太大，进一步降低质量
        if len(compressed) > MAX_ENCODED_SIZE:
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=50, optimize=True)
            compressed = buf.getvalue()
        
        return compressed, 'image/jpeg', width, height
        
    except ImportError:
        logger.warning("[image] PIL/Pillow 未安装，无法压缩图片")
        return None, '', 0, 0
    except Exception as e:
        logger.debug(f"[image] 压缩失败: {e}")
        return None, '', 0, 0


def _parse_urls_from_refs(search_refs: List[str]) -> List[Dict]:
    """从搜索引用 Markdown 表格中解析 URL 和标题
    
    Returns:
        [{"url": "...", "title": "..."}]
    """
    pages = []
    seen_urls = set()
    
    # 匹配 Markdown 链接格式：[title](url)
    link_pattern = re.compile(r'\[([^\]]+)\]\((https?://[^)]+)\)')
    
    for ref_text in search_refs:
        for match in link_pattern.finditer(ref_text):
            title = match.group(1).strip()
            url = match.group(2).strip()
            
            if url not in seen_urls:
                seen_urls.add(url)
                pages.append({'url': url, 'title': title})
    
    return pages
