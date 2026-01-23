"""
数据库模型定义
包含User和LoginHistory表
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import bcrypt as bcrypt_lib  # 使用bcrypt原生库替代passlib

db = SQLAlchemy()


class Tenant(db.Model):
    """租户模型 - 多租户SaaS架构"""
    __tablename__ = 'tenants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # 租户名称（企业名/组织名）
    
    # 配额和限制配置（JSON格式）
    # 示例：{"max_sessions": 100, "max_users": 50, "max_skills": 20}
    quota_config = db.Column(db.JSON, nullable=True)
    
    # 状态
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # 关联关系
    users = db.relationship('User', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Tenant {self.name}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'quota_config': self.quota_config,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class User(UserMixin, db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    # 多租户关联
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True, index=True)
    
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
        
        # 租户ID + 创建时间：优化租户级查询
        db.Index('idx_tenant_created', 'tenant_id', 'created_at'),
        
        # 租户ID + 状态：优化租户级统计
        db.Index('idx_tenant_status', 'tenant_id', 'status'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)  # 允许NULL支持匿名用户
    
    # 多租户关联（冗余字段，便于查询优化）
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=True, index=True)
    
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
    tenant = db.relationship('Tenant', backref=db.backref('discussion_sessions', lazy='dynamic'))
    
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


class Skill(db.Model):
    """技能模型 - 存储租户自定义的Agent技能"""
    __tablename__ = 'skills'
    
    # 复合索引定义
    __table_args__ = (
        # 租户ID + 分类：优化租户技能分类查询
        db.Index('idx_skills_tenant_category', 'tenant_id', 'category'),
        
        # 租户ID + 创建时间：优化租户技能列表查询
        db.Index('idx_skills_tenant_created', 'tenant_id', 'created_at'),
        
        # 名称唯一性约束（同一租户内技能名称不能重复）
        db.UniqueConstraint('tenant_id', 'name', name='uq_tenant_skill_name'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    
    # 技能元数据（对应YAML frontmatter）
    name = db.Column(db.String(100), nullable=False)                     # 技能唯一标识
    display_name = db.Column(db.String(200), nullable=False)             # 技能显示名称
    version = db.Column(db.String(20), default='1.0.0', nullable=False)  # 语义化版本号
    category = db.Column(db.String(50), nullable=False, index=True)      # 分类（analysis/technical/financial等）
    tags = db.Column(db.JSON, nullable=True)                             # 标签数组
    description = db.Column(db.Text, nullable=True)                      # 技能描述
    
    # 技能内容（Markdown格式，不含frontmatter）
    content = db.Column(db.Text, nullable=False)
    
    # 适用范围
    applicable_roles = db.Column(db.JSON, nullable=True)                 # 适用角色列表 ['策论家', '监察官']
    requirements = db.Column(db.JSON, nullable=True)                     # 使用要求 {context: '...', output: '...'}
    
    # 作者和版权
    author = db.Column(db.String(100), nullable=True)
    source = db.Column(db.String(200), nullable=True)                    # 来源（URL/GitHub repo）
    
    # 状态
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_builtin = db.Column(db.Boolean, default=False, nullable=False)    # 是否为内置技能（不可删除）
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关联关系
    tenant = db.relationship('Tenant', backref=db.backref('skills', lazy='dynamic'))
    subscriptions = db.relationship('TenantSkillSubscription', back_populates='skill', cascade='all, delete-orphan')
    usage_stats = db.relationship('SkillUsageStat', back_populates='skill', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Skill {self.name} v{self.version} tenant={self.tenant_id}>'
    
    def to_dict(self, include_content=False):
        """转换为字典格式"""
        result = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'name': self.name,
            'display_name': self.display_name,
            'version': self.version,
            'category': self.category,
            'tags': self.tags,
            'description': self.description,
            'applicable_roles': self.applicable_roles,
            'requirements': self.requirements,
            'author': self.author,
            'source': self.source,
            'is_active': self.is_active,
            'is_builtin': self.is_builtin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_content:
            result['content'] = self.content
        
        return result


class TenantSkillSubscription(db.Model):
    """租户技能订阅关系 - 管理租户对技能的启用状态"""
    __tablename__ = 'tenant_skill_subscriptions'
    
    # 复合索引定义
    __table_args__ = (
        # 租户ID + 启用状态：快速查询租户已启用的技能
        db.Index('idx_tenant_enabled', 'tenant_id', 'enabled'),
        
        # 技能ID + 租户ID：唯一约束（一个租户对一个技能只有一条订阅记录）
        db.UniqueConstraint('tenant_id', 'skill_id', name='uq_tenant_skill'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False, index=True)
    
    # 订阅状态
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    
    # 自定义配置（可选，为技能提供租户特定的参数）
    custom_config = db.Column(db.JSON, nullable=True)
    
    # 时间戳
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关联关系
    tenant = db.relationship('Tenant', backref=db.backref('skill_subscriptions', lazy='dynamic'))
    skill = db.relationship('Skill', back_populates='subscriptions')
    
    def __repr__(self):
        return f'<TenantSkillSubscription tenant={self.tenant_id} skill={self.skill_id} enabled={self.enabled}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'skill_id': self.skill_id,
            'enabled': self.enabled,
            'custom_config': self.custom_config,
            'subscribed_at': self.subscribed_at.isoformat() if self.subscribed_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SkillUsageStat(db.Model):
    """技能使用统计 - 跟踪技能被使用的频率"""
    __tablename__ = 'skill_usage_stats'
    
    # 复合索引定义
    __table_args__ = (
        # 租户ID + 技能ID：统计特定租户的技能使用情况
        db.Index('idx_tenant_skill', 'tenant_id', 'skill_id'),
        
        # 技能ID + 使用次数：排序最受欢迎的技能
        db.Index('idx_skill_usage', 'skill_id', 'usage_count'),
        
        # 租户ID + 技能ID唯一约束
        db.UniqueConstraint('tenant_id', 'skill_id', name='uq_tenant_skill_stat'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False, index=True)
    
    # 统计数据
    usage_count = db.Column(db.Integer, default=0, nullable=False)       # 累计使用次数
    last_used_at = db.Column(db.DateTime, nullable=True)                 # 最后使用时间
    
    # 使用效果统计（可选，未来可扩展）
    success_count = db.Column(db.Integer, default=0, nullable=False)     # 成功使用次数
    failure_count = db.Column(db.Integer, default=0, nullable=False)     # 失败次数
    avg_execution_time = db.Column(db.Float, nullable=True)              # 平均执行时间（秒）
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关联关系
    tenant = db.relationship('Tenant', backref=db.backref('skill_usage_stats', lazy='dynamic'))
    skill = db.relationship('Skill', back_populates='usage_stats')
    
    def increment_usage(self, success=True, execution_time=None):
        """增加使用次数并更新统计"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        # 更新平均执行时间（移动平均）
        if execution_time is not None:
            if self.avg_execution_time is None:
                self.avg_execution_time = execution_time
            else:
                # 指数移动平均：新值权重0.3，旧值权重0.7
                self.avg_execution_time = 0.7 * self.avg_execution_time + 0.3 * execution_time
    
    def __repr__(self):
        return f'<SkillUsageStat tenant={self.tenant_id} skill={self.skill_id} usage={self.usage_count}>'
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'skill_id': self.skill_id,
            'usage_count': self.usage_count,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': (self.success_count / self.usage_count * 100) if self.usage_count > 0 else 0,
            'avg_execution_time': self.avg_execution_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
