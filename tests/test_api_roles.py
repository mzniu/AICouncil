"""测试角色管理API端点"""
import pytest
import json
from src.web.app import app


class TestRolesAPI:
    """测试/api/roles相关端点"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_get_roles_list(self, client):
        """测试获取角色列表"""
        response = client.get('/api/roles')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'roles' in data
        assert 'total' in data
        
        # 应该至少有5个核心角色
        assert data['total'] >= 5
        
        # 检查角色数据结构
        roles = data['roles']
        role_names = [r['name'] for r in roles]
        
        assert 'leader' in role_names
        assert 'planner' in role_names
        assert 'auditor' in role_names
        assert 'devils_advocate' in role_names
        assert 'reporter' in role_names
        
        # 检查第一个角色的结构
        first_role = roles[0]
        assert 'name' in first_role
        assert 'display_name' in first_role
        assert 'version' in first_role
        assert 'description' in first_role
        assert 'default_model' in first_role
        assert 'tags' in first_role
        assert 'ui' in first_role
        assert 'stages' in first_role
        assert isinstance(first_role['stages'], list)
    
    def test_get_roles_with_tag_filter(self, client):
        """测试按tag过滤角色"""
        response = client.get('/api/roles?tag=core')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        
        # 核心角色应该至少有3个
        assert data['total'] >= 3
        
        # 检查所有返回的角色是否都有core标签
        for role in data['roles']:
            assert 'core' in role['tags']
    
    def test_get_role_detail(self, client):
        """测试获取指定角色详情"""
        response = client.get('/api/roles/leader')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'role' in data
        
        role = data['role']
        
        # 检查基本字段
        assert role['name'] == 'leader'
        assert role['display_name'] == '议长 (Leader)'
        assert 'version' in role
        assert 'description' in role
        assert 'parameters' in role
        assert 'ui' in role
        
        # 检查stages结构
        assert 'stages' in role
        stages = role['stages']
        assert isinstance(stages, list)
        assert len(stages) == 2  # Leader有decomposition和summary两个阶段
        
        # 检查prompt_preview字段
        assert 'prompt_preview' in role
        assert isinstance(role['prompt_preview'], str)
        assert len(role['prompt_preview']) > 0
    
    def test_get_role_not_found(self, client):
        """测试获取不存在的角色"""
        response = client.get('/api/roles/nonexistent_role')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert '不存在' in data['message']
    
    def test_reload_role(self, client):
        """测试角色热加载"""
        response = client.post('/api/roles/leader/reload')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert '重新加载' in data['message']
        assert 'data' in data
        assert data['data']['name'] == 'leader'
    
    def test_reload_role_not_found(self, client):
        """测试热加载不存在的角色"""
        response = client.post('/api/roles/nonexistent_role/reload')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['status'] == 'error'


class TestRoleUIInfo:
    """测试角色UI信息"""
    
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_all_roles_have_ui_config(self, client):
        """测试所有角色都有UI配置"""
        response = client.get('/api/roles')
        data = json.loads(response.data)
        
        for role in data['roles']:
            # 跳过临时测试角色
            if role['name'].startswith('temp_'):
                continue
            
            assert 'ui' in role, f"Role {role['name']} missing 'ui' field"
            ui = role['ui']
            assert 'icon' in ui, f"Role {role['name']} missing 'ui.icon' field, ui={ui}"
            assert 'color' in ui, f"Role {role['name']} missing 'ui.color' field"
            assert 'description_short' in ui or 'enabled' in ui, f"Role {role['name']} missing 'ui.description_short' or 'ui.enabled'"
    
    def test_role_stages_info(self, client):
        """测试角色stages信息完整性"""
        response = client.get('/api/roles/planner')
        data = json.loads(response.data)
        
        role = data['role']
        assert 'stages' in role
        
        stages = role['stages']
        assert isinstance(stages, list)
        assert len(stages) > 0
        
        # 检查每个stage的结构
        for stage in stages:
            assert 'name' in stage
            assert 'prompt_file' in stage
            assert 'input_vars' in stage
            assert isinstance(stage['input_vars'], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
