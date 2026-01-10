"""
Meta-Orchestrator Fallback机制测试

测试目标：
1. 验证当role_stage_mapping为空但存在专业角色时，fallback机制能否自动创建专业分析stage
2. 验证专业角色能够在自动创建的stage中正确参与讨论
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# 设置工作目录为项目根目录
os.chdir(project_root)

from agents.langchain_agents import execute_orchestration_plan
from agents.schemas import OrchestrationPlan, FrameworkSelection, RolePlanning, RoleMatch, ExecutionConfig
from agents.role_manager import RoleManager
import json

def test_fallback_mechanism():
    """测试fallback机制：当role_stage_mapping为空但有专业角色时自动创建stage"""
    print("\n" + "="*80)
    print("测试：Fallback机制 - 自动创建专业分析stage")
    print("="*80)
    
    # 1. 确保有测试用的专业角色
    role_manager = RoleManager()
    test_role_name = "test_expert"
    
    if test_role_name not in role_manager.list_roles():
        print(f"🔧 创建测试角色: {test_role_name}")
        test_role = {
            "name": test_role_name,
            "display_name": "测试专家",
            "description": "用于测试fallback机制的专家角色",
            "expertise_areas": ["测试", "质量保证"],
            "stages": [{
                "name": "default",
                "system_prompt": "你是测试专家，负责提供测试相关的专业建议。",
                "input_vars": ["issue", "context"],
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "analysis": {"type": "string"},
                        "recommendations": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["analysis", "recommendations"]
                }
            }]
        }
        role_manager.save_role(test_role)
        print(f"✅ 已创建测试角色")
    
    # 2. 构造一个OrchestrationPlan，包含专业角色但role_stage_mapping为空
    plan = OrchestrationPlan(
        framework_selection=FrameworkSelection(
            framework_id="critical_thinking",
            framework_name="批判性思维框架",
            rationale="用于测试fallback机制"
        ),
        role_planning=RolePlanning(
            existing_roles=[
                RoleMatch(
                    name=test_role_name,
                    display_name="测试专家",
                    match_score=0.9,
                    match_reasoning="用于测试",
                    assigned_count=1
                ),
                RoleMatch(
                    name="planner",
                    display_name="策论家",
                    match_score=0.7,
                    match_reasoning="框架角色",
                    assigned_count=1
                )
            ],
            roles_to_create=[]
        ),
        execution_config=ExecutionConfig(
            agent_counts={
                "planner": 1,
                "auditor": 1,
                "leader": 1,
                test_role_name: 1  # 专业角色
            },
            total_rounds=1,
            role_stage_mapping={}  # 故意设为空，触发fallback
        )
    )
    
    print(f"\n📋 测试配置:")
    print(f"  - 框架: {plan.framework_selection.framework_name}")
    print(f"  - Agent配置: {plan.execution_config.agent_counts}")
    print(f"  - role_stage_mapping: {plan.execution_config.role_stage_mapping or '空'}")
    print(f"\n🎯 预期结果:")
    print(f"  1. 检测到专业角色 '{test_role_name}' 但 role_stage_mapping 为空")
    print(f"  2. 自动创建'专业分析'stage并插入到框架")
    print(f"  3. 为 '{test_role_name}' 生成 role_stage_mapping: {{'test_expert': ['专业分析']}}")
    print(f"  4. 讨论过程中应看到该专业角色的发言")
    
    # 3. 执行规划
    print(f"\n🚀 开始执行...")
    try:
        result = execute_orchestration_plan(
            plan=plan,
            user_requirement="如何提高软件测试质量？请提供系统性的建议。",
            model_config={"type": "deepseek", "model": "deepseek-reasoner"}
        )
        
        print(f"\n✅ 执行完成")
        
        # 4. 验证结果
        workspace_path = Path(result["workspace_path"])
        print(f"\n🔍 验证结果: {workspace_path}")
        
        # 检查history.json
        history_file = workspace_path / "history.json"
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # 检查是否有专业分析stage的记录
            events = history.get("discussion_events", [])
            stage_starts = [e for e in events if e.get("type") == "stage_start"]
            stage_names = [e.get("stage_name") for e in stage_starts]
            
            print(f"\n📊 执行的stages: {stage_names}")
            
            if "专业分析" in stage_names:
                print(f"✅ 成功创建并执行'专业分析'stage")
            else:
                print(f"❌ 未找到'专业分析'stage")
                return False
            
            # 检查专业角色是否参与
            agent_actions = [e for e in events if e.get("type") == "agent_action"]
            expert_actions = [e for e in agent_actions if test_role_name in e.get("role_type", "")]
            
            if expert_actions:
                print(f"✅ 专业角色'{test_role_name}'参与了讨论 ({len(expert_actions)}条发言)")
                print(f"   示例发言: {expert_actions[0].get('content', '')[:100]}...")
            else:
                print(f"⚠️ 专业角色'{test_role_name}'未在讨论中发言")
            
            return True
        else:
            print(f"❌ 未找到 history.json")
            return False
            
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行测试"""
    print("\n" + "="*80)
    print("Meta-Orchestrator Fallback机制测试")
    print("="*80)
    
    try:
        result = test_fallback_mechanism()
        
        print("\n" + "="*80)
        print("测试结果")
        print("="*80)
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - Fallback机制测试")
        
        return result
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

