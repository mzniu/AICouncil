"""
测试SessionRepository数据访问层
验证CRUD操作、分页、多用户隔离、错误处理
"""
import pytest
from datetime import datetime
from src.models import db, User, DiscussionSession
from src.repositories import SessionRepository


@pytest.fixture
def test_users(app):
    """创建多个测试用户"""
    with app.app_context():
        users = []
        for i in range(3):
            user = User(username=f'user{i}', email=f'user{i}@test.com')
            user.set_password('pass123')
            db.session.add(user)
            users.append(user)
        db.session.commit()
        yield users


@pytest.fixture
def sample_config():
    """示例配置"""
    return {
        'backend': 'deepseek',
        'model': 'deepseek-chat',
        'rounds': 3,
        'planners': 2,
        'auditors': 2
    }


class TestSessionRepository:
    """SessionRepository测试套件"""
    
    def test_create_session(self, app, test_users, sample_config):
        """测试创建会话"""
        with app.app_context():
            user = test_users[0]
            session = SessionRepository.create_session(
                user_id=user.id,
                session_id='20260116_001',
                issue='测试议题1',
                config=sample_config
            )
            
            assert session is not None
            assert session.session_id == '20260116_001'
            assert session.user_id == user.id
            assert session.issue == '测试议题1'
            assert session.backend == 'deepseek'
            assert session.model == 'deepseek-chat'
            assert session.config['rounds'] == 3
            assert session.status == 'running'
    
    def test_update_history(self, app, test_users, sample_config):
        """测试更新讨论历史"""
        with app.app_context():
            user = test_users[0]
            session = SessionRepository.create_session(
                user_id=user.id,
                session_id='20260116_002',
                issue='历史测试',
                config=sample_config
            )
            
            # 更新history
            test_history = [
                {'round': 1, 'plans': ['Plan A', 'Plan B']},
                {'round': 2, 'plans': ['Plan C']}
            ]
            result = SessionRepository.update_history('20260116_002', test_history)
            
            assert result is True
            
            # 验证更新
            retrieved = SessionRepository.get_session_by_id('20260116_002')
            assert retrieved.history == test_history
            assert len(retrieved.history) == 2
    
    def test_update_decomposition(self, app, test_users, sample_config):
        """测试更新议题分解"""
        with app.app_context():
            user = test_users[0]
            session = SessionRepository.create_session(
                user_id=user.id,
                session_id='20260116_003',
                issue='分解测试',
                config=sample_config
            )
            
            decomposition = {
                'core_goal': '核心目标',
                'key_questions': ['Q1', 'Q2', 'Q3'],
                'boundaries': '边界条件'
            }
            result = SessionRepository.update_decomposition('20260116_003', decomposition)
            
            assert result is True
            retrieved = SessionRepository.get_session_by_id('20260116_003')
            assert retrieved.decomposition['core_goal'] == '核心目标'
            assert len(retrieved.decomposition['key_questions']) == 3
    
    def test_save_final_report(self, app, test_users, sample_config):
        """测试保存最终报告"""
        with app.app_context():
            user = test_users[0]
            session = SessionRepository.create_session(
                user_id=user.id,
                session_id='20260116_004',
                issue='报告测试',
                config=sample_config
            )
            
            report_html = '<html><body>测试报告</body></html>'
            report_json = {'title': '测试报告', 'sections': []}
            
            result = SessionRepository.save_final_report(
                '20260116_004',
                report_html,
                report_json
            )
            
            assert result is True
            retrieved = SessionRepository.get_session_by_id('20260116_004')
            assert retrieved.report_html == report_html
            assert retrieved.report_json == report_json
            assert retrieved.status == 'completed'
            assert retrieved.completed_at is not None
    
    def test_increment_report_version(self, app, test_users, sample_config):
        """测试报告版本递增"""
        with app.app_context():
            user = test_users[0]
            session = SessionRepository.create_session(
                user_id=user.id,
                session_id='20260116_005',
                issue='版本测试',
                config=sample_config
            )
            
            # 初始版本为1
            assert session.report_version == 1
            
            # 递增版本
            new_version = SessionRepository.increment_report_version('20260116_005')
            assert new_version == 2
            
            # 再次递增
            new_version = SessionRepository.increment_report_version('20260116_005')
            assert new_version == 3
            
            # 验证
            retrieved = SessionRepository.get_session_by_id('20260116_005')
            assert retrieved.report_version == 3
    
    def test_update_status(self, app, test_users, sample_config):
        """测试更新状态"""
        with app.app_context():
            user = test_users[0]
            session = SessionRepository.create_session(
                user_id=user.id,
                session_id='20260116_006',
                issue='状态更新测试',
                config=sample_config
            )
            
            # 更新为completed
            result = SessionRepository.update_status('20260116_006', 'completed')
            assert result is True
            
            retrieved = SessionRepository.get_session_by_id('20260116_006')
            assert retrieved.status == 'completed'
            assert retrieved.completed_at is not None
            
            # 更新为failed
            result = SessionRepository.update_status('20260116_006', 'failed')
            assert result is True
            assert SessionRepository.get_session_by_id('20260116_006').status == 'failed'
    
    def test_get_user_sessions_pagination(self, app, test_users, sample_config):
        """测试分页获取用户会话"""
        with app.app_context():
            user = test_users[0]
            
            # 创建10个会话
            for i in range(10):
                SessionRepository.create_session(
                    user_id=user.id,
                    session_id=f'20260116_{i:03d}',
                    issue=f'议题{i}',
                    config=sample_config
                )
            
            # 获取第1页（每页5条）
            page1 = SessionRepository.get_user_sessions(user.id, page=1, per_page=5)
            assert len(page1) == 5
            
            # 获取第2页
            page2 = SessionRepository.get_user_sessions(user.id, page=2, per_page=5)
            assert len(page2) == 5
            
            # 验证顺序（最新的在前）
            assert page1[0].session_id > page1[-1].session_id
    
    def test_get_user_sessions_with_status_filter(self, app, test_users, sample_config):
        """测试按状态过滤会话"""
        with app.app_context():
            user = test_users[0]
            
            # 创建不同状态的会话
            for i, status in enumerate(['running', 'completed', 'running', 'failed', 'completed']):
                session = SessionRepository.create_session(
                    user_id=user.id,
                    session_id=f'20260116_status_{i}',
                    issue=f'议题{i}',
                    config=sample_config
                )
                SessionRepository.update_status(session.session_id, status)
            
            # 只查询running状态
            running_sessions = SessionRepository.get_user_sessions(
                user.id, 
                status_filter='running'
            )
            assert len(running_sessions) == 2
            assert all(s.status == 'running' for s in running_sessions)
            
            # 只查询completed状态
            completed_sessions = SessionRepository.get_user_sessions(
                user.id,
                status_filter='completed'
            )
            assert len(completed_sessions) == 2
            assert all(s.status == 'completed' for s in completed_sessions)
    
    def test_get_session_by_id(self, app, test_users, sample_config):
        """测试根据ID获取会话"""
        with app.app_context():
            user = test_users[0]
            created = SessionRepository.create_session(
                user_id=user.id,
                session_id='20260116_getbyid',
                issue='获取测试',
                config=sample_config
            )
            
            # 获取存在的会话
            retrieved = SessionRepository.get_session_by_id('20260116_getbyid')
            assert retrieved is not None
            assert retrieved.session_id == created.session_id
            assert retrieved.user_id == user.id
            
            # 获取不存在的会话
            not_found = SessionRepository.get_session_by_id('nonexistent_id')
            assert not_found is None
    
    def test_update_nonexistent_session(self, app):
        """测试更新不存在的会话"""
        with app.app_context():
            # 尝试更新不存在的会话
            result = SessionRepository.update_history('nonexistent', [])
            assert result is False
            
            result = SessionRepository.update_decomposition('nonexistent', {})
            assert result is False
            
            result = SessionRepository.update_status('nonexistent', 'completed')
            assert result is False
            
            result = SessionRepository.save_final_report('nonexistent', '<html></html>')
            assert result is False
    
    def test_multi_user_isolation(self, app, test_users, sample_config):
        """测试多用户数据隔离"""
        with app.app_context():
            user1, user2, user3 = test_users
            
            # 用户1创建3个会话
            for i in range(3):
                SessionRepository.create_session(
                    user_id=user1.id,
                    session_id=f'user1_session_{i}',
                    issue=f'用户1议题{i}',
                    config=sample_config
                )
            
            # 用户2创建2个会话
            for i in range(2):
                SessionRepository.create_session(
                    user_id=user2.id,
                    session_id=f'user2_session_{i}',
                    issue=f'用户2议题{i}',
                    config=sample_config
                )
            
            # 验证隔离
            user1_sessions = SessionRepository.get_user_sessions(user1.id)
            user2_sessions = SessionRepository.get_user_sessions(user2.id)
            user3_sessions = SessionRepository.get_user_sessions(user3.id)
            
            assert len(user1_sessions) == 3
            assert len(user2_sessions) == 2
            assert len(user3_sessions) == 0
            
            # 验证用户1看不到用户2的会话
            assert all(s.user_id == user1.id for s in user1_sessions)
            assert all(s.user_id == user2.id for s in user2_sessions)
    
    def test_check_user_permission(self, app, test_users, sample_config):
        """测试用户权限检查"""
        with app.app_context():
            user1, user2 = test_users[0], test_users[1]
            
            # 用户1创建会话
            SessionRepository.create_session(
                user_id=user1.id,
                session_id='permission_test',
                issue='权限测试',
                config=sample_config
            )
            
            # 用户1有权限
            assert SessionRepository.check_user_permission('permission_test', user1.id) is True
            
            # 用户2无权限
            assert SessionRepository.check_user_permission('permission_test', user2.id) is False
            
            # 不存在的会话
            assert SessionRepository.check_user_permission('nonexistent', user1.id) is False
    
    def test_get_session_count(self, app, test_users, sample_config):
        """测试获取会话计数"""
        with app.app_context():
            user = test_users[0]
            
            # 初始计数为0
            count = SessionRepository.get_session_count(user.id)
            assert count == 0
            
            # 创建5个会话
            for i in range(5):
                session = SessionRepository.create_session(
                    user_id=user.id,
                    session_id=f'count_test_{i}',
                    issue=f'议题{i}',
                    config=sample_config
                )
                if i < 2:
                    SessionRepository.update_status(session.session_id, 'completed')
            
            # 总计数
            total_count = SessionRepository.get_session_count(user.id)
            assert total_count == 5
            
            # 按状态过滤计数
            completed_count = SessionRepository.get_session_count(user.id, status_filter='completed')
            assert completed_count == 2
            
            running_count = SessionRepository.get_session_count(user.id, status_filter='running')
            assert running_count == 3
    
    def test_update_search_references(self, app, test_users, sample_config):
        """测试更新搜索引用"""
        with app.app_context():
            user = test_users[0]
            session = SessionRepository.create_session(
                user_id=user.id,
                session_id='20260116_search',
                issue='搜索测试',
                config=sample_config
            )
            
            search_data = {
                'queries': ['query1', 'query2'],
                'results': [
                    {'title': 'Result 1', 'url': 'http://example.com/1'},
                    {'title': 'Result 2', 'url': 'http://example.com/2'}
                ]
            }
            
            result = SessionRepository.update_search_references('20260116_search', search_data)
            assert result is True
            
            retrieved = SessionRepository.get_session_by_id('20260116_search')
            assert retrieved.search_references == search_data
            assert len(retrieved.search_references['results']) == 2
    
    def test_update_final_session_data(self, app, test_users, sample_config):
        """测试更新最终会话数据"""
        with app.app_context():
            user = test_users[0]
            session = SessionRepository.create_session(
                user_id=user.id,
                session_id='20260116_final',
                issue='最终数据测试',
                config=sample_config
            )
            
            final_data = {
                'issue': '最终数据测试',
                'decomposition': {'core_goal': '目标'},
                'history': [{'round': 1}],
                'final_summary': {'summary': '总结内容'}
            }
            
            result = SessionRepository.update_final_session_data('20260116_final', final_data)
            assert result is True
            
            retrieved = SessionRepository.get_session_by_id('20260116_final')
            assert retrieved.final_session_data == final_data
    
    def test_database_rollback_on_error(self, app, test_users):
        """测试数据库错误回滚"""
        with app.app_context():
            user = test_users[0]
            
            # 创建会话
            session = SessionRepository.create_session(
                user_id=user.id,
                session_id='rollback_test',
                issue='回滚测试',
                config={}
            )
            assert session is not None
            
            # 尝试创建重复session_id（应该失败并返回None）
            duplicate = SessionRepository.create_session(
                user_id=user.id,
                session_id='rollback_test',  # 重复
                issue='重复会话',
                config={}
            )
            assert duplicate is None
            
            # 验证原会话仍然存在且未损坏
            original = SessionRepository.get_session_by_id('rollback_test')
            assert original is not None
            assert original.issue == '回滚测试'
    
    def test_concurrent_access(self, app, test_users, sample_config):
        """测试并发访问（基础测试）"""
        with app.app_context():
            user = test_users[0]
            session = SessionRepository.create_session(
                user_id=user.id,
                session_id='concurrent_test',
                issue='并发测试',
                config=sample_config
            )
            
            # 模拟多次快速更新
            for i in range(10):
                SessionRepository.update_history('concurrent_test', [{'round': i}])
            
            # 验证最终状态
            retrieved = SessionRepository.get_session_by_id('concurrent_test')
            assert retrieved.history == [{'round': 9}]
    
    def test_empty_user_sessions(self, app, test_users):
        """测试空会话列表"""
        with app.app_context():
            user = test_users[2]  # 没有创建任何会话的用户
            
            sessions = SessionRepository.get_user_sessions(user.id)
            assert sessions == []
            
            count = SessionRepository.get_session_count(user.id)
            assert count == 0
    
    def test_large_json_fields(self, app, test_users, sample_config):
        """测试大型JSON字段存储"""
        with app.app_context():
            user = test_users[0]
            session = SessionRepository.create_session(
                user_id=user.id,
                session_id='large_json_test',
                issue='大数据测试',
                config=sample_config
            )
            
            # 创建大型history（模拟真实场景）
            large_history = []
            for r in range(10):  # 10轮讨论
                large_history.append({
                    'round': r + 1,
                    'plans': [f'Plan {i}' * 100 for i in range(5)],  # 5个策论家，每个100字符
                    'audits': [f'Audit {i}' * 100 for i in range(5)],
                    'summary': {
                        'summary': 'Summary text' * 50,
                        'instructions': 'Instructions' * 50
                    }
                })
            
            result = SessionRepository.update_history('large_json_test', large_history)
            assert result is True
            
            # 验证能够正确读取
            retrieved = SessionRepository.get_session_by_id('large_json_test')
            assert retrieved.history is not None
            assert len(retrieved.history) == 10
