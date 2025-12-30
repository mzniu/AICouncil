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
from src.utils import logger
from pydantic import ValidationError
import time
import argparse
import json
from src.agents.langchain_agents import run_full_cycle
from src import config_manager as config


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

    result = run_full_cycle(
        issue_text, 
        model_config=model_cfg, 
        max_rounds=args.rounds,
        num_planners=args.planners,
        num_auditors=args.auditors,
        agent_configs=agent_configs
    )
    logger.info(f"[demo] 完成 {args.rounds} 轮流程，结果摘要:\n" + json.dumps(result, indent=2, ensure_ascii=False))
    
    if "report_md" in result:
        print("\n" + "="*20 + " 最终 Markdown 报告 " + "="*20)
        print(result["report_md"])
        print("="*60 + "\n")


if __name__ == '__main__':
    run_demo()
