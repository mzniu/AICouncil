from langchain_core.prompts import PromptTemplate
from src.agents.langchain_llm import AdapterLLM, ModelConfig
from src.agents import schemas, model_adapter
from src.utils.logger import logger
from src.utils import search_utils
from src.utils.path_manager import get_workspace_dir
from src.agents.frameworks import get_framework
from src.agents.tool_calling_agent import stream_tool_calling_agent
from pydantic import ValidationError
import json
import requests
import os
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import uuid
import traceback
from datetime import datetime

# 数据库支持（可选，如果未初始化则跳过）
try:
    from src.repositories import SessionRepository
    DB_AVAILABLE = True
except Exception as e:
    logger.warning(f"[langchain_agents] SessionRepository导入失败，数据库功能禁用: {e}")
    DB_AVAILABLE = False
    SessionRepository = None

def send_web_event(event_type: str, **kwargs):
    """发送事件到 Web 监控面板。"""
    try:
        url = "http://127.0.0.1:5000/api/update"
        payload = {"type": event_type, **kwargs}
        requests.post(url, json=payload, timeout=1)
    except Exception:
        pass

def convert_chain_to_tool_calling_format(chain, prompt_vars: Dict[str, Any], role_type: str) -> tuple:
    """将PromptTemplate chain转换为tool-calling格式
    
    Args:
        chain: PromptTemplate | LLM chain
        prompt_vars: prompt变量字典
        role_type: 角色类型（用于获取system prompt）
        
    Returns:
        (system_prompt: str, user_prompt: str, model_config: Dict)
    """
    from src.agents.role_manager import RoleManager
    
    # 从chain中提取prompt和model_config
    if hasattr(chain, 'first') and isinstance(chain.first, PromptTemplate):
        prompt_template = chain.first
    else:
        # 如果不是标准chain结构，返回默认值
        logger.warning(f"Cannot extract PromptTemplate from chain for role_type: {role_type}")
        return "You are an AI assistant.", json.dumps(prompt_vars, ensure_ascii=False), {"type": "deepseek", "model": "deepseek-reasoner"}
    
    # 从chain中提取LLM配置
    if hasattr(chain, 'last') and hasattr(chain.last, 'backend_config'):
        backend_config = chain.last.backend_config
        model_config = {
            "type": backend_config.backend,
            "model": backend_config.model
        }
    else:
        # 使用默认配置
        model_config = {"type": "deepseek", "model": "deepseek-reasoner"}
    
    # 渲染prompt
    try:
        full_prompt = prompt_template.format(**prompt_vars)
    except Exception as e:
        logger.error(f"Failed to format prompt: {e}")
        full_prompt = json.dumps(prompt_vars, ensure_ascii=False)
    
    # 分离system和user部分（简单策略：将prompt作为user prompt，system为角色说明）
    role_manager = RoleManager()
    try:
        role_config = role_manager.get_role(role_type.lower())
        system_prompt = f"你是{role_config.display_name}。\n{role_config.description}"
    except:
        system_prompt = f"You are a {role_type} agent."
    
    user_prompt = full_prompt
    
    return system_prompt, user_prompt, model_config

def clean_json_string(s: str) -> str:
    """清理字符串中的 Markdown JSON 标签，并尝试提取第一个完整的 JSON 对象。
    
    修复内容：
    1. 移除 Markdown 代码块标记（```json 和 ```）
    2. 提取完整的 JSON 对象/数组（使用括号匹配）
    3. 修复常见的格式问题（尾随逗号、未闭合的字符串等）
    """
    if not s:
        return ""
    s = s.strip()
    
    # 移除 Markdown 代码块标记
    s = s.replace('```json', '').replace('```', '').strip()
    
    # 寻找第一个 { 或 [
    start = s.find('{')
    if start == -1:
        start = s.find('[')
        if start == -1:
            return s
            
    # 使用括号匹配寻找对应的结束位置
    brace_count = 0
    in_string = False
    escape = False
    
    for i in range(start, len(s)):
        char = s[i]
        
        if char == '"' and not escape:
            in_string = not in_string
            
        if not in_string:
            if char == '{' or char == '[':
                brace_count += 1
            elif char == '}' or char == ']':
                brace_count -= 1
                if brace_count == 0:
                    extracted = s[start:i+1]
                    # 尝试修复常见格式问题
                    return _fix_json_format(extracted)
        
        if char == '\\':
            escape = not escape
        else:
            escape = False
            
    # 如果没找到匹配的括号，回退到原来的逻辑
    end = s.rfind('}')
    if end == -1:
        end = s.rfind(']')
        
    if start != -1 and end != -1 and end > start:
        extracted = s[start:end+1]
        return _fix_json_format(extracted)
    
    return s.strip()


def _fix_json_format(json_str: str) -> str:
    """修复常见的 JSON 格式问题。
    
    修复内容：
    1. 移除对象/数组末尾的尾随逗号（,}、,]）
    2. 修复未转义的引号（简单场景）
    3. 移除注释（// 和 /* */）
    """
    if not json_str:
        return json_str
    
    # 1. 移除单行注释 //
    lines = []
    for line in json_str.split('\n'):
        # 简单处理：移除 // 后的内容（不考虑字符串内的情况）
        comment_pos = line.find('//')
        if comment_pos != -1:
            # 检查是否在字符串内
            before_comment = line[:comment_pos]
            quote_count = before_comment.count('"') - before_comment.count('\\"')
            if quote_count % 2 == 0:  # 偶数个引号，说明在字符串外
                line = line[:comment_pos].rstrip()
        lines.append(line)
    json_str = '\n'.join(lines)
    
    # 2. 移除多行注释 /* */
    import re
    json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
    
    # 3. 修复尾随逗号（对象和数组）
    # 匹配 ,} 或 ,] 前可能有空白字符
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # 4. 修复多余的逗号（连续逗号）
    json_str = re.sub(r',\s*,', ',', json_str)
    
    return json_str.strip()

def _auto_fix_orchestration_plan(plan: schemas.OrchestrationPlan) -> schemas.OrchestrationPlan:
    """自动修正 OrchestrationPlan 的不完整配置（方案E核心逻辑）
    
    修正内容：
    1. 添加缺失的框架必需角色到 agent_counts
    2. 添加缺失的专业角色到 agent_counts
    3. 为缺失映射的专业角色自动生成 role_stage_mapping
    
    Args:
        plan: LLM 输出的原始规划方案
    
    Returns:
        修正后的规划方案
    """
    modified = False
    
    # 1. 获取框架定义，识别必需角色
    try:
        framework = get_framework(plan.framework_selection.framework_id)
        if not framework:
            logger.warning(f"[auto_fix] 未找到框架 {plan.framework_selection.framework_id}，跳过修正")
            return plan
    except Exception as e:
        logger.error(f"[auto_fix] 获取框架失败: {e}，跳过修正")
        return plan
    
    # 2. 提取框架中所有必需角色
    required_roles = set()
    for stage in framework.stages:
        required_roles.update(stage.roles)
    
    # 3. 识别专业角色（非框架角色）
    framework_role_names = {"planner", "auditor", "leader", "devils_advocate", "reporter"}
    professional_roles = [
        role for role in plan.role_planning.existing_roles
        if role.name not in framework_role_names
    ]
    
    # 4. 修正 agent_counts
    # 4.1 添加缺失的框架角色
    for role in required_roles:
        if role not in plan.execution_config.agent_counts:
            plan.execution_config.agent_counts[role] = 1
            logger.warning(f"[auto_fix] 🔧 自动添加缺失的框架角色: {role}")
            modified = True
    
    # 4.2 添加缺失的专业角色
    for role_match in professional_roles:
        if role_match.name not in plan.execution_config.agent_counts:
            count = role_match.assigned_count or 1
            plan.execution_config.agent_counts[role_match.name] = count
            logger.warning(f"[auto_fix] 🔧 自动添加缺失的专业角色: {role_match.name} (count={count})")
            modified = True
    
    # 5. 修正 role_stage_mapping
    if not plan.execution_config.role_stage_mapping:
        plan.execution_config.role_stage_mapping = {}
    
    for role_match in professional_roles:
        if role_match.name not in plan.execution_config.role_stage_mapping:
            # 智能分配：根据匹配度和框架结构分配合适的 stage
            suitable_stages = _find_suitable_stages(role_match, framework)
            plan.execution_config.role_stage_mapping[role_match.name] = suitable_stages
            logger.warning(f"[auto_fix] 🔧 自动为 {role_match.display_name} 分配 stage: {suitable_stages}")
            modified = True
    
    if modified:
        logger.info(f"[auto_fix] ✅ 已自动修正 OrchestrationPlan 配置")
        logger.info(f"[auto_fix]   修正后 agent_counts: {plan.execution_config.agent_counts}")
        logger.info(f"[auto_fix]   修正后 role_stage_mapping: {plan.execution_config.role_stage_mapping}")
    else:
        logger.info(f"[auto_fix] ✓ OrchestrationPlan 配置完整，无需修正")
    
    return plan

def _find_suitable_stages(role_match: schemas.ExistingRoleMatch, framework) -> List[str]:
    """为专业角色寻找合适的参与 stage
    
    策略：
    - 高匹配度角色(>=0.9)：分配到前2个讨论型stage
    - 中匹配度角色：分配到1个中间stage
    - 避免分配到纯 leader 的综合stage
    """
    discussion_stages = [
        stage.name for stage in framework.stages 
        if len(stage.roles) > 1 or "leader" not in stage.roles  # 排除纯leader的stage
    ]
    
    if not discussion_stages:
        # 兜底：返回第一个stage
        return [framework.stages[0].name] if framework.stages else []
    
    # 高匹配度：参与多个stage
    if role_match.match_score >= 0.9:
        return discussion_stages[:2] if len(discussion_stages) >= 2 else [discussion_stages[0]]
    
    # 中等匹配度：参与1个中间stage
    mid_index = len(discussion_stages) // 2
    return [discussion_stages[mid_index]]

def stream_agent_output(chain, prompt_vars, agent_name, role_type, event_type="agent_action"):
    """流式执行 Agent 并实时发送到 Web。支持联网搜索。
    返回: (full_content, search_results)
    """
    full_content = ""
    search_results = ""
    chunk_id = str(uuid.uuid4())
    
    # 先发送一个空占位符
    if event_type == "agent_action":
        send_web_event(event_type, agent_name=agent_name, role_type=role_type, content="", chunk_id=chunk_id)
    
    # 第一轮执行
    for chunk in chain.stream(prompt_vars):
        # 处理可能存在的推理内容 (DeepSeek R1)
        reasoning = ""
        content = ""
        
        if hasattr(chunk, "generation_info") and chunk.generation_info:
            reasoning = chunk.generation_info.get("reasoning", "")
        
        if hasattr(chunk, "text"):
            content = chunk.text
        else:
            content = str(chunk)

        if reasoning:
            send_web_event(event_type, agent_name=agent_name, role_type=role_type, reasoning=reasoning, chunk_id=chunk_id)
        
        if content:
            full_content += content
            # logger.debug(f"[{agent_name}] Accumulated content length: {len(full_content)}")
            if event_type == "final_report":
                # 实时清理并发送到 Web，避免显示 ```html 标签
                display_html = full_content.strip()
                if display_html.startswith("```html"):
                    display_html = display_html[7:]
                elif display_html.startswith("```"):
                    display_html = display_html[3:]
                if display_html.endswith("```"):
                    display_html = display_html[:-3]
                send_web_event(event_type, content=display_html.strip())
            else:
                send_web_event(event_type, agent_name=agent_name, role_type=role_type, content=content, chunk_id=chunk_id)
            
            # 核心改进：如果检测到搜索指令已结束（出现 ]），立即停止当前流，防止后续 JSON 泄露
            if "[SEARCH:" in full_content and "]" in full_content[full_content.find("[SEARCH:"): ]:
                logger.info(f"Detected search tag in {agent_name} output, stopping stream to perform search.")
                break
    
    logger.info(f"[{agent_name}] First pass finished. Content length: {len(full_content)}")
    
    # 检查是否需要搜索
    import re
    queries = re.findall(r'\[SEARCH:\s*(.*?)\]', full_content)
    
    if queries:
        search_query_display = "、".join([q.strip() for q in queries])
        logger.info(f"Detected search queries for {agent_name}: {search_query_display}")
        
        # 1. 立即发送“正在搜索”状态到 Web
        if event_type == "agent_action":
            send_web_event(event_type, agent_name=agent_name, role_type=role_type, 
                           content=f"\n\n### SEARCH PROGRESS\n\n> 🔍 **系统正在搜索**: {search_query_display}...\n\n", chunk_id=chunk_id)
        
        # 2. 执行实际搜索
        search_results = search_utils.search_if_needed(full_content)
        
        if search_results:
            logger.info(f"Search results obtained for {agent_name}: {search_results[:200]}...")
            send_web_event("log", content=f"🔍 [{agent_name}] 搜索结果: {search_results[:500]}...")
            
            # 3. 发送搜索结果汇总和完成提示
            if event_type == "agent_action":
                combined_content = (
                    f"\n\n### SEARCH PROGRESS\n\n"
                    f"**🌐 联网搜索已完成**\n\n"
                    f"{search_results}\n\n"
                    f"> ✅ **正在根据搜索结果重新生成最终方案...**\n\n"
                )
                send_web_event(event_type, agent_name=agent_name, role_type=role_type, 
                               content=combined_content, chunk_id=chunk_id)
            
            # 4. 将搜索结果加入 prompt 并重新执行
            new_prompt_vars = prompt_vars.copy()
            # 寻找合适的 key 来注入搜索结果
            target_key = None
            for key in ["issue", "inputs", "final_data"]:
                if key in new_prompt_vars:
                    target_key = key
                    break
            
            if target_key:
                new_prompt_vars[target_key] = (
                    f"{new_prompt_vars[target_key]}\n\n"
                    f"【联网搜索结果】:\n{search_results}\n\n"
                    f"**重要指令**：你已经获得了一次联网搜索的结果。请根据以上信息直接输出最终的 JSON 结果。**严禁再次输出 [SEARCH:] 标签**，否则你的输出将被视为无效。"
                )
            
            # 第二轮执行（最终输出）
            full_content = "" # 重置内容
            for chunk in chain.stream(new_prompt_vars):
                reasoning = ""
                content = ""
                if hasattr(chunk, "generation_info") and chunk.generation_info:
                    reasoning = chunk.generation_info.get("reasoning", "")
                
                if hasattr(chunk, "text"):
                    content = chunk.text
                else:
                    content = str(chunk)

                if reasoning:
                    send_web_event(event_type, agent_name=agent_name, role_type=role_type, reasoning=reasoning, chunk_id=chunk_id)
                if content:
                    full_content += content
                    if event_type == "final_report":
                        display_html = full_content.strip()
                        if display_html.startswith("```html"): display_html = display_html[7:]
                        elif display_html.startswith("```"): display_html = display_html[3:]
                        if display_html.endswith("```"): display_html = display_html[:-3]
                        send_web_event(event_type, content=display_html.strip())
                    else:
                        send_web_event(event_type, agent_name=agent_name, role_type=role_type, content=content, chunk_id=chunk_id)
                    
                    # 第二轮也增加 break 逻辑，防止 agent 强行再次搜索导致死循环
                    if "[SEARCH:" in full_content and "]" in full_content[full_content.find("[SEARCH:"): ]:
                        logger.warning(f"Agent {agent_name} tried to search AGAIN in the second run. Stopping.")
                        break
            
            logger.info(f"[{agent_name}] Second pass finished. Content length: {len(full_content)}")
                
    return full_content, search_results

def make_generic_role_chain(role_name: str, stage_name: str, model_config: Dict[str, Any]):
    """通用的角色chain创建函数，支持任意自定义角色
    
    Args:
        role_name: 角色名称（如 "international_law_expert"）
        stage_name: Stage名称（如 "analysis"）
        model_config: 模型配置
        
    Returns:
        LangChain chain对象
    """
    from src.agents.role_manager import RoleManager
    
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    role_manager = RoleManager()
    
    # 从RoleManager加载角色配置
    role_config = role_manager.get_role(role_name)
    if not role_config:
        raise ValueError(f"未找到角色: {role_name}")
    
    # 获取stage配置（如果没有指定stage，使用第一个stage）
    if stage_name not in role_config.stages:
        available_stages = list(role_config.stages.keys())
        if not available_stages:
            raise ValueError(f"角色 {role_name} 没有任何stage配置")
        stage_name = available_stages[0]
        logger.warning(f"[make_generic_role_chain] 角色 {role_name} 没有 stage '{stage_name}'，使用第一个stage: {available_stages[0]}")
    
    # 加载prompt和输入变量
    prompt_text = role_manager.load_prompt(role_name, stage_name)
    input_vars = role_config.stages[stage_name].input_vars
    
    prompt = PromptTemplate(template=prompt_text, input_variables=input_vars)
    return prompt | llm


def make_planner_chain(model_config: Dict[str, Any], tenant_id: Optional[int] = None):
    """创建策论家链（使用RoleManager + Skills注入）
    
    Args:
        model_config: 模型配置
        tenant_id: 租户ID（用于加载订阅的Skills）
    """
    from src.agents.role_manager import RoleManager
    from src.skills.loader_v2 import SkillLoaderV2
    
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    role_manager = RoleManager()
    
    # 从RoleManager加载prompt和配置
    stage_name = "proposal"  # planner的stage名称
    prompt_text = role_manager.load_prompt("planner", stage_name)
    role_config = role_manager.get_role("planner")
    input_vars = role_config.stages[stage_name].input_vars
    
    # 加载并注入Skills
    try:
        skill_loader = SkillLoaderV2()
        # 加载策论家适用的技能（包含订阅的builtin + custom skills）
        skills = skill_loader.get_skills_by_role('策论家', tenant_id=tenant_id)
        
        if skills:
            logger.info(f"[planner_chain] Loaded {len(skills)} skills for tenant {tenant_id}")
            # 格式化技能为prompt（不包含metadata以节省token）
            skills_text = skill_loader.format_all_skills_for_prompt(skills, include_metadata=False)
            # 在prompt末尾注入技能库
            prompt_text = prompt_text + "\n\n" + skills_text
        else:
            logger.info(f"[planner_chain] No skills loaded for tenant {tenant_id}")
    except Exception as e:
        logger.warning(f"[planner_chain] Failed to load skills: {e}")
    
    prompt = PromptTemplate(template=prompt_text, input_variables=input_vars)
    return prompt | llm



def make_auditor_chain(model_config: Dict[str, Any], tenant_id: Optional[int] = None):
    """创建监察官链（使用RoleManager + Skills注入）
    
    Args:
        model_config: 模型配置
        tenant_id: 租户ID（用于加载订阅的Skills）
    """
    from src.agents.role_manager import RoleManager
    from src.skills.loader_v2 import SkillLoaderV2
    
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    role_manager = RoleManager()
    
    # 从RoleManager加载prompt和配置
    stage_name = "review"  # auditor的stage名称
    prompt_text = role_manager.load_prompt("auditor", stage_name)
    role_config = role_manager.get_role("auditor")
    input_vars = role_config.stages[stage_name].input_vars
    
    # 加载并注入Skills
    try:
        skill_loader = SkillLoaderV2()
        # 加载监察官适用的技能（包含订阅的builtin + custom skills）
        skills = skill_loader.get_skills_by_role('监察官', tenant_id=tenant_id)
        
        if skills:
            logger.info(f"[auditor_chain] Loaded {len(skills)} skills for tenant {tenant_id}")
            # 格式化技能为prompt（不包含metadata以节省token）
            skills_text = skill_loader.format_all_skills_for_prompt(skills, include_metadata=False)
            # 在prompt末尾注入技能库
            prompt_text = prompt_text + "\n\n" + skills_text
        else:
            logger.info(f"[auditor_chain] No skills loaded for tenant {tenant_id}")
    except Exception as e:
        logger.warning(f"[auditor_chain] Failed to load skills: {e}")
    
    prompt = PromptTemplate(template=prompt_text, input_variables=input_vars)
    return prompt | llm


def make_leader_chain(model_config: Dict[str, Any], is_final_round: bool = False):
    """创建议长链（使用RoleManager）
    
    Args:
        model_config: 模型配置
        is_final_round: 是否为最后一轮（影响prompt策略）
    """
    from src.agents.role_manager import RoleManager
    
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    role_manager = RoleManager()
    
    # 根据轮次选择stage
    stage = "summary" if is_final_round else "decomposition"
    
    # 从RoleManager加载prompt和配置
    prompt_text = role_manager.load_prompt("leader", stage)
    role_config = role_manager.get_role("leader")
    input_vars = role_config.stages[stage].input_vars
    
    prompt = PromptTemplate(template=prompt_text, input_variables=input_vars)
    return prompt | llm


# 保留原来的函数签名作为过渡（向后兼容，已废弃）
def make_devils_advocate_chain(model_config: Dict[str, Any], stage: str = "summary"):
    """创建Devil's Advocate链（使用RoleManager）
    
    Args:
        model_config: 模型配置
        stage: 质疑阶段 ("decomposition" | "summary")
    """
    from src.agents.role_manager import RoleManager
    
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    role_manager = RoleManager()
    
    # 从RoleManager加载对应stage的prompt
    prompt_text = role_manager.load_prompt("devils_advocate", stage)
    role_config = role_manager.get_role("devils_advocate")
    input_vars = role_config.stages[stage].input_vars
    
    prompt = PromptTemplate(template=prompt_text, input_variables=input_vars)
    return prompt | llm


def make_report_auditor_chain(model_config: Dict[str, Any]):
    """创建报告审核官链（使用RoleManager）"""
    from src.agents.role_manager import RoleManager
    
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    role_manager = RoleManager()
    
    # 从RoleManager加载prompt和配置
    stage_name = "revision"  # report_auditor的stage名称
    prompt_text = role_manager.load_prompt("report_auditor", stage_name)
    role_config = role_manager.get_role("report_auditor")
    input_vars = role_config.stages[stage_name].input_vars
    
    prompt = PromptTemplate(template=prompt_text, input_variables=input_vars)
    return prompt | llm


def make_reporter_chain(model_config: Dict[str, Any]):
    """创建记录员链（使用RoleManager）"""
    from src.agents.role_manager import RoleManager
    
    role_manager = RoleManager()
    role_config = role_manager.get_role("reporter")
    
    # 如果 model_config 没有明确指定 model，使用 reporter 的 default_model
    if not model_config or not model_config.get('model'):
        model_config = model_config or {}
        model_config['model'] = role_config.default_model
        model_config['type'] = model_config.get('type', 'deepseek')  # 默认使用 deepseek backend
    
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    
    # 从RoleManager加载prompt和配置
    prompt_text = role_manager.load_prompt("reporter", "generate")
    input_vars = role_config.stages["generate"].input_vars
    
    prompt = PromptTemplate(template=prompt_text, input_variables=input_vars)
    return prompt | llm


# ========== 参考资料整理功能 ==========


def _extract_url_from_reference(ref_text: str) -> Optional[str]:
    """从搜索结果文本中提取URL"""
    import re
    # 匹配markdown链接格式 [title](url)
    match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', ref_text)
    if match:
        return match.group(2)
    # 匹配纯URL
    match = re.search(r'https?://[^\s\)]+', ref_text)
    if match:
        return match.group(0)
    return None


def _extract_title_from_reference(ref_text: str) -> Optional[str]:
    """从搜索结果文本中提取标题"""
    import re
    # 匹配markdown链接格式 [title](url)
    match = re.search(r'\[([^\]]+)\]\(', ref_text)
    if match:
        return match.group(1)
    # 匹配表格格式中的标题
    match = re.search(r'\| \d+ \| \[([^\]]+)\]', ref_text)
    if match:
        return match.group(1)
    return None


def _title_similarity(title1: str, title2: str) -> float:
    """计算两个标题的相似度（简单的字符重叠率）"""
    if not title1 or not title2:
        return 0.0
    set1 = set(title1)
    set2 = set(title2)
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def deduplicate_search_references(raw_references: List[str]) -> tuple[List[str], dict]:
    """算法层面去重搜索结果
    
    去重策略：
    1. URL完全相同的去重
    2. 标题相似度>80%的去重
    
    注意：不做内容过滤（如域名/标题黑名单），由后续LLM相关性筛选处理
    
    Returns:
        (去重后的引用列表, 统计信息dict)
    """
    stats = {
        "original_count": len(raw_references),
        "url_duplicates": 0,
        "title_duplicates": 0,
    }
    
    seen_urls = set()
    seen_titles = []
    deduplicated = []
    
    for ref in raw_references:
        url = _extract_url_from_reference(ref)
        title = _extract_title_from_reference(ref)
        
        # 1. URL去重
        if url and url in seen_urls:
            stats["url_duplicates"] += 1
            continue
        
        # 2. 标题相似度去重
        is_similar = False
        for existing_title in seen_titles:
            if _title_similarity(title, existing_title) > 0.8:
                is_similar = True
                stats["title_duplicates"] += 1
                break
        
        if is_similar:
            continue
        
        # 通过所有检查，保留
        if url:
            seen_urls.add(url)
        if title:
            seen_titles.append(title)
        deduplicated.append(ref)
    
    stats["after_dedup_count"] = len(deduplicated)
    logger.info(f"[dedup] 去重统计: 原始{stats['original_count']} -> 去重后{stats['after_dedup_count']} "
                f"(URL重复:{stats['url_duplicates']}, 标题相似:{stats['title_duplicates']})")
    
    return deduplicated, stats


def make_reference_refiner_chain(model_config: Dict[str, Any]):
    """创建参考资料整理官链"""
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    
    prompt_text = """你是一位专业的参考资料整理官，负责从搜索结果中筛选与议题相关的高质量引用。

## 原始议题
{topic}

## 待筛选的搜索结果（已经过算法去重）
{deduplicated_references}

## 你的任务

1. **相关性过滤**：只保留与议题直接相关的结果，排除：
   - 与议题无关的内容（如日历、节假日、纪念币等）
   - 过于泛泛的内容（如百度百科年份页）
   - 重复/冗余的信息

2. **精简格式**：将每条保留的引用精简为：
   - title: 标题
   - url: 链接
   - summary: 一句话要点（15-50字，提炼核心信息）
   - relevance: 与议题的相关性说明

3. **数量控制**：最多保留15条最相关的引用

## 输出格式（严格JSON）
```json
{{
    "topic": "原始议题",
    "original_count": 去重前数量,
    "after_dedup_count": 去重后数量,
    "refined_references": [
        {{
            "title": "文章标题",
            "url": "https://...",
            "summary": "一句话要点",
            "relevance": "相关性说明"
        }}
    ],
    "filtering_notes": "过滤说明，如：排除了X条日历相关、Y条政策公告等"
}}
```

**重要**：只输出JSON，不要任何其他文字。"""
    
    prompt = PromptTemplate(
        template=prompt_text,
        input_variables=["topic", "deduplicated_references"]
    )
    return prompt | llm


def refine_search_references(
    raw_references: List[str],
    topic: str,
    model_config: Dict[str, Any],
    workspace_path: str
) -> tuple[str, schemas.ReferenceRefinerOutput]:
    """执行完整的参考资料整理流程
    
    流程：
    1. 算法去重（URL、标题相似度、黑名单）
    2. LLM相关性过滤+精简
    3. 保存结果到refined_references.json
    
    Returns:
        (精简后的文本用于报告生成, 结构化输出)
    """
    # 发送开始事件
    send_web_event("agent_action", 
                   agent_name="参考资料整理官", 
                   role_type="reference_refiner",
                   content=f"📚 开始整理参考资料...\n原始搜索结果: {len(raw_references)}条",
                   chunk_id=str(uuid.uuid4()))
    
    # 1. 算法去重
    deduplicated, stats = deduplicate_search_references(raw_references)
    
    send_web_event("agent_action",
                   agent_name="参考资料整理官",
                   role_type="reference_refiner", 
                   content=f"✅ 算法去重完成\n├─ URL重复: {stats['url_duplicates']}条\n├─ 标题相似: {stats['title_duplicates']}条\n└─ 保留: {stats['after_dedup_count']}条",
                   chunk_id=str(uuid.uuid4()))
    
    # 如果去重后为空，直接返回
    if not deduplicated:
        empty_output = schemas.ReferenceRefinerOutput(
            topic=topic,
            original_count=stats["original_count"],
            after_dedup_count=0,
            refined_references=[],
            filtering_notes="所有搜索结果均被算法过滤（无关内容）"
        )
        send_web_event("agent_action",
                       agent_name="参考资料整理官",
                       role_type="reference_refiner",
                       content="⚠️ 算法过滤后无有效结果",
                       chunk_id=str(uuid.uuid4()))
        return "无有效的联网搜索参考资料。", empty_output
    
    # 2. LLM相关性过滤+精简
    send_web_event("agent_action",
                   agent_name="参考资料整理官",
                   role_type="reference_refiner",
                   content="🔍 正在进行相关性筛选...",
                   chunk_id=str(uuid.uuid4()))
    
    refiner_chain = make_reference_refiner_chain(model_config)
    
    # 限制输入长度，避免超token
    deduplicated_text = "\n\n".join(deduplicated)
    if len(deduplicated_text) > 30000:
        deduplicated_text = deduplicated_text[:30000] + "\n\n...(内容过长已截断)"
    
    try:
        raw_output, _ = stream_agent_output(
            refiner_chain,
            {
                "topic": topic,
                "deduplicated_references": deduplicated_text
            },
            "参考资料整理官",
            "reference_refiner"
        )
        
        # 解析JSON
        cleaned = clean_json_string(raw_output)
        parsed = json.loads(cleaned)
        
        # 更新统计数据
        parsed["original_count"] = stats["original_count"]
        parsed["after_dedup_count"] = stats["after_dedup_count"]
        
        output = schemas.ReferenceRefinerOutput(**parsed)
        
    except Exception as e:
        logger.error(f"[refine] LLM精简失败: {e}")
        # 降级：直接使用去重后的结果（截断）
        output = schemas.ReferenceRefinerOutput(
            topic=topic,
            original_count=stats["original_count"],
            after_dedup_count=stats["after_dedup_count"],
            refined_references=[],
            filtering_notes=f"LLM精简失败，使用原始去重结果: {str(e)[:100]}"
        )
        # 构造简单的文本
        fallback_text = "\n\n".join(deduplicated[:10])
        if len(fallback_text) > 8000:
            fallback_text = fallback_text[:8000] + "\n\n...(内容过长已截断)"
        
        send_web_event("agent_action",
                       agent_name="参考资料整理官",
                       role_type="reference_refiner",
                       content=f"⚠️ LLM精简失败，使用降级方案\n保留前10条去重结果",
                       chunk_id=str(uuid.uuid4()))
        return fallback_text, output
    
    # 3. 生成精简文本并返回
    refined_text_parts = []
    for i, ref in enumerate(output.refined_references, 1):
        refined_text_parts.append(f"{i}. [{ref.title}]({ref.url})\n   要点: {ref.summary}")
    
    refined_text = "\n\n".join(refined_text_parts) if refined_text_parts else "无相关联网搜索参考资料。"
    
    logger.info(f"[refine] 完成引用精简：原始{output.original_count}条 -> 去重{output.after_dedup_count}条 -> 精简{len(output.refined_references)}条")
    logger.info(f"[refine] 完成引用精简：原始{output.original_count}条 -> 去重{output.after_dedup_count}条 -> 精简{len(output.refined_references)}条")
    
    # 发送完成事件
    send_web_event("agent_action",
                   agent_name="参考资料整理官",
                   role_type="reference_refiner",
                   content=f"✅ 参考资料整理完成\n├─ 原始结果: {output.original_count}条\n├─ 算法去重后: {output.after_dedup_count}条\n├─ 相关性筛选后: {len(output.refined_references)}条\n└─ {output.filtering_notes}",
                   chunk_id=str(uuid.uuid4()))
    
    return refined_text, output


def run_full_cycle(issue_text: str, model_config: Dict[str, Any] = None, max_rounds: int = 3, num_planners: int = 2, num_auditors: int = 2, agent_configs: Dict[str, Any] = None, user_id: Optional[int] = None, tenant_id: Optional[int] = None) -> Dict[str, Any]:
    """Run a multi-round LangChain-driven cycle: leader decomposes, planners generate plans, auditors review, leader summarizes.
    
    Args:
        issue_text: 议题内容
        model_config: 模型配置
        max_rounds: 最大轮次
        num_planners: 策论家数量
        num_auditors: 监察官数量
        agent_configs: Agent配置覆盖
        user_id: 用户ID（用于数据库存储，可选）
        tenant_id: 租户ID（用于多租户隔离，可选）
        
    Returns:
        dict: 包含decomposition, history, final, report_html的结果字典
    """
    # 1. 初始化 Session 和 Workspace
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
    workspace_path = get_workspace_dir() / session_id
    workspace_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"[cycle] Session ID: {session_id}, Workspace: {workspace_path}, User: {user_id or 'anonymous'}, Tenant: {tenant_id or 'N/A'}")
    
    # 2. 创建数据库会话记录（需要Flask应用上下文）
    if DB_AVAILABLE and user_id and SessionRepository:
        try:
            from src.web.app import app
            
            logger.info(f"[cycle] 准备创建数据库会话，user_id={user_id}, tenant_id={tenant_id}, session_id={session_id}")
            
            config_data = {
                "backend": model_config.get("type") if model_config else None,
                "model": model_config.get("model") if model_config else None,
                "rounds": max_rounds,
                "planners": num_planners,
                "auditors": num_auditors,
                "agent_configs": agent_configs
            }
            
            # 需要应用上下文进行数据库操作
            with app.app_context():
                db_session = SessionRepository.create_session(
                    user_id=user_id,
                    session_id=session_id,
                    issue=issue_text,
                    config=config_data,
                    tenant_id=tenant_id  # 传递tenant_id
                )
                if db_session:
                    logger.info(f"[cycle] ✅ 数据库会话创建成功: {session_id}")
                else:
                    logger.warning(f"[cycle] ⚠️ 数据库会话创建返回None: {session_id}")
        except Exception as e:
            logger.error(f"[cycle] ❌ 数据库操作失败: {e}")
            logger.error(traceback.format_exc())

    # 重置 Web 面板
    try:
        requests.post("http://127.0.0.1:5000/api/reset", timeout=1)
    except:
        pass

    # 发送启动事件
    send_web_event("system_start", message=f"议事厅启动 (ID: {session_id})：正在准备元老席位...", issue=issue_text, session_id=session_id)

    model_config = model_config or {"type": model_adapter.config.MODEL_BACKEND, "model": model_adapter.config.MODEL_NAME}
    agent_configs = agent_configs or {}
    
    max_retries = 3
    
    # 初始化各角色的 Chain
    leader_cfg = agent_configs.get("leader") or model_config
    # 初始拆解阶段明确使用中间轮次行为（因为不是最后一轮）
    leader_chain = make_leader_chain(leader_cfg, is_final_round=False)
    
    devils_advocate_cfg = agent_configs.get("devils_advocate") or model_config
    devils_advocate_decomposition_chain = make_devils_advocate_chain(devils_advocate_cfg, stage="decomposition")
    devils_advocate_summary_chain = make_devils_advocate_chain(devils_advocate_cfg, stage="summary")
    
    reporter_cfg = agent_configs.get("reporter") or model_config
    reporter_chain = make_reporter_chain(reporter_cfg)

    # 策论家和监察官的 Chain 列表
    planner_chains = []
    for i in range(num_planners):
        # 优先从 agent_configs 获取 planner_i，否则使用全局 model_config
        p_cfg = agent_configs.get(f"planner_{i}") or model_config
        planner_chains.append(make_planner_chain(p_cfg, tenant_id=tenant_id))
        
    auditor_chains = []
    for i in range(num_auditors):
        # 优先从 agent_configs 获取 auditor_i，否则使用全局 model_config
        a_cfg = agent_configs.get(f"auditor_{i}") or model_config
        auditor_chains.append(make_auditor_chain(a_cfg, tenant_id=tenant_id))

    # 1. Leader initial decomposition
    logger.info("[cycle] 议长正在进行初始议题拆解...")
    decomposition = {
        "core_goal": "解析失败",
        "key_questions": [],
        "boundaries": "未知",
    }
    all_search_references = []
    for attempt in range(max_retries):
        try:
            logger.info(f"[cycle] 议长正在调用模型进行拆解 (尝试 {attempt + 1}/{max_retries})...")
            current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 使用tool-calling agent
            prompt_vars = {"inputs": issue_text, "current_time": current_time_str}
            system_prompt, user_prompt, model_config = convert_chain_to_tool_calling_format(leader_chain, prompt_vars, "leader")
            out, tool_calls = stream_tool_calling_agent(
                role_type="leader",
                agent_name="议长",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_config=model_config,
                event_type="agent_action"
            )
            
            # 记录工具调用（替代search_res）
            if tool_calls:
                search_results = [tc for tc in tool_calls if tc['tool_name'] == 'web_search']
                if search_results:
                    all_search_references.append("\n".join([sr['formatted_result'] for sr in search_results]))
            
            # 记录原始输出到日志（调试用）
            logger.debug(f"[cycle] 议长原始输出 (尝试 {attempt + 1}): {out[:500]}...")
            
            cleaned = clean_json_string(out)
            if not cleaned:
                logger.error(f"[cycle] 议长输出为空或不包含 JSON。原始输出长度: {len(out)}")
                logger.debug(f"[cycle] 完整原始输出: {out}")
                raise ValueError("议长未返回有效的 JSON 拆解结果")
            
            # 记录清理后的JSON到日志（调试用）
            logger.debug(f"[cycle] 清理后JSON (尝试 {attempt + 1}): {cleaned[:500]}...")
                
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError as json_err:
                logger.error(f"[cycle] JSON解析失败: {json_err}")
                logger.debug(f"[cycle] 完整清理后JSON: {cleaned}")
                raise
                
            summary = schemas.LeaderSummary(**parsed)
            decomposition = summary.decomposition.model_dump()
            
            # 保存到数据库（需要应用上下文）
            if DB_AVAILABLE and user_id and SessionRepository:
                try:
                    from src.web.app import app
                    with app.app_context():
                        SessionRepository.update_decomposition(session_id, decomposition)
                        logger.info(f"[cycle] decomposition已保存到数据库")
                except Exception as e:
                    logger.error(f"[cycle] 数据库保存失败: {e}")
            
            logger.info(f"[cycle] 议长拆解成功 (尝试 {attempt + 1})")
            break
        except Exception as e:
            logger.warning(f"[cycle] 议长拆解尝试 {attempt + 1} 失败: {e}")
            if attempt < max_retries - 1:
                logger.info(f"[cycle] 将进行第 {attempt + 2} 次尝试...")
            else:
                logger.error(f"[cycle] 议长拆解失败，已达最大重试次数 ({max_retries})")
                logger.error(traceback.format_exc())

    # Devil's Advocate 质疑初始拆解
    logger.info("[cycle] 质疑官正在验证问题拆解...")
    decomposition_da_result = None
    for attempt in range(max_retries):
        logger.info(f"[cycle] 质疑官正在调用模型进行拆解质疑 (尝试 {attempt + 1}/{max_retries})...")
        try:
            current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            da_prompt_vars = {
                "issue": issue_text,
                "core_goal": decomposition.get("core_goal", ""),
                "key_questions": json.dumps(decomposition.get("key_questions", []), ensure_ascii=False),
                "boundaries": decomposition.get("boundaries", ""),
                "current_time": current_time_str
            }
            
            out, search_res = stream_agent_output(
                devils_advocate_decomposition_chain, 
                da_prompt_vars, 
                "质疑官", 
                "devils_advocate", 
                event_type="agent_action"
            )
            if search_res:
                all_search_references.append(search_res)
            
            cleaned = clean_json_string(out)
            if not cleaned:
                raise ValueError("质疑官输出为空或不包含 JSON")
                
            parsed = json.loads(cleaned)
            da_obj = schemas.DevilsAdvocateSchema(**parsed)
            decomposition_da_result = da_obj.model_dump()
            logger.info(f"[cycle] 质疑官验证拆解成功 (尝试 {attempt + 1})")
            break
        except Exception as e:
            logger.warning(f"[cycle] 质疑官验证拆解尝试 {attempt + 1} 失败: {e}")
            logger.error(traceback.format_exc())
            if attempt == max_retries - 1:
                decomposition_da_result = {
                    "round": 0,
                    "stage": "decomposition",
                    "decomposition_challenge": {
                        "missing_dimensions": [],
                        "hidden_assumptions": [],
                        "alternative_frameworks": [],
                        "extreme_scenario_issues": []
                    },
                    "overall_assessment": f"验证失败: {str(e)}",
                    "critical_issues": ["质疑官执行异常"],
                    "recommendations": ["请检查模型配置和输出格式"]
                }

    # 议长根据质疑进行修正（如果存在严重问题）
    if decomposition_da_result and (decomposition_da_result.get("critical_issues") or "严重" in decomposition_da_result.get("overall_assessment", "")):
        logger.info("[cycle] 议长正在根据质疑官的反馈修正问题拆解...")
        send_web_event("agent_action", agent_name="议长", role_type="Leader", content="正在根据质疑官的反馈修正问题拆解...", chunk_id=str(uuid.uuid4()))
        
        revision_inputs = {
            "issue": issue_text,
            "previous_decomposition": decomposition,
            "devils_advocate_feedback": decomposition_da_result
        }
        
        for attempt in range(max_retries):
            try:
                current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                out, search_res = stream_agent_output(leader_chain, {"inputs": json.dumps(revision_inputs, ensure_ascii=False), "current_time": current_time_str}, "议长", "Leader")
                
                cleaned = clean_json_string(out)
                if not cleaned:
                    raise ValueError("议长修正输出为空或不包含 JSON")
                    
                parsed = json.loads(cleaned)
                summary = schemas.LeaderSummary(**parsed)
                decomposition = summary.decomposition.model_dump()
                
                logger.info(f"[cycle] 议长修正拆解成功 (尝试 {attempt + 1})")
                break
            except Exception as e:
                logger.warning(f"[cycle] 议长修正拆解尝试 {attempt + 1} 失败: {e}")
                logger.error(traceback.format_exc())

    history = []
    current_instructions = f"议题: {issue_text}\n核心目标: {decomposition['core_goal']}\n关键问题: {decomposition['key_questions']}"
    
    last_plans_map = {i: None for i in range(1, num_planners + 1)}
    last_audits = []
    user_interventions = []
    last_da_result = decomposition_da_result  # 初始质疑为拆解阶段的质疑

    for r in range(1, max_rounds + 1):
        logger.info(f"=== 开始第 {r} 轮讨论 ===")
        send_web_event("round_start", round=r)
        
        # 检查用户干预
        intervention_file = os.path.join(workspace_path, "user_intervention.json")
        if os.path.exists(intervention_file):
            try:
                with open(intervention_file, "r", encoding="utf-8") as f:
                    intervention_data = json.load(f)
                    user_msg = intervention_data.get("content")
                    if user_msg:
                        logger.info(f"[round {r}] 收到用户干预: {user_msg}")
                        # 将干预加入指令
                        current_instructions += f"\n\n[用户干预指令]: {user_msg}"
                        user_interventions.append(user_msg)
                        # 记录到 history 中
                        history.append({
                            "round": r,
                            "type": "user_intervention",
                            "content": user_msg
                        })
                os.remove(intervention_file)
            except Exception as e:
                logger.error(f"处理用户干预失败: {e}")

        def execute_planner(i):
            logger.info(f"[round {r}] 策论家 {i} 正在生成/迭代方案...")
            feedback = "无（首轮或上轮无反馈）"
            prev_plan = last_plans_map[i]
            if prev_plan and last_audits:
                relevant_feedbacks = []
                target_id = prev_plan.get("id")
                for audit in last_audits:
                    if isinstance(audit, dict) and "reviews" in audit:
                        for review in audit["reviews"]:
                            if review.get("plan_id") == target_id:
                                relevant_feedbacks.append(f"评级: {review.get('rating')}\n质疑: {review.get('issues')}\n建议: {review.get('suggestions')}")
                if relevant_feedbacks:
                    feedback = "\n---\n".join(relevant_feedbacks)

            prompt_vars = {
                "planner_id": f"策论家 {i}-方案 1",
                "issue": current_instructions,
                "previous_plan": json.dumps(prev_plan, ensure_ascii=False) if prev_plan else "无",
                "feedback": feedback
            }
            
            for attempt in range(max_retries):
                try:
                    # 使用tool-calling agent
                    system_prompt, user_prompt, model_config = convert_chain_to_tool_calling_format(planner_chains[i-1], prompt_vars, "planner")
                    out, tool_calls = stream_tool_calling_agent(
                        role_type="planner",
                        agent_name=f"策论家 {i}",
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model_config=model_config,
                        event_type="agent_action"
                    )
                    
                    # 记录工具调用
                    if tool_calls:
                        search_results = [tc for tc in tool_calls if tc['tool_name'] == 'web_search']
                        if search_results:
                            all_search_references.append("\n".join([sr['formatted_result'] for sr in search_results]))
                    
                    cleaned = clean_json_string(out)
                    if not cleaned:
                        raise ValueError("策论家输出为空或不包含 JSON")
                        
                    parsed = json.loads(cleaned)
                    p = schemas.PlanSchema(**parsed)
                    plan_dict = p.model_dump()
                    logger.info(f"[round {r}] 策论家 {i} 成功 (尝试 {attempt + 1})")
                    return plan_dict
                except Exception as e:
                    logger.warning(f"[round {r}] 策论家 {i} 尝试 {attempt + 1} 失败: {e}")
                    logger.error(traceback.format_exc())
                    if attempt == max_retries - 1:
                        return {"text": out if 'out' in locals() else "N/A", "error": str(e), "id": f"策论家{i}-错误"}
            return None

        with ThreadPoolExecutor(max_workers=num_planners) as executor:
            planner_results = list(executor.map(execute_planner, range(1, num_planners + 1)))
        
        plans = []
        for i, res in enumerate(planner_results, 1):
            if res:
                plans.append(res)
                last_plans_map[i] = res

        def execute_auditor(j):
            logger.info(f"[round {r}] 监察官 {j} 正在审核方案...")
            prompt_vars = {
                "auditor_id": f"监察官 {j}",
                "plans": json.dumps(plans, ensure_ascii=False),
                "issue": f"核心目标: {decomposition['core_goal']}\n关键问题: {decomposition['key_questions']}"
            }
            
            for attempt in range(max_retries):
                try:
                    # 使用tool-calling agent
                    system_prompt, user_prompt, model_config = convert_chain_to_tool_calling_format(auditor_chains[j-1], prompt_vars, "auditor")
                    out, tool_calls = stream_tool_calling_agent(
                        role_type="auditor",
                        agent_name=f"监察官 {j}",
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model_config=model_config,
                        event_type="agent_action"
                    )
                    
                    # 记录工具调用
                    if tool_calls:
                        search_results = [tc for tc in tool_calls if tc['tool_name'] == 'web_search']
                        if search_results:
                            all_search_references.append("\n".join([sr['formatted_result'] for sr in search_results]))
                    
                    cleaned = clean_json_string(out)
                    if not cleaned:
                        raise ValueError("监察官输出为空或不包含 JSON")
                        
                    parsed = json.loads(cleaned)
                    a = schemas.AuditorSchema(**parsed)
                    logger.info(f"[round {r}] 监察官 {j} 成功 (尝试 {attempt + 1})")
                    return a.model_dump()
                except Exception as e:
                    logger.warning(f"[round {r}] 监察官 {j} 尝试 {attempt + 1} 失败: {e}")
                    logger.error(traceback.format_exc())
                    if attempt == max_retries - 1:
                        return {"text": out if 'out' in locals() else "N/A", "error": str(e)}
            return None

        with ThreadPoolExecutor(max_workers=num_auditors) as executor:
            audits = list(executor.map(execute_auditor, range(1, num_auditors + 1)))
        audits = [a for a in audits if a]
        last_audits = audits

        # 保存本轮原始数据
        round_data = {
            "round": r,
            "plans": plans,
            "audits": audits
        }
        # round_data 不再保存到文件，已在history中记录

        # 4. Leader Summary & Next Instructions
        logger.info(f"[round {r}] 议长正在汇总本轮结果...")
        
        # 根据是否为最后一轮动态创建Leader chain
        is_final_round = (r == max_rounds)
        current_leader_chain = make_leader_chain(leader_cfg, is_final_round=is_final_round)
        
        inputs = {
            "original_goal": decomposition['core_goal'],
            "previous_decomposition": decomposition,
            "plans": plans,
            "audits": audits,
            "previous_instructions": current_instructions,
            "user_interventions": user_interventions,
            "last_round_da_challenge": last_da_result
        }
        
        final_summary = None
        for attempt in range(max_retries):
            logger.info(f"[round {r}] 议长正在调用模型进行汇总 (尝试 {attempt + 1}/{max_retries})...")
            try:
                current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 使用tool-calling agent
                prompt_vars = {"inputs": json.dumps(inputs, ensure_ascii=False), "current_time": current_time_str}
                system_prompt, user_prompt, model_config = convert_chain_to_tool_calling_format(current_leader_chain, prompt_vars, "leader")
                out, tool_calls = stream_tool_calling_agent(
                    role_type="leader",
                    agent_name="议长",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model_config=model_config,
                    event_type="agent_action"
                )
                
                # 记录工具调用
                if tool_calls:
                    search_results = [tc for tc in tool_calls if tc['tool_name'] == 'web_search']
                    if search_results:
                        all_search_references.append("\n".join([sr['formatted_result'] for sr in search_results]))
                    all_search_references.append(search_res)
                
                cleaned = clean_json_string(out)
                if not cleaned:
                    raise ValueError("议长总结输出为空或不包含 JSON")
                    
                parsed = json.loads(cleaned)
                if "decomposition" not in parsed:
                    parsed["decomposition"] = decomposition
                else:
                    parsed["decomposition"]["core_goal"] = decomposition["core_goal"]
                
                summary_obj = schemas.LeaderSummary(**parsed)
                final_summary = summary_obj.model_dump()
                logger.info(f"[round {r}] 议长汇总成功 (尝试 {attempt + 1})")
                break
            except Exception as e:
                logger.warning(f"[round {r}] 议长汇总尝试 {attempt + 1} 失败: {e}")
                logger.error(traceback.format_exc())
                if attempt == max_retries - 1:
                    final_summary = {
                        "round": r,
                        "decomposition": decomposition,
                        "instructions": "继续优化方案",
                        "summary": {"consensus": ["无法达成共识"], "controversies": ["格式解析失败"]}
                    }

        history.append({
            "round": r,
            "plans": plans,
            "audits": audits,
            "summary": final_summary
        })

        # Devil's Advocate 阶段 - 验证总结质量
        logger.info(f"[round {r}] 质疑官正在验证总结质量...")
        da_result = None
        synthesis_clusters = "（待实现Synthesizer后填充）"  # Phase 1暂时使用占位符
        
        for attempt in range(max_retries):
            logger.info(f"[round {r}] 质疑官正在调用模型进行质疑 (尝试 {attempt + 1}/{max_retries})...")
            try:
                da_prompt_vars = {
                    "round": r,
                    "synthesis_clusters": synthesis_clusters,
                    "leader_summary": json.dumps(final_summary, ensure_ascii=False),
                    "history": json.dumps(history[-3:], ensure_ascii=False) if len(history) >= 3 else json.dumps(history, ensure_ascii=False)  # 只传递最近3轮历史
                }
                
                out, search_res = stream_agent_output(devils_advocate_summary_chain, da_prompt_vars, "质疑官", "devils_advocate", event_type="agent_action")
                if search_res:
                    all_search_references.append(search_res)
                
                cleaned = clean_json_string(out)
                if not cleaned:
                    raise ValueError("质疑官输出为空或不包含 JSON")
                    
                parsed = json.loads(cleaned)
                da_obj = schemas.DevilsAdvocateSchema(**parsed)
                da_result = da_obj.model_dump()
                logger.info(f"[round {r}] 质疑官验证成功 (尝试 {attempt + 1})")
                
                # 将DA结果附加到本轮history
                history[-1]["devils_advocate"] = da_result
                break
            except Exception as e:
                logger.warning(f"[round {r}] 质疑官验证尝试 {attempt + 1} 失败: {e}")
                logger.error(traceback.format_exc())
                if attempt == max_retries - 1:
                    da_result = {
                        "round": r,
                        "stage": "summary",
                        "summary_challenge": {
                            "logical_gaps": [],
                            "missing_points": [],
                            "inconsistencies": [],
                            "optimism_bias": None
                        },
                        "overall_assessment": f"验证失败: {str(e)}",
                        "critical_issues": ["质疑官执行异常"],
                        "recommendations": ["请检查模型配置和输出格式"]
                    }
                    history[-1]["devils_advocate"] = da_result

        # 最后一轮强制修正：议长根据质疑官反馈进行最终打磨
        if r == max_rounds and da_result:
            logger.info(f"[round {r}] 🏁 最后一轮：议长正在根据质疑官反馈进行最终修正...")
            send_web_event("agent_action", agent_name="议长", role_type="Leader", content="正在根据质疑官反馈进行最终修正...", chunk_id=str(uuid.uuid4()))
            
            revision_inputs = {
                "original_summary": final_summary,
                "devils_advocate_feedback": da_result,
                "core_goal": decomposition['core_goal'],
                "all_rounds_history": history  # 提供完整历史以便全局整合
            }
            
            for attempt in range(max_retries):
                logger.info(f"[round {r}] 议长正在进行最终修正 (尝试 {attempt + 1}/{max_retries})...")
                try:
                    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # 使用最后一轮的chain（已经在前面创建了current_leader_chain）
                    out, search_res = stream_agent_output(
                        current_leader_chain, 
                        {"inputs": json.dumps(revision_inputs, ensure_ascii=False), "current_time": current_time_str}, 
                        "议长", 
                        "Leader"
                    )
                    if search_res:
                        all_search_references.append(search_res)
                    
                    cleaned = clean_json_string(out)
                    if not cleaned:
                        raise ValueError("议长最终修正输出为空或不包含 JSON")
                        
                    parsed = json.loads(cleaned)
                    if "decomposition" not in parsed:
                        parsed["decomposition"] = decomposition
                    else:
                        parsed["decomposition"]["core_goal"] = decomposition["core_goal"]
                    
                    revised_summary = schemas.LeaderSummary(**parsed)
                    final_summary = revised_summary.model_dump()
                    
                    # 更新history中的summary
                    history[-1]["summary"] = final_summary
                    history[-1]["revision_trigger"] = "final_round_mandatory_revision"
                    
                    logger.info(f"[round {r}] 议长最终修正成功 (尝试 {attempt + 1})")
                    send_web_event("agent_action", agent_name="议长", role_type="Leader", content=f"✅ 最终修正完成", chunk_id=str(uuid.uuid4()))
                    break
                except Exception as e:
                    logger.warning(f"[round {r}] 议长最终修正尝试 {attempt + 1} 失败: {e}")
                    logger.error(traceback.format_exc())
                    if attempt == max_retries - 1:
                        logger.warning(f"[round {r}] 议长最终修正失败，保留原总结")
                        send_web_event("agent_action", agent_name="议长", role_type="Leader", content=f"⚠️ 最终修正失败，保留原总结", chunk_id=str(uuid.uuid4()))

        # 保存history到数据库（需要应用上下文）
        if DB_AVAILABLE and user_id and SessionRepository:
            try:
                from src.web.app import app
                with app.app_context():
                    SessionRepository.update_history(session_id, history)
                    logger.info(f"[round {r}] history已保存到数据库")
            except Exception as e:
                logger.error(f"[round {r}] 数据库保存失败: {e}")

        # 更新下一轮指令
        current_instructions = f"核心目标: {decomposition['core_goal']}\n上轮总结: {final_summary['summary']}\n议长指令: {final_summary['instructions']}"

        # 5. 检查终止条件
        has_excellent = False
        excellent_plan_ids = []
        for audit in audits:
            if isinstance(audit, dict) and "reviews" in audit:
                for review in audit["reviews"]:
                    if review.get("rating") == "优秀":
                        has_excellent = True
                        excellent_plan_ids.append(review.get("plan_id"))
        
        no_controversies = False
        controversies = []
        if final_summary and "summary" in final_summary:
            controversies = final_summary["summary"].get("controversies", [])
            if not controversies:
                no_controversies = True

        all_infeasible = True
        if not audits:
            all_infeasible = False
        else:
            for audit in audits:
                if isinstance(audit, dict) and "reviews" in audit:
                    for review in audit["reviews"]:
                        if review.get("rating") != "不可行":
                            all_infeasible = False
                            break
                if not all_infeasible: break

        if has_excellent and no_controversies:
            logger.info(f"[round {r}] 判定结论：达成共识。依据：发现优秀方案({excellent_plan_ids})且无核心争议。")
            break
        elif all_infeasible and len(audits) > 0:
            logger.warning(f"[round {r}] 判定结论：讨论终止。依据：所有方案均被判定为不可行。")
            break
        elif r == max_rounds:
            logger.info(f"[round {r}] 判定结论：达到最大轮数。")
        else:
            logger.info(f"[round {r}] 判定结论：进入下一轮。")

    # 5. Final Reporting
    send_web_event("discussion_complete")
    logger.info("[cycle] 报告者正在生成最终 HTML 报告...")
    
    simplified_history = []
    for h in history:
        if h.get("type") == "user_intervention":
            simplified_history.append(h)
            continue
            
        simplified_history.append({
            "round": h["round"],
            "plans": [{"id": p.get("id"), "text": p.get("text")} for p in h.get("plans", [])],
            "audits": [{"auditor_id": a.get("auditor_id"), "reviews": a.get("reviews")} for a in h.get("audits", [])],
            "devils_advocate": h.get("devils_advocate"),
            "summary": h.get("summary")
        })

    # 找到最后一个包含 summary 的记录作为最终总结
    last_summary = None
    for h in reversed(history):
        if "summary" in h:
            last_summary = h["summary"]
            break

    final_data = {
        "issue": issue_text,
        "decomposition": decomposition,
        "decomposition_challenge": decomposition_da_result,
        "history": simplified_history,
        "final_summary": last_summary
    }
    
    # 保存最终数据到数据库（需要应用上下文）
    if DB_AVAILABLE and user_id and SessionRepository:
        try:
            from src.web.app import app
            with app.app_context():
                SessionRepository.update_final_session_data(session_id, final_data)
                SessionRepository.update_search_references(session_id, all_search_references)
                logger.info(f"[cycle] final_session_data 和 search_references 已保存到数据库")
        except Exception as e:
            logger.error(f"[cycle] 数据库保存失败: {e}")

    report_html = generate_report_from_workspace(workspace_path, model_config, session_id)
    
    # 保存报告到数据库（需要应用上下文）
    if DB_AVAILABLE and user_id and SessionRepository:
        try:
            from src.web.app import app
            with app.app_context():
                SessionRepository.save_final_report(session_id, report_html)
                logger.info(f"[cycle] 报告已保存到数据库")
        except Exception as e:
            logger.error(f"[cycle] 数据库更新失败（不影响主流程）: {e}")

    return {
        "decomposition": decomposition,
        "history": history,
        "final": last_summary,
        "report_html": report_html,
        "session_id": session_id  # 返回session_id供app.py使用
    }

def generate_report_from_workspace(workspace_path: str, model_config: Dict[str, Any], session_id: str = None) -> str:
    """从数据库重新生成报告（不再使用文件）。
    
    Args:
        workspace_path: 工作区路径（保留兼容性，实际不再使用）
        model_config: 模型配置
        session_id: 会话ID，必需
    """
    if not session_id:
        session_id = os.path.basename(workspace_path)
    
    logger.info(f"[report] 正在从数据库重新生成报告（Session ID: {session_id}）...")
    
    try:
        # 从数据库加载会话数据（需要Flask应用上下文）
        if not DB_AVAILABLE or not SessionRepository:
            raise RuntimeError("数据库功能未启用，无法生成报告")
        
        # 导入Flask app并创建应用上下文
        from src.web.app import app
        with app.app_context():
            session = SessionRepository.get_session_by_id(session_id)
            if not session:
                raise ValueError(f"数据库中不存在会话: {session_id}")
            
            # 构造 final_data 结构
            final_data = {
                "issue": session.issue,
                "decomposition": session.decomposition or {},
                "decomposition_challenge": "",
                "history": session.history or [],
                "final_summary": session.final_session_data or {}
            }
            
            # 从数据库获取搜索引用
            all_search_references = session.search_references or []
            logger.info(f"[report] 从数据库加载: 议题={session.issue}, 轮次={len(final_data['history'])}, 搜索结果={len(all_search_references)}条")
        
        # ===== 参考资料整理环节 =====
        # 获取原始议题用于相关性判断
        issue_text = final_data.get("issue", "")
        if not issue_text:
            # 尝试从其他字段获取
            issue_text = final_data.get("decomposition", {}).get("core_goal", "")
        
        if all_search_references and len(all_search_references) > 0:
            logger.info(f"[report] 开始参考资料整理，原始结果: {len(all_search_references)}条")
            
            # 每次动态精简引用（不再依赖文件缓存）
            search_refs_text, refined_output = refine_search_references(
                all_search_references,
                issue_text,
                model_config,
                workspace_path
            )
        else:
            search_refs_text = "无联网搜索参考资料。"
            logger.info(f"[report] 无搜索结果需要整理")
            
        reporter_chain = make_reporter_chain(model_config)

        max_retries = 3
        report_html = "报告生成失败"
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[report] 正在调用模型生成最终报告 (尝试 {attempt + 1}/{max_retries})...")
                report_html, _ = stream_agent_output(
                    reporter_chain, 
                    {
                        "final_data": json.dumps(final_data, ensure_ascii=False),
                        "search_references": search_refs_text
                    }, 
                    "报告者", 
                    "Reporter",
                    event_type="final_report"
                )
                
                report_html = report_html.strip()
                if report_html.startswith("```html"):
                    report_html = report_html[7:]
                elif report_html.startswith("```"):
                    report_html = report_html[3:]
                if report_html.endswith("```"):
                    report_html = report_html[:-3]
                report_html = report_html.strip()
                
                # **核心修复**: 将 workspace_id 注入 HTML（查找meta标签并替换内容）
                if session_id:
                    # 查找并替换 meta 标签中的 workspace-id（如果LLM已生成）
                    import re
                    if 'name="workspace-id"' in report_html:
                        # 如果LLM生成了meta标签，替换其中的内容
                        report_html = re.sub(
                            r'<meta\s+name="workspace-id"\s+content="[^"]*">',
                            f'<meta name="workspace-id" content="{session_id}">',
                            report_html
                        )
                    else:
                        # 如果没有生成meta标签，在<head>后插入
                        if '<head>' in report_html:
                            report_html = report_html.replace(
                                '<head>',
                                f'<head>\n    <meta name="workspace-id" content="{session_id}">',
                                1
                            )
                    logger.info(f"[report] 已将 workspace-id 注入 HTML: {session_id}")
                
                send_web_event("final_report", content=report_html)
                
                # 保存到 Workspace
                filepath = os.path.join(workspace_path, "report.html")
                
                # 如果已存在旧报告，则重命名备份
                if os.path.exists(filepath):
                    old_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = os.path.join(workspace_path, f"report_old_{old_timestamp}.html")
                    try:
                        os.rename(filepath, backup_path)
                        logger.info(f"[report] 已将旧报告重命名为: {backup_path}")
                    except Exception as e:
                        logger.warning(f"[report] 重命名旧报告失败: {e}")

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(report_html)
                
                # 同时保留一份到全局 reports 目录
                reports_dir = os.path.join(os.getcwd(), "reports")
                if not os.path.exists(reports_dir):
                    os.makedirs(reports_dir)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                legacy_filepath = os.path.join(reports_dir, f"report_{timestamp}.html")
                with open(legacy_filepath, "w", encoding="utf-8") as f:
                    f.write(report_html)
                
                logger.info(f"[report] 报告已保存至 Workspace: {filepath}")
                return report_html
            except Exception as e:
                logger.warning(f"[report] 报告生成尝试 {attempt + 1} 失败: {e}")
                logger.error(traceback.format_exc())
        
        return report_html
        
    except Exception as e:
        logger.error(f"[report] 从工作区生成报告失败: {e}")
        logger.error(traceback.format_exc())
        return "报告生成失败"


def call_role_designer(requirement: str, backend_config: Optional[Dict[str, Any]] = None) -> schemas.RoleDesignOutput:
    """调用角色设计师Agent生成角色设计
    
    Args:
        requirement: 用户的需求描述
        backend_config: 可选的后端配置，格式为 {"type": "backend_name", "model": "model_name"}
                       如果不提供，则使用全局配置
    
    Returns:
        RoleDesignOutput: 角色设计输出
    
    Raises:
        Exception: 如果生成失败或验证失败
    """
    from src.agents.role_manager import RoleManager
    
    try:
        rm = RoleManager()
        
        # 尝试加载role_designer的prompt，如果失败则刷新角色列表
        try:
            prompt_template_str = rm.load_prompt('role_designer', 'generate')
        except ValueError as e:
            logger.warning(f"[role_designer] 首次加载失败，尝试刷新角色列表: {e}")
            rm.refresh_all_roles()
            prompt_template_str = rm.load_prompt('role_designer', 'generate')
        
        # 直接使用字符串替换，避免LangChain PromptTemplate对{{}}的解析问题
        prompt_text = prompt_template_str.replace('{{requirement}}', requirement)
        
        # 使用传入的配置，或从全局配置读取
        if backend_config:
            model_config = ModelConfig(**backend_config)
        else:
            model_config = ModelConfig(
                type=model_adapter.config.MODEL_BACKEND,
                model=model_adapter.config.MODEL_NAME
            )
        
        logger.info(f"[role_designer] 使用模型: backend={model_config.type}, model={model_config.model}")
        llm = AdapterLLM(backend_config=model_config)
        
        logger.info("[role_designer] 开始生成角色设计...")
        
        # 发送用户需求到前端（显示在reasoning区域顶部）
        send_web_event("role_designer_reasoning", 
                      content=f"📋 用户需求：\n{requirement}\n\n{'='*60}\n\n",
                      agent_name="角色设计师")
        
        # 使用stream模式捕获推理过程
        reasoning_parts = []
        content_parts = []
        
        for chunk in llm.stream(prompt_text):
            if hasattr(chunk, 'generation_info') and chunk.generation_info:
                reasoning = chunk.generation_info.get('reasoning', '')
                if reasoning:
                    reasoning_parts.append(reasoning)
                    # 发送reasoning到前端
                    send_web_event("role_designer_reasoning", content=reasoning, agent_name="角色设计师")
            
            if chunk.text:
                content_parts.append(chunk.text)
                # 发送content到前端
                send_web_event("role_designer_content", content=chunk.text, agent_name="角色设计师")
        
        raw_output = ''.join(content_parts)
        full_reasoning = ''.join(reasoning_parts)
        
        logger.info(f"[role_designer] Reasoning长度: {len(full_reasoning)}, 输出长度: {len(raw_output)}")
        
        # 清理并解析JSON
        json_str = clean_json_string(raw_output)
        
        try:
            json_obj = json.loads(json_str)
            design = schemas.RoleDesignOutput(**json_obj)
            logger.info(f"[role_designer] ✅ 成功生成角色: {design.display_name}")
            return design
            
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"[role_designer] JSON解析失败: {e}")
            logger.error(f"[role_designer] 原始输出: {raw_output[:500]}")
            logger.error(f"[role_designer] 完整Reasoning: {full_reasoning[:1000]}")
            raise Exception(f"角色设计格式错误: {str(e)}")
        
    except Exception as e:
        logger.error(f"[role_designer] 调用失败: {e}")
        logger.error(traceback.format_exc())
        raise


# ========== 议事编排官 Agent ==========

def run_meta_orchestrator(user_requirement: str, model_config: Dict[str, Any] = None) -> schemas.OrchestrationPlan:
    """
    运行议事编排官进行智能规划
    
    Args:
        user_requirement: 用户需求描述
        model_config: 模型配置（可选）
        
    Returns:
        OrchestrationPlan对象，包含完整的规划方案
    """
    try:
        logger.info(f"[meta_orchestrator] 开始规划，需求: {user_requirement[:100]}...")
        
        # 使用固定的chunk_id，所有议事编排官的输出都追加到同一个卡片
        orchestrator_chunk_id = str(uuid.uuid4())
        
        # 发送Web事件 - 开始
        send_web_event("agent_action", agent_name="议事编排官", role_type="meta_orchestrator", 
                      content="🧭 开始分析需求并规划讨论方案...\n", chunk_id=orchestrator_chunk_id)
        
        # 获取可用角色列表
        from src.agents.role_manager import RoleManager
        rm = RoleManager()
        available_roles_raw = rm.list_roles()
        
        # 格式化角色信息
        available_roles = "\n".join([
            f"• {role.display_name} ({role.name}): {role.description[:100]}..."
            for role in available_roles_raw[:20]  # 只显示前20个，避免prompt过长
        ])
        
        # 获取可用框架列表
        from src.agents.frameworks import list_frameworks
        frameworks_list = list_frameworks()
        available_frameworks = "\n".join([
            f"{i+1}. {fw['name']} ({fw['id']}): {fw['description'][:100]}..."
            for i, fw in enumerate(frameworks_list)
        ])
        
        # 加载prompt模板
        from src.agents.role_manager import RoleManager
        rm = RoleManager()
        prompt_text = rm.load_prompt("meta_orchestrator", "planning")
        
        # 替换变量
        prompt_filled = prompt_text.replace("{user_requirement}", user_requirement)
        prompt_filled = prompt_filled.replace("{available_roles}", available_roles)
        prompt_filled = prompt_filled.replace("{available_frameworks}", available_frameworks)
        
        # 准备初始消息
        initial_messages = [{"role": "user", "content": prompt_filled}]
        
        # 获取工具schemas
        from src.agents.meta_tools import get_tool_schemas
        tools = get_tool_schemas()
        
        logger.info(f"[meta_orchestrator] 使用 {len(tools)} 个工具: {[t['function']['name'] for t in tools]}")
        
        # 调用带工具的模型
        from src.agents.model_adapter import call_model_with_tools
        
        send_web_event("agent_action", agent_name="议事编排官", role_type="meta_orchestrator", 
                      content="🔍 正在调用LLM分析需求...", 
                      chunk_id=orchestrator_chunk_id)
        
        response_text = call_model_with_tools(
            agent_id="meta_orchestrator",
            messages=initial_messages,
            model_config=model_config,
            tools=tools,
            max_tool_rounds=10,  # 议事编排官可能需要多次调用工具
            stream_chunk_id=orchestrator_chunk_id  # 传入固定chunk_id
        )
        
        logger.info(f"[meta_orchestrator] LLM返回响应，长度: {len(response_text)}")
        
        # 清理JSON
        cleaned = clean_json_string(response_text)
        
        send_web_event("agent_action", agent_name="议事编排官", role_type="meta_orchestrator", 
                      content=f"\n\n📋 解析规划方案... (响应长度: {len(cleaned)} 字符)", 
                      chunk_id=orchestrator_chunk_id)
        
        # 解析为OrchestrationPlan
        try:
            plan_dict = json.loads(cleaned)
            plan = schemas.OrchestrationPlan(**plan_dict)
            
            logger.info(f"[meta_orchestrator] ✅ 成功生成规划方案")
            logger.info(f"  - 问题类型: {plan.analysis.problem_type}")
            logger.info(f"  - 推荐框架: {plan.framework_selection.framework_name}")
            logger.info(f"  - 现有角色: {len(plan.role_planning.existing_roles)} 个")
            logger.info(f"  - 需创建角色: {len(plan.role_planning.roles_to_create)} 个")
            
            # 详细日志：打印匹配到的角色
            if plan.role_planning.existing_roles:
                logger.info(f"[meta_orchestrator] 匹配到的现有角色:")
                for role in plan.role_planning.existing_roles:
                    logger.info(f"    • {role.display_name} ({role.name}): score={role.match_score}, count={role.assigned_count}")
            
            # 详细日志：打印 agent_counts（修正前）
            logger.info(f"[meta_orchestrator] agent_counts 配置（LLM输出）: {plan.execution_config.agent_counts}")
            
            # 详细日志：打印 role_stage_mapping（修正前）
            if plan.execution_config.role_stage_mapping:
                logger.info(f"[meta_orchestrator] role_stage_mapping（LLM输出）: {plan.execution_config.role_stage_mapping}")
            else:
                logger.warning(f"[meta_orchestrator] ⚠️ role_stage_mapping 为空或未设置")
            
            # 🔧 自动修正配置（方案E核心逻辑）
            plan = _auto_fix_orchestration_plan(plan)
            
            # 构建详细的输出信息
            existing_roles_detail = ""
            if plan.role_planning.existing_roles:
                existing_roles_detail = "\n".join([
                    f"  • {role.display_name} ({role.name}): {role.match_reason}"
                    for role in plan.role_planning.existing_roles[:10]  # 最多显示10个
                ])
            else:
                existing_roles_detail = "  （未使用现有角色）"
            
            new_roles_detail = ""
            if plan.role_planning.roles_to_create:
                new_roles_detail = "\n".join([
                    f"  • {role.capability}: {role.requirement[:80]}..."
                    for role in plan.role_planning.roles_to_create[:5]  # 最多显示5个
                ])
            else:
                new_roles_detail = "  （无需创建新角色）"
            
            # 发送综合事件
            summary_text = f"""
🧭 **议事编排官规划完成**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **需求分析**
• 问题类型：{plan.analysis.problem_type}
• 复杂度：{plan.analysis.complexity}
• 所需能力：{', '.join(plan.analysis.required_capabilities[:5])}
{'  ...' if len(plan.analysis.required_capabilities) > 5 else ''}

🎯 **推荐框架**
• 框架：{plan.framework_selection.framework_name}
• 理由：{plan.framework_selection.selection_reason[:150]}{'...' if len(plan.framework_selection.selection_reason) > 150 else ''}

👥 **角色配置**

**✅ 匹配到 {len(plan.role_planning.existing_roles)} 个现有角色**
{existing_roles_detail}

**🔧 需要创建 {len(plan.role_planning.roles_to_create)} 个新角色**
{new_roles_detail}

⚙️ **执行配置**
• 讨论轮次：{plan.execution_config.total_rounds} 轮
• Agent数量：{sum(plan.execution_config.agent_counts.values())} 个
• 预估耗时：{plan.execution_config.estimated_duration}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """.strip()
            
            send_web_event("agent_action", agent_name="议事编排官", role_type="meta_orchestrator", 
                          content="\n\n" + summary_text, chunk_id=orchestrator_chunk_id)
            
            return plan
            
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"[meta_orchestrator] JSON解析失败: {e}")
            logger.error(f"[meta_orchestrator] 清理后的JSON: {cleaned[:500]}")
            logger.error(f"[meta_orchestrator] 原始响应: {response_text[:500]}")
            
            send_web_event("error", agent_name="议事编排官", role_type="meta_orchestrator", 
                          content=f"\n\n❌ 规划方案解析失败: {str(e)}", chunk_id=orchestrator_chunk_id)
            
            raise Exception(f"规划方案格式错误: {str(e)}")
        
    except Exception as e:
        logger.error(f"[meta_orchestrator] 调用失败: {e}")
        logger.error(traceback.format_exc())
        
        # 注意：这里可能没有orchestrator_chunk_id，使用新的
        send_web_event("error", agent_name="议事编排官", role_type="meta_orchestrator", 
                      content=f"❌ 规划失败: {str(e)}", chunk_id=str(uuid.uuid4()))
        
        raise


def execute_orchestration_plan(
    plan: schemas.OrchestrationPlan, 
    user_requirement: str, 
    model_config: Dict[str, Any] = None,
    workspace_path: Path = None,
    session_id: str = None,
    agent_configs: Dict[str, Any] = None,
    user_id: int = None
) -> Dict[str, Any]:
    """
    执行议事编排官生成的规划方案
    
    Args:
        plan: OrchestrationPlan规划方案
        user_requirement: 原始用户需求
        model_config: 模型配置
        workspace_path: 工作目录路径（可选，如果不提供会自动创建）
        session_id: 会话ID（可选，如果不提供会自动生成）
        agent_configs: 可选的每个Agent的模型配置覆盖
        user_id: 用户ID（用于数据库保存）
        
    Returns:
        执行结果字典
    """
    from src.agents.framework_engine import FrameworkEngine
    from src.agents.frameworks import get_framework
    from datetime import datetime
    from pathlib import Path
    import uuid
    
    try:
        logger.info(f"[execute_orchestration_plan] 开始执行规划方案")
        logger.info(f"  - 框架: {plan.framework_selection.framework_name} (ID: {plan.framework_selection.framework_id})")
        logger.info(f"  - 轮次: {plan.execution_config.total_rounds}")
        logger.info(f"  - Agent配置: {plan.execution_config.agent_counts}")
        
        # 1. 创建workspace（如果未提供）
        if not workspace_path or not session_id:
            session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
            workspace_path = get_workspace_dir() / session_id
            workspace_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"[execute_orchestration_plan] 创建workspace: {workspace_path}")
        
        # 1.5 创建数据库会话记录（如果提供了user_id）
        if user_id and DB_AVAILABLE:
            try:
                from src.repositories.session_repository import SessionRepository
                from src.web.app import app
                
                logger.info(f"[execute_orchestration_plan] 准备创建数据库会话，user_id={user_id}, session_id={session_id}")
                
                config_data = {
                    "framework_id": plan.framework_selection.framework_id,
                    "framework_name": plan.framework_selection.framework_name,
                    "backend": model_config.get("type") if model_config else None,
                    "model": model_config.get("model") if model_config else None,
                    "rounds": plan.execution_config.total_rounds,
                    "agent_counts": plan.execution_config.agent_counts,
                    "agent_configs": agent_configs
                }
                
                # 需要应用上下文进行数据库操作
                with app.app_context():
                    db_session = SessionRepository.create_session(
                        user_id=user_id,
                        session_id=session_id,
                        issue=user_requirement,
                        config=config_data
                    )
                    if db_session:
                        logger.info(f"[execute_orchestration_plan] ✅ 数据库会话创建成功: {session_id}")
                    else:
                        logger.warning(f"[execute_orchestration_plan] ⚠️ 数据库会话创建返回None: {session_id}")
            except Exception as e:
                logger.error(f"[execute_orchestration_plan] ❌ 数据库操作失败: {e}")
                logger.error(traceback.format_exc())
        
        # 2. 获取框架定义
        framework = get_framework(plan.framework_selection.framework_id)
        if not framework:
            raise ValueError(f"未找到框架: {plan.framework_selection.framework_id}")
        
        # 3. 准备Agent数量配置（从规划方案中提取）
        agent_counts = plan.execution_config.agent_counts
        role_stage_mapping = plan.execution_config.role_stage_mapping
        
        # 3.5. Fallback机制：如果有专业角色但role_stage_mapping为空，自动创建专业分析stage
        framework_roles = {"planner", "auditor", "leader", "devils_advocate", "reporter"}
        professional_roles = [role for role in agent_counts.keys() if role not in framework_roles]
        
        if professional_roles and (not role_stage_mapping or len(role_stage_mapping) == 0):
            logger.warning(f"[execute_orchestration_plan] 检测到专业角色但role_stage_mapping为空，启动fallback机制")
            logger.info(f"  - 专业角色: {professional_roles}")
            
            # 创建专业分析stage
            from agents.frameworks import FrameworkStage
            professional_stage = FrameworkStage(
                name="专业分析",
                description="专业角色基于其专长领域对议题进行深入分析",
                roles=professional_roles,  # 包含所有专业角色
                min_agents=1,
                max_agents=len(professional_roles),
                rounds=1,
                prompt_suffix="请从你的专业角度分析议题，提供独特的见解和建议。"
            )
            
            # 将专业分析stage插入到框架中（在第一个stage之后）
            framework.stages.insert(1, professional_stage)
            logger.info(f"[execute_orchestration_plan] 已插入'专业分析'stage到框架第2位")
            
            # 为所有专业角色创建role_stage_mapping
            role_stage_mapping = {role: ["专业分析"] for role in professional_roles}
            logger.info(f"[execute_orchestration_plan] 自动创建 role_stage_mapping: {role_stage_mapping}")
            
            send_web_event("system_info", 
                          message=f"🔧 检测到{len(professional_roles)}个专业角色，自动启用fallback机制创建专业分析stage",
                          chunk_id=str(uuid.uuid4()))
        
        # 4. 准备模型配置
        model_config = model_config or {
            "type": model_adapter.config.MODEL_BACKEND, 
            "model": model_adapter.config.MODEL_NAME
        }
        agent_configs = agent_configs or {}
        
        # 5. 创建并执行FrameworkEngine
        send_web_event("system_info", message=f"🚀 开始执行框架: {framework.name}", chunk_id=str(uuid.uuid4()))
        
        engine = FrameworkEngine(
            framework=framework,
            model_config=model_config,
            workspace_path=workspace_path,
            session_id=session_id
        )
        
        execution_result = engine.execute(
            user_requirement=user_requirement,
            agent_counts=agent_counts,
            agent_configs=agent_configs,
            role_stage_mapping=role_stage_mapping
        )
        
        # 6. 构造完整结果（仅内存）
        final_result = {
            "success": True,
            "session_id": session_id,
            "workspace_path": str(workspace_path),
            "user_requirement": user_requirement,
            "plan": plan.model_dump(),
            "execution": execution_result,
            "all_outputs": engine.get_all_outputs(),
            "timestamp": datetime.now().isoformat()
        }
        
        # 议事编排官结果已在数据库保存，不再写入文件
        
        # 提取搜索引用（已在数据库中）
        all_outputs = engine.get_all_outputs()
        search_refs = all_outputs.get("search_references", [])
        if search_refs:
            logger.info(f"[execute_orchestration_plan] 搜索结果已保存到数据库，共 {len(search_refs)} 条")
        
        logger.info(f"[execute_orchestration_plan] 执行完成，结果已保存到数据库")
        
        # 7. 生成报告
        logger.info(f"[execute_orchestration_plan] 开始生成报告...")
        try:
            report_html = generate_report_from_workspace(str(workspace_path), model_config, session_id)
            final_result["report_html"] = report_html
            logger.info(f"[execute_orchestration_plan] 报告生成完成")
        except Exception as e:
            logger.error(f"[execute_orchestration_plan] 报告生成失败: {e}")
            logger.error(traceback.format_exc())
            final_result["report_html"] = f"<p>报告生成失败: {str(e)}</p>"
        
        send_web_event("system_info", message=f"✅ 框架执行完成", chunk_id=str(uuid.uuid4()))
        
        return final_result
        
    except Exception as e:
        logger.error(f"[execute_orchestration_plan] 执行失败: {e}")
        logger.error(traceback.format_exc())
        
        send_web_event("error", message=f"❌ 执行失败: {str(e)}", chunk_id=str(uuid.uuid4()))
        
        raise

