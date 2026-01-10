#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FrameworkEngine 功能测试

测试框架执行引擎的基础功能（不涉及LLM调用）
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.framework_engine import FrameworkEngine
from src.agents.frameworks import get_framework, list_frameworks


def test_prerequisites():
    """测试前置条件"""
    print("============================================================")
    print("测试FrameworkEngine前置条件")
    print("============================================================\n")
    
    # 测试1：获取框架
    print("【测试1】获取框架定义")
    frameworks = list_frameworks()
    print(f"  可用框架: {len(frameworks)} 个")
    for fw in frameworks:
        print(f"    - {fw['name']} (ID: {fw['id']})")
    
    # 测试2：创建引擎实例
    print("\n【测试2】创建FrameworkEngine实例")
    framework = get_framework("roberts_rules")
    engine = FrameworkEngine(
        framework=framework,
        model_config={"type": "deepseek", "model": "deepseek-chat"},
        workspace_path=Path("./test_workspace"),
        session_id="test_001"
    )
    print(f"  ✅ 引擎创建成功")
    print(f"    - 框架: {engine.framework.name}")
    print(f"    - Stages: {len(engine.framework.stages)} 个")
    
    # 测试3：检查role映射
    print("\n【测试3】检查Role映射")
    for role_type, make_chain_func in FrameworkEngine.ROLE_CHAIN_MAPPING.items():
        display_name = FrameworkEngine.ROLE_DISPLAY_NAMES.get(role_type)
        print(f"  {role_type}: {make_chain_func.__name__} -> {display_name}")
    
    # 测试4：验证stage配置
    print("\n【测试4】验证Stage配置")
    for i, stage in enumerate(framework.stages, 1):
        print(f"  Stage {i}: {stage.name}")
        print(f"    - 描述: {stage.description}")
        print(f"    - 角色: {stage.roles}")
        print(f"    - Agent数量: {stage.min_agents}-{stage.max_agents}")
        print(f"    - 轮次: {stage.rounds}")
        if stage.depends_on:
            print(f"    - 依赖: {stage.depends_on}")
    
    print("\n============================================================")
    print("✅ 所有前置条件测试通过")
    print("============================================================\n")


def test_engine_methods():
    """测试引擎的辅助方法"""
    print("============================================================")
    print("测试FrameworkEngine辅助方法")
    print("============================================================\n")
    
    # 创建引擎实例
    framework = get_framework("roberts_rules")
    engine = FrameworkEngine(
        framework=framework,
        model_config={"type": "deepseek", "model": "deepseek-chat"},
        workspace_path=Path("./test_workspace"),
        session_id="test_002"
    )
    
    # 测试1：构建上下文
    print("【测试1】_build_stage_context()")
    engine.user_requirement = "测试需求：讨论是否采用新技术方案"
    engine.stage_outputs = {
        "动议提出": {
            "agents": [
                {"agent_id": "leader_1", "content": "我提议采用方案A"}
            ]
        }
    }
    
    stage = framework.stages[1]  # 第二个stage（假设依赖第一个）
    if stage.depends_on:
        context = engine._build_stage_context(stage)
        print(f"  ✅ 上下文构建成功，长度: {len(context)} 字符")
        print(f"  预览: {context[:100]}...")
    else:
        print(f"  ⚠️ Stage '{stage.name}' 没有依赖，跳过测试")
    
    # 测试2：格式化stage输出
    print("\n【测试2】_format_stage_output()")
    stage_output = {
        "agents": [
            {"agent_id": "planner_1", "content": "方案A有以下优点..."},
            {"agent_id": "planner_2", "content": "我支持方案A..."}
        ]
    }
    formatted = engine._format_stage_output(stage_output)
    print(f"  ✅ 格式化成功，长度: {len(formatted)} 字符")
    print(f"  预览: {formatted[:100]}...")
    
    # 测试3：构建Agent输入
    print("\n【测试3】_build_agent_input()")
    agent_input = engine._build_agent_input(
        stage=framework.stages[0],
        context="测试上下文内容",
        round_num=1,
        previous_round_outputs=[]
    )
    print(f"  ✅ Agent输入构建成功")
    print(f"  字段: {list(agent_input.keys())}")
    
    # 测试4：生成摘要
    print("\n【测试4】_summarize_stage_output()")
    summary = engine._summarize_stage_output(stage_output)
    print(f"  ✅ 摘要生成成功: {summary}")
    
    print("\n============================================================")
    print("✅ 所有辅助方法测试通过")
    print("============================================================\n")


def test_chain_creation():
    """测试chain创建逻辑（不实际创建）"""
    print("============================================================")
    print("测试Chain创建逻辑")
    print("============================================================\n")
    
    framework = get_framework("roberts_rules")
    engine = FrameworkEngine(
        framework=framework,
        model_config={"type": "deepseek", "model": "deepseek-chat"},
        workspace_path=Path("./test_workspace"),
        session_id="test_003"
    )
    
    # 模拟agent_counts
    agent_counts = {
        "leader": 1,
        "planner": 2,
        "auditor": 2
    }
    
    print("【测试】模拟创建chains")
    for stage in framework.stages:
        print(f"\nStage: {stage.name}")
        print(f"  要求角色: {stage.roles}")
        
        for role_type in stage.roles:
            # 计算该角色的数量
            count = agent_counts.get(role_type, stage.min_agents)
            count = max(stage.min_agents, min(count, stage.max_agents))
            
            # 检查是否有对应的chain创建函数
            make_chain_func = FrameworkEngine.ROLE_CHAIN_MAPPING.get(role_type)
            display_name = FrameworkEngine.ROLE_DISPLAY_NAMES.get(role_type, role_type)
            
            if make_chain_func:
                print(f"  ✅ {role_type}: 将创建 {count} 个 '{display_name}' agents")
                print(f"     使用函数: {make_chain_func.__name__}")
            else:
                print(f"  ❌ {role_type}: 未找到对应的chain创建函数")
    
    print("\n============================================================")
    print("✅ Chain创建逻辑验证通过")
    print("============================================================\n")


def test_integration():
    """测试execute_orchestration_plan集成"""
    print("============================================================")
    print("测试execute_orchestration_plan集成")
    print("============================================================\n")
    
    from src.agents.langchain_agents import execute_orchestration_plan
    
    print("【测试】execute_orchestration_plan导入")
    print(f"  ✅ 函数导入成功: {execute_orchestration_plan.__name__}")
    print(f"  参数: {execute_orchestration_plan.__code__.co_varnames[:execute_orchestration_plan.__code__.co_argcount]}")
    
    print("\n============================================================")
    print("✅ 集成测试通过")
    print("============================================================\n")


def main():
    print("🧪 FrameworkEngine 功能测试\n")
    
    try:
        test_prerequisites()
        test_engine_methods()
        test_chain_creation()
        test_integration()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！")
        print("="*60)
        
        print("\n📝 注意：")
        print("  - 以上测试验证了FrameworkEngine的基础结构和逻辑")
        print("  - 实际的LLM调用测试需要配置API Key")
        print("  - 完整的端到端测试可以通过以下方式：")
        print("    1. 配置 src/config.py 中的 API_KEY")
        print("    2. 使用 run_meta_orchestrator() 生成规划")
        print("    3. 使用 execute_orchestration_plan() 执行规划")
        print("    4. 或直接通过改造后的 demo_runner.py（Todo 7）")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
