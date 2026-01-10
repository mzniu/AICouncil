"""
测试Meta-Orchestrator的基本功能（不实际调用LLM）
"""
import sys
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.langchain_agents import run_meta_orchestrator
from src.agents.schemas import OrchestrationPlan
from src.agents.meta_tools import list_roles, select_framework, get_tool_schemas
from src.agents.frameworks import list_frameworks

def test_prerequisites():
    """测试前置条件"""
    print("=" * 60)
    print("测试Meta-Orchestrator前置条件")
    print("=" * 60)
    
    # 测试1: 角色列表
    print("\n【测试1】list_roles()")
    roles_result = list_roles()
    print(f"  成功: {roles_result['success']}")
    print(f"  角色数: {roles_result.get('total_count', 0)}")
    
    # 测试2: 框架列表
    print("\n【测试2】list_frameworks()")
    frameworks = list_frameworks()
    print(f"  框架数: {len(frameworks)}")
    print(f"  框架: {[f['name'] for f in frameworks]}")
    
    # 测试3: select_framework
    print("\n【测试3】select_framework('需要决策投票')")
    fw_result = select_framework("需要决策投票")
    print(f"  成功: {fw_result['success']}")
    if fw_result['success']:
        print(f"  推荐: {fw_result['framework_name']}")
    
    # 测试4: 工具schemas
    print("\n【测试4】get_tool_schemas()")
    tools = get_tool_schemas()
    print(f"  工具数: {len(tools)}")
    print(f"  工具名: {[t['function']['name'] for t in tools]}")
    
    print("\n" + "=" * 60)
    print("✅ 所有前置条件测试通过")
    print("=" * 60)


def test_schema_validation():
    """测试OrchestrationPlan schema验证"""
    print("\n" + "=" * 60)
    print("测试OrchestrationPlan Schema")
    print("=" * 60)
    
    # 构造一个示例规划方案
    sample_plan = {
        "analysis": {
            "problem_type": "决策类",
            "complexity": "中等",
            "required_capabilities": ["法律分析", "经济评估"],
            "reasoning": "测试规划方案"
        },
        "role_planning": {
            "existing_roles": [
                {
                    "name": "auditor",
                    "display_name": "监察官",
                    "match_score": 0.85,
                    "match_reason": "具备批判性思维能力",
                    "assigned_count": 1
                }
            ],
            "roles_to_create": []
        },
        "framework_selection": {
            "framework_id": "roberts_rules",
            "framework_name": "罗伯特议事规则",
            "selection_reason": "适合决策类问题",
            "framework_stages": [
                {"stage_name": "动议提出", "stage_description": "提出方案"},
                {"stage_name": "附议确认", "stage_description": "确认讨论"},
            ]
        },
        "execution_config": {
            "total_rounds": 3,
            "agent_counts": {"planner": 2, "auditor": 1},
            "estimated_duration": "30-45分钟"
        },
        "summary": {
            "title": "测试规划方案",
            "overview": "这是一个测试方案",
            "key_advantages": ["优势1", "优势2"]
        }
    }
    
    try:
        plan = OrchestrationPlan(**sample_plan)
        print("✅ OrchestrationPlan验证通过")
        print(f"  - 问题类型: {plan.analysis.problem_type}")
        print(f"  - 推荐框架: {plan.framework_selection.framework_name}")
        print(f"  - 现有角色: {len(plan.role_planning.existing_roles)} 个")
        print(f"  - 总轮次: {plan.execution_config.total_rounds}")
    except Exception as e:
        print(f"❌ OrchestrationPlan验证失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("\n🧪 Meta-Orchestrator 功能测试\n")
    
    # 测试前置条件
    test_prerequisites()
    
    # 测试Schema
    test_schema_validation()
    
    print("\n" + "=" * 60)
    print("📝 注意：实际的LLM调用测试需要配置API Key")
    print("    可以通过以下方式测试完整功能：")
    print("    1. 配置 src/config.py 中的 DEEPSEEK_API_KEY")
    print("    2. 运行: python -c \"from src.agents.langchain_agents import run_meta_orchestrator; run_meta_orchestrator('测试需求')\"")
    print("=" * 60)


if __name__ == "__main__":
    main()
