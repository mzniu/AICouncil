"""
测试DiscussionSession模型
验证模型字段、关系、约束和序列化功能
"""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from src.models import db, User, DiscussionSession


@pytest.fixture
def test_user(app):
    """创建测试用户"""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
        yield user
        # Cleanup在test_app fixture中统一处理


@pytest.fixture
def test_session_data():
    """测试会话数据"""
    return {
        'session_id': '20260116_120000_testid',
        'issue': '测试议题：如何提升系统性能',
        'backend': 'deepseek',
        'model': 'deepseek-chat',
        'config': {
            'rounds': 3,
            'planners': 2,
            'auditors': 2,
            'reasoning': 'enabled'
        }
    }


class TestDiscussionSessionModel:
    """DiscussionSession模型测试套件"""
    
    def test_create_session(self, app, test_user, test_session_data):
        """测试创建会话"""
        with app.app_context():
            session = DiscussionSession(
                session_id=test_session_data['session_id'],
                user_id=test_user.id,
                issue=test_session_data['issue'],
                backend=test_session_data['backend'],
                model=test_session_data['model'],
                config=test_session_data['config'],
                status='running'
            )
            db.session.add(session)
            db.session.commit()
            
            # 验证创建成功
            assert session.id is not None
            assert session.session_id == test_session_data['session_id']
            assert session.user_id == test_user.id
            assert session.issue == test_session_data['issue']
            assert session.status == 'running'
            assert session.report_version == 1
            assert session.created_at is not None
            assert session.completed_at is None
    
    def test_session_user_relationship(self, app, test_user, test_session_data):
        """测试用户关联关系"""
        with app.app_context():
            session = DiscussionSession(
                session_id=test_session_data['session_id'],
                user_id=test_user.id,
                issue=test_session_data['issue'],
                status='running'
            )
            db.session.add(session)
            db.session.commit()
            
            # 测试正向关系：session.user
            assert session.user is not None
            assert session.user.id == test_user.id
            assert session.user.username == 'testuser'
            
            # 测试反向关系：user.discussion_sessions
            user_sessions = test_user.discussion_sessions.all()
            assert len(user_sessions) == 1
            assert user_sessions[0].session_id == test_session_data['session_id']
    
    def test_json_fields_storage(self, app, test_user):
        """测试JSON字段存储和查询"""
        with app.app_context():
            test_config = {'rounds': 5, 'backend': 'openai'}
            test_history = [
                {'round': 1, 'plans': ['Plan A', 'Plan B']},
                {'round': 2, 'plans': ['Plan C']}
            ]
            test_decomposition = {
                'core_goal': '提升性能',
                'key_questions': ['问题1', '问题2']
            }
            
            session = DiscussionSession(
                session_id='test_json_001',
                user_id=test_user.id,
                issue='JSON测试',
                config=test_config,
                history=test_history,
                decomposition=test_decomposition,
                status='running'
            )
            db.session.add(session)
            db.session.commit()
            
            # 重新查询验证
            retrieved = DiscussionSession.query.filter_by(session_id='test_json_001').first()
            assert retrieved is not None
            assert retrieved.config == test_config
            assert retrieved.history == test_history
            assert retrieved.decomposition == test_decomposition
            assert retrieved.decomposition['core_goal'] == '提升性能'
            assert len(retrieved.history) == 2
    
    def test_unique_session_id_constraint(self, app, test_user):
        """测试session_id唯一性约束"""
        with app.app_context():
            session1 = DiscussionSession(
                session_id='duplicate_test',
                user_id=test_user.id,
                issue='第一个会话',
                status='running'
            )
            db.session.add(session1)
            db.session.commit()
            
            # 尝试创建相同session_id的会话
            session2 = DiscussionSession(
                session_id='duplicate_test',  # 重复的session_id
                user_id=test_user.id,
                issue='第二个会话',
                status='running'
            )
            db.session.add(session2)
            
            with pytest.raises(IntegrityError):
                db.session.commit()
            
            db.session.rollback()
    
    def test_status_transitions(self, app, test_user):
        """测试状态转换"""
        with app.app_context():
            session = DiscussionSession(
                session_id='status_test',
                user_id=test_user.id,
                issue='状态测试',
                status='running'
            )
            db.session.add(session)
            db.session.commit()
            
            # 初始状态
            assert session.status == 'running'
            assert session.completed_at is None
            
            # 转换为completed状态
            session.status = 'completed'
            session.completed_at = datetime.utcnow()
            db.session.commit()
            
            retrieved = DiscussionSession.query.filter_by(session_id='status_test').first()
            assert retrieved.status == 'completed'
            assert retrieved.completed_at is not None
            
            # 测试其他状态
            for status in ['failed', 'stopped']:
                session.status = status
                db.session.commit()
                assert DiscussionSession.query.get(session.id).status == status
    
    def test_report_version_increment(self, app, test_user):
        """测试报告版本递增"""
        with app.app_context():
            session = DiscussionSession(
                session_id='version_test',
                user_id=test_user.id,
                issue='版本测试',
                status='running',
                report_version=1
            )
            db.session.add(session)
            db.session.commit()
            
            # 初始版本
            assert session.report_version == 1
            
            # 递增版本
            session.report_version += 1
            db.session.commit()
            
            retrieved = DiscussionSession.query.filter_by(session_id='version_test').first()
            assert retrieved.report_version == 2
    
    def test_to_dict_method(self, app, test_user):
        """测试to_dict序列化方法"""
        with app.app_context():
            session = DiscussionSession(
                session_id='dict_test',
                user_id=test_user.id,
                issue='字典转换测试',
                backend='deepseek',
                model='deepseek-chat',
                config={'rounds': 3},
                status='completed',
                history=[{'round': 1}],
                report_html='<html></html>',
                report_version=2
            )
            db.session.add(session)
            db.session.commit()
            
            # 测试完整数据
            full_dict = session.to_dict(include_data=True)
            assert full_dict['session_id'] == 'dict_test'
            assert full_dict['issue'] == '字典转换测试'
            assert full_dict['backend'] == 'deepseek'
            assert full_dict['status'] == 'completed'
            assert full_dict['history'] == [{'round': 1}]
            assert full_dict['report_html'] == '<html></html>'
            assert full_dict['report_version'] == 2
            
            # 测试不包含数据
            minimal_dict = session.to_dict(include_data=False)
            assert minimal_dict['session_id'] == 'dict_test'
            assert minimal_dict['status'] == 'completed'
            assert 'history' not in minimal_dict
            assert 'report_html' not in minimal_dict
    
    def test_cascade_delete(self, app):
        """测试级联删除：删除用户时应删除其会话"""
        with app.app_context():
            # 创建用户和会话
            user = User(username='delete_test', email='delete@test.com')
            user.set_password('pass123')
            db.session.add(user)
            db.session.commit()
            user_id = user.id
            
            session = DiscussionSession(
                session_id='cascade_test',
                user_id=user_id,
                issue='级联删除测试',
                status='running'
            )
            db.session.add(session)
            db.session.commit()
            session_id = session.id
            
            # 验证会话存在
            assert DiscussionSession.query.get(session_id) is not None
            
            # 删除用户
            db.session.delete(user)
            db.session.commit()
            
            # 验证会话也被删除
            assert DiscussionSession.query.get(session_id) is None
    
    def test_nullable_fields(self, app, test_user):
        """测试可空字段"""
        with app.app_context():
            # 只提供必需字段
            session = DiscussionSession(
                session_id='minimal_test',
                user_id=test_user.id,
                issue='最小字段测试',
                status='running'
            )
            db.session.add(session)
            db.session.commit()
            
            # 验证可空字段为None
            assert session.backend is None
            assert session.model is None
            assert session.config is None
            assert session.history is None
            assert session.decomposition is None
            assert session.final_session_data is None
            assert session.search_references is None
            assert session.report_html is None
            assert session.report_json is None
            assert session.completed_at is None
