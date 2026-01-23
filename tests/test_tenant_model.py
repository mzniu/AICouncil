"""
测试Tenant模型和多租户功能
"""
import pytest
from src.models import db, User, Tenant, DiscussionSession
from datetime import datetime


def test_tenant_model_creation(app):
    """测试Tenant模型创建"""
    with app.app_context():
        # 创建租户
        tenant = Tenant(
            name="Test Organization",
            quota_config={"max_sessions": 100, "max_users": 50},
            is_active=True
        )
        db.session.add(tenant)
        db.session.commit()
        
        # 验证创建成功
        assert tenant.id is not None
        assert tenant.name == "Test Organization"
        assert tenant.quota_config["max_sessions"] == 100
        assert tenant.is_active is True
        assert tenant.created_at is not None
        
        # 清理
        db.session.delete(tenant)
        db.session.commit()


def test_user_tenant_relationship(app):
    """测试User和Tenant的关系"""
    with app.app_context():
        # 创建租户
        tenant = Tenant(name="Test Tenant", is_active=True)
        db.session.add(tenant)
        db.session.commit()
        
        # 创建用户并关联租户
        user = User(
            username="testuser_tenant",
            email="tenant@test.com",
            tenant_id=tenant.id
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        
        # 验证关系
        assert user.tenant_id == tenant.id
        assert user.tenant.name == "Test Tenant"
        assert user in tenant.users.all()
        
        # 清理
        db.session.delete(user)
        db.session.delete(tenant)
        db.session.commit()


def test_session_tenant_relationship(app):
    """测试DiscussionSession和Tenant的关系"""
    with app.app_context():
        # 创建租户和用户
        tenant = Tenant(name="Session Test Tenant", is_active=True)
        db.session.add(tenant)
        db.session.commit()
        
        user = User(
            username="sessionuser",
            email="session@test.com",
            tenant_id=tenant.id
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        
        # 创建讨论会话
        session = DiscussionSession(
            session_id="test_session_123",
            user_id=user.id,
            tenant_id=tenant.id,
            issue="Test issue",
            status="running"
        )
        db.session.add(session)
        db.session.commit()
        
        # 验证关系
        assert session.tenant_id == tenant.id
        assert session.tenant.name == "Session Test Tenant"
        assert session in tenant.discussion_sessions.all()
        
        # 清理
        db.session.delete(session)
        db.session.delete(user)
        db.session.delete(tenant)
        db.session.commit()


def test_tenant_nullable_fields(app):
    """测试tenant_id字段可空（向后兼容）"""
    with app.app_context():
        # 创建没有tenant_id的用户（旧数据兼容）
        user = User(
            username="legacy_user",
            email="legacy@test.com"
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        
        assert user.tenant_id is None
        assert user.tenant is None
        
        # 创建没有tenant_id的会话
        session = DiscussionSession(
            session_id="legacy_session_456",
            user_id=user.id,
            issue="Legacy issue",
            status="running"
        )
        db.session.add(session)
        db.session.commit()
        
        assert session.tenant_id is None
        assert session.tenant is None
        
        # 清理
        db.session.delete(session)
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def app():
    """创建测试用的Flask应用"""
    from src.web.app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()
