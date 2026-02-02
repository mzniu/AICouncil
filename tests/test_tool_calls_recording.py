"""
快速测试Skills工具调用记录

创建一个简短的讨论，验证tool_calls是否被正确保存到history中
"""

from src.agents.langchain_agents import run_full_cycle
import json
from pathlib import Path

print("=" * 70)
print("快速测试：Skills工具调用记录")
print("=" * 70)
print()

# 简单的测试议题（容易触发Skills调用）
test_issue = """
请评估：一家初创公司准备开发一款面向中小企业的财务管理SaaS产品。
- 初始资金：100万
- 团队规模：5人
- 开发周期：3个月MVP

请从市场、技术、财务三个维度简要分析可行性。
"""

print("测试议题:", test_issue[:100] + "...")
print()
print("配置：1轮，1个策论家，1个监察官（最小配置，快速测试）")
print()

model_config = {
    "type": "deepseek",
    "model": "deepseek-chat"
}

try:
    result = run_full_cycle(
        issue_text=test_issue,
        model_config=model_config,
        max_rounds=1,
        num_planners=1,  # 只1个策论家
        num_auditors=1,  # 只1个监察官
        user_id=1,
        tenant_id=1
    )
    
    print()
    print("=" * 70)
    print("✅ 讨论完成！")
    print("=" * 70)
    print()
    
    # 检查history文件
    workspace = Path(result.get('workspace_path', ''))
    history_file = workspace / "history.json"
    
    if history_file.exists():
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        print("【验证结果】")
        print(f"✅ 历史记录文件存在: {history_file}")
        print(f"✅ 轮次数: {len(history)}")
        
        if len(history) > 0:
            round1 = history[0]
            
            # 检查策论家
            if 'plans' in round1 and len(round1['plans']) > 0:
                plan = round1['plans'][0]
                has_tool_calls = 'tool_calls' in plan
                has_name = 'name' in plan
                
                print()
                print("策论家输出:")
                print(f"  - 有'tool_calls'字段: {has_tool_calls}")
                print(f"  - 有'name'字段: {has_name}")
                
                if has_tool_calls:
                    tool_calls = plan['tool_calls']
                    print(f"  - 工具调用数量: {len(tool_calls)}")
                    if len(tool_calls) > 0:
                        print(f"  - 调用的工具:")
                        for tc in tool_calls[:5]:  # 最多显示5个
                            print(f"    • {tc.get('tool_name', 'unknown')}")
                    else:
                        print("  ⚠️  tool_calls字段存在但为空（Agent没有调用工具）")
                else:
                    print("  ❌ 缺少'tool_calls'字段！修复未生效")
            
            # 检查监察官
            if 'audits' in round1 and len(round1['audits']) > 0:
                audit = round1['audits'][0]
                has_tool_calls = 'tool_calls' in audit
                has_name = 'name' in audit
                
                print()
                print("监察官输出:")
                print(f"  - 有'tool_calls'字段: {has_tool_calls}")
                print(f"  - 有'name'字段: {has_name}")
                
                if has_tool_calls:
                    tool_calls = audit['tool_calls']
                    print(f"  - 工具调用数量: {len(tool_calls)}")
                    if len(tool_calls) > 0:
                        print(f"  - 调用的工具:")
                        for tc in tool_calls[:5]:
                            print(f"    • {tc.get('tool_name', 'unknown')}")
                    else:
                        print("  ⚠️  tool_calls字段存在但为空（Agent没有调用工具）")
                else:
                    print("  ❌ 缺少'tool_calls'字段！修复未生效")
        
        print()
        print("=" * 70)
        print("提示：如果tool_calls为空，说明Agent选择不调用工具")
        print("     这是正常的（Agent根据需要自主决定是否使用工具）")
        print("=" * 70)
    else:
        print(f"❌ 历史记录文件不存在: {history_file}")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
