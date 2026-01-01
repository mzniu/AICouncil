"""
Google Custom Search API 测试

使用 Google 官方 API 进行搜索，无需担心反爬虫问题。

配置步骤：
1. 访问 https://developers.google.com/custom-search/v1/overview
2. 创建 API Key
3. 创建 Custom Search Engine ID
4. 在 src/config.py 中添加：
   GOOGLE_API_KEY = "your_api_key"
   GOOGLE_SEARCH_ENGINE_ID = "your_search_engine_id"
"""

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.search_utils import google_search_api


def test_google_api_basic():
    """测试 Google Custom Search API 基本功能"""
    print("\n" + "="*60)
    print("测试: Google Custom Search API - '人工智能'")
    print("="*60)
    
    result = google_search_api("人工智能", max_results=5)
    
    print(f"\n搜索结果长度: {len(result)} 字符")
    print("\n搜索结果预览（前 800 字符）:")
    print(result[:800])
    
    # 检查配置
    if "未配置" in result:
        print("\n⚠️ 提示:")
        print("1. 访问 https://developers.google.com/custom-search/v1/overview")
        print("2. 创建 API Key 和 Search Engine ID")
        print("3. 在 src/config.py 中添加:")
        print("   GOOGLE_API_KEY = 'your_api_key'")
        print("   GOOGLE_SEARCH_ENGINE_ID = 'your_search_engine_id'")
        return False
    
    # 检查配额
    if "配额已用尽" in result:
        print("\n⚠️ Google API 免费配额已用尽（100次/天）")
        return False
    
    # 验证结果
    if "失败" in result and "API" not in result:
        print("\n❌ 搜索失败")
        return False
    
    if "|" in result and ("标题" in result or "title" in result.lower()):
        print("\n✅ Google API 搜索成功！")
        return True
    else:
        print(f"\n⚠️ 结果格式异常")
        return False


def test_google_api_english():
    """测试英文查询"""
    print("\n" + "="*60)
    print("测试: 英文查询 - 'Python tutorial'")
    print("="*60)
    
    result = google_search_api("Python tutorial", max_results=3)
    
    print(f"\n搜索结果长度: {len(result)} 字符")
    print("\n搜索结果预览（前 500 字符）:")
    print(result[:500])
    
    if "未配置" in result or "配额已用尽" in result:
        return False
    
    return "|" in result


def compare_google_methods():
    """对比 API 和 Playwright 两种方式"""
    print("\n" + "="*60)
    print("对比测试: Google API vs Playwright")
    print("="*60)
    
    from src.utils.search_utils import google_search_playwright
    import time
    
    query = "机器学习"
    
    # 测试 API
    print("\n1️⃣ 测试 Google Custom Search API...")
    start = time.time()
    result_api = google_search_api(query, max_results=5)
    time_api = time.time() - start
    
    print(f"耗时: {time_api:.2f}秒")
    print(f"结果长度: {len(result_api)} 字符")
    api_success = "|" in result_api and "失败" not in result_api
    print(f"状态: {'✅ 成功' if api_success else '❌ 失败'}")
    
    # 测试 Playwright
    print("\n2️⃣ 测试 Playwright（无代理，预期失败）...")
    start = time.time()
    result_playwright = google_search_playwright(query, max_results=5, max_retries=1)
    time_playwright = time.time() - start
    
    print(f"耗时: {time_playwright:.2f}秒")
    print(f"结果长度: {len(result_playwright)} 字符")
    playwright_success = "|" in result_playwright
    print(f"状态: {'✅ 成功' if playwright_success else '❌ 失败（预期）'}")
    
    print("\n" + "="*60)
    print("对比总结:")
    print("="*60)
    print(f"Google API: {'✅ 推荐' if api_success else '❌ 需配置'} | 速度: {time_api:.2f}s | 稳定性: 高")
    print(f"Playwright: {'✅' if playwright_success else '⚠️ 需代理'} | 速度: {time_playwright:.2f}s | 稳定性: 中")
    print("\n建议：")
    if api_success:
        print("✅ Google API 已配置且可用，推荐使用！")
    else:
        print("⚠️ Google API 未配置，建议配置后使用（国内无需代理，速度快）")
    print("💡 Playwright 方案适合海外服务器或已配置代理的环境")


if __name__ == "__main__":
    print("\n🔍 Google Custom Search API 测试套件")
    print("="*60)
    
    # 基本测试
    api_works = test_google_api_basic()
    
    if api_works:
        # 英文测试
        test_google_api_english()
        
        # 对比测试
        compare_google_methods()
    else:
        print("\n" + "="*60)
        print("⚠️ 请先配置 Google Custom Search API")
        print("="*60)
        print("\n配置步骤：")
        print("1. 访问 Google Cloud Console:")
        print("   https://console.cloud.google.com/")
        print("\n2. 启用 Custom Search API")
        print("   https://console.cloud.google.com/apis/library/customsearch.googleapis.com")
        print("\n3. 创建 API 凭据:")
        print("   https://console.cloud.google.com/apis/credentials")
        print("   - 选择「创建凭据」→「API 密钥」")
        print("   - 复制 API Key")
        print("\n4. 创建自定义搜索引擎:")
        print("   https://programmablesearchengine.google.com/")
        print("   - 点击「添加」创建新搜索引擎")
        print("   - 搜索范围：选择「搜索整个网络」")
        print("   - 复制「搜索引擎 ID」")
        print("\n5. 在 src/config.py 中添加:")
        print("   GOOGLE_API_KEY = 'your_api_key_here'")
        print("   GOOGLE_SEARCH_ENGINE_ID = 'your_search_engine_id_here'")
        print("\n💡 免费配额：100 次搜索/天")
        print("💰 付费价格：$5/1000 次查询")
