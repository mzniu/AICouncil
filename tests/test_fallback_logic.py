"""
测试Fallback机制的核心逻辑
不依赖完整的LLM执行，仅验证逻辑正确性
"""

import sys
from pathlib import Path

# 设置路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_fallback_logic():
    """测试fallback逻辑：检测专业角色并创建stage"""
    print("\n" + "="*80)
    print("测试：Fallback机制核心逻辑")
    print("="*80)
    
    # 模拟场景：有专业角色但role_stage_mapping为空
    agent_counts = {
        "planner": 1,
        "auditor": 1,
        "leader": 1,
        "test_expert": 1,  # 专业角色
        "another_expert": 1  # 另一个专业角色
    }
    
    role_stage_mapping = {}  # 空的映射，触发fallback
    
    print(f"\n📋 初始配置:")
    print(f"  - agent_counts: {agent_counts}")
    print(f"  - role_stage_mapping: {role_stage_mapping or '空'}")
    
    # 执行fallback逻辑
    framework_roles = {"planner", "auditor", "leader", "devils_advocate", "reporter"}
    professional_roles = [role for role in agent_counts.keys() if role not in framework_roles]
    
    print(f"\n🔍 检测结果:")
    print(f"  - 框架角色: {[r for r in agent_counts.keys() if r in framework_roles]}")
    print(f"  - 专业角色: {professional_roles}")
    
    if professional_roles and (not role_stage_mapping or len(role_stage_mapping) == 0):
        print(f"\n✅ 触发fallback条件:")
        print(f"  - 存在专业角色: {len(professional_roles)}个")
        print(f"  - role_stage_mapping为空")
        
        # 创建fallback的role_stage_mapping
        role_stage_mapping = {role: ["专业分析"] for role in professional_roles}
        
        print(f"\n🔧 自动生成 role_stage_mapping:")
        for role, stages in role_stage_mapping.items():
            print(f"  - {role} → {stages}")
        
        print(f"\n✅ Fallback机制逻辑验证通过")
        return True
    else:
        print(f"\n❌ 未触发fallback（不应该发生）")
        return False

def test_no_fallback_needed():
    """测试不需要fallback的场景：role_stage_mapping已配置"""
    print("\n" + "="*80)
    print("测试：不需要Fallback的场景")
    print("="*80)
    
    agent_counts = {
        "planner": 1,
        "auditor": 1,
        "leader": 1,
        "test_expert": 1
    }
    
    role_stage_mapping = {
        "test_expert": ["逻辑推理", "替代视角"]
    }
    
    print(f"\n📋 配置:")
    print(f"  - agent_counts: {agent_counts}")
    print(f"  - role_stage_mapping: {role_stage_mapping}")
    
    framework_roles = {"planner", "auditor", "leader", "devils_advocate", "reporter"}
    professional_roles = [role for role in agent_counts.keys() if role not in framework_roles]
    
    if professional_roles and (not role_stage_mapping or len(role_stage_mapping) == 0):
        print(f"\n❌ 不应触发fallback但触发了")
        return False
    else:
        print(f"\n✅ 正确判断：不需要fallback")
        return True

def test_no_professional_roles():
    """测试无专业角色的场景：不应触发fallback"""
    print("\n" + "="*80)
    print("测试：无专业角色场景")
    print("="*80)
    
    agent_counts = {
        "planner": 2,
        "auditor": 2,
        "leader": 1
    }
    
    role_stage_mapping = {}
    
    print(f"\n📋 配置:")
    print(f"  - agent_counts: {agent_counts}")
    print(f"  - role_stage_mapping: {role_stage_mapping or '空'}")
    
    framework_roles = {"planner", "auditor", "leader", "devils_advocate", "reporter"}
    professional_roles = [role for role in agent_counts.keys() if role not in framework_roles]
    
    print(f"\n🔍 检测结果:")
    print(f"  - 专业角色: {professional_roles or '无'}")
    
    if professional_roles and (not role_stage_mapping or len(role_stage_mapping) == 0):
        print(f"\n❌ 不应触发fallback但触发了")
        return False
    else:
        print(f"\n✅ 正确判断：无专业角色，不需要fallback")
        return True

def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("Fallback机制逻辑测试")
    print("="*80)
    
    tests = [
        ("有专业角色且mapping为空", test_fallback_logic),
        ("mapping已配置", test_no_fallback_needed),
        ("无专业角色", test_no_professional_roles)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    success_count = sum(1 for _, r in results if r)
    total_count = len(results)
    print(f"\n总计: {success_count}/{total_count} 测试通过")
    
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
