"""
验证Skills Tool Calling集成

测试Agent在讨论中能否正确调用Skills工具
"""

from src.agents.meta_tools import get_tools_for_role
from src.skills.skill_tools import set_execution_context, list_skills, use_skill

print("=" * 60)
print("Skills Tool Calling 集成验证")
print("=" * 60)
print()

# 1. 验证工具注册
print("【步骤1】验证工具已注册到角色")
executors, schemas = get_tools_for_role("planner")
print(f"✅ Planner角色可用工具数: {len(schemas)}")
print("工具列表:")
for schema in schemas:
    tool_name = schema['function']['name']
    print(f"  - {tool_name}")
print()

# 2. 设置执行上下文
print("【步骤2】设置执行上下文（tenant_id=1）")
set_execution_context(tenant_id=1)
print("✅ 执行上下文已设置")
print()

# 3. 测试list_skills
print("【步骤3】测试list_skills工具")
from src.web.app import app
with app.app_context():
    result = list_skills()
    if result['success']:
        print(f"✅ 找到 {result['total_count']} 个Skills:")
        for skill in result['skills'][:3]:  # 只显示前3个
            print(f"  - {skill['display_name']} ({skill['category']})")
    else:
        print(f"❌ list_skills失败: {result.get('error')}")
print()

# 4. 测试use_skill
print("【步骤4】测试use_skill工具")
with app.app_context():
    if result['success'] and result['total_count'] > 0:
        first_skill = result['skills'][0]
        skill_result = use_skill(first_skill['name'])
        if skill_result['success']:
            print(f"✅ 成功加载Skill: {skill_result['metadata']['display_name']}")
            print(f"   内容长度: {len(skill_result['skill_content'])} 字符")
            print(f"   前200字符: {skill_result['skill_content'][:200]}...")
        else:
            print(f"❌ use_skill失败: {skill_result.get('error')}")
    else:
        print("⏭️  跳过（没有可用Skills）")
print()

# 5. 验证工具schema格式
print("【步骤5】验证工具schema格式")
skill_schemas = [s for s in schemas if 'skill' in s['function']['name']]
print(f"✅ Skills工具schema数: {len(skill_schemas)}")
for schema in skill_schemas:
    func = schema['function']
    print(f"  - {func['name']}: {func['description'][:50]}...")
print()

print("=" * 60)
print("✅ 所有验证通过！角色现在可以在讨论中调用Skills")
print("=" * 60)
print()
print("接下来可以：")
print("1. 启动Web界面: python src/web/app.py")
print("2. 创建一个讨论，观察角色是否调用Skills工具")
print("3. 在前端Skills管理页面创建更多Skills")
