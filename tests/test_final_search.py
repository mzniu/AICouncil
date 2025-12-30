import sys
import os
import time

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import search_utils
from src import config_manager as config

def test_multi_page_search():
    # 模拟用户多选供应商
    print("=== 测试 1: 百度多页搜索 (请求 12 条) ===")
    # 临时修改配置以测试百度
    original_provider = config.SEARCH_PROVIDER
    config.SEARCH_PROVIDER = "baidu"
    
    test_text = "[SEARCH: 2025年中国经济展望]"
    print(f"执行搜索指令: {test_text}")
    
    start_time = time.time()
    # 注意：search_if_needed 内部调用 baidu_search 时目前默认传的是 10
    # 我们直接调用 baidu_search 来验证多页逻辑
    results = search_utils.baidu_search("2025年中国经济展望", max_results=12)
    end_time = time.time()
    
    print(f"\n搜索耗时: {end_time - start_time:.2f} 秒")
    print("搜索结果摘要:")
    lines = results.split('\n')
    for line in lines[:20]: # 只打印前20行
        print(line)
    
    print("\n" + "="*50 + "\n")

    print("=== 测试 2: 并行多供应商搜索 (Bing + Baidu) ===")
    config.SEARCH_PROVIDER = "bing,baidu"
    test_text_parallel = "[SEARCH: DeepSeek R1 架构特点]"
    
    start_time = time.time()
    results_parallel = search_utils.search_if_needed(test_text_parallel)
    end_time = time.time()
    
    print(f"并行搜索耗时: {end_time - start_time:.2f} 秒")
    print("结果包含供应商:")
    if "来源: bing" in results_parallel: print("- 包含 Bing 结果")
    if "来源: baidu" in results_parallel: print("- 包含 Baidu 结果")
    
    # 恢复原始配置
    config.SEARCH_PROVIDER = original_provider

if __name__ == "__main__":
    test_multi_page_search()
