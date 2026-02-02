"""创建默认租户并更新admin用户"""
import sys
from pathlib import Path

# 添加项目根目录到sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.models import db, Tenant, User
from src.web.app import app

def setup_default_tenant():
    """创建默认租户并更新admin用户"""
    with app.app_context():
        print("=" * 80)
        print("设置默认租户")
        print("=" * 80)
        
        # 1. 检查是否已存在默认租户
        default_tenant = Tenant.query.filter_by(name="默认租户").first()
        
        if not default_tenant:
            print("\n创建默认租户...")
            default_tenant = Tenant(
                name="默认租户",
                quota_config={
                    "max_sessions": 1000,
                    "max_users": 100,
                    "max_skills": 50,
                    "description": "系统默认租户，用于独立用户"
                },
                is_active=True
            )
            db.session.add(default_tenant)
            db.session.commit()
            print(f"✅ 默认租户创建成功: ID={default_tenant.id}")
        else:
            print(f"\n默认租户已存在: ID={default_tenant.id}")
        
        # 2. 更新所有tenant_id为NULL的用户
        null_tenant_users = User.query.filter(User.tenant_id.is_(None)).all()
        
        if null_tenant_users:
            print(f"\n发现 {len(null_tenant_users)} 个无租户用户，正在更新...")
            for user in null_tenant_users:
                print(f"  - 更新用户: {user.username} (ID={user.id})")
                user.tenant_id = default_tenant.id
            
            db.session.commit()
            print(f"✅ 已将 {len(null_tenant_users)} 个用户分配到默认租户")
        else:
            print("\n✅ 所有用户都已有租户")
        
        # 3. 更新所有tenant_id为NULL的会话
        from src.models import DiscussionSession
        null_tenant_sessions = DiscussionSession.query.filter(
            DiscussionSession.tenant_id.is_(None)
        ).all()
        
        if null_tenant_sessions:
            print(f"\n发现 {len(null_tenant_sessions)} 个无租户会话，正在更新...")
            for session in null_tenant_sessions:
                print(f"  - 更新会话: {session.session_id}")
                session.tenant_id = default_tenant.id
            
            db.session.commit()
            print(f"✅ 已将 {len(null_tenant_sessions)} 个会话分配到默认租户")
        else:
            print("\n✅ 所有会话都已有租户")
        
        # 4. 验证结果
        print("\n" + "=" * 80)
        print("验证结果")
        print("=" * 80)
        
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print(f"\nadmin用户:")
            print(f"  ID: {admin.id}")
            print(f"  tenant_id: {admin.tenant_id}")
            print(f"  租户名称: {admin.tenant.name if admin.tenant else 'N/A'}")
        
        from src.repositories import SessionRepository
        sessions = SessionRepository.get_user_sessions(
            user_id=admin.id if admin else 1,
            tenant_id=default_tenant.id
        )
        print(f"\nadmin的会话数: {len(sessions)}")
        for s in sessions:
            print(f"  - {s.session_id}: tenant_id={s.tenant_id}")
        
        print("\n" + "=" * 80)
        print("✅ 默认租户设置完成！")
        print("=" * 80)

if __name__ == "__main__":
    setup_default_tenant()
