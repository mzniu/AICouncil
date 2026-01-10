"""
测试 _auto_fix_orchestration_plan 自动修正逻辑
"""

import sys
from pathlib import Path

# 设置路径和环境
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
import os
os.chdir(src_path)  # 切换到 src 目录

from agents import schemas
from agents.langchain_agents import _auto_fix_orchestration_plan
from agents.frameworks import get_framework

def test_auto_fix_missing_framework_roles():
    """测试场景1：缺失框架必需角色（如 leader）"""
    print("\n" + "="*80)
    print("测试场景1：缺失框架必需角色")
    print("="*80)
    
    # 构造一个缺少 leader 的配置
    plan = schemas.OrchestrationPlan(
        analysis=schemas.RequirementAnalysis(
            problem_type="分析类",
            complexity="中等",
            required_capabilities=["逻辑分析", "批判思维"]
        ),
        framework_selection=schemas.FrameworkSelection(
            framework_id="critical_thinking",
            framework_name="批判性思维框架",
            rationale="测试用"
        ),
        role_planning=schemas.RolePlanning(
            existing_roles=[
                schemas.RoleMatch(
                    name="planner",
                    display_name="策论家",
                    match_score=0.8,
                    match_reasoning="框架角色",
                    assigned_count=2
                ),
                schemas.RoleMatch(
                    name="auditor",
                    display_name="监察官",
                    match_score=0.7,
                    match_reasoning="框架角色",
                    assigned_count=1
                )
            ],
            roles_to_create=[]
        ),
        execution_config=schemas.ExecutionConfig(
            agent_counts={
                "planner": 2,
                "auditor": 1
                # 缺少 leader！
            },
            total_rounds=2,
            role_stage_mapping={}
        )
    )
    
    print(f"📋 修正前:")
    print(f"  - agent_counts: {plan.execution_config.agent_counts}")
    
    # 执行自动修正
    fixed_plan = _auto_fix_orchestration_plan(plan)
    
    print(f"\n📊 修正后:")
    print(f"  - agent_counts: {fixed_plan.execution_config.agent_counts}")
    
    # 验证
    if "leader" in fixed_plan.execution_config.agent_counts:
        print(f"\n✅ 成功添加缺失的 leader 角色")
        return True
    else:
        print(f"\n❌ 未能添加 leader 角色")
        return False

def test_auto_fix_missing_professional_roles():
    """测试场景2：缺失专业角色"""
    print("\n" + "="*80)
    print("测试场景2：缺失专业角色")
    print("="*80)
    
    plan = schemas.OrchestrationPlan(
        analysis=schemas.RequirementAnalysis(
            problem_type="分析类",
            complexity="中等",
            required_capabilities=["辩论分析"]
        ),
        framework_selection=schemas.FrameworkSelection(
            framework_id="critical_thinking",
            framework_name="批判性思维框架",
            rationale="测试用"
        ),
        role_planning=schemas.RolePlanning(
            existing_roles=[
                schemas.RoleMatch(
                    name="planner",
                    display_name="策论家",
                    match_score=0.8,
                    match_reasoning="框架角色",
                    assigned_count=1
                ),
                schemas.RoleMatch(
                    name="auditor",
                    display_name="监察官",
                    match_score=0.7,
                    match_reasoning="框架角色",
                    assigned_count=1
                ),
                # 专业角色
                schemas.RoleMatch(
                    name="debate_methodology_analyst",
                    display_name="辩论方法论分析专家",
                    match_score=1.0,
                    match_reasoning="高度匹配辩论分析需求",
                    assigned_count=1
                )
            ],
            roles_to_create=[]
        ),
        execution_config=schemas.ExecutionConfig(
            agent_counts={
                "planner": 1,
                "auditor": 1
                # 缺少 leader 和 debate_methodology_analyst！
            },
            total_rounds=2,
            role_stage_mapping={}
        )
    )
    
    print(f"📋 修正前:")
    print(f"  - agent_counts: {plan.execution_config.agent_counts}")
    print(f"  - role_stage_mapping: {plan.execution_config.role_stage_mapping or '空'}")
    
    fixed_plan = _auto_fix_orchestration_plan(plan)
    
    print(f"\n📊 修正后:")
    print(f"  - agent_counts: {fixed_plan.execution_config.agent_counts}")
    print(f"  - role_stage_mapping: {fixed_plan.execution_config.role_stage_mapping}")
    
    # 验证
    checks = []
    
    if "leader" in fixed_plan.execution_config.agent_counts:
        print(f"\n✅ 成功添加缺失的 leader")
        checks.append(True)
    else:
        print(f"\n❌ 未能添加 leader")
        checks.append(False)
    
    if "debate_methodology_analyst" in fixed_plan.execution_config.agent_counts:
        print(f"✅ 成功添加缺失的专业角色 debate_methodology_analyst")
        checks.append(True)
    else:
        print(f"❌ 未能添加专业角色 debate_methodology_analyst")
        checks.append(False)
    
    if "debate_methodology_analyst" in fixed_plan.execution_config.role_stage_mapping:
        stages = fixed_plan.execution_config.role_stage_mapping["debate_methodology_analyst"]
        print(f"✅ 成功为 debate_methodology_analyst 分配 stage: {stages}")
        checks.append(True)
    else:
        print(f"❌ 未为 debate_methodology_analyst 分配 stage")
        checks.append(False)
    
    return all(checks)

def test_auto_fix_complete_config():
    """测试场景3：配置完整，无需修正"""
    print("\n" + "="*80)
    print("测试场景3：配置完整，无需修正")
    print("="*80)
    
    plan = schemas.OrchestrationPlan(
        analysis=schemas.RequirementAnalysis(
            problem_type="分析类",
            complexity="中等",
            required_capabilities=["辩论分析"]
        ),
        framework_selection=schemas.FrameworkSelection(
            framework_id="critical_thinking",
            framework_name="批判性思维框架",
            rationale="测试用"
        ),
        role_planning=schemas.RolePlanning(
            existing_roles=[
                schemas.RoleMatch(
                    name="planner",
                    display_name="策论家",
                    match_score=0.8,
                    match_reasoning="框架角色",
                    assigned_count=1
                ),
                schemas.RoleMatch(
                    name="auditor",
                    display_name="监察官",
                    match_score=0.7,
                    match_reasoning="框架角色",
                    assigned_count=1
                ),
                schemas.RoleMatch(
                    name="debate_methodology_analyst",
                    display_name="辩论方法论分析专家",
                    match_score=1.0,
                    match_reasoning="高度匹配",
                    assigned_count=1
                )
            ],
            roles_to_create=[]
        ),
        execution_config=schemas.ExecutionConfig(
            agent_counts={
                "planner": 1,
                "auditor": 1,
                "leader": 1,
                "debate_methodology_analyst": 1
            },
            total_rounds=2,
            role_stage_mapping={
                "debate_methodology_analyst": ["逻辑推理", "替代视角"]
            }
        )
    )
    
    print(f"📋 原始配置:")
    print(f"  - agent_counts: {plan.execution_config.agent_counts}")
    print(f"  - role_stage_mapping: {plan.execution_config.role_stage_mapping}")
    
    fixed_plan = _auto_fix_orchestration_plan(plan)
    
    print(f"\n📊 修正后:")
    print(f"  - agent_counts: {fixed_plan.execution_config.agent_counts}")
    print(f"  - role_stage_mapping: {fixed_plan.execution_config.role_stage_mapping}")
    
    # 验证配置未被改变
    if fixed_plan.execution_config.agent_counts == plan.execution_config.agent_counts:
        print(f"\n✅ 配置未被修改（符合预期）")
        return True
    else:
        print(f"\n❌ 配置被错误修改")
        return False

def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("_auto_fix_orchestration_plan 自动修正逻辑测试")
    print("="*80)
    
    tests = [
        ("缺失框架必需角色", test_auto_fix_missing_framework_roles),
        ("缺失专业角色", test_auto_fix_missing_professional_roles),
        ("配置完整无需修正", test_auto_fix_complete_config)
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
