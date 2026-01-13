"""
数据库模型单元测试
测试User和LoginHistory模型的基本功能
"""
import pytest
from datetime import datetime, timedelta
from src.models import db, User, LoginHistory


@pytest.fixture
def app():
    """创建测试Flask应用"""
    from flask import Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key-for-testing-only'
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


class TestUserModel:
    """测试User模型"""
    
    def test_create_user(self, app):
        """测试创建用户"""
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com',
                mfa_enabled=False
            )
            user.set_password('TestPassword123!')
            db.session.add(user)
            db.session.commit()
            
            # 验证用户创建成功
            assert user.id is not None
            assert user.username == 'testuser'
            assert user.email == 'test@example.com'
            assert user.mfa_enabled is False
            assert user.session_version == 1
            assert user.failed_login_count == 0
    
    def test_password_hashing(self, app):
        """测试密码哈希和验证"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            password = 'SecurePassword123!'
            user.set_password(password)
            
            # 验证密码哈希不等于明文
            assert user.password_hash != password
            
            # 验证正确密码
            assert user.check_password(password) is True
            
            # 验证错误密码
            assert user.check_password('WrongPassword') is False
    
    def test_account_locking(self, app):
        """测试账户锁定机制"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('TestPassword123!')  # 必须设置密码
            db.session.add(user)
            db.session.commit()
            
            # 初始状态未锁定
            assert user.is_locked() is False
            
            # 模拟5次失败登录
            for i in range(5):
                user.increment_failed_login()
                db.session.commit()
            
            # 第5次后应该被锁定
            assert user.is_locked() is True
            assert user.locked_until is not None
            
            # 重置锁定
            user.reset_failed_login()
            db.session.commit()
            
            assert user.is_locked() is False
            assert user.failed_login_count == 0
            assert user.locked_until is None
    
    def test_force_logout(self, app):
        """测试强制logout（递增session_version）"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('TestPassword123!')  # 必须设置密码
            db.session.add(user)
            db.session.commit()
            
            initial_version = user.session_version
            user.force_logout()
            db.session.commit()
            
            assert user.session_version == initial_version + 1
    
    def test_unique_constraints(self, app):
        """测试唯一性约束（用户名和邮箱）"""
        with app.app_context():
            user1 = User(username='testuser', email='test@example.com')
            user1.set_password('password')
            db.session.add(user1)
            db.session.commit()
            
            # 尝试创建重复用户名
            user2 = User(username='testuser', email='other@example.com')
            user2.set_password('password')
            db.session.add(user2)
            
            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()
            
            db.session.rollback()
            
            # 尝试创建重复邮箱
            user3 = User(username='otheruser', email='test@example.com')
            user3.set_password('password')
            db.session.add(user3)
            
            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()


class TestLoginHistoryModel:
    """测试LoginHistory模型"""
    
    def test_create_login_history(self, app):
        """测试创建登录历史记录"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            
            history = LoginHistory(
                user_id=user.id,
                action='login_success',
                ip='127.0.0.1',
                user_agent='Mozilla/5.0',
                success=True
            )
            db.session.add(history)
            db.session.commit()
            
            # 验证记录创建成功
            assert history.id is not None
            assert history.user_id == user.id
            assert history.action == 'login_success'
            assert history.success is True
    
    def test_relationship(self, app):
        """测试User和LoginHistory的关联关系"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            
            # 添加多条历史记录
            for i in range(3):
                history = LoginHistory(
                    user_id=user.id,
                    action='login_success',
                    ip='127.0.0.1',
                    success=True
                )
                db.session.add(history)
            db.session.commit()
            
            # 通过关联查询
            assert user.login_history.count() == 3
    
    def test_cascade_delete(self, app):
        """测试级联删除（删除用户时自动删除历史记录）"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            
            # 添加历史记录
            history = LoginHistory(
                user_id=user.id,
                action='login_success',
                ip='127.0.0.1',
                success=True
            )
            db.session.add(history)
            db.session.commit()
            
            user_id = user.id
            
            # 删除用户
            db.session.delete(user)
            db.session.commit()
            
            # 验证历史记录也被删除
            orphan_history = LoginHistory.query.filter_by(user_id=user_id).first()
            assert orphan_history is None


class TestPasswordSecurity:
    """测试密码安全性"""
    
    def test_bcrypt_hashing(self, app):
        """验证使用bcrypt哈希"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('TestPassword123!')
            
            # bcrypt哈希以$2b$开头（使用bcrypt原生库）
            assert user.password_hash.startswith('$2b$')
    
    def test_same_password_different_hash(self, app):
        """测试相同密码产生不同哈希（salt随机性）"""
        with app.app_context():
            user1 = User(username='user1', email='user1@example.com')
            user2 = User(username='user2', email='user2@example.com')
            
            password = 'SamePassword123!'
            user1.set_password(password)
            user2.set_password(password)
            
            # 相同密码应产生不同哈希
            assert user1.password_hash != user2.password_hash
            
            # 但都能验证成功
            assert user1.check_password(password) is True
            assert user2.check_password(password) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
