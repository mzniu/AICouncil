import sys
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.web.app import app as flask_app
import time


def test_status():
    """测试 /api/status 端点
    
    场景：获取系统运行状态
    预期：返回 200 状态码，响应包含 is_running 字段
    """
    with flask_app.test_client() as c:
        rv = c.get('/api/status')
        assert rv.status_code == 200
        j = rv.get_json()
        assert 'is_running' in j


def test_start_missing_issue():
    """测试启动讨论时缺少必填参数
    
    场景：POST /api/start 不提供 issue 参数
    预期：返回 400 错误（参数校验失败）
    """
    with flask_app.test_client() as c:
        rv = c.post('/api/start', json={})
        assert rv.status_code == 400


def test_start_and_stop_flow():
    """测试完整的启动-停止讨论流程
    
    场景：
      1. 启动一个单轮讨论（issue='unittest issue', rounds=1）
      2. 等待后台线程初始化（0.5秒）
      3. 停止讨论
    预期：
      - 启动请求返回 200，status='ok'
      - 停止请求返回 200，status='ok'
    """
    with flask_app.test_client() as c:
        rv = c.post('/api/start', json={'issue': 'unittest issue', 'rounds': 1})
        assert rv.status_code == 200
        assert rv.get_json().get('status') == 'ok'
        time.sleep(0.5)
        s = c.post('/api/stop')
        assert s.status_code == 200
        assert s.get_json().get('status') == 'ok'


def test_events_and_reset():
    """测试事件获取与重置功能
    
    场景：
      1. 调用 /api/reset 清空讨论状态
      2. 获取 /api/events 返回空的事件列表
    预期：
      - 返回 200 状态码
      - 响应包含 events、logs、final_report 三个字段
    """
    with flask_app.test_client() as c:
        c.post('/api/reset')
        rv = c.get('/api/events')
        assert rv.status_code == 200
        j = rv.get_json()
        assert 'events' in j and 'logs' in j and 'final_report' in j


def test_presets_crud():
    """测试议会配置预设的 CRUD 操作
    
    场景：
      1. 创建预设（POST /api/presets，name='testpreset', config={'a': 1}）
      2. 列出所有预设（GET /api/presets），验证新预设存在
      3. 删除预设（DELETE /api/presets/testpreset）
    预期：
      - 所有操作返回 200 状态码
      - 创建后能在列表中找到该预设
      - 删除成功返回 status='success'
    """
    with flask_app.test_client() as c:
        rv = c.post('/api/presets', json={'name': 'testpreset', 'config': {'a': 1}})
        assert rv.status_code == 200
        assert rv.get_json().get('status') == 'success'
        g = c.get('/api/presets')
        assert g.status_code == 200
        data = g.get_json()
        assert data.get('status') == 'success'
        assert 'testpreset' in data.get('presets', {})
        d = c.delete('/api/presets/testpreset')
        assert d.status_code == 200
        assert d.get_json().get('status') == 'success'


def test_rereport_without_session():
    """测试在没有会话时重新生成报告
    
    场景：未启动讨论时调用 /api/rereport
    预期：返回 400 错误（缺少当前会话 ID）
    """
    with flask_app.test_client() as c:
        rv = c.post('/api/rereport', json={})
        assert rv.status_code == 400


def test_list_workspaces_empty(tmp_path, monkeypatch):
    """测试列出工作空间（空列表场景）
    
    场景：
      1. 使用 monkeypatch 将工作空间目录指向临时目录
      2. 调用 GET /api/workspaces
    预期：
      - 返回 200 状态码
      - 响应包含 workspaces 字段（空列表）
    注意：使用 tmp_path 隔离测试，避免污染真实工作空间
    """
    from src.utils import path_manager
    tmp_workspaces = tmp_path / 'workspaces'
    tmp_workspaces.mkdir()
    monkeypatch.setattr(path_manager, 'get_workspace_dir', lambda: tmp_workspaces)
    with flask_app.test_client() as c:
        rv = c.get('/api/workspaces')
        assert rv.status_code == 200
        j = rv.get_json()
        assert 'workspaces' in j
