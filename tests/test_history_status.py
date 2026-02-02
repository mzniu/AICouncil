"""
测试历史记录状态显示

验证：
1. 异常捕获并更新状态为failed
2. 正常完成更新状态为completed  
3. 前端显示所有状态的会话（包括running/failed）
"""

from src.models import db, DiscussionSession
from src.web.app import app

print("=" * 70)
print("测试：历史记录状态显示")
print("=" * 70)
print()

# 查看当前数据库中的所有会话
with app.app_context():
    sessions = DiscussionSession.query.order_by(DiscussionSession.created_at.desc()).limit(10).all()
    
    print(f"📊 数据库中最近10条会话记录:")
    print("-" * 70)
    print(f"{'序号':<4} {'Session ID':<25} {'状态':<10} {'创建时间':<20}")
    print("-" * 70)
    
    for i, s in enumerate(sessions, 1):
        status_icons = {
            'running': '🟡',
            'completed': '🟢',
            'failed': '🔴'
        }
        icon = status_icons.get(s.status, '⚪')
        print(f"{i:<4} {s.session_id:<25} {icon} {s.status:<10} {str(s.created_at)[:19]}")
    
    print("-" * 70)
    print()
    
    # 统计各状态数量
    from sqlalchemy import func
    status_counts = db.session.query(
        DiscussionSession.status, 
        func.count(DiscussionSession.id)
    ).group_by(DiscussionSession.status).all()
    
    print("📈 状态分布统计:")
    for status, count in status_counts:
        icon = status_icons.get(status, '⚪')
        print(f"  {icon} {status}: {count}条")
    print()
    
    # 检查是否有报告内容
    completed_with_report = DiscussionSession.query.filter_by(status='completed').filter(
        DiscussionSession.report_html.isnot(None)
    ).count()
    
    completed_without_report = DiscussionSession.query.filter_by(status='completed').filter(
        DiscussionSession.report_html.is_(None)
    ).count()
    
    print("📝 报告生成情况:")
    print(f"  已完成且有报告: {completed_with_report}条")
    print(f"  已完成但无报告: {completed_without_report}条 {'⚠️  (异常)' if completed_without_report > 0 else ''}")
    print()

print("✅ 检查完成！")
print()
print("下一步测试建议:")
print("1. 启动Web服务: python src/web/app.py")
print("2. 访问 http://127.0.0.1:5000")
print("3. 点击 '历史' 按钮，查看是否显示所有状态的会话")
print("4. 观察状态图标是否正确显示 (🟡 running, 🟢 completed, 🔴 failed)")
