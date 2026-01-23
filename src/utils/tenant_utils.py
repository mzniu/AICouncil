"""
租户管理工具函数
"""
from src.models import db, Tenant
from src.utils.logger import logger


def get_or_create_default_tenant() -> Tenant:
    """
    获取或创建默认租户
    
    Returns:
        Tenant: 默认租户对象
    """
    default_tenant = Tenant.query.filter_by(name="默认租户").first()
    
    if not default_tenant:
        default_tenant = Tenant(
            name="默认租户",
            quota_config={
                "max_sessions": 1000,
                "max_users": 100,
                "max_skills": 50,
                "description": "系统默认租户，用于独立用户"
            },
            is_active=True
        )
        db.session.add(default_tenant)
        db.session.flush()  # 获取tenant.id但不提交事务
        logger.info(f"✅ 创建默认租户: ID={default_tenant.id}")
    
    return default_tenant


def ensure_default_tenant() -> int:
    """
    确保默认租户存在并返回其ID
    
    这是一个独立事务操作，确保在任何情况下都能获取默认租户ID
    
    Returns:
        int: 默认租户ID
    """
    try:
        default_tenant = Tenant.query.filter_by(name="默认租户").first()
        
        if not default_tenant:
            default_tenant = Tenant(
                name="默认租户",
                quota_config={
                    "max_sessions": 1000,
                    "max_users": 100,
                    "max_skills": 50,
                    "description": "系统默认租户，用于独立用户"
                },
                is_active=True
            )
            db.session.add(default_tenant)
            db.session.commit()
            logger.info(f"✅ 自动创建默认租户: ID={default_tenant.id}")
        
        return default_tenant.id
    except Exception as e:
        logger.error(f"❌ 获取或创建默认租户失败: {e}")
        db.session.rollback()
        # 如果失败，返回1（假设默认租户ID总是1）
        return 1
