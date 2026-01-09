"""快速测试role_designer是否能加载"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.role_manager import RoleManager

def test_role_designer_loading():
    print("=" * 60)
    print("测试 role_designer 角色加载")
    print("=" * 60)
    
    rm = RoleManager()
    
    # 测试1: 检查角色是否存在
    print("\n[测试1] 检查角色是否已加载...")
    if rm.has_role('role_designer'):
        print("✅ role_designer已加载")
    else:
        print("❌ role_designer未加载，尝试刷新...")
        rm.refresh_all_roles()
        if rm.has_role('role_designer'):
            print("✅ 刷新后成功加载role_designer")
        else:
            print("❌ 刷新后仍未加载，请检查文件")
            return False
    
    # 测试2: 获取角色配置
    print("\n[测试2] 获取角色配置...")
    try:
        role = rm.get_role('role_designer')
        print(f"✅ 角色名称: {role.name}")
        print(f"   显示名称: {role.display_name}")
        print(f"   版本: {role.version}")
        print(f"   阶段数: {len(role.stages)}")
    except Exception as e:
        print(f"❌ 获取配置失败: {e}")
        return False
    
    # 测试3: 加载prompt
    print("\n[测试3] 加载prompt模板...")
    try:
        prompt = rm.load_prompt('role_designer', 'generate')
        print(f"✅ Prompt长度: {len(prompt)} 字符")
        print(f"   前50字: {prompt[:50]}...")
    except Exception as e:
        print(f"❌ 加载prompt失败: {e}")
        return False
    
    # 测试4: 验证Schema
    print("\n[测试4] 验证输出Schema...")
    try:
        schema_class = rm.get_schema_class('role_designer', 'generate')
        print(f"✅ Schema类: {schema_class.__name__}")
    except Exception as e:
        print(f"❌ 获取Schema失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！role_designer可以正常使用")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_role_designer_loading()
    exit(0 if success else 1)
