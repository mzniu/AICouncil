"""
Skills工具函数库 - 将Skills转换为Function Calling工具

提供Skills作为可调用工具，供Agent在思考过程中主动调用：
1. 按需加载：工具列表包含Skill元数据，完整内容仅在调用时加载
2. 自动发现：扫描skills/builtin/目录，自动注册所有Skills
3. 标准格式：遵循OpenAI Function Calling规范

架构设计：
- get_skill_tool_schemas() -> 返回所有Skill的工具schema列表
- execute_skill_tool(skill_name) -> 返回指定Skill的完整内容
- 与现有meta_tools.py架构保持一致
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from src.skills.loader import SkillLoader, Skill
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# 全局SkillLoader实例（懒加载）
_skill_loader: Optional[SkillLoader] = None
_cached_skills: Optional[List[Skill]] = None


def _get_skill_loader() -> SkillLoader:
    """获取SkillLoader单例"""
    global _skill_loader
    if _skill_loader is None:
        _skill_loader = SkillLoader()
        logger.info("[skill_tools] SkillLoader initialized")
    return _skill_loader


def _load_all_skills() -> List[Skill]:
    """加载所有Skills（带缓存）"""
    global _cached_skills
    if _cached_skills is None:
        loader = _get_skill_loader()
        _cached_skills = loader.load_all_builtin_skills()
        logger.info(f"[skill_tools] Loaded {len(_cached_skills)} skills from builtin directory")
    return _cached_skills


def refresh_skills_cache():
    """刷新Skills缓存（用于热重载）"""
    global _cached_skills
    _cached_skills = None
    logger.info("[skill_tools] Skills cache cleared")


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
            filtered_skills = [s for s in filtered_skills if s.category == filter_category]
        if filter_tags:
            filtered_skills = [
                s for s in filtered_skills 
                if any(tag in s.tags for tag in filter_tags)
            ]
        
        # 格式化为摘要信息
        skills_summary = []
        for skill in filtered_skills:
            skills_summary.append({
                "name": skill.name,
                "display_name": skill.display_name,
                "category": skill.category,
                "tags": skill.tags,
                "description": skill.description,
                "version": skill.version,
                "applicable_roles": skill.applicable_roles,
                "author": skill.author
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
        logger.error(f"[list_skills] Failed to list skills: {e}")
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
                    "description": "按分类过滤（可选），如 'business_analysis', 'decision_making', 'problem_solving'"
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
    获取指定Skill的完整内容（框架、模板、质量标准等）
    
    Args:
        skill_name: Skill的name字段（如 "cost_benefit"）
    
    Returns:
        字典包含：
        - success: bool, 操作是否成功
        - skill_name: str, Skill名称
        - skill_content: str, 完整Skill内容（Markdown格式）
        - metadata: Dict, Skill元数据
        - error: Optional[str], 错误信息（如有）
    """
    try:
        all_skills = _load_all_skills()
        
        # 查找指定Skill
        target_skill = None
        for skill in all_skills:
            if skill.name == skill_name:
                target_skill = skill
                break
        
        if target_skill is None:
            available_names = [s.name for s in all_skills]
            return {
                "success": False,
                "error": f"Skill '{skill_name}' 不存在。可用Skills: {', '.join(available_names)}"
            }
        
        # 返回完整内容
        logger.info(f"[use_skill] Returning full content for skill: {skill_name} ({len(target_skill.content)} chars)")
        
        return {
            "success": True,
            "skill_name": target_skill.name,
            "skill_content": target_skill.content,
            "metadata": {
                "display_name": target_skill.display_name,
                "version": target_skill.version,
                "category": target_skill.category,
                "tags": target_skill.tags,
                "description": target_skill.description,
                "applicable_roles": target_skill.applicable_roles,
                "requirements": target_skill.requirements,
                "author": target_skill.author,
                "created": target_skill.created,
                "updated": target_skill.updated
            },
            "message": f"已加载Skill '{target_skill.display_name}' 的完整内容"
        }
    
    except Exception as e:
        logger.error(f"[use_skill] Failed to retrieve skill '{skill_name}': {e}")
        return {
            "success": False,
            "error": f"获取Skill失败: {str(e)}"
        }


# Function Calling Schema for use_skill
USE_SKILL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "use_skill",
        "description": "获取指定专业技能(Skill)的完整内容，包括分析框架、操作步骤、模板、质量标准等。先用list_skills找到需要的Skill名称，再调用此工具获取详细内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Skill的标识符（name字段），如 'cost_benefit', 'swot_analysis', 'risk_assessment'"
                }
            },
            "required": ["skill_name"]
        }
    }
}


# ========== 工具注册与执行 ==========

# 所有Skills相关工具的schema列表
SKILL_TOOL_SCHEMAS = [
    LIST_SKILLS_SCHEMA,
    USE_SKILL_SCHEMA
]

# 工具名称到执行函数的映射
SKILL_TOOL_EXECUTORS = {
    "list_skills": list_skills,
    "use_skill": use_skill
}


def get_skill_tool_schemas() -> List[Dict]:
    """
    获取所有Skills工具的OpenAI Function Calling schemas
    
    Returns:
        工具schema列表
    """
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
        # 参数错误
        logger.error(f"[execute_skill_tool] Invalid arguments for '{tool_name}': {e}")
        return {
            "success": False,
            "error": f"参数错误: {str(e)}"
        }
    
    except Exception as e:
        # 执行异常
        logger.error(f"[execute_skill_tool] Tool '{tool_name}' execution failed: {e}")
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
    print("=== Skills Tool System Test ===\n")
    
    # 测试1: list_skills
    print("【测试1】list_skills()")
    result = list_skills()
    print(f"Success: {result['success']}")
    print(f"Total count: {result['total_count']}")
    if result['success']:
        for skill in result['skills'][:3]:
            print(f"  - {skill['display_name']} ({skill['name']}): {skill['description'][:60]}...")
    print()
    
    # 测试2: list_skills with filter
    print("【测试2】list_skills(filter_category='business_analysis')")
    result = list_skills(filter_category="business_analysis")
    print(f"Filtered count: {result['filtered_count']}")
    print()
    
    # 测试3: use_skill
    print("【测试3】use_skill('cost_benefit')")
    result = use_skill("cost_benefit")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Skill name: {result['skill_name']}")
        print(f"Content length: {len(result['skill_content'])} chars")
        print(f"Metadata: {result['metadata']['display_name']}")
    print()
    
    # 测试4: get_skill_tool_schemas
    print("【测试4】get_skill_tool_schemas()")
    schemas = get_skill_tool_schemas()
    print(f"Total schemas: {len(schemas)}")
    for schema in schemas:
        print(f"  - {schema['function']['name']}: {schema['function']['description'][:80]}...")
    print()
    
    # 测试5: execute_skill_tool
    print("【测试5】execute_skill_tool('list_skills', {})")
    result = execute_skill_tool("list_skills", {})
    print(f"Success: {result['success']}")
    print()
    
    # 测试6: format_skill_tool_result_for_llm
    print("【测试6】format_skill_tool_result_for_llm('use_skill', ...)")
    result = use_skill("cost_benefit")
    formatted = format_skill_tool_result_for_llm("use_skill", result)
    print(formatted[:500] + "..." if len(formatted) > 500 else formatted)
