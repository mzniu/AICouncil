"""
端到端测试脚本 - 测试角色设计师完整流程
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def test_role_designer_flow():
    """测试完整的角色设计流程"""
    print("=" * 60)
    print("角色设计师端到端测试")
    print("=" * 60)
    
    # Step 1: 测试角色设计API
    print("\n[Step 1] 调用角色设计API...")
    requirement = "我需要一个擅长数据分析的角色，能够处理统计分析、数据可视化和趋势预测任务"
    
    design_response = requests.post(
        f"{BASE_URL}/api/roles/design",
        json={"requirement": requirement},
        timeout=120  # 允许2分钟超时（DeepSeek可能较慢）
    )
    
    print(f"状态码: {design_response.status_code}")
    
    if design_response.status_code != 200:
        print(f"❌ 设计失败: {design_response.text}")
        return False
    
    design_data = design_response.json()
    print(f"✅ 设计成功!")
    print(f"角色名称: {design_data['design']['role_name']}")
    print(f"显示名称: {design_data['design']['display_name']}")
    print(f"描述: {design_data['design']['role_description'][:50]}...")
    print(f"阶段数: {len(design_data['design']['stages'])}")
    
    # Step 2: 测试创建角色API
    print("\n[Step 2] 调用创建角色API...")
    
    # 修改role_name避免冲突
    design_data['design']['role_name'] = f"test_{design_data['design']['role_name']}_e2e"
    
    create_response = requests.post(
        f"{BASE_URL}/api/roles",
        json=design_data['design']
    )
    
    print(f"状态码: {create_response.status_code}")
    
    if create_response.status_code != 200:
        print(f"❌ 创建失败: {create_response.text}")
        return False
    
    create_data = create_response.json()
    print(f"✅ 创建成功!")
    print(f"角色名称: {create_data['role_name']}")
    print(f"显示名称: {create_data['display_name']}")
    
    # Step 3: 验证角色是否可用
    print("\n[Step 3] 验证角色加载...")
    
    roles_response = requests.get(f"{BASE_URL}/api/roles")
    roles_data = roles_response.json()
    
    created_role = None
    for role in roles_data.get('roles', []):
        if role['name'] == create_data['role_name']:
            created_role = role
            break
    
    if created_role:
        print(f"✅ 角色已加载到系统: {created_role['display_name']}")
        print(f"版本: {created_role.get('version', 'N/A')}")
        print(f"标签: {created_role.get('tags', [])}")
    else:
        print(f"❌ 角色未在系统中找到")
        return False
    
    # Step 4: 清理测试角色
    print("\n[Step 4] 清理测试数据...")
    from pathlib import Path
    from src.agents.role_manager import RoleManager
    
    rm = RoleManager()
    roles_dir = rm.get_roles_directory()
    test_yaml = roles_dir / f"{create_data['role_name']}.yaml"
    test_prompt = roles_dir / f"{create_data['role_name']}_main.md"
    
    if test_yaml.exists():
        test_yaml.unlink()
        print(f"✅ 已删除: {test_yaml.name}")
    if test_prompt.exists():
        test_prompt.unlink()
        print(f"✅ 已删除: {test_prompt.name}")
    
    print("\n" + "=" * 60)
    print("✅ 端到端测试通过!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_role_designer_flow()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
