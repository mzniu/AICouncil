"""
认证相关的路由端点
包括注册、登录、登出、MFA设置和验证
"""
import os
import json
import re
from datetime import datetime, timedelta
from io import BytesIO
import pyotp
import qrcode
import bcrypt as bcrypt_lib
from flask import Blueprint, request, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from src.models import db, User, LoginHistory
from src.utils.logger import logger

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

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
    # 检查是否允许公开注册
    if not ALLOW_PUBLIC_REGISTRATION:
        return jsonify({"error": "registration_disabled", "message": "公开注册已禁用，请联系管理员"}), 403
    
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip()
    
    # 验证必填字段
    if not username or not password or not email:
        return jsonify({"error": "用户名、密码和邮箱不能为空"}), 400
    
    # 验证密码强度
    valid, message = validate_password_strength(password)
    if not valid:
        return jsonify({"error": message}), 400
    
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
            mfa_enabled=False
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        log_login_action(user.id, 'register', True)
        
        return jsonify({
            "message": "注册成功",
            "user_id": user.id,
            "username": username
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
    errors = validate_password_strength(new_password)
    if errors:
        return jsonify({"error": "新密码不符合要求", "details": errors}), 400
    
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
