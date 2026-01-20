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
    
    # 管理员权限
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    
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


class PasswordResetToken(db.Model):
    """密码重置令牌"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)  # 标记token是否已使用
    
    # 关联关系
    user = db.relationship('User', backref=db.backref('reset_tokens', lazy='dynamic'))
    
    def is_valid(self):
        """检查token是否有效"""
        if self.used_at is not None:
            return False  # 已使用
        if datetime.utcnow() > self.expires_at:
            return False  # 已过期
        return True
    
    def mark_as_used(self):
        """标记token为已使用"""
        self.used_at = datetime.utcnow()
    
    def __repr__(self):
        return f'<PasswordResetToken user_id={self.user_id} expires_at={self.expires_at}>'


class DiscussionSession(db.Model):
    """议事会话模型 - 存储完整的讨论数据"""
    __tablename__ = 'discussion_sessions'
    
    # 复合索引定义（优化查询性能）
    __table_args__ = (
        # 用户ID + 创建时间：优化用户会话列表查询（按时间倒序）
        db.Index('idx_user_created', 'user_id', 'created_at'),
        
        # 用户ID + 状态 + 创建时间：优化带状态过滤的查询
        db.Index('idx_user_status_created', 'user_id', 'status', 'created_at'),
        
        # 用户ID + 状态：优化状态统计查询
        db.Index('idx_user_status', 'user_id', 'status'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # 讨论配置
    issue = db.Column(db.Text, nullable=False)
    backend = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    config = db.Column(db.JSON, nullable=True)  # {rounds, planners, auditors, reasoning, agent_configs}
    
    # 状态管理
    status = db.Column(db.String(20), default='running', nullable=False, index=True)  # running/completed/failed/stopped
    
    # 讨论数据（JSON/JSONB存储，PostgreSQL会自动使用JSONB）
    history = db.Column(db.JSON, nullable=True)                    # 完整history.json
    decomposition = db.Column(db.JSON, nullable=True)              # decomposition.json
    final_session_data = db.Column(db.JSON, nullable=True)         # final_session_data.json
    search_references = db.Column(db.JSON, nullable=True)          # search_references.json
    interventions = db.Column(db.JSON, nullable=True)              # 用户干预记录列表 [{content, timestamp}]
    
    # 报告数据
    report_html = db.Column(db.Text, nullable=True)                # 最新报告HTML
    report_json = db.Column(db.JSON, nullable=True)                # 结构化报告
    report_version = db.Column(db.Integer, default=1, nullable=False)  # 支持重新生成计数
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # 关联关系
    user = db.relationship('User', backref=db.backref('discussion_sessions', lazy='dynamic', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<DiscussionSession {self.session_id} by user {self.user_id} status={self.status}>'
    
    def to_dict(self, include_data=True):
        """转换为字典格式，用于API响应"""
        result = {
            'session_id': self.session_id,
            'issue': self.issue,
            'backend': self.backend,
            'model': self.model,
            'config': self.config,
            'status': self.status,
            'report_version': self.report_version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
        
        if include_data:
            result.update({
                'history': self.history,
                'decomposition': self.decomposition,
                'final_session_data': self.final_session_data,
                'search_references': self.search_references,
                'interventions': self.interventions,
                'report_html': self.report_html,
                'report_json': self.report_json,
            })
        
        return result
