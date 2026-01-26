"""
测试失败状态的记录

通过故意触发异常来验证状态更新机制
"""

from src.agents.langchain_agents import run_full_cycle
import traceback

print("=" * 70)
print("测试：异常处理和状态更新")
print("=" * 70)
print()

print("⚠️ 将故意传入无效参数触发异常，验证状态更新为'failed'...")
print()

try:
    # 故意传入会导致错误的参数
    result = run_full_cycle(
        issue_text="",  # 空议题可能导致问题
        model_config={"type": "invalid_backend", "model": "invalid_model"},  # 无效后端
        max_rounds=1,
        num_planners=1,
        num_auditors=1,
        user_id=1,
        tenant_id=1
    )
    
    print("结果:", result)
    
except Exception as e:
    print(f"❌ 捕获到异常 (符合预期): {e}")
    print()
    print("异常详情:")
    traceback.print_exc()

print()
print("=" * 70)
print("现在检查数据库中的状态...")
print("=" * 70)

from src.models import db, DiscussionSession
from src.web.app import app

with app.app_context():
    # 查看最新的会话
    latest = DiscussionSession.query.order_by(DiscussionSession.created_at.desc()).first()
    if latest:
        print(f"最新会话:")
        print(f"  Session ID: {latest.session_id}")
        print(f"  状态: {latest.status}")
        print(f"  创建时间: {latest.created_at}")
        print()
        
        if latest.status == 'failed':
            print("✅ 测试成功！状态已正确更新为'failed'")
        elif latest.status == 'running':
            print("⚠️ 状态仍为'running'，可能异常处理未生效")
        else:
            print(f"⚠️ 状态为: {latest.status}")
    else:
        print("❌ 数据库中没有找到会话记录")
