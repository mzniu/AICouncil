"""
Meta-Orchestrator工具函数库

提供3个核心工具供Meta-Orchestrator在规划过程中调用：
1. list_roles(): 获取所有可用角色的详细列表
2. create_role(requirement): 调用role_designer生成新角色
3. select_framework(requirement): 根据需求匹配最优框架

每个工具函数提供OpenAI Function Calling格式的schema定义。
"""

import json
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path

# 添加项目根目录到path
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.role_manager import RoleManager
from src.agents.frameworks import search_frameworks, get_framework, list_frameworks
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# ========== 工具1: list_roles ==========

def list_roles() -> Dict[str, Any]:
    """
    获取系统中所有可用角色的详细列表
    
    Returns:
        字典包含：
        - success: bool, 操作是否成功
        - roles: List[Dict], 角色列表
        - total_count: int, 角色总数
        - error: Optional[str], 错误信息（如有）
    """
    try:
        # 发送 Web 事件
        from src.agents.langchain_agents import send_web_event
        import uuid
        send_web_event("agent_action", agent_name="元调度器", role_type="meta_orchestrator", 
                      content="📚 正在查看系统现有角色库...", chunk_id=str(uuid.uuid4()))
        
        rm = RoleManager()
        roles_data = rm.list_roles()
        
        # 格式化角色信息，提取Meta-Orchestrator需要的关键字段
        formatted_roles = []
        for role in roles_data:
            formatted_roles.append({
                "name": role.name,
                "display_name": role.display_name,
                "description": role.description,
                "tags": role.tags,
                "ui": role.ui,
                "version": role.version,
                # 提取capabilities（如果在description中）
                "capabilities_summary": _extract_capabilities(role.description)
            })
        
        logger.info(f"[list_roles] 成功获取 {len(formatted_roles)} 个角色")
        
        # 发送结果事件
        send_web_event("agent_action", agent_name="元调度器", role_type="meta_orchestrator", 
                      content=f"✅ 已查看完毕，系统中共有 {len(formatted_roles)} 个可用角色", 
                      chunk_id=str(uuid.uuid4()))
        
        return {
            "success": True,
            "roles": formatted_roles,
            "total_count": len(formatted_roles),
            "message": f"成功获取 {len(formatted_roles)} 个可用角色"
        }
    
    except Exception as e:
        logger.error(f"[list_roles] 获取角色列表失败: {str(e)}")
        return {
            "success": False,
            "roles": [],
            "total_count": 0,
            "error": f"获取角色列表失败: {str(e)}"
        }


def _extract_capabilities(description: str) -> str:
    """
    从角色描述中提取能力摘要（简化版本）
    
    Args:
        description: 角色描述文本
        
    Returns:
        能力摘要字符串（最多前200字符）
    """
    # 简单提取：取描述的前200字符作为能力摘要
    if len(description) <= 200:
        return description
    return description[:200] + "..."


# Function Calling Schema for list_roles
LIST_ROLES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_roles",
        "description": "获取系统中所有可用角色的详细列表，包括角色名称、描述、标签、能力等信息。用于查看完整角色库以便进行角色匹配。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}


# ========== 工具2: create_role ==========

def create_role(requirement: str) -> Dict[str, Any]:
    """
    调用角色设计师生成新角色
    
    Args:
        requirement: 详细的角色需求描述，必须包含：
                    - 专业领域（如"国际法"）
                    - 核心能力（如"多国法律体系分析"）
                    - 工作方式（如"提供权威法律意见"）
    
    Returns:
        字典包含：
        - success: bool, 操作是否成功
        - role_name: str, 生成的角色名称（如成功）
        - role_info: Dict, 角色详细信息（如成功）
        - error: Optional[str], 错误信息（如有）
    """
    try:
        # 发送 Web 事件
        from src.agents.langchain_agents import send_web_event
        import uuid
        
        # 提取需求摘要
        requirement_summary = requirement[:80] + "..." if len(requirement) > 80 else requirement
        send_web_event("agent_action", agent_name="元调度器", role_type="meta_orchestrator", 
                      content=f"🔧 正在生成新角色...\n需求：{requirement_summary}", 
                      chunk_id=str(uuid.uuid4()))
        
        # 验证需求描述
        if not requirement or len(requirement.strip()) < 20:
            return {
                "success": False,
                "error": "需求描述过于简短，必须包含专业领域、核心能力、工作方式等详细信息（至少20字符）"
            }
        
        logger.info(f"[create_role] 开始生成角色，需求: {requirement[:100]}...")
        
        # 1. 调用 RoleDesigner Agent 生成角色设计
        from src.agents.langchain_agents import call_role_designer
        
        try:
            design_output = call_role_designer(requirement)
            logger.info(f"[create_role] RoleDesigner 返回角色: {design_output.display_name}")
            
            # 发送设计完成事件
            send_web_event("agent_action", agent_name="元调度器", role_type="meta_orchestrator", 
                          content=f"🎨 角色设计完成：{design_output.display_name} ({design_output.role_name})", 
                          chunk_id=str(uuid.uuid4()))
        except Exception as e:
            logger.error(f"[create_role] RoleDesigner 调用失败: {e}")
            return {
                "success": False,
                "error": f"角色设计失败: {str(e)}"
            }
        
        # 2. 将生成的角色保存到 RoleManager
        rm = RoleManager()
        success, error_msg = rm.create_new_role(design_output)
        
        if not success:
            logger.error(f"[create_role] 保存角色失败: {error_msg}")
            return {
                "success": False,
                "error": f"保存角色失败: {error_msg}"
            }
        
        # 3. 返回成功信息
        role_info = {
            "display_name": design_output.display_name,
            "description": design_output.role_description,
            "stages": [
                {
                    "name": stage.stage_name, 
                    "responsibilities": stage.responsibilities,
                    "thinking_style": stage.thinking_style,
                    "output_format": stage.output_format
                } 
                for stage in design_output.stages
            ],
            "ui": {
                "icon": design_output.ui.icon,
                "color": design_output.ui.color,
                "short_description": design_output.ui.short_description
            }
        }
        
        logger.info(f"[create_role] ✅ 成功创建角色: {design_output.role_name}")
        
        # 发送成功事件
        send_web_event("agent_action", agent_name="元调度器", role_type="meta_orchestrator", 
                      content=f"✅ 角色创建成功！\n名称：{design_output.display_name}\n技术名：{design_output.role_name}", 
                      chunk_id=str(uuid.uuid4()))
        
        return {
            "success": True,
            "role_name": design_output.role_name,
            "role_info": role_info,
            "message": f"成功创建角色 '{design_output.display_name}' (role_name: {design_output.role_name})"
        }
    
    except Exception as e:
        logger.error(f"[create_role] 生成角色失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": f"生成角色失败: {str(e)}"
        }


# Function Calling Schema for create_role
CREATE_ROLE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_role",
        "description": "调用角色设计师生成新角色。当现有角色库中没有匹配的角色时使用。需求描述必须详细具体，包含专业领域、核心能力和工作方式。",
        "parameters": {
            "type": "object",
            "properties": {
                "requirement": {
                    "type": "string",
                    "description": """详细的角色需求描述，必须包含：
1. 专业领域：如"国际法"、"数据科学"、"供应链管理"
2. 核心能力：如"多国法律体系分析"、"机器学习建模"、"物流优化"
3. 工作方式：如"提供权威法律意见和合规性评估"、"构建预测模型并解释结果"

示例："需要一位精通国际法的法律专家，能够从多国法律体系角度分析跨国法律冲突，在讨论中提供权威的法律意见和合规性评估，熟悉WTO规则和国际商法。"
"""
                }
            },
            "required": ["requirement"]
        }
    }
}


# ========== 工具3: select_framework ==========

def select_framework(requirement: str) -> Dict[str, Any]:
    """
    根据需求描述选择最适合的讨论框架
    
    Args:
        requirement: 问题描述或关键需求
        
    Returns:
        字典包含：
        - success: bool, 操作是否成功
        - framework_id: str, 推荐的框架ID（如成功）
        - framework_name: str, 框架显示名称（如成功）
        - match_score: float, 匹配度评分（如成功）
        - reason: str, 推荐理由（如成功）
        - alternatives: List[Dict], 备选框架列表（如有）
        - error: Optional[str], 错误信息（如有）
    """
    try:
        # 发送 Web 事件
        from src.agents.langchain_agents import send_web_event
        import uuid
        send_web_event("agent_action", agent_name="元调度器", role_type="meta_orchestrator", 
                      content="🎯 正在匹配最佳讨论框架...", chunk_id=str(uuid.uuid4()))
        
        # 验证输入
        if not requirement or len(requirement.strip()) < 5:
            return {
                "success": False,
                "error": "需求描述过于简短，至少需要5个字符"
            }
        
        logger.info(f"[select_framework] 匹配框架，需求: {requirement[:100]}...")
        
        # 使用frameworks.py的搜索功能
        matched_frameworks = search_frameworks(requirement)
        
        if not matched_frameworks:
            # 如果没有匹配，返回默认框架（罗伯特议事规则）
            default_fw = get_framework("roberts_rules")
            
            send_web_event("agent_action", agent_name="元调度器", role_type="meta_orchestrator", 
                          content=f"✅ 已选择框架：{default_fw.name}\n（通用默认框架）", 
                          chunk_id=str(uuid.uuid4()))
            
            return {
                "success": True,
                "framework_id": default_fw.id,
                "framework_name": default_fw.name,
                "match_score": 0.5,
                "reason": "未找到高度匹配的框架，推荐使用罗伯特议事规则作为通用框架",
                "alternatives": _format_frameworks(list_frameworks()[:2])
            }
        
        # 返回最佳匹配
        best_match = matched_frameworks[0]
        alternatives = matched_frameworks[1:3] if len(matched_frameworks) > 1 else []
        
        # 发送匹配成功事件
        send_web_event("agent_action", agent_name="元调度器", role_type="meta_orchestrator", 
                      content=f"✅ 已选择框架：{best_match.name}\n阶段数：{len(best_match.stages)} 个", 
                      chunk_id=str(uuid.uuid4()))
        
        return {
            "success": True,
            "framework_id": best_match.id,
            "framework_name": best_match.name,
            "match_score": 0.9,  # 简化评分，实际可以基于关键词匹配度计算
            "reason": _generate_selection_reason(best_match, requirement),
            "alternatives": _format_frameworks([fw.to_dict() for fw in alternatives]),
            "framework_details": {
                "description": best_match.description,
                "stages": [
                    {
                        "name": stage.name,
                        "description": stage.description
                    }
                    for stage in best_match.stages
                ],
                "tags": best_match.tags
            }
        }
    
    except Exception as e:
        logger.error(f"[select_framework] 选择框架失败: {str(e)}")
        return {
            "success": False,
            "error": f"选择框架失败: {str(e)}"
        }


def _generate_selection_reason(framework, requirement: str) -> str:
    """
    生成框架选择理由
    
    Args:
        framework: Framework对象
        requirement: 需求描述
        
    Returns:
        选择理由字符串
    """
    # 基于框架的keywords和tags生成理由
    matched_keywords = [kw for kw in framework.keywords if kw in requirement]
    
    if matched_keywords:
        return (
            f"该框架与需求高度匹配，匹配的关键特征包括：{', '.join(matched_keywords)}。"
            f"{framework.description.split('。')[0]}。"
        )
    else:
        return f"根据问题特征，推荐使用{framework.name}。{framework.description.split('。')[0]}。"


def _format_frameworks(frameworks_list: List[Dict]) -> List[Dict]:
    """
    格式化框架列表为简化版本
    
    Args:
        frameworks_list: 框架字典列表
        
    Returns:
        简化的框架列表
    """
    return [
        {
            "id": fw.get("id"),
            "name": fw.get("name"),
            "description": fw.get("description", "")[:100] + "..." if len(fw.get("description", "")) > 100 else fw.get("description", "")
        }
        for fw in frameworks_list
    ]


# Function Calling Schema for select_framework
SELECT_FRAMEWORK_SCHEMA = {
    "type": "function",
    "function": {
        "name": "select_framework",
        "description": "根据需求描述选择最适合的讨论框架（罗伯特议事规则、图尔敏论证法、批判性思维框架等）。返回推荐框架及理由。",
        "parameters": {
            "type": "object",
            "properties": {
                "requirement": {
                    "type": "string",
                    "description": "问题描述或关键需求，用于匹配最合适的讨论框架。可以包含问题类型（决策/论证/分析）、关键词、期望的讨论方式等。"
                }
            },
            "required": ["requirement"]
        }
    }
}


# ========== 工具注册表 ==========

# 所有可用工具的映射
AVAILABLE_TOOLS = {
    "list_roles": list_roles,
    "create_role": create_role,
    "select_framework": select_framework,
}

# 所有工具的OpenAI Function Calling schemas
TOOL_SCHEMAS = [
    LIST_ROLES_SCHEMA,
    CREATE_ROLE_SCHEMA,
    SELECT_FRAMEWORK_SCHEMA,
]


# ========== 工具调用执行器 ==========

def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行指定的工具函数
    
    Args:
        tool_name: 工具名称（list_roles/create_role/select_framework）
        arguments: 工具参数字典
        
    Returns:
        工具执行结果字典
    """
    if tool_name not in AVAILABLE_TOOLS:
        return {
            "success": False,
            "error": f"未知的工具: {tool_name}。可用工具: {list(AVAILABLE_TOOLS.keys())}"
        }
    
    try:
        tool_func = AVAILABLE_TOOLS[tool_name]
        logger.info(f"[execute_tool] 执行工具: {tool_name}, 参数: {arguments}")
        
        result = tool_func(**arguments)
        
        logger.info(f"[execute_tool] 工具 {tool_name} 执行{'成功' if result.get('success') else '失败'}")
        return result
    
    except TypeError as e:
        return {
            "success": False,
            "error": f"工具参数错误: {str(e)}"
        }
    except Exception as e:
        logger.error(f"[execute_tool] 工具 {tool_name} 执行异常: {str(e)}")
        return {
            "success": False,
            "error": f"工具执行异常: {str(e)}"
        }


def get_tool_schemas() -> List[Dict]:
    """
    获取所有工具的OpenAI Function Calling schemas
    
    Returns:
        工具schema列表
    """
    return TOOL_SCHEMAS


def format_tool_result_for_llm(tool_name: str, result: Dict[str, Any]) -> str:
    """
    将工具执行结果格式化为适合LLM理解的文本
    
    Args:
        tool_name: 工具名称
        result: 工具执行结果
        
    Returns:
        格式化的结果文本
    """
    if not result.get("success"):
        return f"❌ 工具 {tool_name} 执行失败: {result.get('error', '未知错误')}"
    
    if tool_name == "list_roles":
        roles_count = result.get("total_count", 0)
        roles_summary = "\n".join([
            f"  • {role['display_name']} ({role['name']}): {role['description'][:80]}..."
            for role in result.get("roles", [])[:10]  # 只显示前10个
        ])
        return f"✅ 获取到 {roles_count} 个可用角色:\n{roles_summary}"
    
    elif tool_name == "create_role":
        role_name = result.get("role_name", "未知")
        role_info = result.get("role_info", {})
        return f"✅ 成功生成新角色: {role_info.get('display_name', role_name)}\n描述: {role_info.get('description', '无')}"
    
    elif tool_name == "select_framework":
        fw_name = result.get("framework_name", "未知")
        reason = result.get("reason", "")
        return f"✅ 推荐框架: {fw_name}\n理由: {reason}"
    
    else:
        return f"✅ 工具 {tool_name} 执行成功\n结果: {json.dumps(result, ensure_ascii=False, indent=2)}"


# ========== 模块自检 ==========

if __name__ == "__main__":
    """测试所有工具函数"""
    print("=" * 60)
    print("Meta-Tools 自检")
    print("=" * 60)
    
    # 测试1: list_roles
    print("\n【测试1】list_roles()")
    result1 = list_roles()
    print(f"  成功: {result1['success']}")
    print(f"  角色数: {result1.get('total_count', 0)}")
    if result1['success'] and result1.get('roles'):
        print(f"  示例角色: {result1['roles'][0]['display_name']}")
    
    # 测试2: select_framework
    print("\n【测试2】select_framework('需要进行决策投票')")
    result2 = select_framework("需要进行决策投票")
    print(f"  成功: {result2['success']}")
    if result2['success']:
        print(f"  推荐框架: {result2['framework_name']}")
        print(f"  理由: {result2['reason'][:100]}...")
    
    # 测试3: create_role（预期失败，因为未实现）
    print("\n【测试3】create_role('需要一位法律专家...')")
    result3 = create_role("需要一位精通国际法的法律专家，能够分析跨国法律冲突")
    print(f"  成功: {result3['success']}")
    print(f"  消息: {result3.get('error', result3.get('message', ''))}")
    
    # 测试4: execute_tool
    print("\n【测试4】execute_tool('list_roles', {})")
    result4 = execute_tool("list_roles", {})
    print(f"  成功: {result4['success']}")
    
    # 测试5: get_tool_schemas
    print("\n【测试5】get_tool_schemas()")
    schemas = get_tool_schemas()
    print(f"  工具数量: {len(schemas)}")
    print(f"  工具名称: {[s['function']['name'] for s in schemas]}")
    
    print("\n" + "=" * 60)
    print("✅ Meta-Tools 自检完成")
    print("=" * 60)
