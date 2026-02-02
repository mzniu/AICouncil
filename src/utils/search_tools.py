"""
Search Tools for AICouncil Function Calling

将web搜索功能封装为Function Calling工具，供所有角色使用。
"""

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List

from src import config_manager as config
from src.utils.logger import logger
from src.utils.search_utils import (
    tavily_search, bing_search, baidu_search,
    yahoo_search, mojeek_search, duckduckgo_search,
    google_search_api
)


def web_search(query: str, max_results: int = 10) -> Dict[str, Any]:
    """
    执行web搜索并返回结果。
    
    Args:
        query: 搜索关键词
        max_results: 每个搜索引擎返回的最大结果数
    
    Returns:
        {
            "success": bool,
            "query": str,
            "results": str,  # 格式化的搜索结果文本
            "providers": List[str],  # 使用的搜索引擎列表
            "total_sources": int  # 搜索结果来源数量
        }
    """
    query = query.strip()
    if not query:
        return {
            "success": False,
            "query": "",
            "results": "",
            "providers": [],
            "total_sources": 0,
            "error": "搜索关键词不能为空"
        }
    
    # 获取配置的搜索引擎列表
    provider_str = getattr(config, "SEARCH_PROVIDER", "bing").lower()
    providers = [p.strip() for p in provider_str.split(',') if p.strip()]
    if not providers:
        providers = ["bing"]
    
    logger.info(f"[web_search] Query: '{query}', Providers: {providers}, MaxResults: {max_results}")
    
    def perform_single_search(provider: str) -> tuple:
        """执行单个搜索引擎的查询"""
        try:
            if provider == "tavily":
                return tavily_search(query, max_results=max_results), provider
            elif provider == "bing":
                return bing_search(query, max_results=max_results), provider
            elif provider == "baidu":
                return baidu_search(query, max_results=max_results), provider
            elif provider == "yahoo":
                return yahoo_search(query, max_results=max_results), provider
            elif provider == "mojeek":
                return mojeek_search(query, max_results=max_results), provider
            elif provider == "google":
                return google_search_api(query, max_results=max_results), "google (API)"
            elif provider == "duckduckgo":
                res = duckduckgo_search(query, max_results=max_results)
                if "搜索失败" in res:
                    logger.info(f"DuckDuckGo failed, falling back to Bing")
                    return bing_search(query, max_results=max_results), "bing (fallback)"
                return res, provider
            else:
                return bing_search(query, max_results=max_results), "bing (default)"
        except Exception as e:
            logger.error(f"Search failed on {provider}: {e}")
            return f"搜索出错: {str(e)}", f"{provider} (error)"
    
    # 并行执行所有搜索引擎
    all_results = []
    actual_providers = []
    
    with ThreadPoolExecutor(max_workers=min(len(providers), 10)) as executor:
        futures = [executor.submit(perform_single_search, p) for p in providers]
        
        for future in futures:
            res, actual_provider = future.result()
            all_results.append(f"### 搜索来源: {actual_provider}\n\n{res}")
            actual_providers.append(actual_provider)
    
    # 合并结果
    combined_results = "\n\n---\n\n".join(all_results)
    
    logger.info(f"[web_search] Completed. Used {len(actual_providers)} providers, {len(combined_results)} chars total")
    
    return {
        "success": True,
        "query": query,
        "results": combined_results,
        "providers": actual_providers,
        "total_sources": len(actual_providers)
    }


# ============ Tool Schemas ============

WEB_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "在互联网上搜索信息。当需要获取最新资讯、事实核查、数据查询或任何需要外部信息的场景时使用此工具。支持多搜索引擎并行查询以获得更全面的结果。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或问题。应该清晰、具体，避免过于宽泛。例如：'2024年AI大模型最新进展'、'碳中和政策对制造业的影响'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "每个搜索引擎返回的最大结果数量，默认10条",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    }
}


# ============ Tool Executors ============

SEARCH_TOOL_EXECUTORS = {
    "web_search": web_search
}


def get_search_tool_schemas() -> List[Dict[str, Any]]:
    """返回所有搜索工具的schemas"""
    return [WEB_SEARCH_SCHEMA]


def execute_search_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行搜索工具调用
    
    Args:
        tool_name: 工具名称（web_search）
        arguments: 工具参数字典
    
    Returns:
        工具执行结果
    """
    if tool_name not in SEARCH_TOOL_EXECUTORS:
        logger.error(f"Unknown search tool: {tool_name}")
        return {
            "success": False,
            "error": f"未知的搜索工具: {tool_name}"
        }
    
    try:
        executor = SEARCH_TOOL_EXECUTORS[tool_name]
        result = executor(**arguments)
        return result
    except Exception as e:
        logger.error(f"Search tool execution failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"搜索工具执行失败: {str(e)}"
        }


def format_search_tool_result_for_llm(tool_name: str, result: Dict[str, Any]) -> str:
    """
    将搜索工具结果格式化为适合LLM理解的文本
    
    Args:
        tool_name: 工具名称
        result: 工具执行结果
    
    Returns:
        格式化后的文本
    """
    if not result.get("success"):
        error_msg = result.get("error", "未知错误")
        return f"❌ 搜索失败: {error_msg}"
    
    if tool_name == "web_search":
        query = result.get("query", "")
        providers = result.get("providers", [])
        total_sources = result.get("total_sources", 0)
        results = result.get("results", "")
        
        header = f"""
✅ 搜索成功

**查询关键词**: {query}
**搜索引擎**: {', '.join(providers)}
**结果来源数**: {total_sources}

---

{results}
"""
        return header.strip()
    
    return str(result)


# ============ 测试代码 ============

if __name__ == "__main__":
    print("=" * 80)
    print("Testing Search Tools")
    print("=" * 80)
    
    # Test 1: web_search
    print("\n[Test 1] web_search('AI大模型最新进展', max_results=3)")
    result = web_search("AI大模型最新进展", max_results=3)
    print(f"Success: {result['success']}")
    print(f"Query: {result['query']}")
    print(f"Providers: {result['providers']}")
    print(f"Total sources: {result['total_sources']}")
    print(f"Results length: {len(result['results'])} chars")
    print(f"✅ Test 1 passed" if result['success'] else "❌ Test 1 failed")
    
    # Test 2: get_search_tool_schemas
    print("\n[Test 2] get_search_tool_schemas()")
    schemas = get_search_tool_schemas()
    print(f"Schemas count: {len(schemas)}")
    print(f"Schema names: {[s['function']['name'] for s in schemas]}")
    print(f"✅ Test 2 passed" if len(schemas) == 1 else "❌ Test 2 failed")
    
    # Test 3: execute_search_tool
    print("\n[Test 3] execute_search_tool('web_search', {'query': 'Python', 'max_results': 2})")
    result = execute_search_tool("web_search", {"query": "Python", "max_results": 2})
    print(f"Success: {result['success']}")
    print(f"✅ Test 3 passed" if result['success'] else "❌ Test 3 failed")
    
    # Test 4: format_search_tool_result_for_llm
    print("\n[Test 4] format_search_tool_result_for_llm()")
    formatted = format_search_tool_result_for_llm("web_search", result)
    print(f"Formatted length: {len(formatted)} chars")
    print(f"Contains query: {'query' in formatted.lower()}")
    print(f"✅ Test 4 passed" if len(formatted) > 0 else "❌ Test 4 failed")
    
    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)
