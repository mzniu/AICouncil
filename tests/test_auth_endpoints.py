"""
认证端点测试
测试注册、登录、登出、MFA功能
"""
import pytest
import json
from datetime import datetime, timedelta
from src.models import db, User, LoginHistory
from src.auth_routes import generate_backup_codes, verify_backup_code, validate_password_strength


@pytest.fixture
def app():
    """创建测试Flask应用"""
    from flask import Flask
    from src.models import db
    from src.auth_routes import auth_bp
    from flask_login import LoginManager
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key-for-testing-only'
    app.config['WTF_CSRF_ENABLED'] = False  # 测试时禁用CSRF
    
    # 手动初始化db和login_manager（不使用init_auth以避免Flask-Session冲突）
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        from flask import session
        from src.models import User
        user = db.session.get(User, int(user_id))
        if user and session.get('session_version') != user.session_version:
            return None
        return user
    
    app.register_blueprint(auth_bp)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """创建测试用户"""
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com',
            mfa_enabled=False
        )
        user.set_password('TestPass123!')
        db.session.add(user)
        db.session.commit()
        return user


class TestPasswordValidation:
    """测试密码强度验证"""
    
    def test_weak_password_too_short(self):
        """测试密码过短"""
        valid, msg = validate_password_strength('Pass1!')
        assert valid is False
        assert isinstance(msg, dict)
        assert 'length' in msg
    
    def test_weak_password_no_uppercase(self):
        """测试缺少大写字母"""
        valid, msg = validate_password_strength('password123!')
        assert valid is False
        assert isinstance(msg, dict)
        assert 'uppercase' in msg
    
    def test_weak_password_no_lowercase(self):
        """测试缺少小写字母"""
        valid, msg = validate_password_strength('PASSWORD123!')
        assert valid is False
        assert isinstance(msg, dict)
        assert 'lowercase' in msg
    
    def test_weak_password_no_digit(self):
        """测试缺少数字"""
        valid, msg = validate_password_strength('Password!')
        assert valid is False
        assert isinstance(msg, dict)
        assert 'digit' in msg
    
    def test_weak_password_no_special(self):
        """测试缺少特殊字符"""
        valid, msg = validate_password_strength('Password123')
        assert valid is False
        assert isinstance(msg, dict)
        assert 'special' in msg
    
    def test_strong_password(self):
        """测试强密码"""
        valid, msg = validate_password_strength('StrongPass123!')
        assert valid is True


class TestBackupCodes:
    """测试备份码功能"""
    
    def test_generate_backup_codes(self):
        """测试生成备份码"""
        plain_codes, hashed_codes = generate_backup_codes(10)
        
        assert len(plain_codes) == 10
        assert len(hashed_codes) == 10
        
        # 验证是8位数字
        for code in plain_codes:
            assert len(code) == 8
            assert code.isdigit()
        
        # 验证哈希以$2b$开头
        for hashed in hashed_codes:
            assert hashed.startswith('$2b$')
    
    def test_verify_backup_code_success(self):
        """测试验证正确的备份码"""
        plain_codes, hashed_codes = generate_backup_codes(3)
        
        # 使用第二个备份码
        success, remaining = verify_backup_code(plain_codes[1], hashed_codes)
        
        assert success is True
        assert len(remaining) == 2
        # 验证第二个备份码已被移除
        assert hashed_codes[1] not in remaining
    
    def test_verify_backup_code_fail(self):
        """测试验证错误的备份码"""
        _, hashed_codes = generate_backup_codes(3)
        
        success, remaining = verify_backup_code('99999999', hashed_codes)
        
        assert success is False
        assert len(remaining) == 3


class TestRegister:
    """测试注册功能"""
    
    def test_register_success(self, client, app, monkeypatch):
        """测试成功注册"""
        import src.auth_routes
        monkeypatch.setattr(src.auth_routes, 'ALLOW_PUBLIC_REGISTRATION', True)
        
        with app.app_context():
            response = client.post('/api/auth/register', json={
                'username': 'newuser',
                'password': 'NewPass123!',
                'email': 'new@example.com'
            })
            
            assert response.status_code == 201
            data = response.get_json()
            assert data['message'] == '注册成功'
            assert 'user_id' in data
            
            # 验证用户已创建
            user = User.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.email == 'new@example.com'
    
    def test_register_disabled(self, client, app, monkeypatch):
        """测试公开注册被禁用"""
        import src.auth_routes
        monkeypatch.setattr(src.auth_routes, 'ALLOW_PUBLIC_REGISTRATION', False)
        
        response = client.post('/api/auth/register', json={
            'username': 'newuser',
            'password': 'NewPass123!',
            'email': 'new@example.com'
        })
        
        assert response.status_code == 403
        data = response.get_json()
        assert 'registration_disabled' in data['error'] or '禁用' in data.get('message', '')
    
    def test_register_weak_password(self, client, app, monkeypatch):
        """测试弱密码被拒绝"""
        # 在模块级别修改配置
        import src.auth_routes
        monkeypatch.setattr(src.auth_routes, 'ALLOW_PUBLIC_REGISTRATION', True)
        
        response = client.post('/api/auth/register', json={
            'username': 'newuser',
            'password': 'weak',
            'email': 'new@example.com'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        # 密码验证失败时，error是字典
        assert isinstance(data['error'], dict)
        assert len(data['error']) > 0  # 至少有一个验证错误
    
    def test_register_duplicate_username(self, client, app, test_user, monkeypatch):
        """测试重复用户名"""
        import src.auth_routes
        monkeypatch.setattr(src.auth_routes, 'ALLOW_PUBLIC_REGISTRATION', True)
        
        response = client.post('/api/auth/register', json={
            'username': 'testuser',  # 已存在
            'password': 'NewPass123!',
            'email': 'new@example.com'
        })
        
        assert response.status_code == 400
        assert '用户名已被使用' in response.get_json()['error']


class TestLogin:
    """测试登录功能"""
    
    def test_login_success(self, client, app, test_user):
        """测试正确密码登录"""
        response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'TestPass123!'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == '登录成功'
        assert data['requires_mfa'] is False
    
    def test_login_wrong_password(self, client, app, test_user):
        """测试错误密码"""
        response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'WrongPass123!'
        })
        
        assert response.status_code == 401
        assert '密码错误' in response.get_json()['error']
    
    def test_login_nonexistent_user(self, client, app):
        """测试不存在的用户"""
        response = client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'TestPass123!'
        })
        
        assert response.status_code == 401
    
    def test_login_account_lockout(self, client, app, test_user):
        """测试账户锁定"""
        # 5次错误登录
        for i in range(5):
            client.post('/api/auth/login', json={
                'username': 'testuser',
                'password': 'WrongPass!'
            })
        
        # 第6次应该被锁定
        response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'TestPass123!'  # 即使密码正确也应该被锁
        })
        
        assert response.status_code == 403
        assert '锁定' in response.get_json()['error']


class TestAuthStatus:
    """测试认证状态查询"""
    
    def test_status_not_authenticated(self, client):
        """测试未认证状态"""
        response = client.get('/api/auth/status')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['authenticated'] is False
    
    def test_status_authenticated(self, client, app, test_user):
        """测试已认证状态"""
        # 先登录
        client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'TestPass123!'
        })
        
        response = client.get('/api/auth/status')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['authenticated'] is True
        assert data['username'] == 'testuser'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
