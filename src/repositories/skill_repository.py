"""
SkillRepository - Skills CRUD and subscription management
"""

from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import and_, or_, func
from sqlalchemy.exc import IntegrityError

from src.models import db, Skill, TenantSkillSubscription, SkillUsageStat
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SkillRepository:
    """Repository for managing Skills, subscriptions, and usage statistics"""
    
    # ==================== Skill CRUD Operations ====================
    
    @staticmethod
    def create_skill(
        tenant_id: int,
        name: str,
        display_name: str,
        content: str,
        version: str = "1.0.0",
        category: str = "general",
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        applicable_roles: Optional[List[str]] = None,
        requirements: Optional[Dict] = None,
        author: Optional[str] = None,
        source: Optional[str] = None,
        is_builtin: bool = False
    ) -> Optional[Skill]:
        """
        Create a new skill for a tenant
        
        Args:
            tenant_id: Tenant ID
            name: Skill unique identifier
            display_name: Skill display name
            content: Skill content (markdown)
            version: Semantic version
            category: Category (analysis, technical, financial, etc.)
            tags: Tags list
            description: Skill description
            applicable_roles: Applicable roles list
            requirements: Usage requirements dict
            author: Author name
            source: Source URL/repo
            is_builtin: Whether this is a builtin skill
            
        Returns:
            Created Skill object or None if failed
        """
        try:
            skill = Skill(
                tenant_id=tenant_id,
                name=name,
                display_name=display_name,
                version=version,
                category=category,
                tags=tags or [],
                description=description,
                content=content,
                applicable_roles=applicable_roles or [],
                requirements=requirements or {},
                author=author,
                source=source,
                is_active=True,
                is_builtin=is_builtin,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(skill)
            db.session.commit()
            
            logger.info(f"Created skill: {name} (ID: {skill.id}) for tenant {tenant_id}")
            return skill
            
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Failed to create skill {name} for tenant {tenant_id}: {e}")
            return None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error creating skill {name}: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_skill_by_id(skill_id: int, tenant_id: Optional[int] = None) -> Optional[Skill]:
        """
        Get skill by ID, optionally filtered by tenant
        
        Args:
            skill_id: Skill ID
            tenant_id: Optional tenant ID for access control
            
        Returns:
            Skill object or None
        """
        try:
            query = Skill.query.filter_by(id=skill_id)
            
            if tenant_id is not None:
                query = query.filter_by(tenant_id=tenant_id)
            
            return query.first()
        except Exception as e:
            logger.error(f"Error fetching skill {skill_id}: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_skill_by_name(name: str, tenant_id: int) -> Optional[Skill]:
        """
        Get skill by name within a tenant
        
        Args:
            name: Skill name
            tenant_id: Tenant ID
            
        Returns:
            Skill object or None
        """
        try:
            return Skill.query.filter_by(
                name=name,
                tenant_id=tenant_id
            ).first()
        except Exception as e:
            logger.error(f"Error fetching skill {name} for tenant {tenant_id}: {e}", exc_info=True)
            return None
    
    @staticmethod
    def update_skill(
        skill_id: int,
        tenant_id: int,
        **kwargs
    ) -> Optional[Skill]:
        """
        Update skill attributes
        
        Args:
            skill_id: Skill ID
            tenant_id: Tenant ID (for access control)
            **kwargs: Attributes to update (display_name, content, version, etc.)
            
        Returns:
            Updated Skill object or None
        """
        try:
            skill = SkillRepository.get_skill_by_id(skill_id, tenant_id)
            
            if not skill:
                logger.warning(f"Skill {skill_id} not found for tenant {tenant_id}")
                return None
            
            # Update allowed fields
            allowed_fields = {
                'display_name', 'content', 'version', 'category', 'tags',
                'description', 'applicable_roles', 'requirements', 'author',
                'source', 'is_active'
            }
            
            for key, value in kwargs.items():
                if key in allowed_fields:
                    setattr(skill, key, value)
            
            skill.updated_at = datetime.utcnow()
            
            db.session.commit()
            logger.info(f"Updated skill {skill_id} for tenant {tenant_id}")
            return skill
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating skill {skill_id}: {e}", exc_info=True)
            return None
    
    @staticmethod
    def delete_skill(skill_id: int, tenant_id: int) -> bool:
        """
        Delete a skill (soft delete by setting is_active=False for builtin, hard delete for custom)
        
        Args:
            skill_id: Skill ID
            tenant_id: Tenant ID (for access control)
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            skill = SkillRepository.get_skill_by_id(skill_id, tenant_id)
            
            if not skill:
                logger.warning(f"Skill {skill_id} not found for tenant {tenant_id}")
                return False
            
            if skill.is_builtin:
                # Builtin skills: soft delete
                skill.is_active = False
                skill.updated_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"Soft-deleted builtin skill {skill_id}")
            else:
                # Custom skills: hard delete
                db.session.delete(skill)
                db.session.commit()
                logger.info(f"Hard-deleted custom skill {skill_id}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting skill {skill_id}: {e}", exc_info=True)
            return False
    
    # ==================== Skill Query Operations ====================
    
    @staticmethod
    def get_tenant_skills(
        tenant_id: int,
        category: Optional[str] = None,
        is_active: bool = True,
        include_content: bool = False,
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """
        Get skills for a tenant with pagination
        
        Args:
            tenant_id: Tenant ID
            category: Optional category filter
            is_active: Filter by active status
            include_content: Whether to include full content
            page: Page number (1-indexed)
            page_size: Items per page
            
        Returns:
            Dict with items, total, page, page_size
        """
        try:
            query = Skill.query.filter_by(tenant_id=tenant_id, is_active=is_active)
            
            if category:
                query = query.filter_by(category=category)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            skills = query.order_by(Skill.created_at.desc())\
                         .offset((page - 1) * page_size)\
                         .limit(page_size)\
                         .all()
            
            return {
                'items': [s.to_dict(include_content=include_content) for s in skills],
                'total': total,
                'page': page,
                'page_size': page_size
            }
            
        except Exception as e:
            logger.error(f"Error fetching skills for tenant {tenant_id}: {e}", exc_info=True)
            return {'items': [], 'total': 0, 'page': page, 'page_size': page_size}
    
    @staticmethod
    def get_skills_by_category(tenant_id: int, category: str) -> List[Skill]:
        """
        Get all active skills in a category for a tenant
        
        Args:
            tenant_id: Tenant ID
            category: Category name
            
        Returns:
            List of Skill objects
        """
        try:
            return Skill.query.filter_by(
                tenant_id=tenant_id,
                category=category,
                is_active=True
            ).all()
        except Exception as e:
            logger.error(f"Error fetching skills by category {category}: {e}", exc_info=True)
            return []
    
    @staticmethod
    def search_skills(
        tenant_id: int,
        keyword: str,
        is_active: bool = True
    ) -> List[Skill]:
        """
        Search skills by keyword (name, display_name, description)
        
        Args:
            tenant_id: Tenant ID
            keyword: Search keyword
            is_active: Filter by active status
            
        Returns:
            List of matching Skill objects
        """
        try:
            keyword_pattern = f"%{keyword}%"
            
            return Skill.query.filter(
                and_(
                    Skill.tenant_id == tenant_id,
                    Skill.is_active == is_active,
                    or_(
                        Skill.name.like(keyword_pattern),
                        Skill.display_name.like(keyword_pattern),
                        Skill.description.like(keyword_pattern)
                    )
                )
            ).all()
            
        except Exception as e:
            logger.error(f"Error searching skills with keyword '{keyword}': {e}", exc_info=True)
            return []
    
    # ==================== Subscription Management ====================
    
    @staticmethod
    def subscribe_skill(
        tenant_id: int,
        skill_id: int,
        custom_config: Optional[Dict] = None
    ) -> Optional[TenantSkillSubscription]:
        """
        Subscribe a tenant to a skill
        
        Args:
            tenant_id: Tenant ID
            skill_id: Skill ID
            custom_config: Optional custom configuration
            
        Returns:
            TenantSkillSubscription object or None
        """
        try:
            # Check if subscription already exists
            subscription = TenantSkillSubscription.query.filter_by(
                tenant_id=tenant_id,
                skill_id=skill_id
            ).first()
            
            if subscription:
                # Update existing subscription
                subscription.enabled = True
                subscription.custom_config = custom_config
                subscription.updated_at = datetime.utcnow()
                logger.info(f"Re-enabled skill subscription: tenant {tenant_id}, skill {skill_id}")
            else:
                # Create new subscription
                subscription = TenantSkillSubscription(
                    tenant_id=tenant_id,
                    skill_id=skill_id,
                    enabled=True,
                    custom_config=custom_config,
                    subscribed_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(subscription)
                logger.info(f"Created skill subscription: tenant {tenant_id}, skill {skill_id}")
            
            db.session.commit()
            return subscription
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error subscribing skill {skill_id} for tenant {tenant_id}: {e}", exc_info=True)
            return None
    
    @staticmethod
    def unsubscribe_skill(tenant_id: int, skill_id: int) -> bool:
        """
        Unsubscribe a tenant from a skill (disable, not delete)
        
        Args:
            tenant_id: Tenant ID
            skill_id: Skill ID
            
        Returns:
            True if unsubscribed, False otherwise
        """
        try:
            subscription = TenantSkillSubscription.query.filter_by(
                tenant_id=tenant_id,
                skill_id=skill_id
            ).first()
            
            if not subscription:
                logger.warning(f"Subscription not found: tenant {tenant_id}, skill {skill_id}")
                return False
            
            subscription.enabled = False
            subscription.updated_at = datetime.utcnow()
            
            db.session.commit()
            logger.info(f"Disabled skill subscription: tenant {tenant_id}, skill {skill_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error unsubscribing skill {skill_id} for tenant {tenant_id}: {e}", exc_info=True)
            return False
    
    @staticmethod
    def is_skill_subscribed(tenant_id: int, skill_id: int) -> bool:
        """
        Check if a tenant is subscribed to a skill
        
        Args:
            tenant_id: Tenant ID
            skill_id: Skill ID
            
        Returns:
            True if subscribed and enabled, False otherwise
        """
        try:
            subscription = TenantSkillSubscription.query.filter_by(
                tenant_id=tenant_id,
                skill_id=skill_id,
                enabled=True
            ).first()
            
            return subscription is not None
            
        except Exception as e:
            logger.error(f"Error checking subscription: {e}", exc_info=True)
            return False
    
    @staticmethod
    def get_tenant_subscriptions(
        tenant_id: int,
        enabled_only: bool = True
    ) -> List[TenantSkillSubscription]:
        """
        Get all skill subscriptions for a tenant
        
        Args:
            tenant_id: Tenant ID
            enabled_only: Only return enabled subscriptions
            
        Returns:
            List of TenantSkillSubscription objects
        """
        try:
            query = TenantSkillSubscription.query.filter_by(tenant_id=tenant_id)
            
            if enabled_only:
                query = query.filter_by(enabled=True)
            
            return query.all()
            
        except Exception as e:
            logger.error(f"Error fetching subscriptions for tenant {tenant_id}: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_subscribed_skills(
        tenant_id: int,
        category: Optional[str] = None,
        include_content: bool = False
    ) -> List[Skill]:
        """
        Get all skills that a tenant is subscribed to
        
        Args:
            tenant_id: Tenant ID
            category: Optional category filter
            include_content: Whether to load full content
            
        Returns:
            List of Skill objects
        """
        try:
            # Join Skill with TenantSkillSubscription
            query = db.session.query(Skill).join(
                TenantSkillSubscription,
                and_(
                    TenantSkillSubscription.skill_id == Skill.id,
                    TenantSkillSubscription.tenant_id == tenant_id,
                    TenantSkillSubscription.enabled == True
                )
            ).filter(Skill.is_active == True)
            
            if category:
                query = query.filter(Skill.category == category)
            
            return query.all()
            
        except Exception as e:
            logger.error(f"Error fetching subscribed skills for tenant {tenant_id}: {e}", exc_info=True)
            return []
    
    # ==================== Usage Statistics ====================
    
    @staticmethod
    def record_skill_usage(
        tenant_id: int,
        skill_id: int,
        success: bool = True,
        execution_time: Optional[float] = None
    ) -> Optional[SkillUsageStat]:
        """
        Record a skill usage event
        
        Args:
            tenant_id: Tenant ID
            skill_id: Skill ID
            success: Whether the usage was successful
            execution_time: Optional execution time in seconds
            
        Returns:
            Updated SkillUsageStat object or None
        """
        try:
            # Get or create usage stat
            stat = SkillUsageStat.query.filter_by(
                tenant_id=tenant_id,
                skill_id=skill_id
            ).first()
            
            if not stat:
                stat = SkillUsageStat(
                    tenant_id=tenant_id,
                    skill_id=skill_id,
                    usage_count=0,
                    success_count=0,
                    failure_count=0,
                    avg_execution_time=None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(stat)
            
            # Update statistics
            stat.increment_usage(success=success, execution_time=execution_time)
            
            db.session.commit()
            logger.debug(f"Recorded skill usage: tenant {tenant_id}, skill {skill_id}, success={success}")
            return stat
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error recording skill usage: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_skill_stats(tenant_id: int, skill_id: int) -> Optional[Dict]:
        """
        Get usage statistics for a skill
        
        Args:
            tenant_id: Tenant ID
            skill_id: Skill ID
            
        Returns:
            Dict with usage statistics or None
        """
        try:
            stat = SkillUsageStat.query.filter_by(
                tenant_id=tenant_id,
                skill_id=skill_id
            ).first()
            
            return stat.to_dict() if stat else None
            
        except Exception as e:
            logger.error(f"Error fetching skill stats: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_top_skills(
        tenant_id: int,
        limit: int = 10,
        order_by: str = 'usage_count'
    ) -> List[Dict]:
        """
        Get top skills by usage or success rate
        
        Args:
            tenant_id: Tenant ID
            limit: Number of skills to return
            order_by: Sort field ('usage_count' or 'success_rate')
            
        Returns:
            List of dicts with skill info and stats
        """
        try:
            # Join Skill with SkillUsageStat
            query = db.session.query(Skill, SkillUsageStat).join(
                SkillUsageStat,
                and_(
                    SkillUsageStat.skill_id == Skill.id,
                    SkillUsageStat.tenant_id == tenant_id
                )
            ).filter(Skill.is_active == True)
            
            # Order by specified field
            if order_by == 'usage_count':
                query = query.order_by(SkillUsageStat.usage_count.desc())
            elif order_by == 'success_rate':
                # Calculate success rate: success_count / usage_count
                query = query.order_by(
                    (SkillUsageStat.success_count * 1.0 / SkillUsageStat.usage_count).desc()
                )
            
            results = query.limit(limit).all()
            
            # Format results
            top_skills = []
            for skill, stat in results:
                top_skills.append({
                    'skill': skill.to_dict(include_content=False),
                    'stats': stat.to_dict()
                })
            
            return top_skills
            
        except Exception as e:
            logger.error(f"Error fetching top skills for tenant {tenant_id}: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_tenant_usage_summary(tenant_id: int) -> Dict:
        """
        Get usage summary for all skills of a tenant
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Dict with summary statistics
        """
        try:
            # Aggregate statistics
            result = db.session.query(
                func.count(SkillUsageStat.id).label('total_skills'),
                func.sum(SkillUsageStat.usage_count).label('total_usages'),
                func.sum(SkillUsageStat.success_count).label('total_successes'),
                func.sum(SkillUsageStat.failure_count).label('total_failures'),
                func.avg(SkillUsageStat.avg_execution_time).label('avg_execution_time')
            ).filter(
                SkillUsageStat.tenant_id == tenant_id
            ).first()
            
            total_usages = result.total_usages or 0
            total_successes = result.total_successes or 0
            
            return {
                'total_skills': result.total_skills or 0,
                'total_usages': total_usages,
                'total_successes': total_successes,
                'total_failures': result.total_failures or 0,
                'success_rate': (total_successes / total_usages * 100) if total_usages > 0 else 0,
                'avg_execution_time': result.avg_execution_time
            }
            
        except Exception as e:
            logger.error(f"Error fetching usage summary for tenant {tenant_id}: {e}", exc_info=True)
            return {
                'total_skills': 0,
                'total_usages': 0,
                'total_successes': 0,
                'total_failures': 0,
                'success_rate': 0,
                'avg_execution_time': None
            }
