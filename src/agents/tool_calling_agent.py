"""
Tool-Based Agent Streaming - 统一的Function Calling Agent执行器

替代原有的PromptTemplate + [SEARCH:] 标记检测机制，
使用标准的OpenAI Function Calling工具调用流程。
"""

import json
import uuid
import re
from typing import Dict, Any, List, Tuple, Optional

from src.agents.langchain_llm import AdapterLLM, ModelConfig
from src.agents.model_adapter import call_model_with_tools
from src.agents.meta_tools import get_tools_for_role, execute_tool, format_tool_result_for_llm
from src.utils.logger import logger


def send_web_event(event_type: str, **kwargs):
    """发送事件到 Web 监控面板（复用原有函数）"""
    try:
        import requests
        url = "http://127.0.0.1:5000/api/update"
        payload = {"type": event_type, **kwargs}
        requests.post(url, json=payload, timeout=1)
    except Exception:
        pass


def stream_tool_calling_agent(
    role_type: str,
    agent_name: str,
    system_prompt: str,
    user_prompt: str,
    model_config: Dict[str, Any],
    event_type: str = "agent_action",
    max_tool_iterations: int = 5
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    统一的Function Calling Agent执行器
    
    Args:
        role_type: 角色类型 (meta/leader/planner/auditor/reporter/report_auditor)
        agent_name: Agent显示名称（如"策论家-1"）
        system_prompt: 系统提示词
        user_prompt: 用户提示词（包含所有输入变量）
        model_config: 模型配置 {"type": "deepseek", "model": "deepseek-reasoner"}
        event_type: Web事件类型
        max_tool_iterations: 最大工具调用迭代次数
    
    Returns:
        (final_content: str, tool_calls_history: List[Dict])
        - final_content: 最终的完整输出内容
        - tool_calls_history: 工具调用历史记录
    """
    # 获取该角色可用的工具
    tool_executors, tool_schemas = get_tools_for_role(role_type)
    
    if not tool_schemas:
        logger.warning(f"[{agent_name}] No tools available for role_type: {role_type}")
    
    logger.info(f"[{agent_name}] Starting tool-calling agent with {len(tool_schemas)} tools: {[s['function']['name'] for s in tool_schemas]}")
    
    # 初始化消息历史
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    full_content = ""
    tool_calls_history = []
    chunk_id = str(uuid.uuid4())
    
    # 先发送空占位符
    if event_type == "agent_action":
        send_web_event(event_type, agent_name=agent_name, role_type=role_type, content="", chunk_id=chunk_id)
    
    # 工具调用迭代循环
    for iteration in range(max_tool_iterations):
        logger.info(f"[{agent_name}] Tool-calling iteration {iteration + 1}/{max_tool_iterations}")
        
        # 调用模型（支持工具调用）
        try:
            response = call_model_with_tools(
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
                backend=model_config.get("type", "deepseek"),
                model=model_config.get("model"),
                stream=True
            )
            
            # 流式处理响应
            iteration_content = ""
            tool_calls = []
            
            for chunk in response:
                # 处理DeepSeek R1的reasoning内容
                reasoning = chunk.get("reasoning", "")
                if reasoning:
                    send_web_event(event_type, agent_name=agent_name, role_type=role_type, 
                                   reasoning=reasoning, chunk_id=chunk_id)
                
                # 处理文本内容
                content_delta = chunk.get("content", "")
                if content_delta:
                    iteration_content += content_delta
                    full_content += content_delta
                    send_web_event(event_type, agent_name=agent_name, role_type=role_type, 
                                   content=content_delta, chunk_id=chunk_id)
                
                # 处理工具调用
                tool_call_chunk = chunk.get("tool_calls")
                if tool_call_chunk:
                    # OpenAI格式的tool_calls是数组
                    if isinstance(tool_call_chunk, list):
                        tool_calls.extend(tool_call_chunk)
                    else:
                        tool_calls.append(tool_call_chunk)
            
            logger.info(f"[{agent_name}] Iteration {iteration + 1} completed. Content: {len(iteration_content)} chars, Tool calls: {len(tool_calls)}")
            
            # 如果没有工具调用，说明Agent完成了输出
            if not tool_calls:
                logger.info(f"[{agent_name}] No tool calls detected, agent finished.")
                break
            
            # 执行工具调用
            logger.info(f"[{agent_name}] Executing {len(tool_calls)} tool calls...")
            
            # 将assistant的响应添加到消息历史
            assistant_message = {"role": "assistant", "content": iteration_content}
            if tool_calls:
                assistant_message["tool_calls"] = tool_calls
            messages.append(assistant_message)
            
            # 执行每个工具并添加结果到消息历史
            for tool_call in tool_calls:
                tool_name = tool_call.get("function", {}).get("name")
                tool_args_str = tool_call.get("function", {}).get("arguments", "{}")
                tool_call_id = tool_call.get("id", str(uuid.uuid4()))
                
                logger.info(f"[{agent_name}] Calling tool: {tool_name}, args: {tool_args_str[:100]}...")
                
                # 发送工具调用开始事件
                send_web_event(event_type, agent_name=agent_name, role_type=role_type,
                               content=f"\n\n🔧 **调用工具**: {tool_name}\n", chunk_id=chunk_id)
                
                try:
                    # 解析工具参数
                    tool_args = json.loads(tool_args_str)
                    
                    # 执行工具
                    tool_result = execute_tool(tool_name, tool_args)
                    
                    # 格式化结果供LLM理解
                    formatted_result = format_tool_result_for_llm(tool_name, tool_result)
                    
                    # 记录工具调用历史
                    tool_calls_history.append({
                        "tool_name": tool_name,
                        "arguments": tool_args,
                        "result": tool_result,
                        "formatted_result": formatted_result
                    })
                    
                    # 发送工具调用结果事件
                    result_summary = formatted_result[:300] + "..." if len(formatted_result) > 300 else formatted_result
                    send_web_event(event_type, agent_name=agent_name, role_type=role_type,
                                   content=f"\n✅ **工具结果**:\n{result_summary}\n\n", chunk_id=chunk_id)
                    
                    # 将工具结果添加到消息历史
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": formatted_result
                    })
                    
                    logger.info(f"[{agent_name}] Tool {tool_name} executed successfully")
                    
                except json.JSONDecodeError as e:
                    error_msg = f"工具参数解析失败: {str(e)}"
                    logger.error(f"[{agent_name}] {error_msg}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": f"❌ {error_msg}"
                    })
                except Exception as e:
                    error_msg = f"工具执行失败: {str(e)}"
                    logger.error(f"[{agent_name}] {error_msg}", exc_info=True)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": f"❌ {error_msg}"
                    })
            
            # 继续下一次迭代，让LLM根据工具结果继续生成
        
        except Exception as e:
            logger.error(f"[{agent_name}] Model call failed: {e}", exc_info=True)
            error_content = f"\n\n❌ 模型调用失败: {str(e)}\n"
            full_content += error_content
            send_web_event(event_type, agent_name=agent_name, role_type=role_type,
                           content=error_content, chunk_id=chunk_id)
            break
    
    logger.info(f"[{agent_name}] Tool-calling agent finished. Total content: {len(full_content)} chars, Tool calls: {len(tool_calls_history)}")
    
    return full_content, tool_calls_history


# ============ 测试代码 ============

if __name__ == "__main__":
    print("=" * 80)
    print("Testing Tool-Based Agent Streaming")
    print("=" * 80)
    
    # Test配置
    test_model_config = {
        "type": "deepseek",
        "model": "deepseek-reasoner"
    }
    
    test_system_prompt = """你是一个测试Agent，负责回答问题。
你可以使用以下工具：
- web_search: 搜索互联网信息
- list_skills: 列出可用的专业技能
- use_skill: 获取指定技能的完整内容

请根据问题需要自主选择工具使用。"""
    
    test_user_prompt = "请帮我搜索'AI大模型最新进展'，并列出可用的Skills。"
    
    print("\n[Test] Running tool-calling agent...")
    print(f"Role: planner")
    print(f"System prompt length: {len(test_system_prompt)} chars")
    print(f"User prompt: {test_user_prompt}")
    
    final_content, tool_calls = stream_tool_calling_agent(
        role_type="planner",
        agent_name="测试Agent",
        system_prompt=test_system_prompt,
        user_prompt=test_user_prompt,
        model_config=test_model_config,
        event_type="agent_action",
        max_tool_iterations=3
    )
    
    print(f"\n✅ Test completed!")
    print(f"Final content length: {len(final_content)} chars")
    print(f"Tool calls count: {len(tool_calls)}")
    print(f"Tool calls: {[tc['tool_name'] for tc in tool_calls]}")
    
    print("\n" + "=" * 80)
