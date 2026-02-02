"""
pytest配置和fixtures
"""
import pytest
import tempfile
import os
import sys
from flask import Flask

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models import db, User, DiscussionSession


@pytest.fixture(scope='function')
def app():
    """创建测试Flask应用"""
    from src.web.app import app as flask_app
    
    # 使用临时SQLite数据库
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{temp_db.name}'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    flask_app.config['SECRET_KEY'] = 'test-secret-key'
    flask_app.config['WTF_CSRF_ENABLED'] = False  # 禁用CSRF以简化测试
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()
    
    # 清理临时数据库文件
    try:
        os.unlink(temp_db.name)
    except:
        pass


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()
