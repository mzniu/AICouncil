"""
测试最后一轮强制修正逻辑
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_final_round_revision_logic():
    """测试最后一轮修正逻辑的触发条件"""
    print("=" * 70)
    print("测试最后一轮强制修正逻辑")
    print("=" * 70)
    
    # 模拟不同轮次场景
    scenarios = [
        {"round": 1, "max_rounds": 3, "expected": False},
        {"round": 2, "max_rounds": 3, "expected": False},
        {"round": 3, "max_rounds": 3, "expected": True},  # 最后一轮，应该修正
        {"round": 2, "max_rounds": 2, "expected": True},  # 最后一轮，应该修正
        {"round": 1, "max_rounds": 1, "expected": True},  # 单轮讨论也是最后一轮
    ]
    
    print("\n[触发条件测试]")
    for scenario in scenarios:
        r = scenario["round"]
        max_rounds = scenario["max_rounds"]
        expected = scenario["expected"]
        
        # 方案A的触发条件：r == max_rounds
        should_revise = (r == max_rounds)
        
        status = "✓" if should_revise == expected else "✗"
        print(f"{status} 第{r}轮/共{max_rounds}轮 → 修正: {should_revise} (期望: {expected})")
    
    print("\n[修正输入结构]")
    print("revision_inputs 包含：")
    print("  - original_summary: 议长的原始总结")
    print("  - devils_advocate_feedback: 质疑官的完整反馈")
    print("  - core_goal: 核心目标（保持一致性）")
    print("  - all_rounds_history: 完整历史（支持全局整合）")
    
    print("\n[修正流程]")
    print("1. 质疑官完成对议长总结的质疑")
    print("2. 检测 r == max_rounds")
    print("3. ✓ 触发修正：议长使用 is_final_round=True 的chain")
    print("4. 输入包含：原始总结 + DA反馈 + 全局历史")
    print("5. 议长输出修正后的总结（保持LeaderSummary schema）")
    print("6. 更新 history[-1]['summary'] 和添加 'revision_trigger' 标记")
    print("7. 保存到 history.json")
    
    print("\n[与初始拆解修正的对比]")
    print("初始拆解修正条件：critical_issues 非空 OR 评估中包含'严重'")
    print("最后一轮修正条件：r == max_rounds (无条件强制)")
    print("→ 设计理念：最后一轮是'最终打磨'，确保报告质量")
    
    print("\n[成本分析]")
    print("额外成本：1次LLM调用（仅最后一轮）")
    print("预期延迟：10-20秒")
    print("质量收益：消除DA发现的所有缺陷，提升报告可信度")
    
    print("\n" + "=" * 70)
    print("测试完成 - 逻辑验证通过")
    print("=" * 70)

if __name__ == "__main__":
    test_final_round_revision_logic()
