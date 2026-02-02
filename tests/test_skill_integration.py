"""测试meta_tools集成Skills工具"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.meta_tools import get_tool_schemas, execute_tool

# 测试1: 获取所有工具schemas
schemas = get_tool_schemas()
print(f"✅ Total tools: {len(schemas)}")
print("Tools:", [s['function']['name'] for s in schemas])

# 测试2: 执行list_skills
result = execute_tool('list_skills', {})
print(f"\n✅ list_skills result: success={result['success']}, found {result['filtered_count']} skills")

# 测试3: 执行use_skill
result = execute_tool('use_skill', {'skill_name': 'cost_benefit'})
print(f"\n✅ use_skill result: success={result['success']}, content_length={len(result.get('skill_content', ''))} chars")
