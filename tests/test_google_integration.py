"""
测试 Google 搜索在实际 Agent 讨论中的集成
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.search_utils import search_if_needed
from src import config_manager as config

def test_google_integration():
    """测试 Google 搜索在 Agent 讨论场景中的使用"""
    
    print("=" * 60)
    print("测试场景：Agent 在讨论中触发 Google 搜索")
    print("=" * 60)
    
    # 临时设置搜索引擎为 Google 和 Yahoo
    original_provider = config.SEARCH_PROVIDER
    config.SEARCH_PROVIDER = "google,yahoo"
    
    print(f"\n当前搜索引擎配置: {config.SEARCH_PROVIDER}")
    print(f"Google API Key 已配置: {'是' if config.GOOGLE_API_KEY else '否'}")
    print(f"Google Search Engine ID 已配置: {'是' if config.GOOGLE_SEARCH_ENGINE_ID else '否'}\n")
    
    # 模拟 Agent 输出中包含搜索请求
    test_content = """
这是我对人工智能发展的分析：

人工智能技术正在快速发展，为了获取最新信息，我需要进行搜索。

[SEARCH: 2025年人工智能最新进展]

基于搜索结果，我将提供详细分析...
"""
    
    print(f"原始 Agent 输出:\n{test_content}\n")
    
    # 执行搜索
    print("开始执行搜索（Google API + Yahoo）...\n")
    
    search_result = search_if_needed(test_content)
    
    # 恢复原始配置
    config.SEARCH_PROVIDER = original_provider
    
    print("=" * 60)
    print("搜索执行完成")
    print("=" * 60)
    
    # 检查结果
    if search_result:
        if "Google 搜索结果" in search_result or "Yahoo 搜索结果" in search_result:
            print("✅ 搜索结果已生成")
        else:
            print("⚠️ 搜索结果格式可能异常")
        
        lines = search_result.split('\n')
        print(f"\n搜索结果行数: {len(lines)}")
        print(f"搜索结果字符数: {len(search_result)}")
        
        # 检查是否包含多个引擎的结果
        if "Google" in search_result and "Yahoo" in search_result:
            print("✅ 成功使用多个搜索引擎（Google + Yahoo）")
        elif "Google" in search_result:
            print("✅ 使用了 Google 搜索")
        elif "Yahoo" in search_result:
            print("✅ 使用了 Yahoo 搜索")
        
        print(f"\n搜索结果预览（前 800 字符）:")
        print("-" * 60)
        print(search_result[:800])
        if len(search_result) > 800:
            print("...")
    else:
        print("❌ 未生成搜索结果")
    
    print("\n" + "=" * 60)
    print("集成测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_google_integration()
