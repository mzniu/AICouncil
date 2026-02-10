"""
Skill Auto-Discovery — 议事启动时自动从技能市场搜索并导入议题相关技能

在 run_full_cycle() 创建 agent chains 之前调用，用议题文本语义搜索 SkillsMP，
自动导入高相关度技能并设 applicable_roles 为全角色，使所有角色在本次议事中受益。
"""
import time
import threading
from typing import Dict, List, Optional, Any

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 所有参与议事的角色中文名（与 YAML display_name 中的中文部分保持一致）
ALL_DISCUSSION_ROLES = ['议长', '策论家', '监察官', '质疑官', '记录员', '报告审核官']


def _ensure_app_context(app_context=None):
    """确保 Flask app context 可用，返回已进入的 context 或 None"""
    if app_context is not None:
        return app_context.__enter__()
    try:
        from flask import current_app
        current_app._get_current_object()  # 测试是否已在 context 内
        return None  # 已在 context 内，无需额外操作
    except RuntimeError:
        pass
    try:
        from src.web.app import app
        ctx = app.app_context()
        ctx.__enter__()
        return ctx
    except Exception as e:
        logger.debug(f"[auto_discovery] Could not create app context: {e}")
        return None

# 默认配置
DEFAULT_SCORE_THRESHOLD = 0.45   # AI 搜索相关度阈值
DEFAULT_MAX_IMPORT = 3           # 单次最多自动导入数量
DEFAULT_USER_WAIT_SECONDS = 8    # 等待用户确认/取消的超时时间（秒）


def discover_skills_for_issue(
    issue: str,
    tenant_id: Optional[int] = None,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    max_import: int = DEFAULT_MAX_IMPORT,
    user_wait_seconds: float = DEFAULT_USER_WAIT_SECONDS,
    send_event_fn=None,
    app_context=None,
) -> List[Dict[str, Any]]:
    """
    根据议题自动搜索并导入相关技能

    Args:
        issue: 议题文本
        tenant_id: 租户ID
        score_threshold: AI 搜索相关度阈值
        max_import: 最多导入几个技能
        user_wait_seconds: 等待用户确认的超时秒数（0=不等待，立即导入）
        send_event_fn: 向前端推送事件的回调 (event_type, **kwargs)
        app_context: Flask app context（用于在线程/子进程中操作数据库）

    Returns:
        已导入的技能列表 [{"name": ..., "description": ..., "score": ...}, ...]
    """
    if not issue or not issue.strip():
        return []

    # 检查 SkillsMP API Key
    from src import config_manager as config
    skillsmp_key = getattr(config, 'SKILLSMP_API_KEY', None)
    if not skillsmp_key:
        logger.info("[auto_discovery] No SKILLSMP_API_KEY configured, skipping")
        return []

    _send = send_event_fn or _noop_send

    _send("system_status", message="🔍 正在从技能市场搜索议题相关技能...")
    logger.info(f"[auto_discovery] Searching skills for issue: {issue[:80]}...")

    try:
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient(timeout=12)
        result = client._search_skillsmp_ai(issue)
    except Exception as e:
        logger.warning(f"[auto_discovery] SkillsMP AI search failed: {e}")
        _send("system_status", message="⚠️ 技能市场搜索超时，继续议事...")
        return []

    if not result or not result.get('items'):
        logger.info("[auto_discovery] No relevant skills found")
        _send("system_status", message="📋 未找到高度相关的技能，使用现有技能库")
        return []

    # 过滤：相关度 > 阈值
    candidates = [
        item for item in result['items']
        if item.get('score', 0) >= score_threshold
    ][:max_import]

    if not candidates:
        logger.info(f"[auto_discovery] No skills above threshold {score_threshold}")
        _send("system_status", message="📋 未找到高度相关的技能，使用现有技能库")
        return []

    # 去重：排除已存在的技能
    new_candidates = _filter_existing_skills(candidates, tenant_id, app_context)

    if not new_candidates:
        logger.info("[auto_discovery] All candidate skills already exist")
        names = [c['name'] for c in candidates]
        _send("system_status", message=f"✅ 已有相关技能：{', '.join(names)}")
        return []

    # 向前端推送候选列表
    names_str = ', '.join(f"{c['name']}({c.get('score', 0):.0%})" for c in new_candidates)
    _send("skill_discovery",
           message=f"🎯 发现 {len(new_candidates)} 个相关技能：{names_str}",
           skills=[{
               'name': c['name'],
               'description': c.get('description', ''),
               'score': c.get('score', 0),
               'author': c.get('author', ''),
           } for c in new_candidates],
           wait_seconds=user_wait_seconds)

    # 等待用户确认/取消（超时自动继续）
    if user_wait_seconds > 0:
        cancelled = _wait_for_user_response(user_wait_seconds)
        if cancelled:
            logger.info("[auto_discovery] User cancelled skill import")
            _send("system_status", message="⏭️ 用户取消导入，继续议事...")
            return []

    # 执行导入
    imported = []
    for candidate in new_candidates:
        try:
            skill = _import_single_skill(candidate, tenant_id, client, app_context)
            if skill:
                imported.append(skill)
                logger.info(f"[auto_discovery] Imported: {skill['name']} (score={candidate.get('score', 0):.2f})")
        except Exception as e:
            logger.warning(f"[auto_discovery] Failed to import {candidate['name']}: {e}")

    if imported:
        names = [s['name'] for s in imported]
        _send("system_status",
               message=f"✅ 已自动导入 {len(imported)} 个技能：{', '.join(names)}")
    else:
        _send("system_status", message="📋 技能导入未成功，使用现有技能库")

    return imported


def _filter_existing_skills(
    candidates: List[Dict],
    tenant_id: Optional[int],
    app_context=None,
) -> List[Dict]:
    """排除 tenant 中已存在同名的技能"""
    if tenant_id is None:
        return candidates

    try:
        from src.repositories.skill_repository import SkillRepository

        ctx = _ensure_app_context(app_context)
        new = []
        for c in candidates:
            name = c.get('name', '')
            if not name:
                continue
            existing = SkillRepository.get_skill_by_name(name, tenant_id)
            if existing is None:
                new.append(c)
            else:
                logger.debug(f"[auto_discovery] Skill '{name}' already exists, skipping")
        if ctx:
            ctx.__exit__(None, None, None)
        return new
    except Exception as e:
        logger.warning(f"[auto_discovery] Failed to check existing skills: {e}")
        return candidates


def _import_single_skill(
    candidate: Dict,
    tenant_id: Optional[int],
    client,
    app_context=None,
) -> Optional[Dict]:
    """
    下载并保存单个技能到数据库

    Returns:
        {"name": ..., "description": ..., "score": ...} or None
    """
    github_url = candidate.get('github_url', '')
    if not github_url:
        logger.warning(f"[auto_discovery] No github_url for {candidate.get('name')}")
        return None

    # 下载 SKILL.md
    result = client.import_skill(github_url)
    if not result.get('success'):
        logger.warning(f"[auto_discovery] Download failed: {result.get('error')}")
        return None

    skill_md = result['skill_md']
    skill_data = result['skill_data']

    # 安全扫描
    from src.skills.security_scanner import scan_skill_content
    scan_result = scan_skill_content(skill_md, strict_mode=False)
    if not scan_result.is_safe:
        logger.warning(f"[auto_discovery] Security check failed for {candidate['name']}: "
                        f"{scan_result.issues}")
        return None

    # 如果无 tenant_id，无法持久化
    ctx = _ensure_app_context(app_context)
    if tenant_id is None:
        logger.info(f"[auto_discovery] No tenant_id, skill '{candidate['name']}' loaded but not persisted")
        if ctx:
            ctx.__exit__(None, None, None)
        return {
            'name': candidate.get('name', ''),
            'description': candidate.get('description', ''),
            'score': candidate.get('score', 0),
            'content': skill_md,
        }

    # 保存到数据库
    from src.repositories.skill_repository import SkillRepository

    name = skill_data.get('name') or candidate.get('name', 'imported-skill')
    display_name = skill_data.get('displayName') or candidate.get('displayName', name)

    skill_obj = SkillRepository.create_skill(
        tenant_id=tenant_id,
        name=name,
        display_name=display_name,
        content=skill_md,
        version=skill_data.get('version', '1.0.0'),
        category=skill_data.get('category', 'auto-discovered'),
        tags=skill_data.get('tags', []) if isinstance(skill_data.get('tags'), list) else [],
        description=skill_data.get('description') or candidate.get('description', ''),
        applicable_roles=ALL_DISCUSSION_ROLES,
        author=candidate.get('author', ''),
        source=github_url,
    )

    if skill_obj is None:
        logger.warning(f"[auto_discovery] DB save failed for {name}")
        return None

    # 自动订阅
    try:
        SkillRepository.subscribe_skill(tenant_id, skill_obj.id)
    except Exception as e:
        logger.warning(f"[auto_discovery] Auto-subscribe failed: {e}")

    # 提取属性后再关闭 context（关闭后 ORM 对象不可访问）
    skill_id = skill_obj.id
    if ctx:
        ctx.__exit__(None, None, None)

    return {
        'name': name,
        'display_name': display_name,
        'description': skill_data.get('description', ''),
        'score': candidate.get('score', 0),
        'skill_id': skill_id,
    }


# ===== User Interaction Helpers =====

# 简单的全局标志位（同一进程内生效）
_cancel_flag = threading.Event()


def cancel_skill_discovery():
    """前端调用取消技能自动导入"""
    _cancel_flag.set()


def _wait_for_user_response(seconds: float) -> bool:
    """
    等待用户确认。返回 True = 已取消, False = 超时/确认继续
    """
    _cancel_flag.clear()
    cancelled = _cancel_flag.wait(timeout=seconds)
    return cancelled


def _noop_send(event_type: str, **kwargs):
    """空操作发送函数"""
    pass
