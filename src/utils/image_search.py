"""
独立图片搜索 API：Google Images API + Unsplash API

Phase C：根据报告章节关键词从专业图库搜索高质量配图。
与搜索阶段提取（Phase A+B）互补。
"""

import time
from typing import Dict, List, Optional
from urllib.parse import urlencode, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# ========== 常量 ==========

SEARCH_TIMEOUT = 10  # 单次 API 请求超时
MAX_RESULTS_PER_QUERY = 3  # 每个关键词的最大结果数
MAX_TOTAL_RESULTS = 10  # 总上限


# ========== Google Custom Search - Image Mode ==========

def google_image_search(
    query: str, 
    api_key: str, 
    search_engine_id: str, 
    max_results: int = MAX_RESULTS_PER_QUERY,
    safe: str = "active"
) -> List[Dict]:
    """使用 Google Custom Search API 搜索图片
    
    需要在 Google Cloud Console 创建自定义搜索引擎并启用图片搜索。
    
    Args:
        query: 搜索关键词
        api_key: Google API Key
        search_engine_id: 自定义搜索引擎 ID
        max_results: 最大结果数
        safe: 安全搜索级别 (active/moderate/off)
    
    Returns:
        [{"url": 图片URL, "alt": 描述, "source_url": 来源页面, 
          "source_title": 来源标题, "width": int, "height": int, "type": "google_image"}]
    """
    if not api_key or not search_engine_id:
        return []
    
    results = []
    try:
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'searchType': 'image',
            'num': min(max_results, 10),
            'safe': safe,
            'imgSize': 'large',  # 优先大图
            'imgType': 'photo',  # 优先照片类型
        }
        
        url = f"https://www.googleapis.com/customsearch/v1?{urlencode(params)}"
        resp = requests.get(url, timeout=SEARCH_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        for item in data.get('items', [])[:max_results]:
            img_info = item.get('image', {})
            results.append({
                'url': item.get('link', ''),
                'alt': item.get('title', item.get('snippet', query)),
                'source_url': img_info.get('contextLink', ''),
                'source_title': item.get('displayLink', ''),
                'width': img_info.get('width', 0),
                'height': img_info.get('height', 0),
                'type': 'google_image',
            })
        
        logger.info(f"[image_search] Google Images: '{query}' → {len(results)} 结果")
        
    except requests.RequestException as e:
        logger.warning(f"[image_search] Google Images API 失败: {e}")
    except Exception as e:
        logger.warning(f"[image_search] Google Images 解析失败: {e}")
    
    return results


# ========== Unsplash API ==========

def unsplash_search(
    query: str,
    access_key: str,
    max_results: int = MAX_RESULTS_PER_QUERY,
    orientation: str = "landscape"
) -> List[Dict]:
    """使用 Unsplash API 搜索高质量免费图片
    
    免费额度：50 次/小时（Demo），5000 次/小时（Production）
    
    Args:
        query: 搜索关键词
        access_key: Unsplash Access Key
        max_results: 最大结果数
        orientation: 方向 (landscape/portrait/squarish)
    
    Returns:
        [{"url": 图片URL, "alt": 描述, "source_url": 来源页面, 
          "source_title": 作者, "width": int, "height": int, 
          "type": "unsplash", "attribution": 归属信息}]
    """
    if not access_key:
        return []
    
    results = []
    try:
        params = {
            'query': query,
            'per_page': min(max_results, 10),
            'orientation': orientation,
            'content_filter': 'high',  # 高质量
        }
        
        headers = {
            'Authorization': f'Client-ID {access_key}',
            'Accept-Version': 'v1',
        }
        
        url = f"https://api.unsplash.com/search/photos?{urlencode(params)}"
        resp = requests.get(url, headers=headers, timeout=SEARCH_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        for photo in data.get('results', [])[:max_results]:
            urls = photo.get('urls', {})
            user = photo.get('user', {})
            
            # 使用 regular 尺寸（~1080px 宽，适合报告）
            img_url = urls.get('regular') or urls.get('small') or urls.get('raw', '')
            
            results.append({
                'url': img_url,
                'alt': photo.get('alt_description') or photo.get('description') or query,
                'source_url': photo.get('links', {}).get('html', ''),
                'source_title': f"Photo by {user.get('name', 'Unknown')} on Unsplash",
                'width': photo.get('width', 0),
                'height': photo.get('height', 0),
                'type': 'unsplash',
                'attribution': f"Photo by {user.get('name', 'Unknown')} on Unsplash",
            })
        
        logger.info(f"[image_search] Unsplash: '{query}' → {len(results)} 结果")
        
    except requests.RequestException as e:
        logger.warning(f"[image_search] Unsplash API 失败: {e}")
    except Exception as e:
        logger.warning(f"[image_search] Unsplash 解析失败: {e}")
    
    return results


# ========== Pexels API ==========

def pexels_search(
    query: str,
    api_key: str,
    max_results: int = MAX_RESULTS_PER_QUERY,
    orientation: str = "landscape"
) -> List[Dict]:
    """使用 Pexels API 搜索免费图片
    
    Args:
        query: 搜索关键词
        api_key: Pexels API Key
        max_results: 最大结果数
        orientation: 方向 (landscape/portrait/square)
    
    Returns:
        与其他搜索函数相同格式的结果列表
    """
    if not api_key:
        return []
    
    results = []
    try:
        params = {
            'query': query,
            'per_page': min(max_results, 10),
            'orientation': orientation,
        }
        
        headers = {
            'Authorization': api_key,
        }
        
        url = f"https://api.pexels.com/v1/search?{urlencode(params)}"
        resp = requests.get(url, headers=headers, timeout=SEARCH_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        for photo in data.get('photos', [])[:max_results]:
            src = photo.get('src', {})
            
            results.append({
                'url': src.get('large') or src.get('medium') or src.get('original', ''),
                'alt': photo.get('alt') or query,
                'source_url': photo.get('url', ''),
                'source_title': f"Photo by {photo.get('photographer', 'Unknown')} on Pexels",
                'width': photo.get('width', 0),
                'height': photo.get('height', 0),
                'type': 'pexels',
                'attribution': f"Photo by {photo.get('photographer', 'Unknown')} on Pexels",
            })
        
        logger.info(f"[image_search] Pexels: '{query}' → {len(results)} 结果")
        
    except requests.RequestException as e:
        logger.warning(f"[image_search] Pexels API 失败: {e}")
    except Exception as e:
        logger.warning(f"[image_search] Pexels 解析失败: {e}")
    
    return results


# ========== 统一搜索入口 ==========

def search_images_for_report(
    keywords: List[str],
    config: Optional[Dict] = None
) -> List[Dict]:
    """根据关键词列表搜索配图（自动使用可用的 API）
    
    Args:
        keywords: 关键词列表（通常从报告章节提取）
        config: 配置字典，可选键：
            - google_api_key, google_search_engine_id
            - unsplash_access_key
            - pexels_api_key
    
    Returns:
        候选图片列表（与 image_utils 中的格式兼容）
    """
    if not keywords or not config:
        return []
    
    google_key = config.get('google_api_key', '')
    google_cx = config.get('google_search_engine_id', '')
    unsplash_key = config.get('unsplash_access_key', '')
    pexels_key = config.get('pexels_api_key', '')
    
    if not any([google_key and google_cx, unsplash_key, pexels_key]):
        logger.info("[image_search] 无可用的图片搜索 API Key")
        return []
    
    all_results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=min(len(keywords) * 2, 8)) as executor:
        futures = []
        
        for kw in keywords[:5]:  # 最多 5 个关键词
            if unsplash_key:
                futures.append(executor.submit(unsplash_search, kw, unsplash_key))
            if pexels_key:
                futures.append(executor.submit(pexels_search, kw, pexels_key))
            if google_key and google_cx:
                futures.append(executor.submit(google_image_search, kw, google_key, google_cx))
        
        for future in as_completed(futures):
            if time.time() - start_time > 30:
                logger.warning("[image_search] 图片搜索超时，中止")
                break
            try:
                results = future.result(timeout=SEARCH_TIMEOUT + 2)
                all_results.extend(results)
            except Exception as e:
                logger.debug(f"[image_search] 搜索任务失败: {e}")
    
    # 去重
    seen = set()
    deduped = []
    for r in all_results:
        if r['url'] not in seen:
            seen.add(r['url'])
            deduped.append(r)
    
    deduped = deduped[:MAX_TOTAL_RESULTS]
    logger.info(f"[image_search] API 搜索共获取 {len(deduped)} 张候选图片")
    
    return deduped


def extract_keywords_from_report_data(final_data: Dict, max_keywords: int = 5) -> List[str]:
    """从报告数据中提取关键词（用于图片搜索）
    
    Args:
        final_data: 传给 reporter 的 final_data 字典
        max_keywords: 最大关键词数
    
    Returns:
        关键词列表
    """
    keywords = []
    
    # 1. 从议题提取
    issue = final_data.get('issue', '')
    if issue:
        keywords.append(issue[:50])
    
    # 2. 从 decomposition 的 key_questions 提取
    decomposition = final_data.get('decomposition', {})
    if isinstance(decomposition, dict):
        for kq in decomposition.get('key_questions', [])[:3]:
            if isinstance(kq, dict):
                q = kq.get('question', '')
            else:
                q = str(kq)
            if q:
                keywords.append(q[:50])
    
    # 3. 从 report_design 的 sections 提取
    if isinstance(decomposition, dict):
        report_design = decomposition.get('report_design', {})
        if isinstance(report_design, dict):
            for section in report_design.get('sections', [])[:3]:
                if isinstance(section, dict):
                    title = section.get('title', '')
                    if title:
                        keywords.append(title[:50])
    
    return keywords[:max_keywords]
