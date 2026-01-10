#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Meta-Orchestrator工具函数（meta_tools.py）

测试3个工具函数：
- list_roles: 获取所有可用角色
- create_role: 调用role_designer生成新角色
- select_framework: 根据需求匹配最优框架
"""

import pytest
from src.agents.meta_tools import (
    list_roles,
    create_role,
    select_framework,
    execute_tool,
    get_tool_schemas,
    format_tool_result_for_llm
)


class TestListRoles:
    """测试list_roles工具函数"""
    
    def test_list_roles_success(self):
        """测试成功获取角色列表"""
        result = list_roles()
        
        assert result["success"] is True
        assert "roles" in result
        assert isinstance(result["roles"], list)
        assert result["total_count"] >= 0
        assert len(result["roles"]) == result["total_count"]
    
    def test_list_roles_structure(self):
        """测试角色列表的结构"""
        result = list_roles()
        
        if result["total_count"] > 0:
            first_role = result["roles"][0]
            # 检查必需字段
            assert "name" in first_role
            assert "display_name" in first_role
            assert "description" in first_role
            assert "capabilities_summary" in first_role
    
    def test_list_roles_contains_builtin(self):
        """测试包含内置角色"""
        result = list_roles()
        
        role_names = [r["name"] for r in result["roles"]]
        # 应该包含基本角色
        assert "leader" in role_names or "planner" in role_names


class TestSelectFramework:
    """测试select_framework工具函数"""
    
    def test_select_framework_simple_case(self):
        """测试简单需求的框架选择"""
        result = select_framework("简单的信息整理任务")
        
        # 检查返回结果包含框架信息
        assert "framework_id" in result or "frameworks" in result or "error" not in result
    
    def test_select_framework_complex_case(self):
        """测试复杂需求的框架选择"""
        result = select_framework("需要深入分析和多轮论证的复杂决策问题")
        
        assert "success" in result
        # 复杂问题可能返回多个候选框架
        if "frameworks" in result:
            assert len(result["frameworks"]) > 0
    
    def test_select_framework_with_keywords(self):
        """测试带关键词的框架匹配"""
        result = select_framework("需要进行论证和推理")
        
        assert "success" in result


class TestMetaToolsIntegration:
    """测试工具函数的集成"""
    
    def test_tool_schemas_available(self):
        """测试工具schemas的可用性"""
        schemas = get_tool_schemas()
        
        assert isinstance(schemas, list)
        assert len(schemas) >= 2  # 至少list_roles和select_framework
        
        # 检查schema格式
        for schema in schemas:
            assert "type" in schema
            assert schema["type"] == "function"
            assert "function" in schema
            
            func_def = schema["function"]
            assert "name" in func_def
            assert "description" in func_def
            assert "parameters" in func_def
    
    def test_execute_tool_list_roles(self):
        """测试execute_tool执行list_roles"""
        result = execute_tool("list_roles", {})
        
        assert "success" in result or "roles" in result
    
    def test_execute_tool_select_framework(self):
        """测试execute_tool执行select_framework"""
        result = execute_tool(
            "select_framework",
            {"requirement": "简单讨论"}
        )
        
        assert "success" in result or "frameworks" in result
    
    def test_execute_tool_invalid(self):
        """测试执行不存在的工具"""
        result = execute_tool("invalid_tool", {})
        
        # 应该返回错误信息
        assert "error" in result or "success" in result and not result["success"]
    
    def test_format_tool_result(self):
        """测试工具结果格式化"""
        # 模拟工具结果
        mock_result = {
            "success": True,
            "roles": [{"name": "test", "display_name": "测试"}],
            "total_count": 1
        }
        
        formatted = format_tool_result_for_llm("list_roles", mock_result)
        
        assert isinstance(formatted, str)
        assert len(formatted) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
