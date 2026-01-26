"""
Skills工具函数库 - 将Skills转换为Function Calling工具 (数据库版本)

提供Skills作为可调用工具，供Agent在思考过程中主动调用：
1. 按需加载：工具列表包含Skill元数据，完整内容仅在调用时加载  
2. 数据库驱动：从数据库加载租户的Skills（支持多租户隔离）
3. 标准格式：遵循OpenAI Function Calling规范

架构设计：
- set_execution_context(tenant_id) -> 设置当前执行租户
- get_skill_tool_schemas() -> 返回所有Skill的工具schema列表
- execute_skill_tool(skill_name) -> 返回指定Skill的完整内容
"""

import json
import threading
from typing import Dict, List, Any, Optional

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# 线程本地存储：当前执行上下文
_execution_context = threading.local()


def set_execution_context(tenant_id: Optional[int] = None, user_id: Optional[int] = None):
    """
    设置当前线程的执行上下文
    
    Args:
        tenant_id: 租户ID
        user_id: 用户ID
    """
    _execution_context.tenant_id = tenant_id
    _execution_context.user_id = user_id
    logger.debug(f"[skill_tools] Execution context set: tenant_id={tenant_id}, user_id={user_id}")


def get_execution_context() -> Dict[str, Optional[int]]:
    """获取当前线程的执行上下文"""
    return {
        "tenant_id": getattr(_execution_context, "tenant_id", None),
        "user_id": getattr(_execution_context, "user_id", None)
    }


def _load_all_skills() -> List[Dict[str, Any]]:
    """
    从数据库加载所有Skills（基于当前租户）
    
    Returns:
        Skills字典列表（包含元数据，不含完整content）
    """
    try:
        # 获取当前租户ID
        ctx = get_execution_context()
        tenant_id = ctx.get("tenant_id")
        
        if not tenant_id:
            logger.warning("[skill_tools] No tenant_id in execution context, returning empty skills list")
            return []
        
        # 从数据库加载（延迟导入避免循环依赖）
        from src.repositories.skill_repository import SkillRepository
        
        # 获取租户所有激活的Skills
        result = SkillRepository.get_tenant_skills(
            tenant_id=tenant_id,
            is_active=True,
            include_content=False,  # 不加载完整内容，只要元数据
            page=1,
            page_size=1000  # 一次加载所有（合理租户不会超过1000个Skills）
        )
        
        skills = result.get("items", [])
        logger.info(f"[skill_tools] Loaded {len(skills)} skills for tenant {tenant_id}")
        return skills
        
    except Exception as e:
        logger.error(f"[skill_tools] Failed to load skills: {e}", exc_info=True)
        return []


def refresh_skills_cache():
    """刷新Skills缓存（当前实现直接从数据库读取，无需缓存）"""
    logger.info("[skill_tools] Skills are loaded from database, no cache to clear")


# ========== 工具1: list_skills ==========

def list_skills(filter_category: Optional[str] = None, filter_tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    列出所有可用的Skills（可选过滤）
    
    Args:
        filter_category: 按分类过滤（如 "business_analysis"）
        filter_tags: 按标签过滤（如 ["strategic", "financial"]）
    
    Returns:
        字典包含：
        - success: bool, 操作是否成功
        - skills: List[Dict], Skills摘要列表
        - total_count: int, Skills总数
        - filtered_count: int, 过滤后数量
        - error: Optional[str], 错误信息（如有）
    """
    try:
        all_skills = _load_all_skills()
        
        # 应用过滤器
        filtered_skills = all_skills
        if filter_category:
            filtered_skills = [s for s in filtered_skills if s.get("category") == filter_category]
        if filter_tags:
            filtered_skills = [
                s for s in filtered_skills 
                if any(tag in s.get("tags", []) for tag in filter_tags)
            ]
        
        # 格式化为摘要信息（数据已经是字典格式，直接提取）
        skills_summary = []
        for skill in filtered_skills:
            skills_summary.append({
                "name": skill.get("name"),
                "display_name": skill.get("display_name"),
                "category": skill.get("category"),
                "tags": skill.get("tags", []),
                "description": skill.get("description", ""),
                "version": skill.get("version"),
                "applicable_roles": skill.get("applicable_roles", []),
                "author": skill.get("author", "")
            })
        
        logger.info(f"[list_skills] Listed {len(filtered_skills)}/{len(all_skills)} skills")
        
        return {
            "success": True,
            "skills": skills_summary,
            "total_count": len(all_skills),
            "filtered_count": len(filtered_skills),
            "message": f"找到 {len(filtered_skills)} 个匹配的Skills"
        }
    
    except Exception as e:
        logger.error(f"[list_skills] Failed to list skills: {e}", exc_info=True)
        return {
            "success": False,
            "skills": [],
            "total_count": 0,
            "filtered_count": 0,
            "error": f"列出Skills失败: {str(e)}"
        }


# Function Calling Schema for list_skills
LIST_SKILLS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_skills",
        "description": "列出所有可用的专业技能(Skills)，包括分析框架、方法论、模板等。可按分类或标签过滤。用于发现适用的专业知识。",
        "parameters": {
            "type": "object",
            "properties": {
                "filter_category": {
                    "type": "string",
                    "description": "按分类过滤（可选），如 'business_analysis', 'technical', 'legal', 'financial'"
                },
                "filter_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "按标签过滤（可选），如 ['strategic', 'financial', 'risk_management']"
                }
            },
            "required": []
        }
    }
}


# ========== 工具2: use_skill ==========

def use_skill(skill_name: str) -> Dict[str, Any]:
    """
    加载并使用指定的Skill
    
    Args:
        skill_name: Skill名称（name字段）
    
    Returns:
        字典包含：
        - success: bool, 操作是否成功
        - skill_name: str, Skill名称
        - skill_content: str, Skill完整内容
        - metadata: Dict, Skill元数据
        - error: Optional[str], 错误信息（如有）
    """
    try:
        # 获取当前租户ID
        ctx = get_execution_context()
        tenant_id = ctx.get("tenant_id")
        
        if not tenant_id:
            return {
                "success": False,
                "error": "No tenant_id in execution context"
            }
        
        # 从数据库加载完整Skill
        from src.repositories.skill_repository import SkillRepository
        
        skill = SkillRepository.get_skill_by_name(name=skill_name, tenant_id=tenant_id)
        
        if not skill:
            return {
                "success": False,
                "error": f"Skill '{skill_name}' not found for tenant {tenant_id}"
            }
        
        skill_dict = skill.to_dict(include_content=True)
        
        logger.info(f"[use_skill] Loaded skill '{skill_name}' for tenant {tenant_id}")
        
        return {
            "success": True,
            "skill_name": skill_dict["name"],
            "skill_content": skill_dict["content"],
            "metadata": {
                "display_name": skill_dict["display_name"],
                "category": skill_dict["category"],
                "tags": skill_dict["tags"],
                "version": skill_dict["version"],
                "applicable_roles": skill_dict["applicable_roles"],
                "author": skill_dict["author"],
                "description": skill_dict["description"]
            },
            "message": f"成功加载Skill: {skill_dict['display_name']}"
        }
    
    except Exception as e:
        logger.error(f"[use_skill] Failed to load skill '{skill_name}': {e}", exc_info=True)
        return {
            "success": False,
            "error": f"加载Skill失败: {str(e)}"
        }


# Function Calling Schema for use_skill
USE_SKILL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "use_skill",
        "description": "加载并使用指定的Skill，获取其完整内容（框架、方法论、模板等）。在需要应用特定专业知识时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Skill的名称（name字段），可通过list_skills获取"
                }
            },
            "required": ["skill_name"]
        }
    }
}


# ========== 工具注册表 ==========

SKILL_TOOL_EXECUTORS = {
    "list_skills": list_skills,
    "use_skill": use_skill
}

SKILL_TOOL_SCHEMAS = [
    LIST_SKILLS_SCHEMA,
    USE_SKILL_SCHEMA
]


# ========== 导出函数 ==========

def get_skill_tool_schemas() -> List[Dict]:
    """获取所有Skills工具的OpenAI Function Calling schemas"""
    return SKILL_TOOL_SCHEMAS


def execute_skill_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行指定的Skills工具
    
    Args:
        tool_name: 工具名称（如 "list_skills", "use_skill"）
        arguments: 工具参数字典
    
    Returns:
        工具执行结果
    """
    if tool_name not in SKILL_TOOL_EXECUTORS:
        return {
            "success": False,
            "error": f"未知的Skills工具: {tool_name}"
        }
    
    try:
        executor = SKILL_TOOL_EXECUTORS[tool_name]
        result = executor(**arguments)
        logger.info(f"[execute_skill_tool] Tool '{tool_name}' executed: {result.get('success', False)}")
        return result
    
    except TypeError as e:
        logger.error(f"[execute_skill_tool] Invalid arguments for '{tool_name}': {e}")
        return {
            "success": False,
            "error": f"参数错误: {str(e)}"
        }
    
    except Exception as e:
        logger.error(f"[execute_skill_tool] Tool '{tool_name}' execution failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"工具执行异常: {str(e)}"
        }


def format_skill_tool_result_for_llm(tool_name: str, result: Dict[str, Any]) -> str:
    """
    将Skills工具执行结果格式化为适合LLM理解的文本
    
    Args:
        tool_name: 工具名称
        result: 工具执行结果
        
    Returns:
        格式化的结果文本
    """
    if not result.get("success"):
        return f"❌ 工具 {tool_name} 执行失败: {result.get('error', '未知错误')}"
    
    if tool_name == "list_skills":
        filtered_count = result.get("filtered_count", 0)
        total_count = result.get("total_count", 0)
        skills_list = "\n".join([
            f"  • {s['display_name']} ({s['name']}): {s['description'][:80]}..."
            for s in result.get("skills", [])[:10]  # 只显示前10个
        ])
        return f"✅ 找到 {filtered_count} 个Skills（共{total_count}个）:\n{skills_list}"
    
    elif tool_name == "use_skill":
        skill_name = result.get("skill_name", "未知")
        metadata = result.get("metadata", {})
        content_length = len(result.get("skill_content", ""))
        return (
            f"✅ 已加载Skill: {metadata.get('display_name', skill_name)}\n"
            f"分类: {metadata.get('category', 'N/A')}\n"
            f"标签: {', '.join(metadata.get('tags', []))}\n"
            f"内容长度: {content_length} 字符\n"
            f"\n完整内容:\n{result.get('skill_content', '')}"
        )
    
    else:
        return f"✅ 工具 {tool_name} 执行成功\n结果: {json.dumps(result, ensure_ascii=False, indent=2)}"


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=== Skills Tool System Test (Database Version) ===\n")
    
    # 需要Flask app context
    from src.web.app import app
    
    with app.app_context():
        # 需要先设置执行上下文
        set_execution_context(tenant_id=1)  # 使用admin的租户
        
        # 测试1: list_skills
        print("【测试1】list_skills()")
        result = list_skills()
        print(f"Success: {result['success']}")
        print(f"Total count: {result['total_count']}")
        if result['success']:
            for skill in result['skills']:
                print(f"  - {skill['display_name']} ({skill['name']}): {skill['description'][:60]}...")
        print()
        
        # 测试2: use_skill
        if result['total_count'] > 0:
            print("【测试2】use_skill()")
            first_skill_name = result['skills'][0]['name']
            skill_result = use_skill(first_skill_name)
            print(f"Success: {skill_result['success']}")
            if skill_result['success']:
                print(f"Skill: {skill_result['metadata']['display_name']}")
                print(f"Content length: {len(skill_result['skill_content'])} chars")
                print(f"First 200 chars: {skill_result['skill_content'][:200]}...")
