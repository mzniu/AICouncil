#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Stage任务指导是否正确注入到Agent输入中
"""

import sys
import os
from pathlib import Path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.agents.framework_engine import FrameworkEngine
from src.agents.frameworks import Framework, FrameworkStage

def test_stage_task_injection():
    """测试Stage任务是否正确注入到传统角色的输入中"""
    print("=" * 70)
    print("Stage任务注入测试")
    print("=" * 70)
    
    # 创建测试用的Stage
    test_stage = FrameworkStage(
        name="假设识别",
        description="识别用户需求中的关键假设和前提条件",
        roles=["planner", "auditor"],
        rounds=1,
        prompt_suffix="请特别关注隐含假设和潜在风险"
    )
    
    # 创建最小的Framework用于测试
    test_framework = Framework(
        id="test_framework",
        name="测试框架",
        description="用于测试Stage任务注入",
        stages=[test_stage]
    )
    
    # 创建临时工作目录
    temp_workspace = Path("tests/temp_workspace")
    temp_workspace.mkdir(exist_ok=True)
    
    # 创建FrameworkEngine实例
    engine = FrameworkEngine(
        framework=test_framework,
        model_config={"type": "deepseek", "model": "deepseek-reasoner"},
        workspace_path=temp_workspace,
        session_id="test_session"
    )
    
    # 设置用户需求
    engine.user_requirement = "开发一个智能推荐系统"
    
    # 测试Planner输入构建
    print("\n测试1: Planner输入构建")
    print("-" * 70)
    planner_input = engine._build_agent_input(
        stage=test_stage,
        context="智能推荐系统开发项目",
        round_num=1,
        previous_round_outputs=[],
        role_type="planner",
        agent_id="planner_1"
    )
    
    print(f"✓ Planner输入变量: {list(planner_input.keys())}")
    print(f"\n议题内容 (前200字符):")
    print(planner_input['issue'][:200])
    
    # 验证Stage任务是否注入
    if "本Stage任务" in planner_input['issue'] and "识别用户需求中的关键假设" in planner_input['issue']:
        print("\n✅ Stage任务已成功注入到Planner的议题中")
    else:
        print("\n❌ Stage任务未注入到Planner的议题中")
    
    if "隐含假设" in planner_input['issue']:
        print("✅ prompt_suffix已成功注入")
    else:
        print("❌ prompt_suffix未注入")
    
    # 测试Auditor输入构建
    print("\n\n测试2: Auditor输入构建")
    print("-" * 70)
    
    # 模拟有前置Planner输出
    mock_planner_outputs = [
        {
            "agent_id": "planner_1",
            "role_type": "planner",
            "content": '{"core_idea": "使用协同过滤算法", "steps": ["数据收集", "模型训练"]}'
        }
    ]
    
    auditor_input = engine._build_agent_input(
        stage=test_stage,
        context="智能推荐系统开发项目",
        round_num=1,
        previous_round_outputs=mock_planner_outputs,
        role_type="auditor",
        agent_id="auditor_1"
    )
    
    print(f"✓ Auditor输入变量: {list(auditor_input.keys())}")
    print(f"\n议题内容 (前200字符):")
    print(auditor_input['issue'][:200])
    
    # 验证Stage任务是否注入
    if "本Stage审查重点" in auditor_input['issue'] and "识别用户需求中的关键假设" in auditor_input['issue']:
        print("\n✅ Stage任务已成功注入到Auditor的议题中")
    else:
        print("\n❌ Stage任务未注入到Auditor的议题中")
    
    if "审查重点" in auditor_input['issue']:
        print("✅ 针对Auditor的特殊提示已添加")
    else:
        print("⚠️  Auditor特殊提示未添加")
    
    # 测试自定义角色（不应受影响）
    print("\n\n测试3: 自定义角色输入构建（验证兼容性）")
    print("-" * 70)
    
    custom_stage = FrameworkStage(
        name="技术评估",
        description="评估技术方案的可行性",
        roles=["tech_analyst"],
        rounds=1
    )
    
    try:
        custom_input = engine._build_agent_input(
            stage=custom_stage,
            context="技术方案评估",
            round_num=1,
            previous_round_outputs=[],
            role_type="tech_analyst",
            agent_id="tech_analyst_1"
        )
        print(f"✓ 自定义角色输入变量: {list(custom_input.keys())}")
        
        if "stage_description" in custom_input:
            print("✅ 自定义角色仍然使用独立的stage_description变量")
        else:
            print("⚠️  自定义角色缺少stage_description变量")
            
    except Exception as e:
        print(f"⚠️  自定义角色测试失败: {e}")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)

if __name__ == "__main__":
    test_stage_task_injection()
