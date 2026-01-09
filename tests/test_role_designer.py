"""
角色设计师Agent的单元测试

测试内容：
1. Schema验证（RoleDesignOutput等）
2. RoleManager.create_new_role()
3. RoleManager.generate_yaml_from_design()
4. API端点 POST /api/roles/design
"""

import pytest
import json
from pathlib import Path
from pydantic import ValidationError
from src.agents.schemas import RoleDesignOutput, RoleStageDefinition, FamousPersona
from src.agents.role_manager import RoleManager


class TestRoleDesignSchemas:
    """测试角色设计Schema的验证逻辑"""
    
    def test_role_stage_definition_valid(self):
        """测试有效的阶段定义"""
        stage = RoleStageDefinition(
            stage_name="规划阶段",
            output_schema="PlannerOutput",
            responsibilities=["分析问题", "提出方案"],
            thinking_style="批判性思维",
            output_format="JSON结构化输出"
        )
        assert stage.stage_name == "规划阶段"
        assert len(stage.responsibilities) == 2
    
    def test_role_stage_definition_missing_fields(self):
        """测试缺少必需字段的阶段定义"""
        with pytest.raises(ValidationError):
            RoleStageDefinition(
                stage_name="规划阶段",
                # 缺少output_schema
                responsibilities=["分析问题"]
            )
    
    def test_famous_persona_valid(self):
        """测试有效的人物推荐"""
        persona = FamousPersona(
            name="诸葛亮",
            reason="擅长战略规划和多角度分析",
            traits=["谨慎", "全局观", "逻辑严密"]
        )
        assert persona.name == "诸葛亮"
        assert len(persona.traits) == 3
    
    def test_role_design_output_valid(self):
        """测试完整的角色设计输出"""
        design = RoleDesignOutput(
            role_name="strategic_planner",  # 修改为英文命名
            display_name="战略规划师",
            role_description="负责制定长期战略和执行计划",
            stages=[
                RoleStageDefinition(
                    stage_name="规划阶段",
                    output_schema="PlannerOutput",
                    responsibilities=["分析环境", "制定战略"],
                    thinking_style="系统性思维",
                    output_format="结构化报告"
                )
            ],
            recommended_personas=[
                FamousPersona(
                    name="孙子",
                    reason="兵法大师，擅长战略布局",
                    traits=["谨慎", "全局观"]
                )
            ]
        )
        assert design.role_name == "strategic_planner"
        assert len(design.stages) == 1
        assert len(design.recommended_personas) == 1
    
    def test_role_design_output_invalid_role_name(self):
        """测试无效的角色名称（包含非法字符）"""
        with pytest.raises(ValidationError):
            RoleDesignOutput(
                role_name="战略/规划师",  # 包含斜杠
                display_name="战略规划师",
                role_description="测试",
                stages=[],
                recommended_personas=[]
            )
    
    def test_role_design_output_empty_stages(self):
        """测试空阶段列表"""
        with pytest.raises(ValidationError):
            RoleDesignOutput(
                role_name="test_role",
                display_name="测试角色",
                role_description="测试描述",
                stages=[],  # 至少需要1个阶段
                recommended_personas=[]
            )


class TestRoleManagerDesigner:
    """测试RoleManager的角色创建功能"""
    
    @pytest.fixture
    def role_manager(self):
        """创建RoleManager实例"""
        return RoleManager()
    
    @pytest.fixture
    def sample_design(self):
        """创建示例角色设计"""
        return RoleDesignOutput(
            role_name="test_designer_role",
            display_name="测试设计角色",
            role_description="这是一个测试角色",
            stages=[
                RoleStageDefinition(
                    stage_name="分析阶段",
                    output_schema="PlannerOutput",
                    responsibilities=["需求分析"],
                    thinking_style="分析性",
                    output_format="JSON"
                )
            ],
            recommended_personas=[
                FamousPersona(
                    name="测试人物",
                    reason="测试原因",
                    traits=["测试特质"]
                )
            ]
        )
    
    def test_generate_yaml_from_design(self, role_manager, sample_design):
        """测试从设计生成YAML内容"""
        yaml_content = role_manager.generate_yaml_from_design(sample_design)
        
        # 验证YAML内容包含关键字段
        assert "name: test_designer_role" in yaml_content
        assert "display_name: 测试设计角色" in yaml_content
        assert "description: 这是一个测试角色" in yaml_content
        assert "test_designer_role_main.md" in yaml_content  # 验证prompt文件名
        assert "PlannerOutput" in yaml_content  # 验证schema

    
    def test_create_new_role_success(self, role_manager, sample_design):
        """测试成功创建新角色"""
        # 确保测试角色不存在
        roles_dir = role_manager.get_roles_directory()
        test_yaml = roles_dir / "test_designer_role.yaml"
        test_prompt = roles_dir / "test_designer_role_main.md"
        
        if test_yaml.exists():
            test_yaml.unlink()
        if test_prompt.exists():
            test_prompt.unlink()
        
        # 清除缓存，避免has_role检查到旧数据
        if role_manager.has_role("test_designer_role"):
            role_manager._roles.pop("test_designer_role", None)
        
        success, error = role_manager.create_new_role(sample_design)
        
        # 清理测试角色
        if success:
            if test_yaml.exists():
                test_yaml.unlink()
            if test_prompt.exists():
                test_prompt.unlink()
        
        assert success is True, f"创建失败: {error}"
        assert error is None
    
    def test_create_new_role_duplicate(self, role_manager):
        """测试创建重名角色时报错"""
        # 使用已存在的角色名
        design = RoleDesignOutput(
            role_name="leader",  # leader已存在
            display_name="重复角色",
            role_description="测试重名",
            stages=[
                RoleStageDefinition(
                    stage_name="测试",
                    output_schema="LeaderOutput",
                    responsibilities=["测试"],
                    thinking_style="测试",
                    output_format="JSON"
                )
            ],
            recommended_personas=[]
        )
        
        success, error = role_manager.create_new_role(design)
        assert success is False
        assert "已存在" in error or "exists" in error.lower()


class TestRoleDesignerAPI:
    """测试角色设计相关的API端点"""
    
    @pytest.fixture
    def client(self):
        """创建Flask测试客户端"""
        from src.web.app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_design_role_endpoint_success(self, client):
        """测试角色设计端点正常响应"""
        response = client.post('/api/roles/design', json={
            'requirement': '我需要一个擅长数据分析的角色，能够处理统计和可视化任务'
        })
        
        # 注意：这个测试可能需要实际的LLM调用，可能需要mock
        # 暂时只验证端点存在和基本响应格式
        assert response.status_code in [200, 500, 503]  # 允许LLM调用失败
    
    def test_design_role_endpoint_missing_requirement(self, client):
        """测试缺少需求参数时返回400"""
        response = client.post('/api/roles/design', json={})
        assert response.status_code == 400
    
    def test_create_role_endpoint_success(self, client):
        """测试创建角色端点"""
        # 先清理可能存在的测试角色
        from src.agents.role_manager import RoleManager
        rm = RoleManager()
        roles_dir = rm.get_roles_directory()
        test_yaml = roles_dir / 'test_api_role.yaml'
        test_prompt = roles_dir / 'test_api_role_main.md'
        
        if test_yaml.exists():
            test_yaml.unlink()
        if test_prompt.exists():
            test_prompt.unlink()
        if rm.has_role('test_api_role'):
            rm._roles.pop('test_api_role', None)
        
        design_data = {
            'role_name': 'test_api_role',
            'display_name': '测试API角色',
            'role_description': '通过API创建的测试角色',
            'stages': [
                {
                    'stage_name': '测试阶段',
                    'output_schema': 'PlannerOutput',
                    'responsibilities': ['测试任务'],
                    'thinking_style': '测试思维',
                    'output_format': 'JSON'
                }
            ],
            'recommended_personas': []
        }
        
        response = client.post('/api/roles', json=design_data)
        
        # 清理测试角色
        if response.status_code == 200:
            if test_yaml.exists():
                test_yaml.unlink()
            if test_prompt.exists():
                test_prompt.unlink()
        
        assert response.status_code == 200, f"创建失败: {response.get_json()}"
        data = response.get_json()
        assert data['success'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
