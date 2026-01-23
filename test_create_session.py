"""测试创建一个会话记录"""
import sys
from pathlib import Path

# 添加项目根目录到sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.models import db
from src.repositories import SessionRepository
from src.web.app import app
from datetime import datetime
import uuid

def test_create_session():
    """测试创建会话"""
    with app.app_context():
        print("=" * 80)
        print("测试创建会话记录")
        print("=" * 80)
        
        # 创建测试会话
        session_id = f"20260123_111500_{uuid.uuid4().hex[:8]}"
        
        config = {
            "backend": "deepseek",
            "model": "deepseek-reasoner",
            "rounds": 2,
            "planners": 2,
            "auditors": 2
        }
        
        print(f"\n创建会话参数:")
        print(f"  session_id: {session_id}")
        print(f"  user_id: 1")
        print(f"  tenant_id: None")
        print(f"  issue: 测试议题")
        
        result = SessionRepository.create_session(
            user_id=1,
            session_id=session_id,
            issue="测试议题：验证admin用户能否创建和查询会话",
            config=config,
            tenant_id=None
        )
        
        if result:
            print(f"\n✅ 会话创建成功!")
            print(f"  ID: {result.id}")
            print(f"  session_id: {result.session_id}")
            print(f"  user_id: {result.user_id}")
            print(f"  tenant_id: {result.tenant_id}")
            print(f"  status: {result.status}")
            
            # 测试查询
            print(f"\n测试查询 user_id=1, tenant_id=None:")
            sessions = SessionRepository.get_user_sessions(
                user_id=1,
                tenant_id=None
            )
            print(f"  查询结果: {len(sessions)}条记录")
            for s in sessions:
                print(f"    - {s.session_id}: {s.issue[:30]}...")
            
            # 测试计数
            count = SessionRepository.get_session_count(
                user_id=1,
                tenant_id=None
            )
            print(f"  计数结果: {count}条")
        else:
            print(f"\n❌ 会话创建失败!")
        
        print("\n" + "=" * 80)

if __name__ == "__main__":
    test_create_session()
