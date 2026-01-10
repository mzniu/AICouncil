"""
Demo runner：演示议长→两名策论家并行盲评→两名监察官并行质疑→议长汇总流程。
默认通过 LangChain orchestration 调用配置的模型后端（以 Ollama 为例）。
"""
import sys
import pathlib

# Ensure project root is on sys.path so imports like `src.agents` work when running
# this file directly: `python src/agents/demo_runner.py` from project root.
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agents import schemas
from src.agents import model_adapter
from src.utils.logger import logger
from pydantic import ValidationError
import time
import argparse
import json
from src.agents.langchain_agents import run_full_cycle, run_meta_orchestrator, execute_orchestration_plan
from src import config_manager as config


def run_meta_orchestrator_flow(issue_text: str, model_config: dict, agent_configs: dict = None):
    """
    使用Meta-Orchestrator的新流程：
    1. Meta-Orchestrator分析需求并生成规划
    2. 如果需要创建新角色，调用RoleDesigner
    3. FrameworkEngine执行规划
    4. Reporter生成最终报告
    
    Args:
        issue_text: 用户需求
        model_config: 模型配置
        agent_configs: Agent配置覆盖
        
    Returns:
        执行结果字典
    """
    logger.info("[meta_flow] 启动Meta-Orchestrator智能规划流程")
    
    try:
        # Stage 0: Meta-Orchestrator智能规划
        logger.info("[meta_flow] Stage 0: 智能规划中...")
        print("\n🧭 Stage 0: Meta-Orchestrator 智能规划")
        print("-" * 60)
        
        orchestration_plan = run_meta_orchestrator(
            user_requirement=issue_text,
            model_config=model_config
        )
        
        print(f"✅ 规划完成")
        print(f"  - 推荐框架: {orchestration_plan.framework_selection.framework_name}")
        print(f"  - 总轮次: {orchestration_plan.execution_config.total_rounds}")
        print(f"  - Agent配置: {orchestration_plan.execution_config.agent_counts}")
        print(f"  - 预计时长: {orchestration_plan.execution_config.estimated_duration}")
        
        # 详细输出：角色规划信息
        print(f"\n📊 角色规划详情:")
        print(f"  - 匹配的现有角色: {len(orchestration_plan.role_planning.existing_roles)} 个")
        if orchestration_plan.role_planning.existing_roles:
            for role in orchestration_plan.role_planning.existing_roles:
                print(f"    • {role.display_name} ({role.name})")
        
        print(f"  - 需创建的角色: {len(orchestration_plan.role_planning.roles_to_create)} 个")
        if orchestration_plan.role_planning.roles_to_create:
            for role in orchestration_plan.role_planning.roles_to_create:
                print(f"    • {role.capability}")
        
        # 详细输出：role_stage_mapping
        if orchestration_plan.execution_config.role_stage_mapping:
            print(f"\n🔗 专业角色映射:")
            for role_name, stages in orchestration_plan.execution_config.role_stage_mapping.items():
                print(f"    • {role_name} → {', '.join(stages)}")
        else:
            print(f"\n⚠️  未配置 role_stage_mapping")
        
        # 处理需要创建的角色
        if orchestration_plan.role_planning.roles_to_create:
            logger.info(f"[meta_flow] 需要创建 {len(orchestration_plan.role_planning.roles_to_create)} 个新角色")
            print(f"\n⚠️ 规划方案建议创建 {len(orchestration_plan.role_planning.roles_to_create)} 个新角色")
            print("-" * 60)
            
            # 自动调用 RoleDesigner 创建角色
            from src.agents.meta_tools import create_role
            created_roles = []
            failed_roles = []
            
            for role_req in orchestration_plan.role_planning.roles_to_create:
                print(f"\n🔧 正在创建角色: {role_req.capability}")
                print(f"   需求描述: {role_req.requirement[:100]}...")
                
                try:
                    result = create_role(role_req.requirement)
                    
                    if result.get("success"):
                        role_name = result.get("role_name")
                        created_roles.append(role_name)
                        print(f"   ✅ 成功创建: {result['role_info']['display_name']} (role_name: {role_name})")
                    else:
                        error_msg = result.get("error", "未知错误")
                        failed_roles.append(role_req.capability)
                        print(f"   ❌ 创建失败: {error_msg}")
                        logger.error(f"[meta_flow] 创建角色失败 ({role_req.capability}): {error_msg}")
                
                except Exception as e:
                    failed_roles.append(role_req.capability)
                    print(f"   ❌ 创建异常: {str(e)}")
                    logger.error(f"[meta_flow] 创建角色异常 ({role_req.capability}): {e}")
            
            # 汇总结果
            print("\n" + "=" * 60)
            print(f"📊 角色创建汇总:")
            print(f"   ✅ 成功: {len(created_roles)} 个")
            if created_roles:
                for role_name in created_roles:
                    print(f"      - {role_name}")
            
            print(f"   ❌ 失败: {len(failed_roles)} 个")
            if failed_roles:
                for capability in failed_roles:
                    print(f"      - {capability}")
            
            if failed_roles:
                print("\n   ⚠️ 部分角色创建失败，将使用现有角色继续执行")
        
        # Stage 1-N: FrameworkEngine执行
        logger.info(f"[meta_flow] Stage 1-N: 框架执行中 ({orchestration_plan.framework_selection.framework_name})...")
        print(f"\n🚀 Stage 1-N: 框架执行 ({orchestration_plan.framework_selection.framework_name})")
        print("-" * 60)
        
        execution_result = execute_orchestration_plan(
            plan=orchestration_plan,
            user_requirement=issue_text,
            model_config=model_config,
            agent_configs=agent_configs
        )
        
        print(f"✅ 框架执行完成")
        print(f"  - Session ID: {execution_result['session_id']}")
        print(f"  - Workspace: {execution_result['workspace_path']}")
        
        # 提取所有stage的输出
        all_outputs = execution_result.get("all_outputs", {})
        stages = all_outputs.get("stages", {})
        
        # 显示每个stage的摘要
        print("\n📊 各阶段输出摘要:")
        for stage_name, stage_output in stages.items():
            agent_count = len(stage_output.get("agents", []))
            print(f"  - {stage_name}: {agent_count} 个Agent参与")
        
        # Stage Final: Reporter生成报告
        logger.info("[meta_flow] Stage Final: 生成最终报告...")
        print(f"\n📝 Stage Final: 生成报告")
        print("-" * 60)
        
        # 使用Reporter生成HTML报告
        from src.agents.langchain_agents import make_reporter_chain
        from pathlib import Path
        import uuid
        
        # 获取 reporter 的配置（如果 agent_configs 中没有，传递空字典让 make_reporter_chain 使用 default_model）
        reporter_config = agent_configs.get("reporter") if agent_configs else None
        if not reporter_config:
            # 传递空字典，让 make_reporter_chain 使用 reporter.yaml 的 default_model
            reporter_config = {"type": model_config.get("type", "deepseek")}
        
        reporter_chain = make_reporter_chain(reporter_config)
        
        # 构建Reporter输入（包含所有stage的输出）
        reporter_input = _build_reporter_input(
            user_requirement=issue_text,
            orchestration_plan=orchestration_plan,
            execution_result=execution_result
        )
        
        # 调用Reporter
        from src.agents.langchain_agents import stream_agent_output
        
        report_content, search_res = stream_agent_output(
            reporter_chain,
            {
                "final_data": reporter_input,
                "search_references": ""  # Meta-Orchestrator模式下搜索引用由各Agent自行处理
            },
            "记录员",
            "reporter",
            event_type="agent_action"
        )
        
        # 保存报告
        workspace_path = Path(execution_result['workspace_path'])
        report_path = workspace_path / "report.html"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"✅ 报告已保存: {report_path}")
        
        # 发送讨论完成事件和最终报告内容
        from src.agents.langchain_agents import send_web_event
        send_web_event("discussion_complete", session_id=execution_result['session_id'])
        send_web_event("final_report", content=report_content, session_id=execution_result['session_id'])
        
        # 返回完整结果
        final_result = {
            "success": True,
            "flow": "meta_orchestrator",
            "session_id": execution_result['session_id'],
            "workspace_path": execution_result['workspace_path'],
            "orchestration_plan": orchestration_plan.model_dump(),
            "execution_result": execution_result,
            "report_path": str(report_path),
            "report_content": report_content
        }
        
        logger.info("[meta_flow] Meta-Orchestrator流程完成")
        return final_result
        
    except Exception as e:
        logger.error(f"[meta_flow] 执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 返回错误结果
        return {
            "success": False,
            "flow": "meta_orchestrator",
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def _build_reporter_input(user_requirement: str, orchestration_plan, execution_result: dict) -> str:
    """
    构建Reporter的输入（包含框架流程和各stage输出）
    
    Args:
        user_requirement: 用户需求
        orchestration_plan: Meta-Orchestrator规划
        execution_result: 框架执行结果
        
    Returns:
        格式化的输入字符串
    """
    lines = [
        "# 用户需求",
        user_requirement,
        "",
        "# 智能规划方案",
        f"**推荐框架**: {orchestration_plan.framework_selection.framework_name}",
        f"**选择理由**: {orchestration_plan.framework_selection.selection_reason}",
        f"**总轮次**: {orchestration_plan.execution_config.total_rounds}",
        f"**Agent配置**: {orchestration_plan.execution_config.agent_counts}",
        "",
        "# 讨论过程"
    ]
    
    # 添加各stage的输出
    all_outputs = execution_result.get("all_outputs", {})
    stages = all_outputs.get("stages", {})
    
    for stage_name, stage_output in stages.items():
        lines.append(f"\n## {stage_name}")
        lines.append(f"**说明**: {stage_output.get('description', '')}")
        lines.append(f"**轮次**: {stage_output.get('rounds', 1)}")
        lines.append("")
        
        # 添加Agent输出
        for agent_data in stage_output.get("agents", []):
            agent_id = agent_data.get("agent_id", "未知")
            display_name = agent_data.get("display_name", "")
            content = agent_data.get("content", "")
            
            lines.append(f"### {display_name} ({agent_id})")
            lines.append(content)
            lines.append("")
    
    # 添加最终综合（如果有）
    if "final_synthesis" in execution_result.get("execution", {}):
        synthesis = execution_result["execution"]["final_synthesis"]
        lines.append("\n## 最终综合")
        lines.append(synthesis.get("content", ""))
    
    return "\n".join(lines)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--backend', type=str, choices=['ollama', 'deepseek', 'openai', 'openrouter'], help='Model backend type')
    p.add_argument('--model', type=str, help='Override model name (e.g. qwen3:8b-q8_0 or deepseek-chat)')
    p.add_argument('--rounds', type=int, default=3, help='Number of discussion rounds')
    p.add_argument('--issue', type=str, help='The issue to discuss')
    p.add_argument('--planners', type=int, default=2, help='Number of planners')
    p.add_argument('--auditors', type=int, default=2, help='Number of auditors')
    p.add_argument('--agent_configs', type=str, help='JSON string of per-agent model configurations')
    p.add_argument('--reasoning', type=str, help='JSON string of reasoning configuration')
    p.add_argument('--use-meta-orchestrator', action='store_true', 
                   help='使用Meta-Orchestrator进行智能规划和框架执行（新流程）')
    return p.parse_args()


def run_demo():
    logger.info("[demo] 启动盲评流程示例")

    args = parse_args()
    
    issue_text = args.issue
    if not issue_text:
        print("\n" + "="*10 + " AICouncil 议事系统 " + "="*10)
        issue_text = input("请输入您想要讨论的议题 (例如: 如何优化社区治理): ").strip()
        if not issue_text:
            issue_text = "如何优化社区治理"
            print(f"未输入议题，使用默认议题: {issue_text}")
    
    backend = args.backend or config.MODEL_BACKEND
    
    # 确定默认模型名称
    if args.model:
        model_name = args.model
    else:
        if backend == 'deepseek':
            model_name = config.DEEPSEEK_MODEL
        elif backend == 'openrouter':
            model_name = config.OPENROUTER_MODEL
        elif backend == 'openai':
            model_name = config.OPENAI_MODEL
        else:
            model_name = config.MODEL_NAME

    # 解析 reasoning
    reasoning = None
    if args.reasoning:
        try:
            reasoning = json.loads(args.reasoning)
        except Exception as e:
            logger.error(f"[demo] 解析 reasoning 失败: {e}")

    model_cfg = {"type": backend, "model": model_name}
    if reasoning:
        model_cfg["reasoning"] = reasoning

    logger.info(f"[demo] 使用模型配置: {model_cfg}, 轮数: {args.rounds}, 策论家: {args.planners}, 监察官: {args.auditors}")
    
    # 解析 agent_configs
    agent_configs = None
    if args.agent_configs:
        try:
            agent_configs = json.loads(args.agent_configs)
            logger.info(f"[demo] 使用自定义 Agent 配置: {agent_configs}")
        except Exception as e:
            logger.error(f"[demo] 解析 agent_configs 失败: {e}")

    print(f"\n>>> 议事开始: {issue_text}")
    print(f">>> 实时监控: 请在另一个终端运行 'python src/web/app.py' 并访问 http://127.0.0.1:5000\n")

    # 判断使用哪种流程
    if args.use_meta_orchestrator:
        # 新流程：Meta-Orchestrator智能规划 + 框架执行
        logger.info("[demo] 使用Meta-Orchestrator新流程")
        result = run_meta_orchestrator_flow(
            issue_text=issue_text,
            model_config=model_cfg,
            agent_configs=agent_configs
        )
    else:
        # 传统流程：run_full_cycle
        logger.info("[demo] 使用传统run_full_cycle流程")
        result = run_full_cycle(
            issue_text, 
            model_config=model_cfg, 
            max_rounds=args.rounds,
            num_planners=args.planners,
            num_auditors=args.auditors,
            agent_configs=agent_configs
        )
    
    logger.info(f"[demo] 完成流程，结果摘要:\n" + json.dumps(result, indent=2, ensure_ascii=False))
    
    if "report_md" in result:
        print("\n" + "="*20 + " 最终 Markdown 报告 " + "="*20)
        print(result["report_md"])
        print("="*60 + "\n")


if __name__ == '__main__':
    run_demo()
