"""检查数据库中的discussion_sessions记录"""
import sys
from pathlib import Path

# 添加项目根目录到sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.models import db, DiscussionSession, User, Tenant
from src.web.app import app

def check_database():
    """检查数据库记录"""
    with app.app_context():
        print("=" * 80)
        print("检查数据库记录")
        print("=" * 80)
        
        # 1. 检查Users表
        print("\n📊 用户表 (users):")
        users = User.query.all()
        print(f"总用户数: {len(users)}")
        for user in users:
            print(f"  - ID={user.id}, username={user.username}, tenant_id={user.tenant_id}")
        
        # 2. 检查Tenants表
        print("\n📊 租户表 (tenants):")
        tenants = Tenant.query.all()
        print(f"总租户数: {len(tenants)}")
        for tenant in tenants:
            print(f"  - ID={tenant.id}, name={tenant.name}, is_active={tenant.is_active}")
        
        # 3. 检查DiscussionSession表
        print("\n📊 讨论会话表 (discussion_sessions):")
        sessions = DiscussionSession.query.all()
        print(f"总会话数: {len(sessions)}")
        
        if not sessions:
            print("⚠️ 数据库中没有任何会话记录！")
        else:
            print("\n会话详情:")
            for session in sessions:
                print(f"\n  会话ID: {session.session_id}")
                print(f"    user_id: {session.user_id}")
                print(f"    tenant_id: {session.tenant_id}")
                print(f"    议题: {session.issue[:50]}...")
                print(f"    状态: {session.status}")
                print(f"    创建时间: {session.created_at}")
        
        # 4. 按user_id分组统计
        print("\n📊 按user_id分组统计:")
        from sqlalchemy import func
        user_stats = db.session.query(
            DiscussionSession.user_id,
            func.count(DiscussionSession.id).label('count')
        ).group_by(DiscussionSession.user_id).all()
        
        for user_id, count in user_stats:
            print(f"  user_id={user_id}: {count}条记录")
        
        # 5. 按tenant_id分组统计
        print("\n📊 按tenant_id分组统计:")
        tenant_stats = db.session.query(
            DiscussionSession.tenant_id,
            func.count(DiscussionSession.id).label('count')
        ).group_by(DiscussionSession.tenant_id).all()
        
        for tenant_id, count in tenant_stats:
            print(f"  tenant_id={tenant_id}: {count}条记录")
        
        # 6. 检查user_id列的nullable属性
        print("\n📊 检查表结构:")
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = inspector.get_columns('discussion_sessions')
        for col in columns:
            if col['name'] in ['user_id', 'tenant_id']:
                print(f"  {col['name']}: nullable={col['nullable']}, type={col['type']}")
        
        print("\n" + "=" * 80)

if __name__ == "__main__":
    check_database()
