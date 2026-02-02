"""
数据库性能测试脚本
测试复合索引对查询性能的提升效果
"""
import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.web.app import app
from src.models import db, DiscussionSession, User
from src.repositories.session_repository import SessionRepository
import random
import string
from datetime import datetime, timedelta


def generate_random_string(length=10):
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def create_test_data(user_id, count=1000):
    """创建测试数据"""
    print(f"\n📊 创建 {count} 条测试数据...")
    
    sessions = []
    statuses = ['running', 'completed', 'failed', 'stopped']
    backends = ['deepseek', 'openai', 'aliyun', 'openrouter']
    
    start_time = time.time()
    
    for i in range(count):
        session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{generate_random_string(8)}"
        
        session = DiscussionSession(
            session_id=session_id,
            user_id=user_id,
            issue=f"测试议题 {i+1}: {generate_random_string(50)}",
            backend=random.choice(backends),
            model=f"model-{random.randint(1, 5)}",
            status=random.choice(statuses),
            config={'test': True, 'index': i},
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 365)),
            report_version=random.randint(1, 5)
        )
        sessions.append(session)
        
        # 批量插入（每100条提交一次）
        if (i + 1) % 100 == 0:
            db.session.bulk_save_objects(sessions)
            db.session.commit()
            sessions = []
            print(f"  已创建 {i+1}/{count} 条记录...")
    
    # 提交剩余数据
    if sessions:
        db.session.bulk_save_objects(sessions)
        db.session.commit()
    
    elapsed = time.time() - start_time
    print(f"✅ 测试数据创建完成！耗时: {elapsed:.2f}秒")


def benchmark_query(description, query_func, iterations=10):
    """性能基准测试"""
    times = []
    
    for i in range(iterations):
        start = time.time()
        result = query_func()
        elapsed = time.time() - start
        times.append(elapsed)
        
        if i == 0:  # 只在第一次显示结果数量
            result_count = len(result) if hasattr(result, '__len__') else 'N/A'
            print(f"  结果数: {result_count}")
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"📈 {description}")
    print(f"   平均: {avg_time*1000:.2f}ms | 最快: {min_time*1000:.2f}ms | 最慢: {max_time*1000:.2f}ms")
    
    return avg_time


def run_performance_tests(user_id):
    """运行性能测试"""
    print("\n" + "="*60)
    print("🚀 开始性能测试")
    print("="*60)
    
    # 测试1：用户会话列表查询（按时间倒序）
    print("\n1️⃣  用户会话列表查询（使用 idx_user_created）")
    def query1():
        return SessionRepository.get_user_sessions(user_id=user_id, page=1, per_page=20)
    
    time1 = benchmark_query("查询用户前20条会话（按创建时间倒序）", query1)
    
    # 测试2：带状态过滤的查询
    print("\n2️⃣  带状态过滤的查询（使用 idx_user_status_created）")
    def query2():
        return SessionRepository.get_user_sessions(
            user_id=user_id, 
            page=1, 
            per_page=20, 
            status_filter='completed'
        )
    
    time2 = benchmark_query("查询用户前20条已完成会话", query2)
    
    # 测试3：状态统计查询
    print("\n3️⃣  状态统计查询（使用 idx_user_status）")
    def query3():
        counts = {}
        for status in ['running', 'completed', 'failed', 'stopped']:
            counts[status] = SessionRepository.get_session_count(
                user_id=user_id,
                status_filter=status
            )
        return counts
    
    time3 = benchmark_query("统计各状态会话数量", query3)
    
    # 测试4：全量统计（无过滤）
    print("\n4️⃣  全量统计（使用 user_id 索引）")
    def query4():
        return SessionRepository.get_session_count(user_id=user_id)
    
    time4 = benchmark_query("统计用户所有会话数", query4)
    
    # 测试5：分页查询多页
    print("\n5️⃣  分页查询（第10页）")
    def query5():
        return SessionRepository.get_user_sessions(user_id=user_id, page=10, per_page=20)
    
    time5 = benchmark_query("查询第10页数据", query5)
    
    print("\n" + "="*60)
    print("📊 性能测试总结")
    print("="*60)
    print(f"1. 会话列表查询:    {time1*1000:.2f}ms")
    print(f"2. 状态过滤查询:    {time2*1000:.2f}ms")
    print(f"3. 状态统计查询:    {time3*1000:.2f}ms")
    print(f"4. 全量统计查询:    {time4*1000:.2f}ms")
    print(f"5. 深度分页查询:    {time5*1000:.2f}ms")
    print("="*60)
    
    # 性能评估
    print("\n✨ 性能评估：")
    if time1 < 0.1:
        print("  ✅ 会话列表查询性能优秀 (<100ms)")
    elif time1 < 0.5:
        print("  ⚠️  会话列表查询性能良好 (100-500ms)")
    else:
        print("  ❌ 会话列表查询性能需优化 (>500ms)")
    
    if time2 < 0.15:
        print("  ✅ 状态过滤查询性能优秀 (<150ms)")
    elif time2 < 0.7:
        print("  ⚠️  状态过滤查询性能良好 (150-700ms)")
    else:
        print("  ❌ 状态过滤查询性能需优化 (>700ms)")


def cleanup_test_data(user_id):
    """清理测试数据"""
    print("\n🧹 清理测试数据...")
    
    count = DiscussionSession.query.filter(
        DiscussionSession.user_id == user_id,
        DiscussionSession.config.contains('"test": true')
    ).delete(synchronize_session=False)
    
    db.session.commit()
    print(f"✅ 已删除 {count} 条测试记录")


def main():
    """主函数"""
    with app.app_context():
        # 获取或创建测试用户
        test_user = User.query.filter_by(username='test_perf').first()
        if not test_user:
            print("📝 创建测试用户...")
            test_user = User(
                username='test_perf',
                email='test_perf@example.com',
                is_admin=False
            )
            test_user.set_password('test123')
            db.session.add(test_user)
            db.session.commit()
            print(f"✅ 测试用户创建成功 (ID: {test_user.id})")
        else:
            print(f"✅ 使用已存在的测试用户 (ID: {test_user.id})")
        
        # 检查现有测试数据
        existing_count = DiscussionSession.query.filter_by(user_id=test_user.id).count()
        print(f"📊 当前测试用户已有 {existing_count} 条记录")
        
        # 如果数据不足1000条，创建更多
        if existing_count < 1000:
            create_test_data(test_user.id, count=1000 - existing_count)
        
        # 运行性能测试
        run_performance_tests(test_user.id)
        
        # 询问是否清理
        print("\n" + "="*60)
        cleanup = input("是否清理测试数据？(y/N): ").strip().lower()
        if cleanup == 'y':
            cleanup_test_data(test_user.id)
        else:
            print("⏭️  跳过清理，测试数据已保留")


if __name__ == "__main__":
    main()
