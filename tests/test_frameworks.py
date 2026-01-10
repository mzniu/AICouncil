#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试框架库（frameworks.py）

测试BaseFramework抽象类和3个预定义框架：
- SimpleDiscussionFramework
- DeepAnalysisFramework
- BrainstormingFramework
"""

import pytest
from src.agents.frameworks import (
    Framework,
    FrameworkStage,
    get_framework,
    list_frameworks
)


class TestFrameworkStage:
    """测试FrameworkStage数据类"""
    
    def test_stage_creation(self):
        """测试创建Stage"""
        stage = FrameworkStage(
            name="Test Stage",
            description="Test description",
            roles=["planner", "auditor"],
            min_agents=2,
            max_agents=4,
            rounds=2,
            depends_on=None
        )
        
        assert stage.name == "Test Stage"
        assert stage.description == "Test description"
        assert len(stage.roles) == 2
        assert stage.min_agents == 2
        assert stage.max_agents == 4
        assert stage.rounds == 2
        assert stage.depends_on is None
    
    def test_stage_with_dependencies(self):
        """测试带依赖的Stage"""
        stage = FrameworkStage(
            name="Dependent Stage",
            description="Depends on previous stage",
            roles=["leader"],
            min_agents=1,
            max_agents=1,
            rounds=1,
            depends_on=["Stage 1"]
        )
        
        assert stage.depends_on == ["Stage 1"]


class TestFramework:
    """测试Framework基类"""
    
    def test_framework_registry(self):
        """测试框架注册表"""
        frameworks = list_frameworks()
        
        # 应该至少有3个框架
        assert len(frameworks) >= 3
        
        # 检查框架ID
        framework_ids = [fw["id"] for fw in frameworks]
        assert "simple_discussion" in framework_ids
        assert "deep_analysis" in framework_ids
        assert "brainstorming" in framework_ids
    
    def test_get_framework_by_id(self):
        """测试通过ID获取框架"""
        # 测试获取罗伯特议事规则
        framework = get_framework("roberts_rules")
        assert framework is not None
        assert isinstance(framework, Framework)
        
        # 测试获取图尔敏论证模型
        framework = get_framework("toulmin_model")
        assert framework is not None
        assert isinstance(framework, Framework)
        
        # 测试获取批判性思维框架
        framework = get_framework("critical_thinking")
        assert framework is not None
        assert isinstance(framework, Framework)
    
    def test_get_invalid_framework(self):
        """测试获取不存在的框架"""
        with pytest.raises(ValueError, match="Unknown framework"):
            get_framework("nonexistent_framework")
    
    def test_framework_has_stages(self):
        """测试框架包含stages"""
        framework = get_framework("roberts_rules")
        assert len(framework.stages) > 0
        assert all(isinstance(stage, FrameworkStage) for stage in framework.stages)


class TestRobertsRules:
    """测试罗伯特议事规则框架"""
    
    @pytest.fixture
    def framework(self):
        """创建框架实例"""
        return get_framework("roberts_rules")
    
    def test_framework_metadata(self, framework):
        """测试框架元数据"""
        assert framework.id == "roberts_rules"
        assert framework.name == "罗伯特议事规则"
        assert len(framework.stages) >= 2
    
    def test_stages_have_valid_roles(self, framework):
        """测试各阶段的角色配置"""
        for stage in framework.stages:
            assert len(stage.roles) > 0
            # 验证角色是有效的
            valid_roles = {"leader", "planner", "auditor", "reporter"}
            for role in stage.roles:
                assert role in valid_roles, f"Invalid role: {role}"


class TestToulminModel:
    """测试图尔敏论证模型"""
    
    @pytest.fixture
    def framework(self):
        """创建框架实例"""
        return get_framework("toulmin_model")
    
    def test_framework_metadata(self, framework):
        """测试框架元数据"""
        assert framework.id == "toulmin_model"
        assert "图尔敏" in framework.name or "Toulmin" in framework.name
        assert len(framework.stages) >= 2
    
    def test_framework_keywords(self, framework):
        """测试框架关键词"""
        # 图尔敏模型应该和论证相关
        assert any(keyword in ["论证", "推理", "evidence", "argument"] 
                   for keyword in framework.keywords)


class TestCriticalThinking:
    """测试批判性思维框架"""
    
    @pytest.fixture
    def framework(self):
        """创建框架实例"""
        return get_framework("critical_thinking")
    
    def test_framework_metadata(self, framework):
        """测试框架元数据"""
        assert framework.id == "critical_thinking"
        assert "批判" in framework.name or "Critical" in framework.name
        assert len(framework.stages) >= 2
    
    def test_framework_tags(self, framework):
        """测试框架标签"""
        # 批判性思维框架应该有相关标签
        assert len(framework.tags) > 0


class TestFrameworkEdgeCases:
    """测试框架的边界情况"""
    
    def test_framework_serialization(self):
        """测试框架序列化"""
        framework = get_framework("roberts_rules")
        framework_dict = framework.to_dict()
        
        assert "id" in framework_dict
        assert "name" in framework_dict
        assert "stages" in framework_dict
        assert isinstance(framework_dict["stages"], list)
    
    def test_framework_immutability(self):
        """测试框架定义的不可变性"""
        framework1 = get_framework("roberts_rules")
        framework2 = get_framework("roberts_rules")
        
        # 每次获取应该返回不同实例
        assert framework1 is not framework2
        
        # 但内容应该相同
        assert framework1.id == framework2.id
        assert len(framework1.stages) == len(framework2.stages)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
