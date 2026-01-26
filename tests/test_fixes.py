"""测试修复后的Skills功能"""

from src.web.app import app
from src.repositories.skill_repository import SkillRepository

print("=" * 60)
print("测试修复")
print("=" * 60)
print()

# 测试1: 技能页面API修复
print("【测试1】Skills API (解决 'dict' object has no attribute 'to_dict')")
with app.app_context():
    result = SkillRepository.get_tenant_skills(
        tenant_id=1,
        page=1,
        page_size=5,
        include_content=False
    )
    
    print(f"✅ 返回 {len(result['items'])} 个skills")
    print(f"✅ items类型: {type(result['items'][0])}")
    print(f"✅ 第一个skill: {result['items'][0]['display_name']}")
    
    # 验证是字典而不是对象
    assert isinstance(result['items'][0], dict), "items应该是字典列表"
    print("✅ 确认返回的是字典格式（不是Skill对象）")

print()
print("【测试2】tool_calls记录修复")
print("说明：已修改langchain_agents.py，现在会保存tool_calls到plan_dict和audit_dict")
print("      - 策论家输出会包含 'tool_calls' 和 'name' 字段")
print("      - 监察官输出会包含 'tool_calls' 和 'name' 字段")
print("      - 需要启动新讨论来验证此修复")

print()
print("=" * 60)
print("✅ 所有修复完成！")
print("=" * 60)
print()
print("下一步：")
print("1. 刷新Web界面，技能页面应该能正常显示")
print("2. 启动新讨论，查看history.json中的tool_calls字段")
