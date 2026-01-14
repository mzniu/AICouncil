"""
认证系统配置和初始化
包括数据库初始化、Flask-Login、Flask-Migrate、CLI命令
"""
import os
import sys
import click
import secrets
from pathlib import Path
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_session import Session
from dotenv import load_dotenv

from src.models import db, User, LoginHistory
from src.utils.logger import logger

# 加载环境变量
load_dotenv()


def validate_config(app):
    """验证必需的配置项"""
    secret_key = app.config.get('SECRET_KEY')
    
    if not secret_key or secret_key == 'dev-secret-key-please-change-in-production':
        logger.warning("⚠️  SECRET_KEY未设置或使用默认值，这在生产环境中不安全！")
        logger.warning("请在.env文件中设置: SECRET_KEY=<your-random-32-byte-key>")
        if app.config.get('ENV') == 'production':
            raise ValueError("生产环境必须设置安全的SECRET_KEY（长度>=32）")
    
    if len(secret_key) < 32:
        logger.warning(f"⚠️  SECRET_KEY长度不足（当前{len(secret_key)}字节，建议>=32字节）")


def init_auth(app: Flask):
    """
    初始化认证系统
    
    集成内容：
    1. Flask-SQLAlchemy（数据库）
    2. Flask-Migrate（数据库迁移）
    3. Flask-Login（会话管理）
    4. Flask-Session（服务端session）
    5. CLI命令（create-admin）
    """
    
    # === 数据库配置 ===
    # 确保data目录在项目根目录（向上两级：src/web -> src -> 项目根）
    logger.info(f"📁 Flask app.root_path: {app.root_path}")
    data_dir = Path(app.root_path).parent.parent / 'data'
    logger.info(f"📁 计算的data目录: {data_dir.absolute()}")
    
    # 创建data目录并验证权限
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ data目录已准备: {data_dir.absolute()}")
    except Exception as e:
        logger.error(f"❌ 创建data目录失败: {e}")
        raise RuntimeError(f"无法创建数据库目录 {data_dir}: {e}")
    
    # 检查目录写权限
    if not os.access(data_dir, os.W_OK):
        logger.error(f"❌ data目录无写权限: {data_dir.absolute()}")
        raise PermissionError(f"无法写入数据库目录: {data_dir.absolute()}")
    
    # 读取DATABASE_URL，如果为空字符串则使用默认相对路径
    database_url = os.getenv('DATABASE_URL') or f"sqlite:///{data_dir.absolute() / 'users.db'}"
    logger.info(f"🗄️  数据库URI: {database_url}")
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # === Session配置（服务端存储） ===
    app.config['SESSION_TYPE'] = os.getenv('SESSION_TYPE', 'sqlalchemy')
    app.config['SESSION_SQLALCHEMY'] = db
    app.config['SESSION_PERMANENT'] = True  # 持久化session
    
    # Session超时时间（默认30天）
    app.config['PERMANENT_SESSION_LIFETIME'] = int(os.getenv('PERMANENT_SESSION_LIFETIME', 86400 * 30))
    
    # Session Cookie配置
    app.config['SESSION_COOKIE_NAME'] = os.getenv('SESSION_COOKIE_NAME', 'aicouncil_session')
    app.config['SESSION_COOKIE_HTTPONLY'] = os.getenv('SESSION_COOKIE_HTTPONLY', 'true').lower() == 'true'
    app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    
    # 生产环境强制HTTPS
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production' or os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    
    # === SECRET_KEY配置 ===
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-please-change-in-production')
    
    # 验证配置
    validate_config(app)
    
    # === 初始化扩展 ===
    db.init_app(app)
    Session(app)  # 初始化Flask-Session
    migrate = Migrate(app, db)
    
    # === Flask-Login配置 ===
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login_page'  # 未登录时重定向到login页面（视图函数名）
    login_manager.login_message = '请先登录'
    
    @login_manager.user_loader
    def load_user(user_id):
        """加载用户回调（Flask-Login要求）"""
        from flask import session
        user = db.session.get(User, int(user_id))
        
        # 验证session_version，如果不匹配则强制logout
        if user and session.get('session_version') != user.session_version:
            return None
        
        return user
    
    # === 创建表（如果不存在） ===
    with app.app_context():
        # 检查是否需要创建表（首次运行）
        try:
            db.create_all()
            logger.info("✅ 数据库表检查完成")
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            raise
    
    # === CLI命令 ===
    @app.cli.command('create-admin')
    @click.option('--username', prompt='管理员用户名', help='管理员用户名')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='管理员密码')
    @click.option('--email', prompt='管理员邮箱', help='管理员邮箱')
    def create_admin(username, password, email):
        """创建初始管理员账户"""
        from passlib.pwd import genword
        
        # 验证密码强度
        if len(password) < 8:
            click.echo('❌ 密码长度必须至少8位', err=True)
            sys.exit(1)
        
        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            click.echo(f'❌ 用户名 "{username}" 已存在', err=True)
            sys.exit(1)
        
        # 检查邮箱是否已存在
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            click.echo(f'❌ 邮箱 "{email}" 已被使用', err=True)
            sys.exit(1)
        
        # 创建管理员用户
        admin = User(
            username=username,
            email=email,
            mfa_enabled=False
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        
        click.echo(f'✅ 管理员账户创建成功！')
        click.echo(f'   用户名: {username}')
        click.echo(f'   邮箱: {email}')
        click.echo(f'   MFA: 未启用（可登录后在设置中启用）')
    
    @app.cli.command('generate-secret-key')
    def generate_secret_key():
        """生成随机SECRET_KEY"""
        key = secrets.token_urlsafe(32)
        click.echo(f'生成的SECRET_KEY（请复制到.env文件）：')
        click.echo(f'SECRET_KEY={key}')
    
    logger.info("✅ 认证系统初始化完成")
    return app
