"""
数据库模型定义
包含User和LoginHistory表
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import bcrypt as bcrypt_lib  # 使用bcrypt原生库替代passlib

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    # MFA相关字段
    mfa_enabled = db.Column(db.Boolean, default=False, nullable=False)
    mfa_secret = db.Column(db.String(32), nullable=True)  # TOTP secret (base32)
    mfa_backup_codes = db.Column(db.Text, nullable=True)  # JSON array of bcrypt hashes
    
    # Session管理
    session_version = db.Column(db.Integer, default=1, nullable=False)  # 用于强制logout
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # 登录失败锁定
    failed_login_count = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)  # 锁定到何时
    
    # 关联关系
    login_history = db.relationship('LoginHistory', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """设置密码（bcrypt哈希）"""
        # bcrypt需要bytes输入
        if isinstance(password, str):
            password = password.encode('utf-8')
        salt = bcrypt_lib.gensalt()
        self.password_hash = bcrypt_lib.hashpw(password, salt).decode('utf-8')
    
    def check_password(self, password):
        """验证密码"""
        # bcrypt需要bytes输入
        if isinstance(password, str):
            password = password.encode('utf-8')
        password_hash = self.password_hash
        if isinstance(password_hash, str):
            password_hash = password_hash.encode('utf-8')
        return bcrypt_lib.checkpw(password, password_hash)
    
    def is_locked(self):
        """检查账户是否被锁定"""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def increment_failed_login(self):
        """增加失败登录次数，达到5次时锁定5分钟"""
        from datetime import timedelta
        self.failed_login_count += 1
        if self.failed_login_count >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=5)
    
    def reset_failed_login(self):
        """重置失败登录次数"""
        self.failed_login_count = 0
        self.locked_until = None
    
    def force_logout(self):
        """强制所有session失效（递增session_version）"""
        self.session_version += 1
    
    def __repr__(self):
        return f'<User {self.username}>'


class LoginHistory(db.Model):
    """登录历史记录"""
    __tablename__ = 'login_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # 操作类型：login_success, login_failed, logout, mfa_success, mfa_failed, account_locked
    action = db.Column(db.String(50), nullable=False, index=True)
    
    # 请求信息
    ip = db.Column(db.String(45), nullable=True)  # IPv6最长39个字符，留余量
    user_agent = db.Column(db.String(255), nullable=True)
    
    # 是否成功
    success = db.Column(db.Boolean, nullable=False)
    
    # 时间戳
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<LoginHistory user_id={self.user_id} action={self.action} success={self.success}>'
