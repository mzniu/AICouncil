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
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    prompt = PromptTemplate.from_template(
        """
        **IMPORTANT: You MUST respond in the SAME LANGUAGE as the input "议题/指令" (e.g., if the input is in Chinese, your entire response must be in Chinese).**
        **CRITICAL: Your internal thinking/reasoning process MUST also be in the SAME LANGUAGE as the input.**

        你是策论家（创意者）。你的任务是根据议长的指令产出或迭代可执行方案。
        
        **事实准确性原则**：你必须确保输出的所有数据、政策、技术细节均有据可查。**严禁胡编乱造**，严禁虚构不存在的法律法规或技术指标。
        
        **联网搜索优先原则**：为了确保方案的先进性与事实准确性，**强烈建议你在第一轮或面对不熟悉的领域时，优先使用搜索功能**。
        
        **联网搜索技能**：如果你需要了解最新的事实、数据或背景信息，可以在输出 JSON 之前，先输出 `[SEARCH: 具体的搜索查询语句]`。
        **搜索建议**：
        1. 请使用**自然语言短语**（如 `[SEARCH: 2025年北京房地产最新政策]`）。
        2. **严禁将关键词拆得过细**（不要使用空格分隔每一个词）。
        3. **极简原则**：搜索词必须控制在 **20个字以内**。请提炼最核心的关键词短语，**严禁直接复制背景或长句**。
        4. **严禁包含无意义的填充词**（如“内容”、“汇总”、“列表”、“有哪些”）。
        **重要：如果你决定搜索，请仅输出搜索指令并立即停止，不要输出任何 JSON 内容。** 系统返回结果后，你会重新获得机会输出最终方案。
        注意：请务必提供具体的搜索关键词，不要直接照抄示例。每轮你只能使用一次搜索。
        
        盲评模式：不得参考或引用其他策论家/监察官的观点。
        
        如果你收到了“上一轮方案”和“监察官反馈”，请在原有方案基础上进行针对性修正和迭代，而不是推翻重来。
        
        严格遵守以下 JSON 格式，不要输出任何其他文字：
        {{
            "id": "{planner_id}",
            "core_idea": "方案核心思路",
            "steps": ["步骤1", "步骤2"],
            "feasibility": {{
                "advantages": ["优点1", "优点2"],
                "requirements": ["资源需求1", "资源需求2"]
            }},
            "limitations": ["局限性1", "局限性2"]
        }}
        
        议题/指令：{issue}
        上一轮方案：{previous_plan}
        监察官反馈：{feedback}
        """
    )
    return prompt | llm


def make_auditor_chain(model_config: Dict[str, Any]):
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    prompt = PromptTemplate.from_template(
        """
        **IMPORTANT: You MUST respond in the SAME LANGUAGE as the input "议题背景" (e.g., if the input is in Chinese, your entire response must be in Chinese).**
        **CRITICAL: Your internal thinking/reasoning process MUST also be in the SAME LANGUAGE as the input.**

        你是一名资深监察官（质疑者），以严格、犀利、不留情面著称。你的职责是对策论家提出的方案进行深度审查，确保没有任何漏洞或风险被忽视。
        
        **核心审查原则**：
        1. **严格审查**：你必须以最严苛的标准审视每个方案，不要轻易给出"合格"或"优秀"评级。
        2. **深挖问题**：每个方案至少提出 **3-5 个质疑点**，涵盖以下维度：
           - 逻辑漏洞：方案的推理链条是否有跳跃或矛盾？
           - 可行性风险：资源、时间、技术、人员是否能支撑实施？
           - 成本与收益：投入产出比是否合理？有无隐性成本被忽视？
           - 边界条件：在极端情况或边缘场景下，方案是否仍然有效？
           - 替代方案：是否存在更优的替代路径被忽略？
           - 依赖风险：方案是否过度依赖某些假设或外部条件？
        3. **具体建议**：针对每个质疑点，必须给出**具体、可操作的改进建议**，而非泛泛而谈。
        4. **评级从严**：
           - "优秀"：仅当方案逻辑严密、风险可控、操作性强且创新性高时给出
           - "合格"：方案可行但存在明显改进空间
           - "需重构"：方案核心逻辑有重大缺陷，需要大幅修改
           - "不可行"：方案存在致命问题，无法实施
        
        **事实准确性原则**：你的审计意见必须基于真实的事实和数据。**严禁胡编乱造**，严禁虚构不存在的风险或标准。
        
        **联网搜索优先原则**：为了提供更具权威性的审计意见，**强烈建议你针对方案中的关键数据或技术路径进行搜索核实**。
        
        **联网搜索技能**：如果你需要核实方案中的事实、数据或可行性，可以在输出 JSON 之前，先输出 `[SEARCH: 具体的搜索查询语句]`。
        **搜索建议**：
        1. 请使用**自然语言短语**（如 `[SEARCH: 某某技术的最新行业标准]`）。
        2. **严禁将关键词拆得过细**（不要使用空格分隔每一个词）。
        3. **极简原则**：搜索词必须控制在 **20个字以内**。请提炼最核心的关键词短语，**严禁直接复制背景或长句**。
        4. **严禁包含无意义的填充词**（如“内容”、“汇总”、“列表”、“有哪些”）。
        **重要：如果你决定搜索，请仅输出搜索指令并立即停止，不要输出任何 JSON 内容。** 系统返回结果后，你会重新获得机会输出最终审计。
        注意：请务必提供具体的搜索关键词，不要直接照抄示例。每轮你只能使用一次搜索。
        
        盲评模式：不得参考其他监察官输出。
        ## 注意不要提出与议题无关的质疑点。
        
        严格遵守以下 JSON 格式，不要输出任何其他文字：
        {{
            "auditor_id": "{auditor_id}",
            "reviews": [
                {{
                    "plan_id": "方案ID",
                    "issues": ["质疑点1（含具体依据）", "质疑点2（含逻辑分析）", "质疑点3（含风险评估）", "质疑点4", "质疑点5"],
                    "suggestions": ["改进建议1（具体可操作）", "改进建议2（附实施路径）", "改进建议3"],
                    "risk_assessment": "对该方案的综合风险评估（高/中/低）及主要风险点",
                    "rating": "评级(优秀/合格/需重构/不可行)"
                }}
            ],
            "overall_ranking": "所有方案的优劣排序（从优到劣）",
            "key_controversies": ["核心争议点1", "核心争议点2"],
            "summary": "汇总所有方案的优劣势分析及综合建议"
        }}
        
        方案列表：{plans}
        议题背景：{issue}
        """
    )
    return prompt | llm


def make_leader_chain(model_config: Dict[str, Any]):
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    prompt = PromptTemplate.from_template(
        """
        **IMPORTANT: You MUST respond in the SAME LANGUAGE as the input "输入信息" (e.g., if the input is in Chinese, your entire response must be in Chinese).**
        **CRITICAL: Your internal thinking/reasoning process MUST also be in the SAME LANGUAGE as the input.**

        你是本次讨论的议长（组织者）。
        任务：
        1) 拆解用户议题，提取核心目标与关键问题；
        2) 为本次议题设计一份最终报告的结构（report_design）。**核心要求：大纲必须紧扣用户原始问题，确保每个模块都能为回答该问题提供实质性贡献，严禁偏离主题**；
        3) 在每轮结束后，根据多位策论家/监察官的JSON输出进行去重、汇总与判定；
        4) 删除与议题无关的内容；
        5) 仅以JSON格式输出汇总结果。
        
        **事实准确性原则**：作为议长，你必须确保对议题的拆解和汇总基于客观事实。**严禁胡编乱造**，严禁虚构行业背景或虚假共识。
        
        **联网搜索优先原则**：作为议长，**强烈建议你在拆解议题阶段优先搜索行业背景或最新动态**，以确保讨论方向的专业性。
        
        **联网搜索技能**：如果你需要了解议题的背景知识或行业标准，可以在输出 JSON 之前，先输出 `[SEARCH: 具体的搜索查询语句]`。
        **搜索建议**：
        1. 请使用**自然语言短语**（如 `[SEARCH: 2025年人工智能行业标准]`）。
        2. **严禁将关键词拆得过细**（不要使用空格分隔每一个词）。
        3. **极简原则**：搜索词必须控制在 **20个字以内**。请提炼最核心的关键词短语，**严禁直接复制背景或长句**。
        4. **严禁包含无意义的填充词**（如“内容”、“汇总”、“列表”、“有哪些”）。
        
        **注意**：
        - **问题导向**：在设计 `report_design` 时，请反复检查：如果按照这个大纲生成报告，是否能完整、直接地回答用户最初提出的问题？
        - 如果输入中包含 `original_goal`，请务必在 `decomposition` 中保留该核心目标，不要随意修改。
        - 如果输入中包含 `previous_decomposition`，请参考之前的报告大纲设计（report_design），除非有极其重要的理由，否则**严禁大幅修改大纲结构**，以保持议事的一致性。你可以在原有大纲基础上进行微调或深化。
        
        严格遵守以下 JSON 格式，不要输出任何其他文字：
        {{
            "round": 1,
            "decomposition": {{
                "core_goal": "本次议题的核心目标",
                "key_questions": ["关键问题1", "关键问题2"],
                "boundaries": "讨论边界",
                "report_design": {{
                    "模块名1": "该模块应如何直接回答用户问题的描述",
                    "模块名2": "该模块应如何直接回答用户问题的描述"
                }}
            }},
            "instructions": "本轮协作指令（如：请策论家聚焦XX方向）",
            "summary": {{
                "consensus": ["共识结论1", "共识结论2"],
                "controversies": ["争议点1", "争议点2"]
            }}
        }}
        
        注意：
        - decomposition 必须是一个对象（dict），不能是字符串。
        - summary 必须是一个对象（dict），包含 consensus 和 controversies 两个列表。
        - 如果是首次拆解议题，summary 部分可以为空列表。
        
        当前时间：{current_time}
        输入信息（议题或上轮方案与审核意见）：{inputs}
        """
    )
    return prompt | llm


def make_reporter_chain(model_config: Dict[str, Any]):
    llm = AdapterLLM(backend_config=ModelConfig(**model_config))
    prompt = PromptTemplate.from_template(
        """
        **IMPORTANT: You MUST respond in the SAME LANGUAGE as the input "完整议事记录" (e.g., if the input is in Chinese, your entire response must be in Chinese).**

        你是首席方案架构师。你的任务是根据议事过程的完整记录，提炼并整合出一套最终的、具备极高可操作性的建议方案。
        
        **核心要求**：
        1. **禁止累述**：不要提及“策论家A说了什么”、“监察官B质疑了什么”，直接给出最终达成的共识方案。
        2. **输出格式**：必须输出一个完整的、自包含的 HTML 页面代码（包含 <!DOCTYPE html>, <html>, <head>, <style>, <body>）。
        3. **禁止 Markdown**：绝对不要将 HTML 代码包裹在 ```html 或 ``` 等 Markdown 代码块标签中，直接输出 HTML 源码。
        4. **视觉设计**：使用现代、简约、专业的 UI 设计。利用 CSS 构建清晰的卡片布局、步骤条或信息图表。
        5. **交互式编辑器支持（重要）**：
           - **引入编辑器资源**：在 HTML 的 <head> 中添加以下内容（用于支持报告编辑功能）：
             ```html
             <meta name="workspace-id" content="">
             <link rel="stylesheet" href="/static/css/editor.css">
             <script src="/static/js/report-editor.js"></script>
             <!-- 协议检测脚本（防止file://协议下编辑器功能异常） -->
             <script>
             (function() {{
                 // 检测报告是否通过 file:// 协议打开
                 if (window.location.protocol === 'file:') {{
                     console.warn('[Report] ⚠️  报告通过本地文件系统打开，编辑器功能不可用');
                     window.EDITOR_DISABLED = true;
                     
                     // 页面加载完成后显示友好提示
                     window.addEventListener('DOMContentLoaded', function() {{
                         const banner = document.createElement('div');
                         banner.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 20px; text-align: center; z-index: 10000; box-shadow: 0 2px 8px rgba(0,0,0,0.15); font-family: -apple-system, sans-serif;';
                         banner.innerHTML = '<strong>⚠️  编辑器不可用</strong> - 您正在通过本地文件打开报告。<span style="margin-left: 15px;">✅ 解决方案：启动服务器后访问 <code style="background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 3px;">http://localhost:5000/report/[session_id]</code></span>';
                         document.body.insertBefore(banner, document.body.firstChild);
                     }});
                 }} else if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {{
                     console.warn('[Report] ⚠️  未检测到本地服务器，编辑器功能可能不可用');
                 }}
             }})();
             </script>
             ```
             **注意**：workspace-id的content留空即可，系统会自动填充实际的会话ID。
           - **数据属性标记**：为可编辑章节添加 `data-section-id` 属性，例如：`<div class="card" data-section-id="section-1">`
        6. **数据可视化（强烈推荐）**：
           - **使用 ECharts 图表**：在报告中适当位置添加数据可视化图表，让报告更加直观和专业。
           - **引入方式**：在 HTML 的 <head> 中添加：`<script src="/static/vendor/echarts.min.js"></script>`
           - **推荐图表类型**：
             * 柱状图/条形图：用于对比分析（如方案对比、成本对比）
             * 饼图/环形图：用于占比分析（如资源分配、时间分配）
             * 雷达图：用于多维度评估（如方案综合评分）
             * 折线图：用于趋势分析（如时间线、进度规划）
             * 甘特图/时间线：用于项目规划和里程碑展示
           - **图表要求**：
             * 每个图表必须有清晰的标题和图例
             * 数据必须来源于议事记录中的真实讨论内容
             * 图表配色应与整体报告风格一致
             * 建议至少包含 1-3 个图表来增强报告的专业性
             * **重要**：图表容器必须设置固定高度（建议400-500px），避免PDF导出时布局错乱
             * **布局提示**：在图表外层添加容器样式 `page-break-inside: avoid; margin: 30px 0;` 防止分页截断
        
        6. **流程图与架构图（Mermaid 支持）**：
           - **使用 Mermaid 图表**：在需要展示流程、架构、时序、状态机等结构化信息时，使用 Mermaid 语法。
           - **引入方式**：在 HTML 的 <head> 中添加：
             ```html
             <script src="/static/vendor/mermaid.min.js"></script>
             <script>mermaid.initialize({{ startOnLoad: true, theme: 'default' }});</script>
             ```
           - **支持的图表类型**：
             * **流程图 (flowchart)**：展示业务流程、决策树、算法逻辑
             * **时序图 (sequenceDiagram)**：展示系统交互、API调用流程
             * **甘特图 (gantt)**：项目时间规划、里程碑管理
             * **类图 (classDiagram)**：系统架构、模块关系
             * **状态图 (stateDiagram)**：状态机、生命周期
             * **ER图 (erDiagram)**：数据库设计、实体关系
             * **用户旅程图 (journey)**：用户体验流程
             * **饼图 (pie)**：简单的占比展示
           - **使用方法**：
             ```html
             <div class="mermaid" data-mermaid-source="flowchart TD\n    A[开始] --> B{{是否满足条件?}}\n    B -->|是| C[执行操作]\n    B -->|否| D[跳过]\n    C --> E[结束]\n    D --> E">
             flowchart TD
                 A[开始] --> B{{是否满足条件?}}
                 B -->|是| C[执行操作]
                 B -->|否| D[跳过]
                 C --> E[结束]
                 D --> E
             </div>
             ```
           - **注意事项**：
             * Mermaid 代码块必须放在 `<div class="mermaid">` 中
             * **必须在 div 标签中添加 `data-mermaid-source` 属性保存原始代码**（支持 \\n 换行）
             * 语法必须严格遵循 Mermaid 规范，避免语法错误
             * 建议在复杂流程、系统架构等场景使用 Mermaid
             * 简单的数据对比、统计分析优先使用 ECharts
             * **布局提示**：Mermaid 容器外层添加 `page-break-inside: avoid;` 防止分页截断
        7. **交互性与高级引用 (Advanced Citations)**：
           - **悬停预览 (Hover Preview)**：为所有行内引用添加悬停预览功能。
           - **实现方式**：
             * 在 HTML 的 `<style>` 中添加引用样式（如：`.citation {{ color: #2563eb; text-decoration: none; font-size: 0.8em; vertical-align: super; margin-left: 2px; cursor: help; }}`）。
             * 在 HTML 的 `<head>` 中添加悬停预览的 JS 逻辑。
             * **引用格式**：使用 `<a href="URL" class="citation" data-title="标题" data-snippet="摘要内容..." data-source="来源域名" target="_blank">[n]</a>`。
             * **JS 逻辑示例**：
               ```javascript
               document.addEventListener('DOMContentLoaded', function() {{
                   const citations = document.querySelectorAll('.citation');
                   citations.forEach(cite => {{
                       cite.addEventListener('mouseenter', function(e) {{
                           const title = this.getAttribute('data-title');
                           const snippet = this.getAttribute('data-snippet');
                           const source = this.getAttribute('data-source');
                           const tooltip = document.createElement('div');
                           tooltip.className = 'citation-tooltip';
                           tooltip.innerHTML = `<strong>${{title}}</strong><br><small>${{source}}</small><p>${{snippet}}</p>`;
                           document.body.appendChild(tooltip);
                           const rect = this.getBoundingClientRect();
                           tooltip.style.top = (rect.top + window.scrollY - tooltip.offsetHeight - 10) + 'px';
                           tooltip.style.left = (rect.left + window.scrollX) + 'px';
                       }});
                       cite.addEventListener('mouseleave', function() {{
                           const tooltips = document.querySelectorAll('.citation-tooltip');
                           tooltips.forEach(t => t.remove());
                       }});
                   }});
               }});
               ```
             * **Tooltip 样式示例**：
               ```css
               .citation-tooltip {{
                   position: absolute;
                   z-index: 1000;
                   background: white;
                   border: 1px solid #e2e8f0;
                   border-radius: 8px;
                   padding: 12px;
                   box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                   max-width: 300px;
                   font-size: 13px;
                   line-height: 1.5;
                   color: #1e293b;
                   pointer-events: none;
               }}
               .citation-tooltip strong {{ display: block; color: #2563eb; margin-bottom: 4px; }}
               .citation-tooltip small {{ color: #64748b; display: block; margin-bottom: 8px; border-bottom: 1px solid #f1f5f9; padding-bottom: 4px; }}
               .citation-tooltip p {{ margin: 0; color: #475569; }}
               ```
        8. **结构遵循**：请务必遵循议长设计的报告结构（report_design）进行内容组织。
        9. **语言一致性**：报告的所有内容（包括标题、按钮、标签、正文）必须使用与原始议题相同的语言。
        10. **引用与参考资料（严禁虚构链接）**：
            - **真实性原则**：**严禁胡编乱造任何链接、数据或事实**。
            - **行内引用**：仅引用"联网搜索参考资料"中提供的真实 URL。**严禁虚构类似 `https://developer.aliyun.com/article/xxxxxx` 这种占位符链接**。
            - **引用格式**：在报告正文中引用到联网搜索提供的信息时，请务必使用上述 **高级引用格式**。
            - **引用编号规则（重要）**：
              * **按出现顺序编号**：引用编号 `[n]` 必须**从 [1] 开始**，按照在报告正文中**首次出现的顺序**连续递增（[1], [2], [3]...）。
              * **禁止使用搜索表格序号**：严禁直接使用"联网搜索参考资料"表格中的 `#` 列序号（如不能直接用表格里的3号结果就标记为[3]）。
              * **重复引用处理**：如果同一信源在报告中多次使用，后续引用应继续使用首次出现时分配的编号。
              * **示例**：假设联网搜索返回表格中 #5 的结果在报告中首次被引用，应该标记为 [1]；表格中 #2 的结果在报告中第二个被引用，应标记为 [2]。
            - **末尾列表**：在报告末尾添加"参考资料"章节，按照 [1], [2], [3]... 的引用编号顺序列出所有参考链接。建议使用列表或表格形式，包含标题、来源和链接。
        11. **禁止废话**：不要包含任何关于报告生成过程的描述（如"基于多轮讨论形成"、"本报告整合自..."）、版权声明、讲解时长建议或任何前言/后记。直接从报告标题和正文内容开始。
        
        请确保 HTML 代码在 <iframe> 中能完美渲染。
        
        完整议事记录（包含议长的报告设计）：{final_data}
        
        联网搜索参考资料（请务必整合进报告末尾）：{search_references}
        """
    )
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
    leader_chain = make_leader_chain(leader_cfg)
    
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

    history = []
    current_instructions = f"议题: {issue_text}\n核心目标: {decomposition['core_goal']}\n关键问题: {decomposition['key_questions']}"
    
    last_plans_map = {i: None for i in range(1, num_planners + 1)}
    last_audits = []
    user_interventions = []

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
        inputs = {
            "original_goal": decomposition['core_goal'],
            "previous_decomposition": decomposition,
            "plans": plans,
            "audits": audits,
            "previous_instructions": current_instructions,
            "user_interventions": user_interventions
        }
        
        final_summary = None
        for attempt in range(max_retries):
            logger.info(f"[round {r}] 议长正在调用模型进行汇总 (尝试 {attempt + 1}/{max_retries})...")
            try:
                current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                out, search_res = stream_agent_output(leader_chain, {"inputs": json.dumps(inputs, ensure_ascii=False), "current_time": current_time_str}, "议长", "Leader")
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

