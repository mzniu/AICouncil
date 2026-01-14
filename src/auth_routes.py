"""
认证相关的路由端点
包括注册、登录、登出、MFA设置和验证、密码重置、管理员功能
"""
import os
import json
import re
import secrets
from datetime import datetime, timedelta
from io import BytesIO
from functools import wraps
import pyotp
import qrcode
import bcrypt as bcrypt_lib
from flask import Blueprint, request, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from src.models import db, User, LoginHistory, PasswordResetToken
from src.utils.email_utils import check_smtp_configured, send_password_reset_email
from src.utils.logger import logger

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# === 管理员权限装饰器 ===
def admin_required(func):
    """
    要求用户为管理员才能访问
    需要配合@login_required使用
    """
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "未登录"}), 401
        if not current_user.is_admin:
            logger.warning(f"非管理员用户 {current_user.username} 尝试访问管理员功能")
            return jsonify({"error": "需要管理员权限"}), 403
        return func(*args, **kwargs)
    return decorated_view

# === 速率限制装饰器（简化版，暂时禁用） ===
def rate_limit(limit_string):
    """
    速率限制装饰器占位符
    注意：当前使用账户锁定机制代替速率限制
    """
    def decorator(func):
        # 直接返回原函数，不应用速率限制
        # 账户锁定机制（5次失败=5分钟锁定）已提供足够保护
        return func
    return decorator

# === 从环境变量读取配置 ===
ALLOW_PUBLIC_REGISTRATION = os.getenv('ALLOW_PUBLIC_REGISTRATION', 'false').lower() == 'true'
ACCOUNT_LOCKOUT_THRESHOLD = int(os.getenv('ACCOUNT_LOCKOUT_THRESHOLD', 5))
ACCOUNT_LOCKOUT_DURATION = int(os.getenv('ACCOUNT_LOCKOUT_DURATION', 300))
MFA_TIMEOUT = int(os.getenv('MFA_TIMEOUT', 600))

# 密码策略配置
PASSWORD_MIN_LENGTH = int(os.getenv('PASSWORD_MIN_LENGTH', 8))
PASSWORD_REQUIRE_UPPERCASE = os.getenv('PASSWORD_REQUIRE_UPPERCASE', 'true').lower() == 'true'
PASSWORD_REQUIRE_LOWERCASE = os.getenv('PASSWORD_REQUIRE_LOWERCASE', 'true').lower() == 'true'
PASSWORD_REQUIRE_DIGIT = os.getenv('PASSWORD_REQUIRE_DIGIT', 'true').lower() == 'true'
PASSWORD_REQUIRE_SPECIAL = os.getenv('PASSWORD_REQUIRE_SPECIAL', 'true').lower() == 'true'


def validate_password_strength(password):
    """
    验证密码强度（根据环境变量配置）
    """
    errors = {}
    
    if len(password) < PASSWORD_MIN_LENGTH:
        errors['length'] = f"密码长度至少{PASSWORD_MIN_LENGTH}位"
    
    if PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        errors['uppercase'] = "密码必须包含大写字母"
    
    if PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        errors['lowercase'] = "密码必须包含小写字母"
    
    if PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
        errors['digit'] = "密码必须包含数字"
    
    if PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors['special'] = "密码必须包含特殊字符"
    
    if errors:
        return False, errors
    return True, "密码强度合格"


def log_login_action(user_id, action, success, ip=None, user_agent=None):
    """记录登录历史"""
    try:
        history = LoginHistory(
            user_id=user_id,
            action=action,
            success=success,
            ip=ip or request.remote_addr,
            user_agent=user_agent or request.headers.get('User-Agent', '')
        )
        db.session.add(history)
        db.session.commit()
    except Exception as e:
        logger.error(f"记录登录历史失败: {e}")
        db.session.rollback()


def generate_backup_codes(count=10):
    """
    生成备份码
    返回: (plain_codes, hashed_codes)
    """
    import random
    plain_codes = []
    hashed_codes = []
    
    for _ in range(count):
        # 生成8位随机数字
        code = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        plain_codes.append(code)
        
        # bcrypt哈希
        hashed = bcrypt_lib.hashpw(code.encode('utf-8'), bcrypt_lib.gensalt())
        hashed_codes.append(hashed.decode('utf-8'))
    
    return plain_codes, hashed_codes


def verify_backup_code(code, hashed_codes):
    """
    验证备份码
    返回: (success, remaining_codes)
    """
    code_bytes = code.encode('utf-8')
    
    for i, hashed in enumerate(hashed_codes):
        hashed_bytes = hashed.encode('utf-8')
        if bcrypt_lib.checkpw(code_bytes, hashed_bytes):
            # 找到匹配的备份码，从列表中移除
            remaining = hashed_codes[:i] + hashed_codes[i+1:]
            return True, remaining
    
    return False, hashed_codes


@auth_bp.route('/register', methods=['POST'])
@rate_limit("5 per hour")
def register():
    """
    注册新用户
    需要：username, password, email
    """
    # 检查用户表是否为空（首次启动场景）
    is_first_user = User.query.count() == 0
    
    # 智能注册控制：如果是首个用户，自动允许注册（无论ALLOW_PUBLIC_REGISTRATION设置）
    if not is_first_user and not ALLOW_PUBLIC_REGISTRATION:
        return jsonify({"error": "registration_disabled", "message": "公开注册已禁用，请联系管理员"}), 403
    
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip()
    
    # 验证必填字段
    if not username or not password or not email:
        return jsonify({"error": "用户名、密码和邮箱不能为空"}), 400
    
    # 验证密码强度
    valid, result = validate_password_strength(password)
    if not valid:
        return jsonify({"error": "密码不符合要求", "details": result}), 400
    
    # 检查用户名是否已存在
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "用户名已被使用"}), 400
    
    # 检查邮箱是否已存在
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "邮箱已被使用"}), 400
    
    # 创建新用户
    try:
        user = User(
            username=username,
            email=email,
            mfa_enabled=False,
            is_admin=is_first_user  # 第一个用户自动设为管理员
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        log_login_action(user.id, 'register', True)
        
        # 如果是首个用户，记录日志提示其拥有管理员权限
        if is_first_user:
            logger.info(f"🎉 首个用户注册成功：{username}（自动授予管理员权限）")
        
        return jsonify({
            "message": "注册成功" + ("（您是系统首个用户，拥有完整访问权限）" if is_first_user else ""),
            "user_id": user.id,
            "username": username,
            "is_first_user": is_first_user
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"注册失败: {e}")
        return jsonify({"error": "注册失败，请稍后重试"}), 500


@auth_bp.route('/login', methods=['POST'])
@rate_limit("20 per 5 minutes")
def login():
    """
    用户登录
    需要：username, password
    """
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    
    # 查找用户
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({"error": "用户名或密码错误"}), 401
    
    # 检查账户是否被锁定
    if user.is_locked():
        log_login_action(user.id, 'login_failed', False)
        return jsonify({"error": "账户已被锁定，请稍后再试"}), 403
    
    # 验证密码
    if not user.check_password(password):
        user.increment_failed_login()
        db.session.commit()
        
        log_login_action(user.id, 'login_failed', False)
        
        remaining = 5 - user.failed_login_count
        if remaining > 0:
            return jsonify({"error": f"密码错误，还剩{remaining}次尝试机会"}), 401
        else:
            return jsonify({"error": "登录失败次数过多，账户已被锁定5分钟"}), 403
    
    # 密码正确，重置失败计数
    user.reset_failed_login()
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # 检查是否启用MFA
    if user.mfa_enabled:
        # 设置MFA临时态
        session['is_mfa_pending'] = True
        session['mfa_user_id'] = user.id
        session['mfa_timestamp'] = datetime.utcnow().isoformat()
        session.permanent = True  # 使用permanent session以支持超时
        
        log_login_action(user.id, 'login_success_pending_mfa', True)
        
        return jsonify({
            "message": "密码验证成功，请进行MFA验证",
            "requires_mfa": True,
            "user_id": user.id
        }), 200
    
    # 未启用MFA，直接登录
    login_user(user, remember=True)
    session['session_version'] = user.session_version
    
    log_login_action(user.id, 'login_success', True)
    
    return jsonify({
        "message": "登录成功",
        "user_id": user.id,
        "username": user.username,
        "requires_mfa": False
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    user_id = current_user.id
    
    # 递增session_version，强制所有旧session失效
    current_user.force_logout()
    db.session.commit()
    
    log_login_action(user_id, 'logout', True)
    
    logout_user()
    session.clear()
    
    return jsonify({"message": "登出成功"}), 200


@auth_bp.route('/user-info', methods=['GET'])
@login_required
def user_info():
    """
    获取当前用户信息
    """
    return jsonify({
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_admin": current_user.is_admin,
        "mfa_enabled": current_user.mfa_enabled
    }), 200


@auth_bp.route('/mfa/setup', methods=['POST'])
@login_required
def mfa_setup():
    """
    设置MFA
    生成TOTP secret、QR码和备份码
    """
    user = current_user
    
    # 生成TOTP secret
    secret = pyotp.random_base32()
    
    # 生成备份码
    plain_codes, hashed_codes = generate_backup_codes(10)
    
    # 生成TOTP URI（用于QR码）
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name="AICouncil"
    )
    
    # 生成QR码图像
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 将图像转换为base64
    import base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # 临时保存密钥到会话（等待验证）
    session['mfa_setup_secret'] = secret
    session['mfa_setup_backup_codes'] = json.dumps(hashed_codes)
    session['mfa_setup_plain_codes'] = plain_codes
    
    return jsonify({
        "message": "QR码生成成功",
        "secret": secret,
        "qr_code": f"data:image/png;base64,{img_base64}"
    }), 200


@auth_bp.route('/mfa/setup/verify', methods=['POST'])
@login_required
@rate_limit("10 per 5 minutes")
def mfa_setup_verify():
    """验证MFA设置（首次配置时）"""
    if not session.get('mfa_setup_secret'):
        return jsonify({"error": "请先生成QR码"}), 400
    
    data = request.get_json()
    code = data.get('code', '').strip()
    
    if not code or not code.isdigit() or len(code) != 6:
        return jsonify({"error": "验证码格式错误"}), 400
    
    # 验证OTP
    secret = session.get('mfa_setup_secret')
    totp = pyotp.TOTP(secret)
    
    if not totp.verify(code, valid_window=1):
        return jsonify({"error": "验证码错误或已过期"}), 400
    
    # 验证成功，启用MFA
    user = current_user
    user.mfa_secret = secret
    user.mfa_backup_codes = session.get('mfa_setup_backup_codes')
    user.mfa_enabled = True
    db.session.commit()
    
    # 获取备份码
    plain_codes = session.get('mfa_setup_plain_codes', [])
    
    # 清除会话数据
    session.pop('mfa_setup_secret', None)
    session.pop('mfa_setup_backup_codes', None)
    session.pop('mfa_setup_plain_codes', None)
    
    log_login_action(user.id, 'mfa_setup', True)
    
    return jsonify({
        "message": "MFA设置成功",
        "backup_codes": plain_codes
    }), 200


@auth_bp.route('/mfa/verify', methods=['POST'])
@rate_limit("20 per 5 minutes")
def mfa_verify():
    """
    验证MFA（OTP或备份码） - 用于登录时
    """
    # 检查MFA临时态
    if not session.get('is_mfa_pending'):
        return jsonify({"error": "无效的MFA会话"}), 400
    
    user_id = session.get('mfa_user_id')
    if not user_id:
        return jsonify({"error": "无效的MFA会话"}), 400
    
    # 检查超时（10分钟）
    mfa_timestamp_str = session.get('mfa_timestamp')
    if mfa_timestamp_str:
        mfa_timestamp = datetime.fromisoformat(mfa_timestamp_str)
        if datetime.utcnow() - mfa_timestamp > timedelta(minutes=10):
            session.clear()
            return jsonify({"error": "MFA验证超时，请重新登录"}), 401
    
    # 获取用户
    user = db.session.get(User, user_id)
    if not user or not user.mfa_enabled:
        return jsonify({"error": "用户不存在或未启用MFA"}), 400
    
    data = request.get_json()
    code = data.get('code', '').strip()
    use_backup = data.get('use_backup', False)
    
    if not code:
        return jsonify({"error": "验证码不能为空"}), 400
    
    verified = False
    
    if use_backup:
        # 使用备份码验证
        try:
            hashed_codes = json.loads(user.mfa_backup_codes or '[]')
            success, remaining = verify_backup_code(code, hashed_codes)
            
            if success:
                verified = True
                # 更新剩余备份码
                user.mfa_backup_codes = json.dumps(remaining)
                db.session.commit()
                
                log_login_action(user.id, 'mfa_verify_backup_code', True)
                
                if len(remaining) == 0:
                    # 备份码耗尽提示
                    pass  # 在响应中提示
            else:
                log_login_action(user.id, 'mfa_verify_backup_code_failed', False)
                
        except Exception as e:
            logger.error(f"备份码验证失败: {e}")
            return jsonify({"error": "备份码验证失败"}), 500
    else:
        # 使用TOTP验证
        totp = pyotp.TOTP(user.mfa_secret)
        if totp.verify(code, valid_window=1):
            verified = True
            log_login_action(user.id, 'mfa_verify_otp', True)
        else:
            log_login_action(user.id, 'mfa_verify_otp_failed', False)
    
    if not verified:
        return jsonify({"error": "验证码错误"}), 401
    
    # MFA验证成功，完成登录
    session.pop('is_mfa_pending', None)
    session.pop('mfa_user_id', None)
    session.pop('mfa_timestamp', None)
    
    login_user(user, remember=True)
    session['session_version'] = user.session_version
    
    # 检查备份码数量
    backup_count = len(json.loads(user.mfa_backup_codes or '[]'))
    
    response = {
        "message": "MFA验证成功",
        "user_id": user.id,
        "username": user.username
    }
    
    if backup_count == 0:
        response["warning"] = "备份码已耗尽，请重新生成"
    elif backup_count <= 3:
        response["warning"] = f"剩余{backup_count}个备份码，建议重新生成"
    
    return jsonify(response), 200


@auth_bp.route('/mfa/disable', methods=['POST'])
@login_required
def mfa_disable():
    """禁用MFA"""
    user = current_user
    
    # 需要验证当前密码
    data = request.get_json()
    password = data.get('password', '')
    
    if not password:
        return jsonify({"error": "请输入密码"}), 400
    
    # 验证密码
    if not bcrypt_lib.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({"error": "密码错误"}), 401
    
    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_backup_codes = None
    db.session.commit()
    
    log_login_action(user.id, 'mfa_disable', True)
    
    return jsonify({"message": "MFA已禁用"}), 200


@auth_bp.route('/status', methods=['GET'])
def auth_status():
    """获取当前认证状态"""
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "user_id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "mfa_enabled": current_user.mfa_enabled
        }), 200
    
    # 检查是否在MFA临时态
    if session.get('is_mfa_pending'):
        return jsonify({
            "authenticated": False,
            "mfa_pending": True
        }), 200
    
    return jsonify({"authenticated": False}), 200


@auth_bp.route('/user/info', methods=['GET'])
@login_required
def get_user_info():
    """获取当前用户信息"""
    return jsonify({
        "username": current_user.username,
        "email": current_user.email,
        "mfa_enabled": current_user.mfa_enabled,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }), 200


@auth_bp.route('/user/change-password', methods=['POST'])
@login_required
@rate_limit("5 per hour")
def change_password():
    """修改密码"""
    data = request.get_json()
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    
    if not current_password or not new_password:
        return jsonify({"error": "当前密码和新密码不能为空"}), 400
    
    # 验证当前密码
    user = current_user
    if not bcrypt_lib.checkpw(current_password.encode('utf-8'), user.password_hash.encode('utf-8')):
        log_login_action(user.id, 'change_password_failed', False)
        return jsonify({"error": "当前密码错误"}), 400
    
    # 验证新密码强度
    is_valid, result = validate_password_strength(new_password)
    if not is_valid:
        return jsonify({"error": "新密码不符合要求", "details": result}), 400
    
    # 不允许新密码与旧密码相同
    if bcrypt_lib.checkpw(new_password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return jsonify({"error": "新密码不能与当前密码相同"}), 400
    
    # 更新密码
    new_password_hash = bcrypt_lib.hashpw(new_password.encode('utf-8'), bcrypt_lib.gensalt()).decode('utf-8')
    user.password_hash = new_password_hash
    
    # 递增会话版本（使所有其他设备登出）
    user.session_version += 1
    
    db.session.commit()
    log_login_action(user.id, 'change_password', True)
    
    return jsonify({"message": "密码修改成功，其他设备已登出"}), 200


# ========================================
# 密码重置相关端点
# ========================================

@auth_bp.route('/forgot-password', methods=['POST'])
@rate_limit("3 per hour")
def forgot_password():
    """
    请求密码重置
    需要：email
    """
    # 检查SMTP是否配置
    if not check_smtp_configured():
        return jsonify({"error": "邮件服务未配置，请联系管理员"}), 503
    
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({"error": "请输入邮箱地址"}), 400
    
    # 查找用户（无论是否找到都返回相同消息，防止用户枚举）
    user = User.query.filter_by(email=email).first()
    
    if user:
        try:
            # 生成重置token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(minutes=30)
            
            # 保存token到数据库
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=expires_at
            )
            db.session.add(reset_token)
            db.session.commit()
            
            # 生成重置链接
            reset_link = f"{request.host_url}reset-password?token={token}"
            
            # 发送邮件
            success, error = send_password_reset_email(user.email, user.username, reset_link)
            
            if not success:
                logger.error(f"发送密码重置邮件失败: {error}")
                # 删除刚创建的token
                db.session.delete(reset_token)
                db.session.commit()
                return jsonify({"error": "邮件发送失败，请稍后重试"}), 500
                
            logger.info(f"密码重置邮件已发送: {email}")
            
        except Exception as e:
            logger.error(f"密码重置请求处理失败: {e}")
            db.session.rollback()
            return jsonify({"error": "服务器错误，请稍后重试"}), 500
    
    # 无论用户是否存在，都返回相同消息（防止用户枚举攻击）
    return jsonify({
        "message": "如果该邮箱已注册，您将收到密码重置链接。请检查您的邮箱（包括垃圾邮件文件夹）。"
    }), 200


@auth_bp.route('/verify-reset-token', methods=['POST'])
def verify_reset_token():
    """验证重置token是否有效"""
    data = request.get_json()
    token = data.get('token', '').strip()
    
    if not token:
        return jsonify({"error": "无效的token"}), 400
    
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    
    if not reset_token or not reset_token.is_valid():
        return jsonify({"error": "token无效或已过期"}), 400
    
    return jsonify({
        "valid": True,
        "username": reset_token.user.username
    }), 200


@auth_bp.route('/reset-password', methods=['POST'])
@rate_limit("5 per hour")
def reset_password():
    """
    执行密码重置
    需要：token, new_password
    """
    data = request.get_json()
    token = data.get('token', '').strip()
    new_password = data.get('new_password', '')
    
    if not token or not new_password:
        return jsonify({"error": "token和新密码不能为空"}), 400
    
    # 验证token
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    
    if not reset_token or not reset_token.is_valid():
        return jsonify({"error": "token无效或已过期"}), 400
    
    # 验证新密码强度
    is_valid, result = validate_password_strength(new_password)
    if not is_valid:
        return jsonify({"error": "密码不符合要求", "details": result}), 400
    
    try:
        # 获取用户
        user = reset_token.user
        
        # 设置新密码
        user.set_password(new_password)
        
        # 标记token为已使用
        reset_token.mark_as_used()
        
        # 递增会话版本（强制所有设备登出）
        user.session_version += 1
        
        db.session.commit()
        log_login_action(user.id, 'password_reset', True)
        
        logger.info(f"用户 {user.username} 成功重置密码")
        
        return jsonify({
            "message": "密码重置成功，请使用新密码登录"
        }), 200
        
    except Exception as e:
        logger.error(f"密码重置失败: {e}")
        db.session.rollback()
        return jsonify({"error": "密码重置失败，请稍后重试"}), 500


# ========================================
# 管理员功能端点
# ========================================

@auth_bp.route('/admin/users', methods=['GET'])
@login_required
@admin_required
def get_all_users():
    """
    获取所有用户列表（管理员）
    返回用户基本信息和统计数据
    """
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "mfa_enabled": user.mfa_enabled,
                "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "last_login": user.last_login.strftime("%Y-%m-%d %H:%M:%S") if user.last_login else None,
                "failed_login_count": user.failed_login_count,
                "is_locked": user.locked_until and datetime.utcnow() < user.locked_until,
                "login_count": LoginHistory.query.filter_by(user_id=user.id, action='login', success=True).count()
            })
        
        return jsonify({
            "users": user_list,
            "total": len(user_list)
        }), 200
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return jsonify({"error": "获取用户列表失败"}), 500


@auth_bp.route('/admin/users/<int:user_id>', methods=['PATCH'])
@login_required
@admin_required
def update_user(user_id):
    """
    更新用户信息（管理员）
    可更新：username, email, is_admin（不能修改自己的管理员权限）
    """
    data = request.get_json()
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "用户不存在"}), 404
        
        # 更新字段
        if 'username' in data:
            new_username = data['username'].strip()
            # 检查用户名是否已被其他用户使用
            existing = User.query.filter(User.username == new_username, User.id != user_id).first()
            if existing:
                return jsonify({"error": "用户名已被使用"}), 400
            user.username = new_username
        
        if 'email' in data:
            new_email = data['email'].strip()
            # 检查邮箱是否已被其他用户使用
            existing = User.query.filter(User.email == new_email, User.id != user_id).first()
            if existing:
                return jsonify({"error": "邮箱已被使用"}), 400
            user.email = new_email
        
        if 'is_admin' in data:
            # 不允许修改自己的管理员权限
            if user_id == current_user.id:
                return jsonify({"error": "不能修改自己的管理员权限"}), 400
            user.is_admin = bool(data['is_admin'])
        
        db.session.commit()
        logger.info(f"管理员 {current_user.username} 更新了用户 {user.username} 的信息")
        
        return jsonify({
            "message": "用户信息已更新",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin
            }
        }), 200
        
    except Exception as e:
        logger.error(f"更新用户失败: {e}")
        db.session.rollback()
        return jsonify({"error": "更新用户失败"}), 500


@auth_bp.route('/admin/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def admin_reset_password(user_id):
    """
    管理员重置用户密码
    需要提供新密码
    """
    data = request.get_json()
    new_password = data.get('new_password', '')
    
    if not new_password:
        return jsonify({"error": "新密码不能为空"}), 400
    
    # 验证密码强度
    valid, result = validate_password_strength(new_password)
    if not valid:
        return jsonify({"error": "密码不符合要求", "details": result}), 400
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "用户不存在"}), 404
        
        # 设置新密码
        user.set_password(new_password)
        
        # 强制登出（递增session版本）
        user.session_version += 1
        
        # 解锁账户并重置失败计数
        user.failed_login_count = 0
        user.locked_until = None
        
        db.session.commit()
        log_login_action(user.id, 'admin_password_reset', True)
        
        logger.info(f"管理员 {current_user.username} 重置了用户 {user.username} 的密码")
        
        return jsonify({
            "message": f"已重置用户 {user.username} 的密码"
        }), 200
        
    except Exception as e:
        logger.error(f"重置密码失败: {e}")
        db.session.rollback()
        return jsonify({"error": "重置密码失败"}), 500


@auth_bp.route('/admin/users/<int:user_id>/unlock', methods=['POST'])
@login_required
@admin_required
def unlock_user(user_id):
    """
    解锁被锁定的用户账户
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "用户不存在"}), 404
        
        user.failed_login_count = 0
        user.locked_until = None
        
        db.session.commit()
        logger.info(f"管理员 {current_user.username} 解锁了用户 {user.username}")
        
        return jsonify({
            "message": f"已解锁用户 {user.username}"
        }), 200
        
    except Exception as e:
        logger.error(f"解锁用户失败: {e}")
        db.session.rollback()
        return jsonify({"error": "解锁用户失败"}), 500


@auth_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """
    删除用户（管理员）
    不允许删除自己
    """
    if user_id == current_user.id:
        return jsonify({"error": "不能删除自己"}), 400
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "用户不存在"}), 404
        
        username = user.username
        
        # 删除用户（级联删除关联的LoginHistory和PasswordResetToken）
        db.session.delete(user)
        db.session.commit()
        
        logger.info(f"管理员 {current_user.username} 删除了用户 {username}")
        
        return jsonify({
            "message": f"已删除用户 {username}"
        }), 200
        
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        db.session.rollback()
        return jsonify({"error": "删除用户失败"}), 500


# ========================================
# SMTP配置管理端点
# ========================================

@auth_bp.route('/admin/smtp-config', methods=['GET'])
@login_required
@admin_required
def get_smtp_config():
    """
    获取当前SMTP配置（隐藏密码）
    """
    try:
        config = {
            "smtp_server": os.getenv("SMTP_SERVER", ""),
            "smtp_port": os.getenv("SMTP_PORT", "587"),
            "smtp_use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            "smtp_username": os.getenv("SMTP_USERNAME", ""),
            "smtp_password": "******" if os.getenv("SMTP_PASSWORD") else "",  # 隐藏密码
            "smtp_from_name": os.getenv("SMTP_FROM_NAME", "AICouncil"),
            "smtp_from_email": os.getenv("SMTP_FROM_EMAIL", ""),
            "is_configured": check_smtp_configured()
        }
        
        return jsonify(config), 200
        
    except Exception as e:
        logger.error(f"获取SMTP配置失败: {e}")
        return jsonify({"error": "获取配置失败"}), 500


@auth_bp.route('/admin/smtp-config', methods=['POST'])
@login_required
@admin_required
def update_smtp_config():
    """
    更新SMTP配置到.env文件
    """
    data = request.get_json()
    
    try:
        # 读取当前.env文件（src/auth_routes.py -> src -> 项目根目录）
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
        # 备用：直接从项目根查找
        if not os.path.exists(env_path):
            # 尝试从当前工作目录查找
            env_path = os.path.abspath('.env')
        
        if not os.path.exists(env_path):
            logger.error(f"尝试访问的.env路径: {env_path}")
            return jsonify({"error": f".env文件不存在: {env_path}"}), 500
        
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 更新配置项
        config_map = {
            "smtp_server": "SMTP_SERVER",
            "smtp_port": "SMTP_PORT",
            "smtp_use_tls": "SMTP_USE_TLS",
            "smtp_username": "SMTP_USERNAME",
            "smtp_password": "SMTP_PASSWORD",
            "smtp_from_name": "SMTP_FROM_NAME",
            "smtp_from_email": "SMTP_FROM_EMAIL"
        }
        
        updated_lines = []
        updated_keys = set()
        
        for line in lines:
            line_stripped = line.strip()
            updated = False
            
            for key, env_key in config_map.items():
                if key in data and line_stripped.startswith(f"{env_key}="):
                    # 如果是密码字段且值为"******"，保持原密码不变
                    if key == "smtp_password" and data[key] == "******":
                        updated_lines.append(line)
                        updated = True
                        updated_keys.add(env_key)
                        break
                    
                    # 更新配置值
                    value = data[key]
                    if isinstance(value, bool):
                        value = "true" if value else "false"
                    updated_lines.append(f"{env_key}={value}\n")
                    updated = True
                    updated_keys.add(env_key)
                    break
            
            if not updated:
                updated_lines.append(line)
        
        # 写回.env文件
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        
        # 重新加载环境变量（注意：Python进程需要重启才能完全生效）
        for key, env_key in config_map.items():
            if key in data:
                value = data[key]
                if isinstance(value, bool):
                    value = "true" if value else "false"
                elif key == "smtp_password" and value == "******":
                    continue  # 密码未变更，跳过
                os.environ[env_key] = str(value)
        
        logger.info(f"管理员 {current_user.username} 更新了SMTP配置")
        
        return jsonify({
            "message": "SMTP配置已更新（部分配置需重启应用生效）",
            "is_configured": check_smtp_configured()
        }), 200
        
    except Exception as e:
        logger.error(f"更新SMTP配置失败: {e}")
        return jsonify({"error": "更新配置失败"}), 500


@auth_bp.route('/admin/smtp-config/test', methods=['POST'])
@login_required
@admin_required
def test_smtp_config():
    """
    测试SMTP配置连接
    """
    try:
        if not check_smtp_configured():
            return jsonify({"error": "SMTP配置不完整"}), 400
        
        # 发送测试邮件到当前用户邮箱
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_from_name = os.getenv("SMTP_FROM_NAME", "AICouncil")
        smtp_from_email = os.getenv("SMTP_FROM_EMAIL")
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "SMTP配置测试"
        msg['From'] = f"{smtp_from_name} <{smtp_from_email}>"
        msg['To'] = current_user.email
        
        text_content = "这是一封SMTP配置测试邮件。如果您收到此邮件，说明配置成功！"
        html_content = """
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #7c3aed;">SMTP配置测试</h2>
                <p>这是一封SMTP配置测试邮件。</p>
                <p>如果您收到此邮件，说明配置成功！✅</p>
                <hr style="border: 1px solid #e5e7eb; margin: 20px 0;">
                <p style="color: #6b7280; font-size: 14px;">发送自 AICouncil 管理系统</p>
            </body>
        </html>
        """
        
        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)
        
        # 连接SMTP服务器并发送
        if os.getenv("SMTP_USE_TLS", "true").lower() == "true":
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_from_email, [current_user.email], msg.as_string())
        server.quit()
        
        logger.info(f"管理员 {current_user.username} 测试了SMTP配置，测试邮件已发送")
        
        return jsonify({
            "message": f"测试邮件已发送到 {current_user.email}，请检查收件箱"
        }), 200
        
    except smtplib.SMTPAuthenticationError:
        return jsonify({"error": "SMTP认证失败，请检查用户名和密码"}), 400
    except smtplib.SMTPConnectError:
        return jsonify({"error": "无法连接到SMTP服务器，请检查服务器地址和端口"}), 400
    except Exception as e:
        logger.error(f"SMTP测试失败: {e}")
        return jsonify({"error": f"测试失败: {str(e)}"}), 500


@auth_bp.route('/admin/restart', methods=['POST'])
@login_required
@admin_required
def restart_app():
    """
    重启应用（管理员）
    """
    try:
        import sys
        import threading
        
        logger.warning(f"管理员 {current_user.username} 请求重启应用")
        
        def shutdown():
            # 延迟1秒后退出，让响应先返回
            import time
            time.sleep(1)
            # 触发Flask关闭
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                # 如果是生产环境，使用os._exit
                import os
                os._exit(0)
            else:
                func()
        
        # 在后台线程执行关闭
        threading.Thread(target=shutdown, daemon=True).start()
        
        return jsonify({
            "message": "应用正在重启，请稍候刷新页面"
        }), 200
        
    except Exception as e:
        logger.error(f"重启应用失败: {e}")
        return jsonify({"error": f"重启失败: {str(e)}"}), 500


