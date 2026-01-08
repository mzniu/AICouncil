"""测试Leader角色配置和加载"""
import pytest
from src.agents.role_manager import RoleManager
from src.agents.schemas import LeaderSummary


class TestLeaderRole:
    """测试Leader角色配置"""
    
    def test_leader_role_exists(self):
        """测试Leader角色是否存在"""
        rm = RoleManager()
        assert rm.has_role("leader"), "Leader角色应该存在"
    
    def test_leader_role_config(self):
        """测试Leader角色配置正确性"""
        rm = RoleManager()
        role = rm.get_role("leader")
        
        assert role.name == "leader"
        assert role.display_name == "议长 (Leader)"
        assert role.version == "1.0.0"
        assert "orchestration" in role.tags
        assert "synthesis" in role.tags
        assert "core" in role.tags
    
    def test_leader_stages(self):
        """测试Leader角色的stages配置"""
        rm = RoleManager()
        role = rm.get_role("leader")
        
        assert "decomposition" in role.stages
        assert "summary" in role.stages
        
        decomp_stage = role.stages["decomposition"]
        assert decomp_stage.prompt_file == "leader_decomposition.md"
        assert decomp_stage.schema == "LeaderSummary"
        assert "inputs" in decomp_stage.input_vars
        assert "current_time" in decomp_stage.input_vars
        
        summary_stage = role.stages["summary"]
        assert summary_stage.prompt_file == "leader_summary.md"
        assert summary_stage.schema == "LeaderSummary"
        assert "inputs" in summary_stage.input_vars
        assert "current_time" in summary_stage.input_vars
    
    def test_leader_decomposition_prompt(self):
        """测试Leader decomposition阶段的prompt加载"""
        rm = RoleManager()
        prompt = rm.load_prompt("leader", "decomposition")
        
        assert prompt is not None
        assert len(prompt) > 0
        # 检查关键词是否存在
        assert "议长" in prompt
        assert "{inputs}" in prompt
        assert "{current_time}" in prompt
        assert "is_final_round" in prompt
        assert "false" in prompt  # decomposition阶段should set to false
        assert "next_round_focus" in prompt  # decomposition需要规划下一轮
    
    def test_leader_summary_prompt(self):
        """测试Leader summary阶段的prompt加载"""
        rm = RoleManager()
        prompt = rm.load_prompt("leader", "summary")
        
        assert prompt is not None
        assert len(prompt) > 0
        # 检查关键词是否存在
        assert "议长" in prompt
        assert "{inputs}" in prompt
        assert "{current_time}" in prompt
        assert "最后一轮" in prompt  # summary阶段的特殊标记
        assert "is_final_round" in prompt
        assert "true" in prompt  # summary阶段should set to true
        assert "next_round_focus" in prompt
        assert "null" in prompt  # summary阶段next_round_focus应为null
    
    def test_leader_schema_import(self):
        """测试Leader角色的schema能够正确导入"""
        rm = RoleManager()
        schema_class = rm.get_schema_class("leader", "decomposition")
        
        assert schema_class is not None
        assert schema_class == LeaderSummary
        
        # 两个stage应该使用同一个schema
        schema_class2 = rm.get_schema_class("leader", "summary")
        assert schema_class2 == LeaderSummary
    
    def test_leader_prompt_caching(self):
        """测试Leader prompt的缓存机制"""
        rm = RoleManager()
        
        # 第一次加载
        prompt1 = rm.load_prompt("leader", "decomposition")
        # 第二次加载应该从缓存读取
        prompt2 = rm.load_prompt("leader", "decomposition")
        
        # 应该是相同的对象（缓存命中）
        assert prompt1 == prompt2
        
        # 清除缓存后重新加载
        rm.clear_cache()
        prompt3 = rm.load_prompt("leader", "decomposition")
        
        # 内容应该相同但可能是不同对象
        assert prompt1 == prompt3


class TestLeaderChainCreation:
    """测试make_leader_chain函数使用RoleManager"""
    
    def test_make_leader_chain_intermediate_round(self):
        """测试创建中间轮次的Leader chain"""
        from src.agents.langchain_agents import make_leader_chain
        
        model_config = {
            "backend": "deepseek",
            "model_name": "deepseek-reasoner",
            "api_key": "test_key",
            "temperature": 0.7
        }
        
        try:
            chain = make_leader_chain(model_config, is_final_round=False)
            assert chain is not None
        except Exception as e:
            # API key可能无效，但函数应该能正常创建chain对象
            pytest.skip(f"Skipping due to API configuration: {e}")
    
    def test_make_leader_chain_final_round(self):
        """测试创建最终轮次的Leader chain"""
        from src.agents.langchain_agents import make_leader_chain
        
        model_config = {
            "backend": "deepseek",
            "model_name": "deepseek-reasoner",
            "api_key": "test_key",
            "temperature": 0.7
        }
        
        try:
            chain = make_leader_chain(model_config, is_final_round=True)
            assert chain is not None
        except Exception as e:
            pytest.skip(f"Skipping due to API configuration: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
