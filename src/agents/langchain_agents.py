from langchain_core.prompts import PromptTemplate
from src.agents.langchain_llm import AdapterLLM, ModelConfig
from src.agents import schemas, model_adapter
from src.utils.logger import logger
from src.utils import search_utils
from src.utils.path_manager import get_workspace_dir
from pydantic import ValidationError
import json
import requests
import os
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import uuid
import traceback
from datetime import datetime

def send_web_event(event_type: str, **kwargs):
    """发送事件到 Web 监控面板。"""
    try:
        url = "http://127.0.0.1:5000/api/update"
        payload = {"type": event_type, **kwargs}
        requests.post(url, json=payload, timeout=1)
    except Exception:
        pass

def clean_json_string(s: str) -> str:
    """清理字符串中的 Markdown JSON 标签，并尝试提取第一个完整的 JSON 对象。"""
    if not s:
        return ""
    s = s.strip()
    
    # 寻找第一个 {
    start = s.find('{')
    if start == -1:
        # 尝试寻找数组 [
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
                    return s[start:i+1]
        
        if char == '\\':
            escape = not escape
        else:
            escape = False
            
    # 如果没找到匹配的括号，回退到原来的逻辑
    end = s.rfind('}')
    if end == -1:
        end = s.rfind(']')
        
    if start != -1 and end != -1 and end > start:
        return s[start:end+1]
    
    return s.strip()

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

def make_planner_chain(model_config: Dict[str, Any]):
    """创建策论家链（使用RoleManager）"""
    from src.agents.role_manager import RoleManager
    
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    role_manager = RoleManager()
    
    # 从RoleManager加载prompt和配置
    stage_name = "proposal"  # planner的stage名称
    prompt_text = role_manager.load_prompt("planner", stage_name)
    role_config = role_manager.get_role("planner")
    input_vars = role_config.stages[stage_name].input_vars
    
    prompt = PromptTemplate(template=prompt_text, input_variables=input_vars)
    return prompt | llm



def make_auditor_chain(model_config: Dict[str, Any]):
    """创建监察官链（使用RoleManager）"""
    from src.agents.role_manager import RoleManager
    
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    role_manager = RoleManager()
    
    # 从RoleManager加载prompt和配置
    stage_name = "review"  # auditor的stage名称
    prompt_text = role_manager.load_prompt("auditor", stage_name)
    role_config = role_manager.get_role("auditor")
    input_vars = role_config.stages[stage_name].input_vars
    
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
    
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    role_manager = RoleManager()
    
    # 从RoleManager加载prompt和配置
    prompt_text = role_manager.load_prompt("reporter", "generate")
    role_config = role_manager.get_role("reporter")
    input_vars = role_config.stages["generate"].input_vars
    
    prompt = PromptTemplate(template=prompt_text, input_variables=input_vars)
    return prompt | llm


def run_full_cycle(issue_text: str, model_config: Dict[str, Any] = None, max_rounds: int = 3, num_planners: int = 2, num_auditors: int = 2, agent_configs: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run a multi-round LangChain-driven cycle: leader decomposes, planners generate plans, auditors review, leader summarizes.
    """
    # 1. 初始化 Session 和 Workspace
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
    workspace_path = get_workspace_dir() / session_id
    workspace_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"[cycle] Session ID: {session_id}, Workspace: {workspace_path}")

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
        planner_chains.append(make_planner_chain(p_cfg))
        
    auditor_chains = []
    for i in range(num_auditors):
        # 优先从 agent_configs 获取 auditor_i，否则使用全局 model_config
        a_cfg = agent_configs.get(f"auditor_{i}") or model_config
        auditor_chains.append(make_auditor_chain(a_cfg))

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
            out, search_res = stream_agent_output(leader_chain, {"inputs": issue_text, "current_time": current_time_str}, "议长", "Leader")
            if search_res:
                all_search_references.append(search_res)
            
            cleaned = clean_json_string(out)
            if not cleaned:
                logger.error(f"[cycle] 议长输出为空或不包含 JSON。原始输出: {out}")
                raise ValueError("议长未返回有效的 JSON 拆解结果")
                
            parsed = json.loads(cleaned)
            summary = schemas.LeaderSummary(**parsed)
            decomposition = summary.decomposition.dict()
            
            # 保存初始拆解结果
            with open(os.path.join(workspace_path, "decomposition.json"), "w", encoding="utf-8") as f:
                json.dump(decomposition, f, ensure_ascii=False, indent=4)
            
            logger.info(f"[cycle] 议长拆解成功 (尝试 {attempt + 1})")
            break
        except Exception as e:
            logger.warning(f"[cycle] 议长拆解尝试 {attempt + 1} 失败: {e}")
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
            decomposition_da_result = da_obj.dict()
            logger.info(f"[cycle] 质疑官验证拆解成功 (尝试 {attempt + 1})")
            
            # 保存拆解质疑结果
            with open(os.path.join(workspace_path, "decomposition_challenge.json"), "w", encoding="utf-8") as f:
                json.dump(decomposition_da_result, f, ensure_ascii=False, indent=4)
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
                decomposition = summary.decomposition.dict()
                
                # 更新保存的拆解结果
                with open(os.path.join(workspace_path, "decomposition_revised.json"), "w", encoding="utf-8") as f:
                    json.dump(decomposition, f, ensure_ascii=False, indent=4)
                
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
                    out, search_res = stream_agent_output(planner_chains[i-1], prompt_vars, f"策论家 {i}", "Planner")
                    if search_res:
                        all_search_references.append(search_res)
                    
                    cleaned = clean_json_string(out)
                    if not cleaned:
                        raise ValueError("策论家输出为空或不包含 JSON")
                        
                    parsed = json.loads(cleaned)
                    p = schemas.PlanSchema(**parsed)
                    plan_dict = p.dict()
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
                    out, search_res = stream_agent_output(auditor_chains[j-1], prompt_vars, f"监察官 {j}", "Auditor")
                    if search_res:
                        all_search_references.append(search_res)
                    
                    cleaned = clean_json_string(out)
                    if not cleaned:
                        raise ValueError("监察官输出为空或不包含 JSON")
                        
                    parsed = json.loads(cleaned)
                    a = schemas.AuditorSchema(**parsed)
                    logger.info(f"[round {r}] 监察官 {j} 成功 (尝试 {attempt + 1})")
                    return a.dict()
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
        with open(os.path.join(workspace_path, f"round_{r}_data.json"), "w", encoding="utf-8") as f:
            json.dump(round_data, f, ensure_ascii=False, indent=4)

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
                out, search_res = stream_agent_output(current_leader_chain, {"inputs": json.dumps(inputs, ensure_ascii=False), "current_time": current_time_str}, "议长", "Leader")
                if search_res:
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
                final_summary = summary_obj.dict()
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
                da_result = da_obj.dict()
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
                    final_summary = revised_summary.dict()
                    
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

        # 保存本轮汇总后的 history
        with open(os.path.join(workspace_path, "history.json"), "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=4)

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
    
    # 保存最终输入数据
    with open(os.path.join(workspace_path, "final_session_data.json"), "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    
    # 保存搜索参考资料
    with open(os.path.join(workspace_path, "search_references.json"), "w", encoding="utf-8") as f:
        json.dump(all_search_references, f, ensure_ascii=False, indent=4)

    report_html = generate_report_from_workspace(workspace_path, model_config, session_id)

    return {
        "decomposition": decomposition,
        "history": history,
        "final": last_summary,
        "report_html": report_html
    }

def generate_report_from_workspace(workspace_path: str, model_config: Dict[str, Any], session_id: str = None) -> str:
    """根据工作区保存的数据重新生成报告。
    
    Args:
        workspace_path: 工作区路径
        model_config: 模型配置
        session_id: 会话ID，用于在HTML中嵌入workspace标识
    """
    # 如果没有传入session_id，从workspace_path中提取
    if not session_id:
        session_id = os.path.basename(workspace_path)
    
    logger.info(f"[report] 正在从工作区 {workspace_path} 重新生成报告（Session ID: {session_id}）...")
    
    try:
        # 加载数据
        with open(os.path.join(workspace_path, "final_session_data.json"), "r", encoding="utf-8") as f:
            final_data = json.load(f)
        
        # 加载搜索参考资料，如果不存在则为空
        all_search_references = []
        refs_path = os.path.join(workspace_path, "search_references.json")
        if os.path.exists(refs_path):
            with open(refs_path, "r", encoding="utf-8") as f:
                all_search_references = json.load(f)
            
        reporter_chain = make_reporter_chain(model_config)
        
        unique_refs = []
        seen_refs = set()
        for ref in all_search_references:
            if ref not in seen_refs:
                unique_refs.append(ref)
                seen_refs.add(ref)
        
        search_refs_text = "\n\n".join(unique_refs) if unique_refs else "无联网搜索参考资料。"
        if len(search_refs_text) > 15000:
            search_refs_text = search_refs_text[:15000] + "\n\n...(内容过长已截断)"

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


def call_role_designer(requirement: str) -> schemas.RoleDesignOutput:
    """调用角色设计师Agent生成角色设计
    
    Args:
        requirement: 用户的需求描述
    
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
        
        prompt_template = PromptTemplate.from_template(prompt_template_str)
        
        # 准备输入
        prompt_text = prompt_template.format(requirement=requirement)
        
        # 调用LLM（使用stream模式捕获reasoning和content）
        model_config = ModelConfig(
            type="deepseek",
            model="deepseek-reasoner"
        )
        llm = AdapterLLM(backend_config=model_config)
        
        logger.info("[role_designer] 开始生成角色设计...")
        
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


