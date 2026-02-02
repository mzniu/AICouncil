"""
TenantRepository - 租户数据访问层
提供tenants表的CRUD操作，支持多租户管理
"""
from src.models import db, Tenant
from src.utils.logger import logger
from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError


class TenantRepository:
    """租户数据仓库，封装所有租户相关数据库操作"""
    
    @staticmethod
    def create_tenant(name: str, quota_config: Optional[dict] = None) -> Optional[Tenant]:
        """
        创建新租户
        
        Args:
            name: 租户名称
            quota_config: 配额配置（可选）
            
        Returns:
            Tenant对象，失败返回None
        """
        try:
            tenant = Tenant(
                name=name,
                quota_config=quota_config or {},
                is_active=True
            )
            db.session.add(tenant)
            db.session.commit()
            logger.info(f"[TenantRepo] 创建租户成功: {name} (ID={tenant.id})")
            return tenant
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[TenantRepo] 创建租户失败: {e}")
            return None
    
    @staticmethod
    def get_tenant_by_id(tenant_id: int) -> Optional[Tenant]:
        """
        根据ID获取租户
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            Tenant对象，不存在返回None
        """
        try:
            tenant = Tenant.query.filter_by(id=tenant_id).first()
            if tenant:
                logger.debug(f"[TenantRepo] 获取租户成功: {tenant.name} (ID={tenant_id})")
            else:
                logger.warning(f"[TenantRepo] 租户不存在: ID={tenant_id}")
            return tenant
        except SQLAlchemyError as e:
            logger.error(f"[TenantRepo] 获取租户失败: {e}")
            return None
    
    @staticmethod
    def get_all_tenants(page: int = 1, per_page: int = 50, 
                       active_only: bool = True) -> List[Tenant]:
        """
        获取租户列表（分页）
        
        Args:
            page: 页码（从1开始）
            per_page: 每页数量
            active_only: 是否只返回激活的租户
            
        Returns:
            List[Tenant]: 租户列表
        """
        try:
            query = Tenant.query
            
            if active_only:
                query = query.filter_by(is_active=True)
            
            tenants = query.order_by(Tenant.created_at.desc())\
                          .paginate(page=page, per_page=per_page, error_out=False)
            
            logger.debug(f"[TenantRepo] 获取租户列表: {len(tenants.items)}条")
            return tenants.items
        except SQLAlchemyError as e:
            logger.error(f"[TenantRepo] 获取租户列表失败: {e}")
            return []
    
    @staticmethod
    def update_tenant_quota(tenant_id: int, quota_config: dict) -> bool:
        """
        更新租户配额配置
        
        Args:
            tenant_id: 租户ID
            quota_config: 新的配额配置
            
        Returns:
            bool: 成功返回True
        """
        try:
            tenant = Tenant.query.filter_by(id=tenant_id).first()
            if not tenant:
                logger.warning(f"[TenantRepo] 租户不存在: ID={tenant_id}")
                return False
            
            tenant.quota_config = quota_config
            db.session.commit()
            logger.info(f"[TenantRepo] 更新租户配额成功: {tenant.name}")
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[TenantRepo] 更新租户配额失败: {e}")
            return False
    
    @staticmethod
    def deactivate_tenant(tenant_id: int) -> bool:
        """
        停用租户（软删除）
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            bool: 成功返回True
        """
        try:
            tenant = Tenant.query.filter_by(id=tenant_id).first()
            if not tenant:
                return False
            
            tenant.is_active = False
            db.session.commit()
            logger.info(f"[TenantRepo] 停用租户成功: {tenant.name}")
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[TenantRepo] 停用租户失败: {e}")
            return False
    
    @staticmethod
    def activate_tenant(tenant_id: int) -> bool:
        """
        激活租户
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            bool: 成功返回True
        """
        try:
            tenant = Tenant.query.filter_by(id=tenant_id).first()
            if not tenant:
                return False
            
            tenant.is_active = True
            db.session.commit()
            logger.info(f"[TenantRepo] 激活租户成功: {tenant.name}")
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"[TenantRepo] 激活租户失败: {e}")
            return False
