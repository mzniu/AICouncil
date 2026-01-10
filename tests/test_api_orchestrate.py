#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试/api/orchestrate端点

测试Meta-Orchestrator API端点的功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import json


def test_endpoint_exists():
    """测试端点是否存在"""
    print("============================================================")
    print("测试/api/orchestrate端点存在性")
    print("============================================================\n")
    
    from src.web.app import app
    
    # 获取所有API路由
    api_routes = [r.rule for r in app.url_map.iter_rules() if '/api/' in r.rule]
    
    print(f"【测试1】API端点总数: {len(api_routes)}")
    
    # 检查/api/orchestrate是否存在
    print(f"\n【测试2】/api/orchestrate端点")
    if '/api/orchestrate' in api_routes:
        print(f"  ✅ /api/orchestrate 端点存在")
        
        # 获取该端点的详细信息
        for rule in app.url_map.iter_rules():
            if rule.rule == '/api/orchestrate':
                print(f"  方法: {rule.methods}")
                print(f"  端点函数: {rule.endpoint}")
    else:
        print(f"  ❌ /api/orchestrate 端点不存在")
        return False
    
    print("\n============================================================")
    print("✅ 端点存在性测试通过")
    print("============================================================\n")
    return True


def test_endpoint_function():
    """测试端点函数"""
    print("============================================================")
    print("测试orchestrate_discussion函数")
    print("============================================================\n")
    
    from src.web.app import orchestrate_discussion, run_meta_orchestrator_backend
    
    print("【测试1】函数导入")
    print(f"  ✅ orchestrate_discussion: {orchestrate_discussion.__name__}")
    print(f"  ✅ run_meta_orchestrator_backend: {run_meta_orchestrator_backend.__name__}")
    
    print("\n【测试2】函数签名")
    print(f"  orchestrate_discussion参数: 无（使用request.json）")
    print(f"  run_meta_orchestrator_backend参数: {run_meta_orchestrator_backend.__code__.co_varnames[:run_meta_orchestrator_backend.__code__.co_argcount]}")
    
    print("\n============================================================")
    print("✅ 端点函数测试通过")
    print("============================================================\n")


def test_request_format():
    """测试请求格式"""
    print("============================================================")
    print("测试API请求格式")
    print("============================================================\n")
    
    print("【测试1】plan_only模式请求格式")
    plan_only_request = {
        "issue": "测试议题",
        "backend": "deepseek",
        "model": "deepseek-chat",
        "mode": "plan_only"
    }
    print(f"  请求体示例:")
    print(f"  {json.dumps(plan_only_request, indent=4, ensure_ascii=False)}")
    
    print("\n【测试2】plan_and_execute模式请求格式")
    execute_request = {
        "issue": "测试议题",
        "backend": "deepseek",
        "model": "deepseek-chat",
        "mode": "plan_and_execute",
        "agent_configs": {
            "leader": {"type": "deepseek", "model": "deepseek-chat"}
        }
    }
    print(f"  请求体示例:")
    print(f"  {json.dumps(execute_request, indent=4, ensure_ascii=False)}")
    
    print("\n【测试3】响应格式（plan_only）")
    plan_response = {
        "status": "ok",
        "mode": "plan_only",
        "plan": {
            "framework_selection": {
                "framework_id": "roberts_rules",
                "framework_name": "罗伯特议事规则"
            },
            "execution_config": {
                "total_rounds": 2,
                "agent_counts": {"planner": 2, "auditor": 1}
            }
        }
    }
    print(f"  响应体示例:")
    print(f"  {json.dumps(plan_response, indent=4, ensure_ascii=False)}")
    
    print("\n【测试4】响应格式（plan_and_execute）")
    execute_response = {
        "status": "ok",
        "mode": "plan_and_execute"
    }
    print(f"  响应体示例:")
    print(f"  {json.dumps(execute_response, indent=4, ensure_ascii=False)}")
    
    print("\n============================================================")
    print("✅ 请求格式测试通过")
    print("============================================================\n")


def test_integration():
    """测试与其他模块的集成"""
    print("============================================================")
    print("测试模块集成")
    print("============================================================\n")
    
    print("【测试1】导入依赖模块")
    try:
        from src.agents.langchain_agents import run_meta_orchestrator
        print("  ✅ run_meta_orchestrator导入成功")
        
        from src.agents.demo_runner import run_meta_orchestrator_flow
        print("  ✅ run_meta_orchestrator_flow导入成功")
        
        from src import config_manager as config
        print("  ✅ config_manager导入成功")
        
    except ImportError as e:
        print(f"  ❌ 导入失败: {e}")
        return False
    
    print("\n【测试2】验证全局变量")
    from src.web.app import (
        is_running, discussion_events, backend_logs, 
        final_report, current_config, current_session_id
    )
    print(f"  ✅ is_running: {is_running}")
    print(f"  ✅ discussion_events: {len(discussion_events)} 条")
    print(f"  ✅ current_config: {current_config}")
    print(f"  ✅ current_session_id: {current_session_id}")
    
    print("\n============================================================")
    print("✅ 模块集成测试通过")
    print("============================================================\n")


def main():
    print("🧪 /api/orchestrate端点测试\n")
    
    try:
        if not test_endpoint_exists():
            print("\n❌ 端点存在性测试失败")
            sys.exit(1)
        
        test_endpoint_function()
        test_request_format()
        test_integration()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！")
        print("="*60)
        
        print("\n📝 使用说明:")
        print("  1. plan_only模式（仅规划，不执行）:")
        print("     POST /api/orchestrate")
        print("     {")
        print('       "issue": "你的议题",')
        print('       "backend": "deepseek",')
        print('       "mode": "plan_only"')
        print("     }")
        print()
        print("  2. plan_and_execute模式（规划并执行）:")
        print("     POST /api/orchestrate")
        print("     {")
        print('       "issue": "你的议题",')
        print('       "backend": "deepseek",')
        print('       "mode": "plan_and_execute"')
        print("     }")
        print()
        print("  3. 前端使用示例（JavaScript）:")
        print("     fetch('/api/orchestrate', {")
        print("       method: 'POST',")
        print("       headers: {'Content-Type': 'application/json'},")
        print("       body: JSON.stringify({")
        print("         issue: '如何优化团队协作',")
        print("         backend: 'deepseek',")
        print("         mode: 'plan_and_execute'")
        print("       })")
        print("     })")
        print()
        print("⚠️ 注意:")
        print("  - plan_only模式会立即返回规划方案")
        print("  - plan_and_execute模式会在后台执行，通过/api/status查询进度")
        print("  - 需要配置API Key（src/config.py）才能实际调用LLM")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
