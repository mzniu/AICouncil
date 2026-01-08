"""单元测试 - RoleManager角色管理器"""
import pytest
from pathlib import Path
from src.agents.role_manager import RoleManager, RoleConfig, RoleStage, ROLES_DIR


class TestRoleManager:
    """测试RoleManager基础功能"""
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = RoleManager()
        manager2 = RoleManager()
        assert manager1 is manager2
    
    def test_load_test_role(self):
        """测试加载测试角色"""
        manager = RoleManager()
        assert manager.has_role("test_role")
        
        role = manager.get_role("test_role")
        assert role.name == "test_role"
        assert role.display_name == "测试角色 (Test Role)"
        assert role.version == "1.0.0"
        assert "test" in role.tags
    
    def test_role_stages(self):
        """测试角色阶段配置"""
        manager = RoleManager()
        role = manager.get_role("test_role")
        
        assert "stage1" in role.stages
        assert "stage2" in role.stages
        
        stage1 = role.stages["stage1"]
        assert stage1.prompt_file == "test_role_stage1.md"
        assert stage1.schema == "LeaderSummary"
        assert stage1.input_vars == ["inputs", "current_time"]
    
    def test_load_prompt(self):
        """测试加载Prompt文件"""
        manager = RoleManager()
        
        prompt = manager.load_prompt("test_role", "stage1")
        assert "Test Role - Stage 1 Prompt" in prompt
        assert "{current_time}" in prompt
        assert "{inputs}" in prompt
    
    def test_load_prompt_cache(self):
        """测试Prompt缓存"""
        manager = RoleManager()
        
        # 第一次加载
        prompt1 = manager.load_prompt("test_role", "stage1")
        # 第二次加载（应该从缓存读取）
        prompt2 = manager.load_prompt("test_role", "stage1")
        
        assert prompt1 == prompt2
        assert manager.load_prompt.cache_info().hits > 0
    
    def test_clear_cache(self):
        """测试清除缓存"""
        manager = RoleManager()
        
        # 加载一次
        manager.load_prompt("test_role", "stage1")
        assert manager.load_prompt.cache_info().currsize > 0
        
        # 清除缓存
        manager.clear_cache()
        assert manager.load_prompt.cache_info().currsize == 0
    
    def test_list_roles(self):
        """测试列出所有角色"""
        manager = RoleManager()
        roles = manager.list_roles()
        
        assert len(roles) > 0
        assert any(r.name == "test_role" for r in roles)
    
    def test_list_roles_by_tag(self):
        """测试按标签过滤角色"""
        manager = RoleManager()
        test_roles = manager.list_roles(tag="test")
        
        assert len(test_roles) > 0
        assert all("test" in r.tags for r in test_roles)
    
    def test_get_schema_class(self):
        """测试获取Schema类"""
        manager = RoleManager()
        
        schema_class = manager.get_schema_class("test_role", "stage1")
        assert schema_class.__name__ == "LeaderSummary"
    
    def test_role_not_found(self):
        """测试角色不存在时抛出异常"""
        manager = RoleManager()
        
        with pytest.raises(ValueError, match="角色未找到"):
            manager.get_role("nonexistent_role")
    
    def test_stage_not_found(self):
        """测试阶段不存在时抛出异常"""
        manager = RoleManager()
        
        with pytest.raises(ValueError, match="没有阶段"):
            manager.load_prompt("test_role", "nonexistent_stage")
    
    def test_prompt_file_not_found(self):
        """测试Prompt文件不存在时抛出异常"""
        manager = RoleManager()
        
        # 创建一个临时角色配置，指向不存在的文件
        test_yaml = ROLES_DIR / "temp_test.yaml"
        test_yaml.write_text("""
name: temp_test
display_name: Temp Test
version: "1.0.0"
description: Temporary test role
stages:
  test_stage:
    prompt_file: nonexistent.md
    schema: LeaderSummary
    input_vars: [inputs]
""", encoding="utf-8")
        
        try:
            # 重新加载以包含新角色
            manager.reload_role("temp_test")
            
            with pytest.raises(FileNotFoundError, match="Prompt文件不存在"):
                manager.load_prompt("temp_test", "test_stage")
        finally:
            # 清理临时文件
            if test_yaml.exists():
                test_yaml.unlink()
    
    def test_role_config_from_yaml(self):
        """测试从YAML文件创建RoleConfig"""
        yaml_path = ROLES_DIR / "test_role.yaml"
        role_config = RoleConfig.from_yaml(yaml_path)
        
        assert isinstance(role_config, RoleConfig)
        assert role_config.name == "test_role"
        assert isinstance(role_config.stages, dict)
        assert isinstance(role_config.default_model, dict)
        assert isinstance(role_config.parameters, dict)
    
    def test_reload_role(self):
        """测试热加载角色"""
        manager = RoleManager()
        
        # 获取原始角色
        original_role = manager.get_role("test_role")
        original_version = original_role.version
        
        # 修改YAML文件
        yaml_path = ROLES_DIR / "test_role.yaml"
        original_content = yaml_path.read_text(encoding="utf-8")
        modified_content = original_content.replace('version: "1.0.0"', 'version: "1.0.1"')
        yaml_path.write_text(modified_content, encoding="utf-8")
        
        try:
            # 重新加载
            manager.reload_role("test_role")
            
            # 验证版本已更新
            reloaded_role = manager.get_role("test_role")
            assert reloaded_role.version == "1.0.1"
        finally:
            # 恢复原始内容
            yaml_path.write_text(original_content, encoding="utf-8")
            manager.reload_role("test_role")


class TestRoleStage:
    """测试RoleStage数据类"""
    
    def test_role_stage_creation(self):
        """测试创建RoleStage"""
        stage = RoleStage(
            prompt_file="test.md",
            schema="TestSchema",
            input_vars=["var1", "var2"]
        )
        
        assert stage.prompt_file == "test.md"
        assert stage.schema == "TestSchema"
        assert stage.input_vars == ["var1", "var2"]


class TestRoleConfig:
    """测试RoleConfig数据类"""
    
    def test_role_config_minimal(self):
        """测试最小配置创建RoleConfig"""
        config = RoleConfig(
            name="test",
            display_name="Test",
            version="1.0.0",
            description="Test role",
            stages={}
        )
        
        assert config.name == "test"
        assert config.default_model == {}
        assert config.parameters == {}
        assert config.tags == []
        assert config.ui == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
