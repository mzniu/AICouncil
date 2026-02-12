"""
测试meta_tools.py的get_tools_for_role函数
"""

import sys
sys.path.insert(0, "D:\\git\\MyCouncil")

from src.agents.meta_tools import get_tools_for_role

print("=" * 80)
print("测试 get_tools_for_role() 函数")
print("=" * 80)

# 测试各种角色类型
roles_to_test = ["meta", "leader", "planner", "auditor", "reporter", "report_auditor", "unknown"]

for role_type in roles_to_test:
    print(f"\n【角色类型: {role_type}】")
    executors, schemas = get_tools_for_role(role_type)
    print(f"  可用工具数: {len(executors)}")
    print(f"  工具名称: {list(executors.keys())}")
    print(f"  Schemas数: {len(schemas)}")
    schema_names = [s['function']['name'] for s in schemas]
    print(f"  Schema名称: {schema_names}")
    
    # 验证工具分配是否符合预期
    if role_type == "meta":
        expected = ["list_roles", "create_role", "select_framework", "list_skills", "use_skill", "web_search"]
        if set(executors.keys()) == set(expected):
            print("  ✅ Meta-Orchestrator工具分配正确")
        else:
            print(f"  ❌ 期望: {expected}")
    
    elif role_type in ["leader", "planner", "auditor"]:
        expected = ["list_skills", "use_skill", "web_search"]
        if set(executors.keys()) == set(expected):
            print(f"  ✅ {role_type.capitalize()}工具分配正确")
        else:
            print(f"  ❌ 期望: {expected}")
    
    elif role_type in ["reporter", "report_auditor"]:
        expected = ["web_search"]
        if set(executors.keys()) == set(expected):
            print(f"  ✅ {role_type.capitalize()}工具分配正确")
        else:
            print(f"  ❌ 期望: {expected}")
    
    elif role_type == "unknown":
        expected = ["web_search"]
        if set(executors.keys()) == set(expected):
            print("  ✅ 未知/自定义角色获得Search工具")
        else:
            print(f"  ❌ 期望自定义角色获得Search工具: {expected}")

print("\n" + "=" * 80)
print("✅ 所有角色工具分配测试完成")
print("=" * 80)
