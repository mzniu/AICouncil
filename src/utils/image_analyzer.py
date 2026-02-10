"""
多模态模型图片分析器

使用视觉模型（Gemini Flash / Qwen-VL / GPT-4V）批量分析图片：
- 生成中文内容描述
- 判断图片类别（图表/照片/截图/示意图/数据可视化/流程图）
- 评估与议题的相关度 (1-5)
- 建议在报告中的放置位置

单次批量调用，降低成本和延迟。
"""

import base64
import io
import json
import re
from typing import Dict, List, Optional

import requests

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# ========== 常量 ==========

ANALYSIS_TIMEOUT = 30       # API 调用超时
MAX_IMAGES_PER_BATCH = 10   # 单次分析最大图片数
THUMBNAIL_MAX_DIM = 512     # 分析用缩略图最大边（降低 token 成本）
MIN_RELEVANCE = 3           # 最低相关度阈值


# ========== 分析 Prompt ==========

ANALYSIS_PROMPT = """你是一个图片内容分析专家。请分析以下{count}张图片，它们来自与议题"{issue}"相关的网页。

对每张图片，请**严格仅输出JSON**（无任何其他文字），格式为数组：
[
  {{
    "index": 1,
    "description": "中文描述，1-2句话，说明图片展示的内容",
    "category": "图表|照片|截图|示意图|数据可视化|流程图|信息图|其他",
    "relevance": 3,
    "suggested_section": "建议放置的报告章节名称"
  }},
  ...
]

评分标准：
- relevance 1: 与议题完全无关（广告、装饰图）
- relevance 2: 略有关联但信息量低
- relevance 3: 有一定相关性，可作为辅助配图
- relevance 4: 高度相关，能增强报告说服力
- relevance 5: 核心图表/数据，对报告至关重要

注意：
- description 必须用中文
- category 从给定选项中选择最接近的
- suggested_section 根据图片内容推断最适合的报告章节
- 如果图片是广告、网站logo、UI元素，relevance设为1
- 仅输出JSON数组，不要有任何前缀后缀文字
"""


def _make_thumbnail(image_data: bytes, max_dim: int = THUMBNAIL_MAX_DIM) -> Optional[str]:
    """将原图压缩为缩略图并转 base64（用于多模态 API）
    
    Returns:
        base64 编码字符串（不含 data: 前缀），或 None
    """
    try:
        from PIL import Image
        
        img = Image.open(io.BytesIO(image_data))
        
        # 跳过动画 GIF
        if getattr(img, 'is_animated', False):
            return None
        
        w, h = img.size
        if max(w, h) > max_dim:
            ratio = max_dim / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        
        if img.mode in ('RGBA', 'LA', 'PA'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=70, optimize=True)
        return base64.b64encode(buf.getvalue()).decode('ascii')
        
    except Exception as e:
        logger.debug(f"[analyzer] 缩略图生成失败: {e}")
        return None


def _download_for_analysis(url: str) -> Optional[bytes]:
    """下载图片原始数据（用于分析，不做最终压缩）"""
    try:
        resp = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/*,*/*;q=0.8',
        }, timeout=8, allow_redirects=True)
        resp.raise_for_status()
        
        ct = resp.headers.get('Content-Type', '')
        if 'image' not in ct and 'octet' not in ct:
            return None
        
        if len(resp.content) < 500 or len(resp.content) > 10 * 1024 * 1024:
            return None
        
        return resp.content
    except Exception:
        return None


def _call_openai_compatible_vision(
    thumbnails: List[Dict],
    issue: str,
    api_key: str,
    base_url: str,
    model: str,
) -> Optional[List[Dict]]:
    """调用 OpenAI 兼容 API（OpenRouter/OpenAI/Aliyun）的 vision 能力
    
    Args:
        thumbnails: [{"index": int, "base64": str, "alt": str}]
        issue: 议题文本
        api_key: API Key
        base_url: API Base URL
        model: 模型名称
    
    Returns:
        [{"index", "description", "category", "relevance", "suggested_section"}]
    """
    # 构建消息
    content_parts = [
        {"type": "text", "text": ANALYSIS_PROMPT.format(count=len(thumbnails), issue=issue[:200])}
    ]
    
    for t in thumbnails:
        content_parts.append({
            "type": "text",
            "text": f"\n--- 图片 {t['index']} (alt: {t.get('alt', '无')[:60]}) ---"
        })
        content_parts.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{t['base64']}",
                "detail": "low",  # 低细节模式，省 token
            }
        })
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": content_parts}
        ],
        "max_tokens": 2000,
        "temperature": 0.3,
    }
    
    url = f"{base_url.rstrip('/')}/chat/completions"
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=ANALYSIS_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        text = data['choices'][0]['message']['content']
        
        # 清理 JSON
        text = text.strip()
        if text.startswith('```'):
            text = re.sub(r'^```\w*\n?', '', text)
            text = re.sub(r'\n?```$', '', text)
            text = text.strip()
        
        # 提取 JSON 数组
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            text = match.group(0)
        
        results = json.loads(text)
        if isinstance(results, list):
            logger.info(f"[analyzer] 多模态分析完成: {len(results)} 张图片")
            return results
        
    except json.JSONDecodeError as e:
        logger.warning(f"[analyzer] JSON 解析失败: {e}")
    except requests.RequestException as e:
        logger.warning(f"[analyzer] API 调用失败: {e}")
    except Exception as e:
        logger.warning(f"[analyzer] 分析异常: {e}")
    
    return None


def analyze_images(
    candidates: List[Dict],
    issue: str,
    model_config: Optional[Dict] = None,
) -> List[Dict]:
    """批量分析候选图片，返回带描述和相关度的增强结果
    
    Args:
        candidates: 候选图片列表（含 url, alt 等）
        issue: 议题文本
        model_config: 视觉模型配置 {"api_key", "base_url", "model"}
                      如不提供，自动从配置中选择
    
    Returns:
        增强后的候选列表（新增 description, category, relevance, suggested_section）
        仅返回 relevance >= MIN_RELEVANCE 的图片
    """
    if not candidates or not issue:
        return candidates  # 无法分析则原样返回
    
    # 确定视觉模型配置
    if not model_config:
        model_config = _get_vision_model_config()
    
    if not model_config or not model_config.get('api_key'):
        logger.info("[analyzer] 无可用视觉模型，跳过多模态分析")
        # 返回原始候选（不过滤，让 reporter 自行判断）
        for c in candidates:
            c.setdefault('description', c.get('alt', ''))
            c.setdefault('category', '未知')
            c.setdefault('relevance', 3)
            c.setdefault('suggested_section', '')
        return candidates
    
    # 下载并生成缩略图
    thumbnails = []
    index_map = {}  # index -> candidate_index
    
    for i, c in enumerate(candidates[:MAX_IMAGES_PER_BATCH]):
        img_data = _download_for_analysis(c['url'])
        if not img_data:
            continue
        
        b64 = _make_thumbnail(img_data)
        if not b64:
            continue
        
        idx = len(thumbnails) + 1
        thumbnails.append({
            'index': idx,
            'base64': b64,
            'alt': c.get('alt', ''),
        })
        index_map[idx] = i
    
    if not thumbnails:
        logger.info("[analyzer] 无可分析的图片缩略图")
        return candidates
    
    logger.info(f"[analyzer] 准备分析 {len(thumbnails)} 张图片...")
    
    # 调用多模态模型
    results = _call_openai_compatible_vision(
        thumbnails,
        issue,
        model_config['api_key'],
        model_config['base_url'],
        model_config['model'],
    )
    
    if not results:
        logger.warning("[analyzer] 多模态分析未返回结果，保留原始候选")
        for c in candidates:
            c.setdefault('description', c.get('alt', ''))
            c.setdefault('category', '未知')
            c.setdefault('relevance', 3)
            c.setdefault('suggested_section', '')
        return candidates
    
    # 合并分析结果到候选
    for r in results:
        idx = r.get('index')
        if idx and idx in index_map:
            ci = index_map[idx]
            candidates[ci]['description'] = r.get('description', candidates[ci].get('alt', ''))
            candidates[ci]['category'] = r.get('category', '未知')
            candidates[ci]['relevance'] = r.get('relevance', 3)
            candidates[ci]['suggested_section'] = r.get('suggested_section', '')
    
    # 为未分析到的候选设置默认值
    for c in candidates:
        c.setdefault('description', c.get('alt', ''))
        c.setdefault('category', '未知')
        c.setdefault('relevance', 3)
        c.setdefault('suggested_section', '')
    
    # 过滤低相关度
    filtered = [c for c in candidates if c.get('relevance', 0) >= MIN_RELEVANCE]
    
    # 按相关度降序排序
    filtered.sort(key=lambda x: (-x.get('relevance', 0), 0 if x['type'] == 'og' else 1))
    
    removed = len(candidates) - len(filtered)
    if removed > 0:
        logger.info(f"[analyzer] 过滤掉 {removed} 张低相关度图片（relevance < {MIN_RELEVANCE}）")
    logger.info(f"[analyzer] 最终保留 {len(filtered)} 张相关图片")
    
    return filtered


def _get_vision_model_config() -> Optional[Dict]:
    """从系统配置中自动选择视觉模型
    
    优先级：
    1. IMAGE_ANALYSIS_MODEL 专用配置
    2. OpenRouter（默认 Gemini Flash，免费且支持 vision）
    3. Aliyun（Qwen-VL）
    4. OpenAI（GPT-4V）
    """
    try:
        from src.config_manager import get_config
        
        # 1. 专用配置
        dedicated_model = get_config('IMAGE_ANALYSIS_MODEL', '')
        dedicated_key = get_config('IMAGE_ANALYSIS_API_KEY', '')
        dedicated_url = get_config('IMAGE_ANALYSIS_BASE_URL', '')
        
        if dedicated_model and dedicated_key and dedicated_url:
            return {
                'model': dedicated_model,
                'api_key': dedicated_key,
                'base_url': dedicated_url,
            }
        
        # 2. OpenRouter（推荐：Gemini Flash 免费）
        or_key = get_config('OPENROUTER_API_KEY', '')
        if or_key:
            return {
                'model': get_config('IMAGE_ANALYSIS_MODEL', '') or 'google/gemini-2.0-flash-exp:free',
                'api_key': or_key,
                'base_url': get_config('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
            }
        
        # 3. Aliyun（Qwen-VL）
        ali_key = get_config('ALIYUN_API_KEY', '')
        if ali_key:
            return {
                'model': 'qwen-vl-max',
                'api_key': ali_key,
                'base_url': get_config('ALIYUN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
            }
        
        # 4. OpenAI
        oai_key = get_config('OPENAI_API_KEY', '')
        if oai_key:
            return {
                'model': 'gpt-4o-mini',
                'api_key': oai_key,
                'base_url': get_config('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
            }
        
    except Exception as e:
        logger.debug(f"[analyzer] 获取视觉模型配置失败: {e}")
    
    return None
