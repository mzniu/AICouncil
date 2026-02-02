"""验证Skills是否可被工具系统加载"""

from src.skills.skill_tools import list_skills
import json

result = list_skills()

print(f"\n✅ 找到 {result['total_count']} 个Skills:\n")

for i, skill in enumerate(result['skills'], 1):
    print(f"{i}. {skill['display_name']} ({skill['category']})")
    print(f"   标签: {', '.join(skill['tags'])}")
    print(f"   适用角色: {', '.join(skill['applicable_roles'])}")
    print(f"   描述: {skill['description']}")
    print()

print(f"📊 总计: {result['total_count']} 个Skills可供调用")
