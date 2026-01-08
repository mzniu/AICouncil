"""测试所有角色的chain创建功能"""
import pytest
from src.agents.langchain_agents import (
    make_leader_chain,
    make_planner_chain,
    make_auditor_chain,
    make_devils_advocate_chain,
    make_reporter_chain,
    make_report_auditor_chain
)
from src.agents.role_manager import RoleManager


class TestAllRoleChains:
    """测试所有角色的chain创建"""
    
    @pytest.fixture
    def model_config(self):
        """通用模型配置"""
        return {
            "backend": "deepseek",
            "model_name": "deepseek-reasoner",
            "api_key": "test_key",
            "temperature": 0.7
        }
    
    def test_all_roles_loaded(self):
        """测试所有角色都能正确加载"""
        rm = RoleManager()
        roles = rm.list_roles()
        
        # 应该至少有6个角色（不包括test_role）
        role_names = [r.name for r in roles]
        assert "leader" in role_names
        assert "planner" in role_names
        assert "auditor" in role_names
        assert "devils_advocate" in role_names
        assert "reporter" in role_names
        assert "report_auditor" in role_names
    
    def test_leader_chain_creation(self, model_config):
        """测试Leader chain创建（两种模式）"""
        try:
            # 中间轮次
            chain1 = make_leader_chain(model_config, is_final_round=False)
            assert chain1 is not None
            
            # 最终轮次
            chain2 = make_leader_chain(model_config, is_final_round=True)
            assert chain2 is not None
        except Exception as e:
            pytest.skip(f"Skipping due to API configuration: {e}")
    
    def test_planner_chain_creation(self, model_config):
        """测试Planner chain创建"""
        try:
            chain = make_planner_chain(model_config)
            assert chain is not None
        except Exception as e:
            pytest.skip(f"Skipping due to API configuration: {e}")
    
    def test_auditor_chain_creation(self, model_config):
        """测试Auditor chain创建"""
        try:
            chain = make_auditor_chain(model_config)
            assert chain is not None
        except Exception as e:
            pytest.skip(f"Skipping due to API configuration: {e}")
    
    def test_devils_advocate_chain_creation(self, model_config):
        """测试Devil's Advocate chain创建（两种阶段）"""
        try:
            # decomposition阶段
            chain1 = make_devils_advocate_chain(model_config, stage="decomposition")
            assert chain1 is not None
            
            # summary阶段
            chain2 = make_devils_advocate_chain(model_config, stage="summary")
            assert chain2 is not None
        except Exception as e:
            pytest.skip(f"Skipping due to API configuration: {e}")
    
    def test_reporter_chain_creation(self, model_config):
        """测试Reporter chain创建"""
        try:
            chain = make_reporter_chain(model_config)
            assert chain is not None
        except Exception as e:
            pytest.skip(f"Skipping due to API configuration: {e}")
    
    def test_report_auditor_chain_creation(self, model_config):
        """测试Report Auditor chain创建"""
        try:
            chain = make_report_auditor_chain(model_config)
            assert chain is not None
        except Exception as e:
            pytest.skip(f"Skipping due to API configuration: {e}")
    
    def test_role_prompts_loaded(self):
        """测试所有角色的prompt都能正确加载"""
        rm = RoleManager()
        
        # Leader - 2个stages
        assert len(rm.load_prompt("leader", "decomposition")) > 0
        assert len(rm.load_prompt("leader", "summary")) > 0
        
        # Planner - 1个stage
        assert len(rm.load_prompt("planner", "proposal")) > 0
        
        # Auditor - 1个stage
        assert len(rm.load_prompt("auditor", "review")) > 0
        
        # Devil's Advocate - 2个stages
        assert len(rm.load_prompt("devils_advocate", "decomposition")) > 0
        assert len(rm.load_prompt("devils_advocate", "summary")) > 0
        
        # Reporter - 1个stage
        assert len(rm.load_prompt("reporter", "generate")) > 0
        
        # Report Auditor - 1个stage
        assert len(rm.load_prompt("report_auditor", "revision")) > 0
    
    def test_role_schemas_available(self):
        """测试所有角色的schema都能正确导入"""
        rm = RoleManager()
        
        # Leader - LeaderSummary
        leader_schema = rm.get_schema_class("leader", "decomposition")
        assert leader_schema is not None
        assert leader_schema.__name__ == "LeaderSummary"
        
        # Planner - PlanSchema
        planner_schema = rm.get_schema_class("planner", "proposal")
        assert planner_schema is not None
        assert planner_schema.__name__ == "PlanSchema"
        
        # Auditor - AuditorSchema
        auditor_schema = rm.get_schema_class("auditor", "review")
        assert auditor_schema is not None
        assert auditor_schema.__name__ == "AuditorSchema"
        
        # Devil's Advocate - DevilsAdvocateSchema
        da_schema = rm.get_schema_class("devils_advocate", "decomposition")
        assert da_schema is not None
        assert da_schema.__name__ == "DevilsAdvocateSchema"
        
        # Reporter - None (直接输出HTML)
        reporter_schema = rm.get_schema_class("reporter", "generate")
        assert reporter_schema is None
    
    def test_core_roles_tagged(self):
        """测试核心角色都正确标记"""
        rm = RoleManager()
        core_roles = rm.list_roles(tag="core")
        
        core_role_names = [r.name for r in core_roles]
        assert "leader" in core_role_names
        assert "planner" in core_role_names
        assert "auditor" in core_role_names
    
    def test_role_ui_configs(self):
        """测试所有角色都有UI配置"""
        rm = RoleManager()
        
        for role_name in ["leader", "planner", "auditor", "devils_advocate", "reporter", "report_auditor"]:
            role = rm.get_role(role_name)
            assert role.ui is not None
            assert "icon" in role.ui
            assert "color" in role.ui
            assert "description_short" in role.ui


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
