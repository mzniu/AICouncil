"""
Unit tests for SkillRepository
"""

import pytest
from datetime import datetime

from src.models import db, Skill, TenantSkillSubscription, SkillUsageStat, Tenant
from src.repositories.skill_repository import SkillRepository


@pytest.fixture
def test_tenant(app):
    """Create a test tenant"""
    with app.app_context():
        tenant = Tenant(
            name='Test Tenant',
            quota_config={'max_skills': 50},
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.session.add(tenant)
        db.session.commit()
        yield tenant
        
        # Cleanup
        db.session.delete(tenant)
        db.session.commit()


class TestSkillCRUD:
    """Test Skill CRUD operations"""
    
    def test_create_skill(self, app, test_tenant):
        """Test creating a skill"""
        with app.app_context():
            skill = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='test_skill',
                display_name='Test Skill',
                content='# Test Content',
                version='1.0.0',
                category='test',
                tags=['test'],
                description='Test skill description',
                applicable_roles=['策论家'],
                author='Test Author'
            )
            
            assert skill is not None
            assert skill.name == 'test_skill'
            assert skill.tenant_id == test_tenant.id
            assert skill.is_active is True
            
            # Cleanup
            db.session.delete(skill)
            db.session.commit()
    
    def test_create_duplicate_skill(self, app, test_tenant):
        """Test creating duplicate skill (should fail)"""
        with app.app_context():
            # Create first skill
            skill1 = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='duplicate_skill',
                display_name='Duplicate Skill',
                content='# Content'
            )
            assert skill1 is not None
            
            # Try to create duplicate
            skill2 = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='duplicate_skill',
                display_name='Another Duplicate',
                content='# Different Content'
            )
            assert skill2 is None  # Should fail due to unique constraint
            
            # Cleanup
            db.session.delete(skill1)
            db.session.commit()
    
    def test_get_skill_by_id(self, app, test_tenant):
        """Test fetching skill by ID"""
        with app.app_context():
            # Create skill
            skill = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='fetch_test',
                display_name='Fetch Test',
                content='# Content'
            )
            
            # Fetch by ID
            fetched = SkillRepository.get_skill_by_id(skill.id, test_tenant.id)
            assert fetched is not None
            assert fetched.id == skill.id
            assert fetched.name == 'fetch_test'
            
            # Cleanup
            db.session.delete(skill)
            db.session.commit()
    
    def test_update_skill(self, app, test_tenant):
        """Test updating skill"""
        with app.app_context():
            # Create skill
            skill = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='update_test',
                display_name='Original Name',
                content='# Original Content'
            )
            
            # Update skill
            updated = SkillRepository.update_skill(
                skill_id=skill.id,
                tenant_id=test_tenant.id,
                display_name='Updated Name',
                version='2.0.0'
            )
            
            assert updated is not None
            assert updated.display_name == 'Updated Name'
            assert updated.version == '2.0.0'
            
            # Cleanup
            db.session.delete(skill)
            db.session.commit()
    
    def test_delete_custom_skill(self, app, test_tenant):
        """Test deleting custom skill (hard delete)"""
        with app.app_context():
            # Create custom skill
            skill = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='delete_test',
                display_name='Delete Test',
                content='# Content',
                is_builtin=False
            )
            skill_id = skill.id
            
            # Delete skill
            result = SkillRepository.delete_skill(skill_id, test_tenant.id)
            assert result is True
            
            # Verify hard delete
            fetched = SkillRepository.get_skill_by_id(skill_id, test_tenant.id)
            assert fetched is None


class TestSkillQuery:
    """Test Skill query operations"""
    
    def test_get_tenant_skills(self, app, test_tenant):
        """Test fetching skills for a tenant"""
        with app.app_context():
            # Create multiple skills
            skill1 = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='skill1',
                display_name='Skill 1',
                content='# Content 1',
                category='category_a'
            )
            skill2 = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='skill2',
                display_name='Skill 2',
                content='# Content 2',
                category='category_b'
            )
            
            # Fetch all skills
            result = SkillRepository.get_tenant_skills(test_tenant.id)
            assert result['total'] >= 2
            assert len(result['items']) >= 2
            
            # Fetch by category
            result_cat_a = SkillRepository.get_tenant_skills(
                test_tenant.id,
                category='category_a'
            )
            assert result_cat_a['total'] >= 1
            
            # Cleanup
            db.session.delete(skill1)
            db.session.delete(skill2)
            db.session.commit()
    
    def test_search_skills(self, app, test_tenant):
        """Test searching skills by keyword"""
        with app.app_context():
            # Create skills
            skill = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='searchable_skill',
                display_name='Searchable Skill',
                content='# Content',
                description='This is a searchable description'
            )
            
            # Search by keyword
            results = SkillRepository.search_skills(test_tenant.id, 'searchable')
            assert len(results) >= 1
            assert results[0].name == 'searchable_skill'
            
            # Cleanup
            db.session.delete(skill)
            db.session.commit()


class TestSubscriptionManagement:
    """Test skill subscription operations"""
    
    def test_subscribe_skill(self, app, test_tenant):
        """Test subscribing to a skill"""
        with app.app_context():
            # Create skill
            skill = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='subscribe_test',
                display_name='Subscribe Test',
                content='# Content'
            )
            
            # Subscribe
            subscription = SkillRepository.subscribe_skill(
                tenant_id=test_tenant.id,
                skill_id=skill.id,
                custom_config={'param': 'value'}
            )
            
            assert subscription is not None
            assert subscription.enabled is True
            assert subscription.custom_config == {'param': 'value'}
            
            # Cleanup
            db.session.delete(subscription)
            db.session.delete(skill)
            db.session.commit()
    
    def test_unsubscribe_skill(self, app, test_tenant):
        """Test unsubscribing from a skill"""
        with app.app_context():
            # Create and subscribe
            skill = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='unsubscribe_test',
                display_name='Unsubscribe Test',
                content='# Content'
            )
            subscription = SkillRepository.subscribe_skill(test_tenant.id, skill.id)
            
            # Unsubscribe
            result = SkillRepository.unsubscribe_skill(test_tenant.id, skill.id)
            assert result is True
            
            # Verify disabled
            assert SkillRepository.is_skill_subscribed(test_tenant.id, skill.id) is False
            
            # Cleanup
            db.session.delete(subscription)
            db.session.delete(skill)
            db.session.commit()
    
    def test_get_subscribed_skills(self, app, test_tenant):
        """Test fetching subscribed skills"""
        with app.app_context():
            # Create skills
            skill1 = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='subscribed1',
                display_name='Subscribed 1',
                content='# Content',
                category='test_cat'
            )
            skill2 = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='subscribed2',
                display_name='Subscribed 2',
                content='# Content',
                category='test_cat'
            )
            
            # Subscribe to both
            sub1 = SkillRepository.subscribe_skill(test_tenant.id, skill1.id)
            sub2 = SkillRepository.subscribe_skill(test_tenant.id, skill2.id)
            
            # Fetch subscribed skills
            subscribed = SkillRepository.get_subscribed_skills(test_tenant.id)
            assert len(subscribed) >= 2
            
            # Filter by category
            subscribed_cat = SkillRepository.get_subscribed_skills(
                test_tenant.id,
                category='test_cat'
            )
            assert len(subscribed_cat) >= 2
            
            # Cleanup
            db.session.delete(sub1)
            db.session.delete(sub2)
            db.session.delete(skill1)
            db.session.delete(skill2)
            db.session.commit()


class TestUsageStatistics:
    """Test skill usage statistics"""
    
    def test_record_skill_usage(self, app, test_tenant):
        """Test recording skill usage"""
        with app.app_context():
            # Create skill
            skill = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='usage_test',
                display_name='Usage Test',
                content='# Content'
            )
            
            # Record usage
            stat = SkillRepository.record_skill_usage(
                tenant_id=test_tenant.id,
                skill_id=skill.id,
                success=True,
                execution_time=1.5
            )
            
            assert stat is not None
            assert stat.usage_count == 1
            assert stat.success_count == 1
            assert stat.avg_execution_time == 1.5
            
            # Record another usage
            stat2 = SkillRepository.record_skill_usage(
                tenant_id=test_tenant.id,
                skill_id=skill.id,
                success=False,
                execution_time=2.0
            )
            
            assert stat2.usage_count == 2
            assert stat2.success_count == 1
            assert stat2.failure_count == 1
            
            # Cleanup
            db.session.delete(stat)
            db.session.delete(skill)
            db.session.commit()
    
    def test_get_skill_stats(self, app, test_tenant):
        """Test fetching skill statistics"""
        with app.app_context():
            # Create skill and record usage
            skill = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='stats_test',
                display_name='Stats Test',
                content='# Content'
            )
            SkillRepository.record_skill_usage(test_tenant.id, skill.id)
            
            # Get stats
            stats = SkillRepository.get_skill_stats(test_tenant.id, skill.id)
            assert stats is not None
            assert stats['usage_count'] >= 1
            assert 'success_rate' in stats
            
            # Cleanup
            stat = SkillUsageStat.query.filter_by(
                tenant_id=test_tenant.id,
                skill_id=skill.id
            ).first()
            db.session.delete(stat)
            db.session.delete(skill)
            db.session.commit()
    
    def test_get_tenant_usage_summary(self, app, test_tenant):
        """Test fetching tenant usage summary"""
        with app.app_context():
            # Create skills and record usages
            skill1 = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='summary_test1',
                display_name='Summary Test 1',
                content='# Content'
            )
            skill2 = SkillRepository.create_skill(
                tenant_id=test_tenant.id,
                name='summary_test2',
                display_name='Summary Test 2',
                content='# Content'
            )
            
            SkillRepository.record_skill_usage(test_tenant.id, skill1.id, success=True)
            SkillRepository.record_skill_usage(test_tenant.id, skill2.id, success=True)
            SkillRepository.record_skill_usage(test_tenant.id, skill2.id, success=False)
            
            # Get summary
            summary = SkillRepository.get_tenant_usage_summary(test_tenant.id)
            assert summary['total_skills'] >= 2
            assert summary['total_usages'] >= 3
            assert summary['total_successes'] >= 2
            assert summary['total_failures'] >= 1
            assert 'success_rate' in summary
            
            # Cleanup
            stat1 = SkillUsageStat.query.filter_by(tenant_id=test_tenant.id, skill_id=skill1.id).first()
            stat2 = SkillUsageStat.query.filter_by(tenant_id=test_tenant.id, skill_id=skill2.id).first()
            db.session.delete(stat1)
            db.session.delete(stat2)
            db.session.delete(skill1)
            db.session.delete(skill2)
            db.session.commit()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
