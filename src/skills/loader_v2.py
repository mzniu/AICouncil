"""
SkillLoaderV2: Tenant-aware skill loader that merges builtin and custom skills

This module provides a unified interface for loading skills in a multi-tenant context,
combining:
1. Builtin skills from the filesystem (via SkillLoader)
2. Tenant-specific custom skills from the database (via SkillRepository)

Key Features:
- Tenant-aware skill loading with subscription filtering
- Deduplication: tenant custom skills override builtin skills with the same name
- Subscription-based filtering: only enabled subscriptions are included
- Support for category and role-based filtering
- Seamless integration with agent prompt generation

Usage Example:
    loader = SkillLoaderV2(db_session)
    skills = loader.load_all_skills(tenant_id=123, category='analysis')
    formatted = loader.format_skill_for_prompt(skills[0])
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from src.skills.loader import SkillLoader, Skill as BuiltinSkill
from src.repositories.skill_repository import SkillRepository
from src.models import db, Skill as SkillModel
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class MergedSkill:
    """Unified skill representation for both builtin and custom skills"""
    name: str
    display_name: str
    version: str
    category: str
    tags: List[str]
    description: str
    content: str
    applicable_roles: List[str]
    author: str
    requirements: Optional[List[str]] = None
    is_builtin: bool = False
    is_subscribed: bool = False
    subscription_config: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_builtin(cls, skill: BuiltinSkill, is_subscribed: bool = False) -> 'MergedSkill':
        """Create MergedSkill from builtin Skill"""
        # Skill dataclass has attributes directly, not in metadata dict
        # requirements is Dict[str, str] in Skill but List[str] in MergedSkill
        requirements_list = None
        if skill.requirements and isinstance(skill.requirements, dict):
            requirements_list = [f"{k}: {v}" for k, v in skill.requirements.items()]
        
        return cls(
            name=skill.name,
            display_name=skill.display_name or skill.name,
            version=skill.version or '1.0.0',
            category=skill.category or 'general',
            tags=skill.tags or [],
            description=skill.description or '',
            content=skill.content,
            applicable_roles=skill.applicable_roles or [],
            author=skill.author or 'Unknown',
            requirements=requirements_list,
            is_builtin=True,
            is_subscribed=is_subscribed
        )
    
    @classmethod
    def from_db_model(cls, skill: SkillModel, subscription_config: Optional[Dict] = None) -> 'MergedSkill':
        """Create MergedSkill from database Skill model"""
        return cls(
            name=skill.name,
            display_name=skill.display_name or skill.name,
            version=skill.version or '1.0.0',
            category=skill.category or 'custom',
            tags=skill.tags or [],
            description=skill.description or '',
            content=skill.content,
            applicable_roles=skill.applicable_roles or [],
            author=skill.author or 'Unknown',
            requirements=skill.requirements,
            is_builtin=skill.is_builtin,
            is_subscribed=True,
            subscription_config=subscription_config
        )
    
    def to_dict(self, include_content: bool = True) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = {
            'name': self.name,
            'display_name': self.display_name,
            'version': self.version,
            'category': self.category,
            'tags': self.tags,
            'description': self.description,
            'applicable_roles': self.applicable_roles,
            'author': self.author,
            'is_builtin': self.is_builtin,
            'is_subscribed': self.is_subscribed
        }
        
        if self.requirements:
            data['requirements'] = self.requirements
        
        if self.subscription_config:
            data['subscription_config'] = self.subscription_config
        
        if include_content:
            data['content'] = self.content
        
        return data


class SkillLoaderV2:
    """
    Tenant-aware skill loader that merges builtin and custom skills
    
    This class provides a unified interface for loading skills in a multi-tenant
    environment. It combines:
    - Builtin skills from the filesystem (loaded via SkillLoader)
    - Tenant-specific custom skills from the database (loaded via SkillRepository)
    
    Skills are deduplicated by name, with tenant custom skills taking precedence
    over builtin skills when they share the same name.
    """
    
    def __init__(self, db_session=None, builtin_loader: Optional[SkillLoader] = None):
        """
        Initialize SkillLoaderV2
        
        Args:
            db_session: SQLAlchemy database session (defaults to db.session)
            builtin_loader: SkillLoader instance (defaults to new instance)
        """
        self.db_session = db_session or db.session
        self.builtin_loader = builtin_loader or SkillLoader()
        logger.info("SkillLoaderV2 initialized")
    
    def load_all_skills(
        self,
        tenant_id: Optional[int] = None,
        category: Optional[str] = None,
        role: Optional[str] = None,
        include_unsubscribed_builtin: bool = False
    ) -> List[MergedSkill]:
        """
        Load all skills for a tenant, merging builtin and custom skills
        
        Args:
            tenant_id: Tenant ID to load skills for (None for builtin only)
            category: Filter by category (e.g., 'analysis', 'evaluation')
            role: Filter by applicable role (e.g., '策论家', '监察官')
            include_unsubscribed_builtin: Include builtin skills not subscribed by tenant
            
        Returns:
            List of MergedSkill objects, deduplicated by name
            
        Note:
            - Tenant custom skills override builtin skills with the same name
            - Only enabled subscriptions are included
            - If tenant_id is None, only builtin skills are returned
        """
        logger.info(f"Loading skills for tenant_id={tenant_id}, category={category}, role={role}")
        
        # Load builtin skills
        builtin_skills = self.builtin_loader.load_all_builtin_skills()
        logger.debug(f"Loaded {len(builtin_skills)} builtin skills")
        
        # Apply category filter to builtin skills
        if category:
            builtin_skills = [s for s in builtin_skills if s.category == category]
        
        # Apply role filter to builtin skills
        if role:
            builtin_skills = [
                s for s in builtin_skills 
                if role in (s.applicable_roles or [])
            ]
        
        # If no tenant_id, return builtin skills only
        if tenant_id is None:
            logger.info(f"No tenant_id provided, returning {len(builtin_skills)} builtin skills")
            return [MergedSkill.from_builtin(s) for s in builtin_skills]
        
        # Load tenant subscribed skills (both builtin and custom)
        subscribed_skills = SkillRepository.get_subscribed_skills(
            tenant_id=tenant_id,
            category=category
        )
        logger.debug(f"Loaded {len(subscribed_skills)} subscribed skills for tenant {tenant_id}")
        
        # Get all subscriptions to extract custom_config
        subscriptions = SkillRepository.get_tenant_subscriptions(tenant_id, enabled_only=True)
        subscription_map = {sub.skill_id: sub.custom_config for sub in subscriptions}
        
        # Build subscription map for builtin skills
        builtin_subscription_map = {}
        custom_skills = []
        
        # get_subscribed_skills returns List[Skill], not tuples
        for db_skill in subscribed_skills:
            subscription_config = subscription_map.get(db_skill.id)
            
            if db_skill.is_builtin:
                # Track builtin skill subscription
                builtin_subscription_map[db_skill.name] = subscription_config
            else:
                # Collect custom skills
                custom_skills.append(
                    MergedSkill.from_db_model(db_skill, subscription_config)
                )
        
        # Apply role filter to custom skills
        if role:
            custom_skills = [
                s for s in custom_skills 
                if role in s.applicable_roles
            ]
        
        # Merge skills: start with custom skills (they override builtin)
        merged_skills = {s.name: s for s in custom_skills}
        
        # Add builtin skills
        for builtin_skill in builtin_skills:
            name = builtin_skill.name
            
            # Skip if custom skill with same name exists
            if name in merged_skills:
                logger.debug(f"Custom skill '{name}' overrides builtin skill")
                continue
            
            # Check subscription status
            is_subscribed = name in builtin_subscription_map
            
            # Include builtin skill if subscribed or if include_unsubscribed_builtin=True
            if is_subscribed or include_unsubscribed_builtin:
                merged_skills[name] = MergedSkill.from_builtin(
                    builtin_skill,
                    is_subscribed=is_subscribed
                )
        
        result = list(merged_skills.values())
        logger.info(f"Merged {len(result)} skills for tenant {tenant_id}")
        
        return result
    
    def load_skill_by_name(
        self,
        name: str,
        tenant_id: Optional[int] = None
    ) -> Optional[MergedSkill]:
        """
        Load a specific skill by name
        
        Args:
            name: Skill name
            tenant_id: Tenant ID (None for builtin only)
            
        Returns:
            MergedSkill object or None if not found
            
        Note:
            - Tenant custom skills take precedence over builtin skills
            - For builtin skills, checks subscription status if tenant_id provided
        """
        logger.debug(f"Loading skill '{name}' for tenant_id={tenant_id}")
        
        # If tenant_id provided, check for custom skill first
        if tenant_id:
            # Try to load tenant custom skill
            db_skill = SkillRepository.get_skill_by_name(name, tenant_id)
            
            if db_skill and not db_skill.is_builtin:
                # Check subscription
                if SkillRepository.is_skill_subscribed(tenant_id, db_skill.id):
                    subscription = SkillRepository.get_tenant_subscriptions(tenant_id)
                    sub_config = next(
                        (s.custom_config for s in subscription if s.skill_id == db_skill.id),
                        None
                    )
                    logger.info(f"Found custom skill '{name}' for tenant {tenant_id}")
                    return MergedSkill.from_db_model(db_skill, sub_config)
        
        # Try to load builtin skill
        builtin_skill = self.builtin_loader.load_skill_by_name(name)
        
        if builtin_skill:
            # Check subscription status if tenant_id provided
            is_subscribed = False
            if tenant_id:
                db_skill = SkillRepository.get_skill_by_name(name, tenant_id)
                if db_skill:
                    is_subscribed = SkillRepository.is_skill_subscribed(tenant_id, db_skill.id)
            
            logger.info(f"Found builtin skill '{name}', subscribed={is_subscribed}")
            return MergedSkill.from_builtin(builtin_skill, is_subscribed)
        
        logger.warning(f"Skill '{name}' not found")
        return None
    
    def get_skills_by_category(
        self,
        category: str,
        tenant_id: Optional[int] = None
    ) -> List[MergedSkill]:
        """
        Get all skills in a specific category
        
        Args:
            category: Category name (e.g., 'analysis', 'evaluation')
            tenant_id: Tenant ID (None for builtin only)
            
        Returns:
            List of MergedSkill objects in the specified category
        """
        return self.load_all_skills(tenant_id=tenant_id, category=category)
    
    def get_skills_by_role(
        self,
        role: str,
        tenant_id: Optional[int] = None
    ) -> List[MergedSkill]:
        """
        Get all skills applicable to a specific role
        
        Args:
            role: Role name (e.g., '策论家', '监察官')
            tenant_id: Tenant ID (None for builtin only)
            
        Returns:
            List of MergedSkill objects applicable to the specified role
        """
        return self.load_all_skills(tenant_id=tenant_id, role=role)
    
    def format_skill_for_prompt(
        self,
        skill: MergedSkill,
        include_metadata: bool = True
    ) -> str:
        """
        Format a skill for inclusion in an agent prompt
        
        Args:
            skill: MergedSkill to format
            include_metadata: Include metadata section (version, author, etc.)
            
        Returns:
            Formatted skill text suitable for prompt injection
        """
        parts = []
        
        # Header
        parts.append(f"## Skill: {skill.display_name}")
        parts.append("")
        
        # Metadata section
        if include_metadata:
            parts.append("**Metadata:**")
            parts.append(f"- Name: `{skill.name}`")
            parts.append(f"- Version: {skill.version}")
            parts.append(f"- Category: {skill.category}")
            if skill.tags:
                parts.append(f"- Tags: {', '.join(skill.tags)}")
            parts.append(f"- Author: {skill.author}")
            if skill.applicable_roles:
                parts.append(f"- Applicable Roles: {', '.join(skill.applicable_roles)}")
            if skill.requirements:
                parts.append(f"- Requirements: {', '.join(skill.requirements)}")
            parts.append("")
            parts.append("**Description:**")
            parts.append(skill.description)
            parts.append("")
        
        # Content
        parts.append("**Content:**")
        parts.append("")
        parts.append(skill.content)
        parts.append("")
        
        return "\n".join(parts)
    
    def format_all_skills_for_prompt(
        self,
        skills: List[MergedSkill],
        include_metadata: bool = False
    ) -> str:
        """
        Format multiple skills for inclusion in an agent prompt
        
        Args:
            skills: List of MergedSkill objects to format
            include_metadata: Include metadata sections
            
        Returns:
            Formatted text with all skills
        """
        if not skills:
            return ""
        
        parts = ["# Available Skills", ""]
        
        for skill in skills:
            parts.append(self.format_skill_for_prompt(skill, include_metadata))
            parts.append("---")
            parts.append("")
        
        return "\n".join(parts)


# Convenience function for quick access
def load_tenant_skills(
    tenant_id: int,
    category: Optional[str] = None,
    role: Optional[str] = None
) -> List[MergedSkill]:
    """
    Convenience function to load skills for a tenant
    
    Args:
        tenant_id: Tenant ID
        category: Filter by category
        role: Filter by role
        
    Returns:
        List of MergedSkill objects
    """
    loader = SkillLoaderV2()
    return loader.load_all_skills(tenant_id=tenant_id, category=category, role=role)
