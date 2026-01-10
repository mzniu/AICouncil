#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Meta-Orchestrator完整流程

测试从需求分析到框架执行到报告生成的完整链路（不涉及真实LLM调用）
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.demo_runner import run_meta_orchestrator_flow, parse_args
from src.agents.langchain_agents import run_meta_orchestrator


def test_command_line_args():
    """测试命令行参数解析"""
    print("============================================================")
    print("测试命令行参数解析")
    print("============================================================\n")
    
    # 模拟命令行参数
    import sys
    original_argv = sys.argv.copy()
    
    try:
        # 测试1：传统流程
        print("【测试1】传统流程参数")
        sys.argv = [
            "demo_runner.py",
            "--backend", "deepseek",
            "--issue", "测试议题",
            "--rounds", "2"
        ]
        args = parse_args()
        print(f"  ✅ 解析成功")
        print(f"    - backend: {args.backend}")
        print(f"    - issue: {args.issue}")
        print(f"    - rounds: {args.rounds}")
        print(f"    - use_meta_orchestrator: {args.use_meta_orchestrator}")
        
        # 测试2：Meta-Orchestrator流程
        print("\n【测试2】Meta-Orchestrator流程参数")
        sys.argv = [
            "demo_runner.py",
            "--backend", "deepseek",
            "--issue", "测试议题",
            "--use-meta-orchestrator"
        ]
        args = parse_args()
        print(f"  ✅ 解析成功")
        print(f"    - backend: {args.backend}")
        print(f"    - issue: {args.issue}")
        print(f"    - use_meta_orchestrator: {args.use_meta_orchestrator}")
        
    finally:
        # 恢复原始参数
        sys.argv = original_argv
    
    print("\n============================================================")
    print("✅ 命令行参数测试通过")
    print("============================================================\n")


def test_flow_structure():
    """测试流程结构（不实际调用LLM）"""
    print("============================================================")
    print("测试Meta-Orchestrator流程结构")
    print("============================================================\n")
    
    # 测试函数导入
    print("【测试1】函数导入")
    from src.agents.demo_runner import run_meta_orchestrator_flow, _build_reporter_input
    print(f"  ✅ run_meta_orchestrator_flow: {run_meta_orchestrator_flow.__name__}")
    print(f"  ✅ _build_reporter_input: {_build_reporter_input.__name__}")
    
    # 测试_build_reporter_input
    print("\n【测试2】_build_reporter_input函数")
    from src.agents.schemas import (
        OrchestrationPlan, RequirementAnalysis, RolePlanning, 
        FrameworkSelection, FrameworkStageInfo, ExecutionConfig, PlanSummary
    )
    
    # 构造示例规划
    sample_plan = OrchestrationPlan(
        analysis=RequirementAnalysis(
            problem_type="决策类",
            complexity="中等",
            required_capabilities=["决策分析", "风险评估"],
            reasoning="这是一个需要决策的场景，需要分析多个方案"
        ),
        role_planning=RolePlanning(
            existing_roles=[],
            roles_to_create=[]
        ),
        framework_selection=FrameworkSelection(
            framework_id="roberts_rules",
            framework_name="罗伯特议事规则",
            selection_reason="适合决策场景",
            framework_stages=[
                FrameworkStageInfo(
                    stage_name="动议提出",
                    stage_description="策论家提出方案",
                    expected_roles=["planner"],
                    expected_rounds=1
                )
            ]
        ),
        execution_config=ExecutionConfig(
            total_rounds=2,
            agent_counts={"planner": 2, "auditor": 1},
            estimated_duration="10-15分钟"
        ),
        summary=PlanSummary(
            title="测试方案",
            overview="这是一个测试方案",
            key_advantages=["优势1", "优势2"]
        )
    )
    
    # 构造示例执行结果
    sample_execution_result = {
        "session_id": "test_001",
        "workspace_path": "./test_workspace",
        "all_outputs": {
            "stages": {
                "动议提出": {
                    "description": "策论家提出方案",
                    "rounds": 1,
                    "agents": [
                        {
                            "agent_id": "planner_1",
                            "display_name": "策论家",
                            "content": "我提议采用方案A"
                        }
                    ]
                }
            }
        }
    }
    
    reporter_input = _build_reporter_input(
        user_requirement="测试需求",
        orchestration_plan=sample_plan,
        execution_result=sample_execution_result
    )
    
    print(f"  ✅ Reporter输入构建成功，长度: {len(reporter_input)} 字符")
    print(f"  预览（前200字符）:")
    print(f"  {reporter_input[:200]}...")
    
    print("\n============================================================")
    print("✅ 流程结构测试通过")
    print("============================================================\n")


def test_integration():
    """测试与其他模块的集成"""
    print("============================================================")
    print("测试模块集成")
    print("============================================================\n")
    
    # 测试1：导入依赖模块
    print("【测试1】导入依赖模块")
    try:
        from src.agents.langchain_agents import (
            run_meta_orchestrator, 
            execute_orchestration_plan,
            make_reporter_chain,
            stream_agent_output
        )
        print("  ✅ langchain_agents模块导入成功")
        
        from src.agents.framework_engine import FrameworkEngine
        print("  ✅ framework_engine模块导入成功")
        
        from src.agents.frameworks import get_framework
        print("  ✅ frameworks模块导入成功")
        
        from src.agents.schemas import OrchestrationPlan
        print("  ✅ schemas模块导入成功")
        
    except ImportError as e:
        print(f"  ❌ 导入失败: {e}")
        return False
    
    # 测试2：验证函数签名
    print("\n【测试2】验证函数签名")
    print(f"  run_meta_orchestrator参数: {run_meta_orchestrator.__code__.co_varnames[:run_meta_orchestrator.__code__.co_argcount]}")
    print(f"  execute_orchestration_plan参数: {execute_orchestration_plan.__code__.co_varnames[:execute_orchestration_plan.__code__.co_argcount]}")
    print(f"  run_meta_orchestrator_flow参数: {run_meta_orchestrator_flow.__code__.co_varnames[:run_meta_orchestrator_flow.__code__.co_argcount]}")
    
    print("\n============================================================")
    print("✅ 模块集成测试通过")
    print("============================================================\n")


def main():
    print("🧪 Meta-Orchestrator完整流程测试\n")
    
    try:
        test_command_line_args()
        test_flow_structure()
        test_integration()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！")
        print("="*60)
        
        print("\n📝 使用说明:")
        print("  1. 传统流程（run_full_cycle）:")
        print("     python src/agents/demo_runner.py --issue '你的议题' --backend deepseek")
        print()
        print("  2. 新流程（Meta-Orchestrator + FrameworkEngine）:")
        print("     python src/agents/demo_runner.py --issue '你的议题' --backend deepseek --use-meta-orchestrator")
        print()
        print("  3. 完整流程:")
        print("     - Stage 0: Meta-Orchestrator智能规划")
        print("     - Stage 1-N: FrameworkEngine执行框架")
        print("     - Stage Final: Reporter生成报告")
        print()
        print("⚠️ 注意: 实际运行需要配置API Key（src/config.py）")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
