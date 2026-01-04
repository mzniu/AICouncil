"""
测试最后一轮议长的Prompt选择逻辑
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents import langchain_agents

def test_leader_prompt_selection():
    """测试议长prompt选择逻辑"""
    print("=" * 60)
    print("测试议长Prompt选择逻辑")
    print("=" * 60)
    
    # 测试中间轮次prompt
    intermediate_prompt = langchain_agents._get_leader_prompt_for_intermediate_round()
    print("\n[中间轮次Prompt]")
    print(f"长度: {len(intermediate_prompt)} 字符")
    print(f"包含'next_round_focus': {'next_round_focus' in intermediate_prompt}")
    print(f"包含'下一轮': {'下一轮' in intermediate_prompt}")
    
    # 测试最后一轮prompt
    final_prompt = langchain_agents._get_leader_prompt_for_final_round()
    print("\n[最后一轮Prompt]")
    print(f"长度: {len(final_prompt)} 字符")
    print(f"包含'🏁': {'🏁' in final_prompt}")
    print(f"包含'最后一轮': {'最后一轮' in final_prompt}")
    print(f"包含'全局性总结': {'全局性总结' in final_prompt}")
    print(f"包含'报告准备': {'报告准备' in final_prompt}")
    
    # 验证Schema差异
    print("\n[Schema约束差异]")
    intermediate_has_required = '"next_round_focus": "' in intermediate_prompt
    final_has_optional = '"next_round_focus": null' in final_prompt or 'Optional' in final_prompt
    
    print(f"中间轮次要求next_round_focus必填: {intermediate_has_required}")
    print(f"最后一轮允许next_round_focus为null: {final_has_optional}")
    
    # 测试make_leader_chain参数传递
    model_config = {"type": "deepseek", "model": "deepseek-chat"}
    
    print("\n[Chain创建测试]")
    try:
        intermediate_chain = langchain_agents.make_leader_chain(model_config, is_final_round=False)
        print("✓ 成功创建中间轮次chain")
    except Exception as e:
        print(f"✗ 创建中间轮次chain失败: {e}")
    
    try:
        final_chain = langchain_agents.make_leader_chain(model_config, is_final_round=True)
        print("✓ 成功创建最后一轮chain")
    except Exception as e:
        print(f"✗ 创建最后一轮chain失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_leader_prompt_selection()
