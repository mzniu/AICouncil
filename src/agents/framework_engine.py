#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
框架执行引擎（FrameworkEngine）

负责根据Framework配置动态编排讨论流程：
1. 按stages顺序执行
2. 将role类型映射到具体Agent
3. 管理stage间的上下文传递
4. 发送实时进度更新
"""

import os
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.agents.frameworks import Framework, FrameworkStage
from src.agents.langchain_agents import (
    stream_agent_output,
    send_web_event,
    clean_json_string,
    make_leader_chain,
    make_planner_chain,
    make_auditor_chain,
    make_devils_advocate_chain,
    make_reporter_chain
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class FrameworkEngine:
    """框架执行引擎
    
    根据Framework定义动态编排多Agent讨论流程。
    """
    
    # Role类型到Chain创建函数的映射表
    ROLE_CHAIN_MAPPING = {
        "leader": make_leader_chain,
        "planner": make_planner_chain,
        "auditor": make_auditor_chain,
        "devils_advocate": make_devils_advocate_chain,
        "reporter": make_reporter_chain,
    }
    
    # Role类型的显示名称（用于Web事件）
    ROLE_DISPLAY_NAMES = {
        "leader": "议长",
        "planner": "策论家",
        "auditor": "监察官",
        "devils_advocate": "质疑官",
        "reporter": "记录员",
    }
    
    def __init__(
        self, 
        framework: Framework, 
        model_config: Dict[str, Any],
        workspace_path: Path,
        session_id: str,
        tenant_id: int = None,
        content_mode: str = "solution"
    ):
        """初始化框架引擎
        
        Args:
            framework: 讨论框架定义
            model_config: 模型配置（backend、model等）
            workspace_path: 工作目录路径
            session_id: 会话ID
            tenant_id: 租户ID（用于加载订阅的Skills）
            content_mode: 内容模式（solution/analysis/research/evaluation/creative/debate）
        """
        self.framework = framework
        self.model_config = model_config
        self.workspace_path = workspace_path
        self.session_id = session_id
        self.tenant_id = tenant_id
        self.content_mode = content_mode
        
        # Stage输出缓存 {stage_name: stage_output}
        self.stage_outputs = {}
        
        # 原始用户需求（用于传递给每个stage）
        self.user_requirement = ""
        
        # 搜索引用记录
        self.all_search_references = []
        
        logger.info(f"[FrameworkEngine] 初始化引擎，框架: {framework.name} (ID: {framework.id})")
    
    def execute(
        self, 
        user_requirement: str, 
        agent_counts: Dict[str, int],
        agent_configs: Optional[Dict[str, Any]] = None,
        role_stage_mapping: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """执行完整的框架流程
        
        Args:
            user_requirement: 用户的原始需求
            agent_counts: 每种角色的Agent数量，如 {"planner": 2, "auditor": 2, "economist": 1}
            agent_configs: 可选的每个Agent的模型配置覆盖
            role_stage_mapping: 专业角色参与的stage映射，如 {"economist": ["证据评估", "替代视角"]}
            
        Returns:
            执行结果字典，包含所有stage的输出和最终总结
        """
        self.user_requirement = user_requirement
        agent_configs = agent_configs or {}
        self.role_stage_mapping = role_stage_mapping or {}
        
        logger.info(f"[FrameworkEngine] 开始执行框架 '{self.framework.name}'")
        logger.info(f"[FrameworkEngine] Agent配置: {agent_counts}")
        if self.role_stage_mapping:
            logger.info(f"[FrameworkEngine] 专业角色映射: {self.role_stage_mapping}")
        
        # 发送框架启动事件
        send_web_event(
            "framework_start",
            message=f"📋 框架启动: {self.framework.name}",
            framework_name=self.framework.name,
            framework_id=self.framework.id,
            total_stages=len(self.framework.stages)
        )
        
        try:
            # 按顺序执行每个stage
            for stage_index, stage in enumerate(self.framework.stages, 1):
                logger.info(f"[FrameworkEngine] 执行Stage {stage_index}/{len(self.framework.stages)}: {stage.name}")
                
                # 发送stage开始事件
                send_web_event(
                    "stage_start",
                    stage_index=stage_index,
                    stage_name=stage.name,
                    stage_description=stage.description,
                    roles=stage.roles,
                    rounds=stage.rounds
                )
                
                # 1. 检查依赖
                if stage.depends_on:
                    self._check_dependencies(stage)
                
                # 2. 创建该stage的Agent chains
                chains = self._create_chains_for_stage(stage, agent_counts, agent_configs)
                
                # 3. 执行stage
                stage_output = self._execute_stage(stage, chains, agent_counts)
                
                # 4. 保存输出到内存
                self.stage_outputs[stage.name] = stage_output
                
                # stage数据已在执行结果中保存到数据库，不再单独写文件
                
                # 发送stage完成事件
                send_web_event(
                    "stage_complete",
                    stage_index=stage_index,
                    stage_name=stage.name,
                    output_summary=self._summarize_stage_output(stage_output)
                )
            
            # 最终综合（如果框架要求）
            final_result = self.stage_outputs
            if self.framework.final_synthesis:
                logger.info("[FrameworkEngine] 执行最终综合...")
                synthesis = self._final_synthesis(agent_configs)
                final_result["final_synthesis"] = synthesis
            
            # 发送框架完成事件
            send_web_event(
                "framework_complete",
                message=f"✅ 框架执行完成: {self.framework.name}",
                total_stages=len(self.framework.stages)
            )
            
            return final_result
            
        except Exception as e:
            logger.error(f"[FrameworkEngine] 执行失败: {e}")
            logger.error(traceback.format_exc())
            send_web_event("error", message=f"❌ 框架执行失败: {str(e)}")
            raise
    
    def _check_dependencies(self, stage: FrameworkStage):
        """检查stage的依赖是否已完成
        
        Args:
            stage: 当前stage
            
        Raises:
            ValueError: 如果依赖的stage未完成
        """
        for dep_name in stage.depends_on:
            if dep_name not in self.stage_outputs:
                raise ValueError(
                    f"Stage '{stage.name}' 依赖的阶段 '{dep_name}' 尚未执行"
                )
        logger.info(f"[FrameworkEngine] Stage '{stage.name}' 依赖检查通过")
    
    def _create_chains_for_stage(
        self, 
        stage: FrameworkStage, 
        agent_counts: Dict[str, int],
        agent_configs: Dict[str, Any]
    ) -> List[tuple]:
        """为stage创建Agent chains
        
        Args:
            stage: Stage配置
            agent_counts: 每种角色的Agent数量
            agent_configs: 每个Agent的模型配置覆盖
            
        Returns:
            List of (chain, agent_id, role_type, display_name) tuples
        """
        from src.agents.langchain_agents import make_generic_role_chain
        from src.agents.role_manager import RoleManager
        
        chains = []
        role_manager = RoleManager()
        
        # 1. 处理框架定义的角色（stage.roles）
        for role_type in stage.roles:
            # 获取该角色的数量（默认使用stage的min_agents）
            count = agent_counts.get(role_type, stage.min_agents)
            count = max(stage.min_agents, min(count, stage.max_agents))
            
            # 优先使用固定的角色类型映射
            make_chain_func = self.ROLE_CHAIN_MAPPING.get(role_type)
            
            # 如果不是固定角色类型，尝试从RoleManager加载自定义角色
            if not make_chain_func:
                logger.info(f"[FrameworkEngine] 检测到自定义角色: {role_type}，尝试从RoleManager加载")
                
                # 验证角色是否存在
                role_config = role_manager.get_role(role_type)
                if not role_config:
                    logger.warning(f"[FrameworkEngine] 未找到角色 '{role_type}'，跳过")
                    continue
                
                # 使用通用chain创建函数
                display_name = role_config.display_name
                logger.info(f"[FrameworkEngine] 成功加载自定义角色: {role_type} ({display_name})")
            else:
                display_name = self.ROLE_DISPLAY_NAMES.get(role_type, role_type)
            
            # 创建多个Agent
            for i in range(count):
                agent_id = f"{role_type}_{i+1}"
                
                # 获取该Agent的配置（优先使用agent_configs中的覆盖配置）
                agent_model_config = agent_configs.get(agent_id) or self.model_config
                
                # 创建chain
                if make_chain_func:
                    # 固定角色类型（某些角色需要特殊参数）
                    if role_type == "leader":
                        chain = make_chain_func(agent_model_config, is_final_round=False, tenant_id=self.tenant_id)
                    elif role_type == "devils_advocate":
                        chain = make_chain_func(agent_model_config, stage="general", tenant_id=self.tenant_id)
                    elif role_type == "planner":
                        chain = make_chain_func(agent_model_config, tenant_id=self.tenant_id, content_mode=self.content_mode)
                    elif role_type == "auditor":
                        chain = make_chain_func(agent_model_config, tenant_id=self.tenant_id, content_mode=self.content_mode)
                    else:
                        chain = make_chain_func(agent_model_config, tenant_id=self.tenant_id)
                else:
                    # 自定义角色，使用通用chain创建函数
                    stage_name = list(role_config.stages.keys())[0] if role_config.stages else "default"
                    chain = make_generic_role_chain(role_type, stage_name, agent_model_config, tenant_id=self.tenant_id)
                
                chains.append((chain, agent_id, role_type, display_name))
                
                logger.info(f"[FrameworkEngine] 创建Agent: {agent_id} ({display_name})")
        
        # 2. 处理通过 role_stage_mapping 映射到此stage的专业角色
        if hasattr(self, 'role_stage_mapping') and self.role_stage_mapping:
            for role_name, stage_names in self.role_stage_mapping.items():
                # 检查该角色是否参与当前stage
                if stage.name in stage_names:
                    # 检查该角色是否在agent_counts中配置
                    if role_name not in agent_counts:
                        logger.warning(f"[FrameworkEngine] 角色 '{role_name}' 在 role_stage_mapping 中但不在 agent_counts 中，跳过")
                        continue
                    
                    # 检查该角色是否已经在stage.roles中（避免重复添加）
                    if role_name in stage.roles:
                        continue
                    
                    # 先检查角色是否存在
                    if not role_manager.has_role(role_name):
                        logger.warning(f"[FrameworkEngine] 角色 '{role_name}' 不存在于系统中，跳过（可能是议事编排官建议的自定义角色）")
                        continue
                    
                    count = agent_counts.get(role_name, 1)
                    
                    # 从RoleManager加载角色配置
                    role_config = role_manager.get_role(role_name)
                    
                    display_name = role_config.display_name
                    logger.info(f"[FrameworkEngine] 映射专业角色 '{role_name}' ({display_name}) 到 stage '{stage.name}'")
                    
                    # 创建Agent
                    for i in range(count):
                        agent_id = f"{role_name}_{i+1}"
                        agent_model_config = agent_configs.get(agent_id) or self.model_config
                        
                        # 使用通用chain创建函数
                        stage_name_for_role = list(role_config.stages.keys())[0] if role_config.stages else "default"
                        chain = make_generic_role_chain(role_name, stage_name_for_role, agent_model_config, tenant_id=self.tenant_id)
                        
                        chains.append((chain, agent_id, role_name, display_name))
                        logger.info(f"[FrameworkEngine] 创建映射Agent: {agent_id} ({display_name})")
        
        return chains
    
    def _execute_stage(
        self, 
        stage: FrameworkStage, 
        chains: List[tuple],
        agent_counts: Dict[str, int]
    ) -> Dict[str, Any]:
        """执行单个stage
        
        Args:
            stage: Stage配置
            chains: Agent chains列表
            agent_counts: Agent数量配置
            
        Returns:
            Stage输出字典
        """
        stage_output = {
            "stage_name": stage.name,
            "description": stage.description,
            "rounds": stage.rounds,
            "agents": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # 准备上下文（包含用户需求和前置stage的输出）
        context = self._build_stage_context(stage)
        
        # 执行多轮讨论
        for round_num in range(1, stage.rounds + 1):
            logger.info(f"[FrameworkEngine] Stage '{stage.name}' - 轮次 {round_num}/{stage.rounds}")
            
            send_web_event(
                "round_start",
                stage_name=stage.name,
                round=round_num,
                total_rounds=stage.rounds
            )
            
            round_outputs = []
            
            # 🔧 按角色类型分组执行（确保 Auditor 能看到 Planner 的输出）
            # 第一组：非 Auditor 角色（Planner、Leader、专业角色等）
            non_auditor_chains = [(c, aid, rt, dn) for c, aid, rt, dn in chains if rt != 'auditor']
            auditor_chains = [(c, aid, rt, dn) for c, aid, rt, dn in chains if rt == 'auditor']
            
            # 先执行非 Auditor 角色（并行）
            if non_auditor_chains:
                logger.info(f"[FrameworkEngine] 执行 {len(non_auditor_chains)} 个非 Auditor 角色")
                with ThreadPoolExecutor(max_workers=len(non_auditor_chains)) as executor:
                    futures = {}
                    
                    for chain, agent_id, role_type, display_name in non_auditor_chains:
                        # 使用前一轮的输出（第一轮时为空）
                        previous_round = stage_output["agents"] if round_num > 1 else []
                        agent_input = self._build_agent_input(
                            stage, context, round_num, previous_round, role_type, agent_id
                        )
                        
                        future = executor.submit(
                            self._run_agent,
                            chain, agent_id, role_type, display_name, agent_input
                        )
                        futures[future] = (agent_id, display_name)
                    
                    # 收集结果
                    for future in as_completed(futures):
                        agent_id, display_name = futures[future]
                        try:
                            agent_output = future.result()
                            round_outputs.append(agent_output)
                            logger.info(f"[FrameworkEngine] Agent {agent_id} 完成")
                        except Exception as e:
                            logger.error(f"[FrameworkEngine] Agent {agent_id} 执行失败: {e}")
                            logger.error(traceback.format_exc())
            
            # 再执行 Auditor 角色（并行），传入本轮已完成的输出
            if auditor_chains:
                logger.info(f"[FrameworkEngine] 执行 {len(auditor_chains)} 个 Auditor 角色")
                with ThreadPoolExecutor(max_workers=len(auditor_chains)) as executor:
                    futures = {}
                    
                    for chain, agent_id, role_type, display_name in auditor_chains:
                        # Auditor 需要看到本轮 Planner 的输出
                        agent_input = self._build_agent_input(
                            stage, context, round_num, round_outputs, role_type, agent_id
                        )
                        
                        future = executor.submit(
                            self._run_agent,
                            chain, agent_id, role_type, display_name, agent_input
                        )
                        futures[future] = (agent_id, display_name)
                    
                    # 收集结果
                    for future in as_completed(futures):
                        agent_id, display_name = futures[future]
                        try:
                            agent_output = future.result()
                            round_outputs.append(agent_output)
                            logger.info(f"[FrameworkEngine] Agent {agent_id} 完成")
                        except Exception as e:
                            logger.error(f"[FrameworkEngine] Agent {agent_id} 执行失败: {e}")
                            logger.error(traceback.format_exc())
            
            # 保存该轮的输出
            stage_output["agents"].extend(round_outputs)
            
            send_web_event(
                "round_complete",
                stage_name=stage.name,
                round=round_num,
                agents_completed=len(round_outputs)
            )
        
        return stage_output
    
    def _build_stage_context(self, stage: FrameworkStage) -> str:
        """构建stage的上下文（包含前置stage的输出）
        
        Args:
            stage: 当前stage
            
        Returns:
            格式化的上下文字符串
        """
        context_parts = [
            f"# 用户需求\n{self.user_requirement}\n"
        ]
        
        # 添加依赖的stage输出
        if stage.depends_on:
            context_parts.append("\n# 前置阶段输出\n")
            for dep_name in stage.depends_on:
                dep_output = self.stage_outputs.get(dep_name, {})
                context_parts.append(f"\n## {dep_name}\n")
                context_parts.append(self._format_stage_output(dep_output))
        
        return "\n".join(context_parts)
    
    def _format_stage_output(self, stage_output: Dict[str, Any]) -> str:
        """格式化stage输出为文本（用于传递给后续stage）
        
        Args:
            stage_output: Stage输出字典
            
        Returns:
            格式化的文本
        """
        lines = []
        
        for agent_data in stage_output.get("agents", []):
            agent_id = agent_data.get("agent_id", "未知")
            content = agent_data.get("content", "")
            lines.append(f"### {agent_id}\n{content}\n")
        
        return "\n".join(lines)
    
    def _build_agent_input(
        self, 
        stage: FrameworkStage, 
        context: str,
        round_num: int,
        previous_round_outputs: List[Dict],
        role_type: str,
        agent_id: str
    ) -> Dict[str, str]:
        """构建Agent的输入变量
        
        Args:
            stage: Stage配置
            context: Stage上下文
            round_num: 当前轮次
            previous_round_outputs: 本stage前面轮次的输出（用于多轮迭代）
            role_type: Agent角色类型（如'planner', 'auditor', 或自定义角色名）
            agent_id: Agent ID（如'planner_1', 'auditor_2'）
            
        Returns:
            输入变量字典
        """
        # 传统角色（planner/auditor）需要特殊的变量格式
        if role_type in ['planner', 'auditor']:
            if role_type == 'planner':
                # Planner需要迭代优化场景的变量
                # 从previous_round_outputs中提取该planner的previous_plan和auditor的feedback
                previous_plan = ""
                feedback = ""
                
                if previous_round_outputs:
                    # 查找该planner上一轮的输出
                    for out in previous_round_outputs:
                        if out.get('agent_id') == agent_id and out.get('role_type') == 'planner':
                            previous_plan = out.get('content', '')
                            break
                    
                    # 查找auditor的反馈
                    auditor_feedbacks = []
                    for out in previous_round_outputs:
                        if out.get('role_type') == 'auditor':
                            auditor_feedbacks.append(out.get('content', ''))
                    
                    if auditor_feedbacks:
                        feedback = "\n\n".join(auditor_feedbacks)
                
                # 构建Stage任务指导（如果在框架模式下）
                stage_task = ""
                if stage.description:
                    stage_task = f"\n\n【本Stage任务】：{stage.description}"
                    if stage.prompt_suffix:
                        stage_task += f"\n【任务要求】：{stage.prompt_suffix}"
                
                # 将Stage任务融入到issue或作为单独的guidance
                enhanced_issue = self.user_requirement
                if stage_task:
                    enhanced_issue = f"{self.user_requirement}{stage_task}\n\n请围绕上述Stage任务提出方案。"
                
                agent_input = {
                    "planner_id": agent_id,
                    "issue": enhanced_issue,
                    "previous_plan": previous_plan,
                    "feedback": feedback
                }
                
            elif role_type == 'auditor':
                # Auditor需要审查planner的方案
                plans_data = []
                if previous_round_outputs:
                    for out in previous_round_outputs:
                        if out.get('role_type') == 'planner':
                            plans_data.append(out.get('content', ''))
                
                logger.info(f"[FrameworkEngine] Auditor {agent_id} 收到 {len(plans_data)} 个方案")
                
                # 构建Stage任务指导
                stage_task = ""
                if stage.description:
                    stage_task = f"\n\n【本Stage审查重点】：{stage.description}"
                    if stage.prompt_suffix:
                        stage_task += f"\n【审查要求】：{stage.prompt_suffix}"
                
                enhanced_issue = self.user_requirement
                if stage_task:
                    enhanced_issue = f"{self.user_requirement}{stage_task}\n\n请围绕上述审查重点进行方案评估。"
                
                agent_input = {
                    "auditor_id": agent_id,
                    "issue": enhanced_issue,
                    "plans": json.dumps(plans_data, ensure_ascii=False) if plans_data else "[]"
                }
            
            logger.info(f"[FrameworkEngine] 为传统角色 {role_type} 构建变量（已注入Stage任务）: {list(agent_input.keys())}")
        
        # 检查是否为自定义角色（不在固定角色映射表中）
        elif role_type not in self.ROLE_CHAIN_MAPPING:
            # 自定义角色：从RoleManager获取input_vars定义
            from src.agents.role_manager import RoleManager
            role_manager = RoleManager()
            role_config = role_manager.get_role(role_type)
            
            if not role_config or not role_config.stages:
                logger.warning(f"[FrameworkEngine] 自定义角色 {role_type} 配置不完整，使用通用变量")
                agent_input = {"inputs": context, "issue": self.user_requirement}
            else:
                # 获取第一个stage的input_vars
                first_stage_name = list(role_config.stages.keys())[0]
                input_vars = role_config.stages[first_stage_name].input_vars
                
                # 根据input_vars构建输入
                agent_input = {}
                for var_name in input_vars:
                    if var_name == "issue" or var_name == "requirement" or var_name == "user_requirement":
                        agent_input[var_name] = self.user_requirement
                    elif var_name == "context" or var_name == "inputs":
                        agent_input[var_name] = context
                    elif var_name == "stage_description":
                        agent_input[var_name] = stage.description
                    elif var_name == "stage_guidance":
                        agent_input[var_name] = stage.prompt_suffix or ""
                    elif var_name == "previous_round" and previous_round_outputs:
                        prev_content = "\n\n".join([
                            f"**{out['agent_id']}**: {out['content']}" 
                            for out in previous_round_outputs
                        ])
                        agent_input[var_name] = prev_content
                    elif var_name == "current_time":
                        agent_input[var_name] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        # 未知变量，设置为空字符串
                        agent_input[var_name] = ""
                        logger.warning(f"[FrameworkEngine] 自定义角色 {role_type} 需要变量 '{var_name}'，但无法自动填充，设置为空")
                
                logger.info(f"[FrameworkEngine] 为自定义角色 {role_type} 构建变量: {list(agent_input.keys())}")
        
        else:
            # 其他固定角色使用通用的Framework变量
            agent_input = {
                "inputs": context,
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "stage_description": stage.description,
                "stage_guidance": stage.prompt_suffix or ""
            }
            
            # 如果有前面轮次的输出，添加到输入中（用于迭代优化）
            if previous_round_outputs:
                prev_content = "\n\n".join([
                    f"**{out['agent_id']}**: {out['content']}" 
                    for out in previous_round_outputs
                ])
                agent_input["previous_round"] = prev_content
        
        return agent_input
    
    def _run_agent(
        self, 
        chain, 
        agent_id: str, 
        role_type: str,
        display_name: str,
        agent_input: Dict[str, str]
    ) -> Dict[str, Any]:
        """执行单个Agent
        
        Args:
            chain: LangChain chain
            agent_id: Agent ID
            role_type: 角色类型
            display_name: 显示名称
            agent_input: 输入变量
            
        Returns:
            Agent输出字典
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[FrameworkEngine] {agent_id} 正在思考 (尝试 {attempt+1}/{max_retries})...")
                
                # 流式输出（会自动发送Web事件）
                output, search_res = stream_agent_output(
                    chain, 
                    agent_input, 
                    display_name, 
                    role_type,
                    event_type="agent_action"
                )
                
                if search_res:
                    self.all_search_references.append(search_res)
                
                # 返回结构化输出
                return {
                    "agent_id": agent_id,
                    "role_type": role_type,
                    "display_name": display_name,
                    "content": output,
                    "timestamp": datetime.now().isoformat(),
                    "attempt": attempt + 1
                }
                
            except Exception as e:
                logger.warning(f"[FrameworkEngine] {agent_id} 执行失败 (尝试 {attempt+1}): {e}")
                if attempt == max_retries - 1:
                    # 最后一次尝试失败，返回错误信息
                    return {
                        "agent_id": agent_id,
                        "role_type": role_type,
                        "display_name": display_name,
                        "content": f"[执行失败] {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                        "error": str(e)
                    }
        
        # 不应该到达这里
        raise RuntimeError(f"Agent {agent_id} 执行失败")
    
    def _final_synthesis(self, agent_configs: Dict[str, Any]) -> Dict[str, Any]:
        """执行最终综合（由Leader总结所有stage的输出）
        
        Args:
            agent_configs: Agent配置
            
        Returns:
            最终综合结果
        """
        # 使用Leader进行最终综合
        leader_config = agent_configs.get("leader") or self.model_config
        leader_chain = make_leader_chain(leader_config, is_final_round=True, tenant_id=self.tenant_id)
        
        # 构建综合输入（包含所有stage的输出）
        synthesis_input = self._build_synthesis_input()
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"[FrameworkEngine] 议长正在进行最终综合 (尝试 {attempt+1}/{max_retries})...")
                
                output, search_res = stream_agent_output(
                    leader_chain,
                    {"inputs": synthesis_input, "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                    "议长",
                    "leader",
                    event_type="synthesis"
                )
                
                if search_res:
                    self.all_search_references.append(search_res)
                
                # 尝试解析JSON
                cleaned = clean_json_string(output)
                if cleaned:
                    parsed = json.loads(cleaned)
                    return {
                        "content": output,
                        "parsed": parsed,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    # 没有JSON，直接返回文本
                    return {
                        "content": output,
                        "timestamp": datetime.now().isoformat()
                    }
                    
            except Exception as e:
                logger.warning(f"[FrameworkEngine] 最终综合尝试 {attempt+1} 失败: {e}")
                if attempt == max_retries - 1:
                    return {
                        "content": f"[综合失败] {str(e)}",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
    
    def _build_synthesis_input(self) -> str:
        """构建最终综合的输入（包含所有stage的输出）
        
        Returns:
            格式化的输入字符串
        """
        lines = [
            f"# 用户需求\n{self.user_requirement}\n",
            f"\n# 框架: {self.framework.name}\n{self.framework.description}\n",
            "\n# 各阶段输出\n"
        ]
        
        for stage_name, stage_output in self.stage_outputs.items():
            lines.append(f"\n## {stage_name}\n")
            lines.append(self._format_stage_output(stage_output))
        
        return "\n".join(lines)
    
    def _summarize_stage_output(self, stage_output: Dict[str, Any]) -> str:
        """生成stage输出的摘要（用于Web事件）
        
        Args:
            stage_output: Stage输出字典
            
        Returns:
            摘要文本
        """
        agent_count = len(stage_output.get("agents", []))
        return f"完成 {agent_count} 个Agent的输出"
    
    def get_all_outputs(self) -> Dict[str, Any]:
        """获取所有stage的输出
        
        Returns:
            完整的输出字典
        """
        return {
            "framework": {
                "id": self.framework.id,
                "name": self.framework.name,
                "description": self.framework.description
            },
            "user_requirement": self.user_requirement,
            "stages": self.stage_outputs,
            "search_references": self.all_search_references
        }


# 自检脚本
if __name__ == "__main__":
    print("🧪 FrameworkEngine 自检\n")
    
    from src.agents.frameworks import get_framework
    
    # 测试1：创建引擎实例
    print("【测试1】创建FrameworkEngine实例")
    framework = get_framework("roberts_rules")
    engine = FrameworkEngine(
        framework=framework,
        model_config={"type": "deepseek", "model": "deepseek-chat"},
        workspace_path=Path("./test_workspace"),
        session_id="test_001"
    )
    print(f"  ✅ 引擎创建成功，框架: {engine.framework.name}")
    
    # 测试2：检查role映射
    print("\n【测试2】检查Role映射")
    for role_type in ["leader", "planner", "auditor"]:
        make_chain = FrameworkEngine.ROLE_CHAIN_MAPPING.get(role_type)
        display_name = FrameworkEngine.ROLE_DISPLAY_NAMES.get(role_type)
        print(f"  {role_type}: {make_chain.__name__} -> {display_name}")
    
    # 测试3：模拟创建chains
    print("\n【测试3】模拟创建chains")
    stage = framework.stages[0]
    print(f"  Stage: {stage.name}")
    print(f"  Roles: {stage.roles}")
    print(f"  Min agents: {stage.min_agents}, Max agents: {stage.max_agents}")
    
    # 注意：不能真正创建chains（需要模型配置），只验证逻辑
    agent_counts = {"leader": 1}
    chains = []
    for role_type in stage.roles:
        count = agent_counts.get(role_type, stage.min_agents)
        count = max(stage.min_agents, min(count, stage.max_agents))
        print(f"  将创建 {count} 个 {role_type} agents")
    
    print("\n✅ 所有自检通过")
    print("\n📝 注意：实际执行需要配置API Key")
    print("    可以通过demo_runner.py或execute_orchestration_plan()测试完整功能")
