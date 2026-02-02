"""
统一工具系统集成测试

测试内容：
1. Meta-tools工具注册正确
2. Search-tools工具注册正确  
3. Skills-tools工具注册正确
4. 各角色获得正确的工具集
5. Tool-calling agent执行流程
"""

import sys
sys.path.insert(0, "D:\\git\\MyCouncil")

from src.agents.meta_tools import get_tools_for_role, execute_tool, get_tool_schemas, format_tool_result_for_llm

print("=" * 80)
print("统一工具系统集成测试")
print("=" * 80)

# Test 1: 全局工具注册
print("\n【Test 1】全局工具注册")
all_schemas = get_tool_schemas()
print(f"  总工具数: {len(all_schemas)}")
tool_names = [s['function']['name'] for s in all_schemas]
print(f"  工具列表: {tool_names}")

expected_tools = ['list_roles', 'create_role', 'select_framework', 'list_skills', 'use_skill', 'web_search']
if set(tool_names) == set(expected_tools):
    print("  ✅ 工具注册正确")
else:
    print(f"  ❌ 期望: {expected_tools}")
    print(f"  实际: {tool_names}")

# Test 2: Meta-Orchestrator工具分配
print("\n【Test 2】Meta-Orchestrator工具分配")
meta_executors, meta_schemas = get_tools_for_role("meta")
meta_tool_names = [s['function']['name'] for s in meta_schemas]
print(f"  工具数: {len(meta_schemas)}")
print(f"  工具列表: {meta_tool_names}")

if set(meta_tool_names) == set(expected_tools):
    print("  ✅ Meta-Orchestrator工具分配正确（6个工具）")
else:
    print(f"  ❌ 期望: {expected_tools}")

# Test 3: Leader工具分配
print("\n【Test 3】Leader工具分配")
leader_executors, leader_schemas = get_tools_for_role("leader")
leader_tool_names = [s['function']['name'] for s in leader_schemas]
print(f"  工具数: {len(leader_schemas)}")
print(f"  工具列表: {leader_tool_names}")

expected_leader_tools = ['list_skills', 'use_skill', 'web_search']
if set(leader_tool_names) == set(expected_leader_tools):
    print("  ✅ Leader工具分配正确（Skills + Search）")
else:
    print(f"  ❌ 期望: {expected_leader_tools}")

# Test 4: Planner工具分配
print("\n【Test 4】Planner工具分配")
planner_executors, planner_schemas = get_tools_for_role("planner")
planner_tool_names = [s['function']['name'] for s in planner_schemas]
print(f"  工具数: {len(planner_schemas)}")
print(f"  工具列表: {planner_tool_names}")

if set(planner_tool_names) == set(expected_leader_tools):
    print("  ✅ Planner工具分配正确（Skills + Search）")
else:
    print(f"  ❌ 期望: {expected_leader_tools}")

# Test 5: Auditor工具分配
print("\n【Test 5】Auditor工具分配")
auditor_executors, auditor_schemas = get_tools_for_role("auditor")
auditor_tool_names = [s['function']['name'] for s in auditor_schemas]
print(f"  工具数: {len(auditor_schemas)}")
print(f"  工具列表: {auditor_tool_names}")

if set(auditor_tool_names) == set(expected_leader_tools):
    print("  ✅ Auditor工具分配正确（Skills + Search）")
else:
    print(f"  ❌ 期望: {expected_leader_tools}")

# Test 6: Reporter工具分配
print("\n【Test 6】Reporter工具分配")
reporter_executors, reporter_schemas = get_tools_for_role("reporter")
reporter_tool_names = [s['function']['name'] for s in reporter_schemas]
print(f"  工具数: {len(reporter_schemas)}")
print(f"  工具列表: {reporter_tool_names}")

expected_reporter_tools = ['web_search']
if set(reporter_tool_names) == set(expected_reporter_tools):
    print("  ✅ Reporter工具分配正确（仅Search）")
else:
    print(f"  ❌ 期望: {expected_reporter_tools}")

# Test 7: 执行list_skills工具
print("\n【Test 7】执行list_skills工具")
try:
    result = execute_tool("list_skills", {})
    if result.get("success"):
        skills_count = len(result.get("skills", []))
        print(f"  ✅ list_skills执行成功，找到{skills_count}个技能")
        if skills_count > 0:
            print(f"  示例技能: {result['skills'][0]['name']}")
    else:
        print(f"  ❌ list_skills执行失败: {result.get('error')}")
except Exception as e:
    print(f"  ❌ 执行异常: {e}")

# Test 8: 执行use_skill工具
print("\n【Test 8】执行use_skill工具")
try:
    result = execute_tool("use_skill", {"skill_name": "cost_benefit"})
    if result.get("success"):
        content_length = len(result.get("skill_content", ""))
        print(f"  ✅ use_skill执行成功，内容长度: {content_length} chars")
    else:
        print(f"  ❌ use_skill执行失败: {result.get('error')}")
except Exception as e:
    print(f"  ❌ 执行异常: {e}")

# Test 9: 执行web_search工具（注意：此测试会实际联网搜索）
print("\n【Test 9】执行web_search工具（跳过实际搜索以加快测试）")
print("  ⏭️  跳过（实际搜索已在search_tools.py中测试）")

# Test 10: 工具结果格式化
print("\n【Test 10】工具结果格式化")
try:
    # Skills工具格式化
    skills_result = {
        "success": True,
        "skills": [{
            "name": "test",
            "display_name": "测试技能",
            "description": "测试技能描述",
            "category": "test",
            "tags": ["test"]
        }],
        "total_count": 1,
        "filtered_count": 1
    }
    formatted_skills = format_tool_result_for_llm("list_skills", skills_result)
    print(f"  list_skills格式化长度: {len(formatted_skills)} chars")
    print(f"  包含'成功': {'成功' in formatted_skills or 'Skills' in formatted_skills}")
    
    # Search工具格式化
    search_result = {"success": True, "query": "test", "results": "测试结果", "providers": ["bing"], "total_sources": 1}
    formatted_search = format_tool_result_for_llm("web_search", search_result)
    print(f"  web_search格式化长度: {len(formatted_search)} chars")
    print(f"  包含'搜索成功': {'搜索成功' in formatted_search or '成功' in formatted_search}")
    
    if len(formatted_skills) > 0 and len(formatted_search) > 0:
        print("  ✅ 工具结果格式化正常")
    else:
        print("  ❌ 格式化结果为空")
except Exception as e:
    print(f"  ❌ 格式化异常: {e}")

print("\n" + "=" * 80)
print("✅ 统一工具系统集成测试完成")
print("=" * 80)
