"""重置用户MFA设置的脚本"""
from src.models import db, User
from src.web.app import app

with app.app_context():
    user = User.query.filter_by(username='testuser').first()
    if user:
        user.mfa_enabled = False
        user.mfa_secret = None
        user.mfa_backup_codes = None
        db.session.commit()
        print(f'✅ 已重置用户 {user.username} 的MFA设置')
        print(f'   - MFA状态: {user.mfa_enabled}')
        print(f'   - 密钥: {user.mfa_secret}')
        print(f'   - 备份码: {user.mfa_backup_codes}')
    else:
        print('❌ 未找到用户 testuser')
