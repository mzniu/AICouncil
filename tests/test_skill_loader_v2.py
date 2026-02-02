"""
Unit tests for SkillLoaderV2
"""

import pytest
from datetime import datetime

from src.models import db, Skill, TenantSkillSubscription, Tenant
from src.skills.loader_v2 import SkillLoaderV2, MergedSkill, load_tenant_skills
from src.skills.loader import SkillLoader
from src.repositories.skill_repository import SkillRepository


@pytest.fixture
def test_tenant(app):
    """Create a test tenant"""
    with app.app_context():
        tenant = Tenant(
            name='Test Tenant V2',
            quota_config={'max_skills': 100},
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.session.add(tenant)
        db.session.commit()
        yield tenant
        
        # Cleanup
        db.session.delete(tenant)
        db.session.commit()


@pytest.fixture
def custom_skill(app, test_tenant):
    """Create a custom skill for testing"""
    with app.app_context():
        skill = SkillRepository.create_skill(
            tenant_id=test_tenant.id,
            name='custom_test_skill',
            display_name='Custom Test Skill',
            content='# Custom Skill Content\n\nThis is a custom skill.',
            version='1.0.0',
            category='test',
            tags=['custom', 'test'],
            description='A custom test skill',
            applicable_roles=['策论家'],
            author='Test Author',
            is_builtin=False
        )
        
        # Subscribe to the skill
        SkillRepository.subscribe_skill(test_tenant.id, skill.id)
        
        yield skill
        
        # Cleanup
        sub = TenantSkillSubscription.query.filter_by(
            tenant_id=test_tenant.id,
            skill_id=skill.id
        ).first()
        if sub:
            db.session.delete(sub)
        db.session.delete(skill)
        db.session.commit()


class TestSkillLoaderV2Initialization:
    """Test SkillLoaderV2 initialization"""
    
    def test_loader_initialization(self, app):
        """Test SkillLoaderV2 can be initialized"""
        with app.app_context():
            loader = SkillLoaderV2()
            assert loader is not None
            assert loader.builtin_loader is not None
            assert isinstance(loader.builtin_loader, SkillLoader)
    
    def test_loader_with_custom_builtin_loader(self, app):
        """Test SkillLoaderV2 with custom builtin loader"""
        with app.app_context():
            custom_loader = SkillLoader()
            loader = SkillLoaderV2(builtin_loader=custom_loader)
            assert loader.builtin_loader is custom_loader


class TestLoadAllSkills:
    """Test loading all skills"""
    
    def test_load_builtin_only(self, app):
        """Test loading builtin skills without tenant"""
        with app.app_context():
            loader = SkillLoaderV2()
            skills = loader.load_all_skills(tenant_id=None)
            
            # Should have 5 builtin skills
            assert len(skills) == 5
            assert all(s.is_builtin for s in skills)
            assert all(not s.is_subscribed for s in skills)
    
    def test_load_with_tenant_no_subscriptions(self, app, test_tenant):
        """Test loading skills for tenant with no subscriptions"""
        with app.app_context():
            loader = SkillLoaderV2()
            skills = loader.load_all_skills(tenant_id=test_tenant.id)
            
            # Should have no skills (no subscriptions)
            assert len(skills) == 0
    
    def test_load_with_tenant_and_custom_skill(self, app, test_tenant, custom_skill):
        """Test loading skills for tenant with custom skill"""
        with app.app_context():
            loader = SkillLoaderV2()
            skills = loader.load_all_skills(tenant_id=test_tenant.id)
            
            # Should have 1 custom skill
            assert len(skills) == 1
            assert skills[0].name == 'custom_test_skill'
            assert not skills[0].is_builtin
            assert skills[0].is_subscribed
    
    def test_load_with_builtin_subscription(self, app, test_tenant):
        """Test loading skills with builtin subscription"""
        with app.app_context():
            # Subscribe to a builtin skill
            builtin_skill = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='policy_analysis',
                display_name='Policy Analysis',
                content='# Builtin content',
                is_builtin=True
            )
            SkillRepository.subscribe_skill(test_tenant.id, builtin_skill.id)
            
            loader = SkillLoaderV2()
            skills = loader.load_all_skills(tenant_id=test_tenant.id)
            
            # Should have 1 builtin skill
            assert len(skills) >= 1
            policy_skills = [s for s in skills if s.name == 'policy_analysis']
            assert len(policy_skills) == 1
            assert policy_skills[0].is_builtin
            assert policy_skills[0].is_subscribed
            
            # Cleanup
            sub = TenantSkillSubscription.query.filter_by(
                tenant_id=test_tenant.id,
                skill_id=builtin_skill.id
            ).first()
            db.session.delete(sub)
            db.session.delete(builtin_skill)
            db.session.commit()
    
    def test_load_with_include_unsubscribed_builtin(self, app, test_tenant):
        """Test loading skills with include_unsubscribed_builtin=True"""
        with app.app_context():
            loader = SkillLoaderV2()
            skills = loader.load_all_skills(
                tenant_id=test_tenant.id,
                include_unsubscribed_builtin=True
            )
            
            # Should have all 5 builtin skills
            assert len(skills) == 5
            assert all(s.is_builtin for s in skills)


class TestLoadSkillByName:
    """Test loading specific skill by name"""
    
    def test_load_builtin_skill(self, app):
        """Test loading builtin skill by name"""
        with app.app_context():
            loader = SkillLoaderV2()
            skill = loader.load_skill_by_name('policy_analysis')
            
            assert skill is not None
            assert skill.name == 'policy_analysis'
            assert skill.is_builtin
            assert not skill.is_subscribed
    
    def test_load_custom_skill(self, app, test_tenant, custom_skill):
        """Test loading custom skill by name"""
        with app.app_context():
            loader = SkillLoaderV2()
            skill = loader.load_skill_by_name('custom_test_skill', test_tenant.id)
            
            assert skill is not None
            assert skill.name == 'custom_test_skill'
            assert not skill.is_builtin
            assert skill.is_subscribed
    
    def test_load_nonexistent_skill(self, app):
        """Test loading non-existent skill"""
        with app.app_context():
            loader = SkillLoaderV2()
            skill = loader.load_skill_by_name('nonexistent_skill')
            
            assert skill is None


class TestFilteringSkills:
    """Test skill filtering by category and role"""
    
    def test_filter_by_category(self, app):
        """Test filtering skills by category"""
        with app.app_context():
            loader = SkillLoaderV2()
            skills = loader.get_skills_by_category('analysis', tenant_id=None)
            
            assert len(skills) >= 1
            assert all(s.category == 'analysis' for s in skills)
    
    def test_filter_by_role(self, app):
        """Test filtering skills by role"""
        with app.app_context():
            loader = SkillLoaderV2()
            skills = loader.get_skills_by_role('策论家', tenant_id=None)
            
            # Should have skills applicable to 策论家
            assert len(skills) >= 1
            for skill in skills:
                assert '策论家' in skill.applicable_roles


class TestSkillFormatting:
    """Test skill formatting for prompts"""
    
    def test_format_skill_with_metadata(self, app):
        """Test formatting skill with metadata"""
        with app.app_context():
            loader = SkillLoaderV2()
            skill = loader.load_skill_by_name('policy_analysis')
            
            formatted = loader.format_skill_for_prompt(skill, include_metadata=True)
            
            assert '## Skill:' in formatted
            assert 'policy_analysis' in formatted
            assert 'Metadata:' in formatted
            assert 'Version:' in formatted
            assert 'Content:' in formatted
    
    def test_format_skill_without_metadata(self, app):
        """Test formatting skill without metadata"""
        with app.app_context():
            loader = SkillLoaderV2()
            skill = loader.load_skill_by_name('policy_analysis')
            
            formatted = loader.format_skill_for_prompt(skill, include_metadata=False)
            
            assert '## Skill:' in formatted
            assert 'Metadata:' not in formatted
            assert 'Content:' in formatted
    
    def test_format_all_skills(self, app):
        """Test formatting multiple skills"""
        with app.app_context():
            loader = SkillLoaderV2()
            skills = loader.load_all_skills(tenant_id=None)[:2]  # Get first 2 skills
            
            formatted = loader.format_all_skills_for_prompt(skills)
            
            assert '# Available Skills' in formatted
            assert '---' in formatted
            assert len([s for s in formatted.split('---') if s.strip()]) >= 2


class TestMergedSkillDataclass:
    """Test MergedSkill dataclass"""
    
    def test_from_builtin(self, app):
        """Test creating MergedSkill from builtin Skill"""
        with app.app_context():
            builtin_loader = SkillLoader()
            builtin_skill = builtin_loader.load_skill_by_name('policy_analysis')
            
            merged = MergedSkill.from_builtin(builtin_skill)
            
            assert merged.name == 'policy_analysis'
            assert merged.is_builtin
            assert not merged.is_subscribed
    
    def test_to_dict_with_content(self, app):
        """Test converting MergedSkill to dict with content"""
        with app.app_context():
            loader = SkillLoaderV2()
            skill = loader.load_skill_by_name('policy_analysis')
            
            skill_dict = skill.to_dict(include_content=True)
            
            assert 'name' in skill_dict
            assert 'content' in skill_dict
            assert skill_dict['is_builtin']
    
    def test_to_dict_without_content(self, app):
        """Test converting MergedSkill to dict without content"""
        with app.app_context():
            loader = SkillLoaderV2()
            skill = loader.load_skill_by_name('policy_analysis')
            
            skill_dict = skill.to_dict(include_content=False)
            
            assert 'name' in skill_dict
            assert 'content' not in skill_dict


class TestConvenienceFunction:
    """Test convenience function"""
    
    def test_load_tenant_skills(self, app, test_tenant, custom_skill):
        """Test convenience function for loading tenant skills"""
        with app.app_context():
            skills = load_tenant_skills(test_tenant.id)
            
            assert len(skills) >= 1
            assert any(s.name == 'custom_test_skill' for s in skills)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
