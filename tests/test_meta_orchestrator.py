#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Meta-Orchestrator完整流程（不涉及真实LLM调用）

测试run_meta_orchestrator和execute_orchestration_plan函数的集成
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.schemas import (
    OrchestrationPlan,
    RequirementAnalysis,
    RolePlanning,
    ExistingRoleMatch,
    RoleToCreate,
    FrameworkSelection,
    FrameworkStageInfo,
    ExecutionConfig,
    PlanSummary
)
from src.agents.langchain_agents import run_meta_orchestrator


class TestOrchestrationPlanSchema:
    """测试OrchestrationPlan Pydantic Schema"""
    
    def test_plan_schema_creation(self):
        """测试创建完整的编排计划"""
        plan = OrchestrationPlan(
            analysis=RequirementAnalysis(
                problem_type="决策类",
                complexity="中等",
                required_capabilities=["逻辑推理", "批判性思维"],
                reasoning="这是一个需要权衡多个方案的决策问题"
            ),
            role_planning=RolePlanning(
                existing_roles=[
                    ExistingRoleMatch(
                        name="planner",
                        display_name="策论家",
                        match_score=0.9,
                        match_reason="擅长提出方案",
                        assigned_count=2
                    )
                ],
                roles_to_create=[
                    RoleToCreate(
                        capability="风险评估",
                        requirement="需要评估方案的潜在风险",
                        assigned_count=1
                    )
                ]
            ),
            framework_selection=FrameworkSelection(
                framework_id="deep_analysis",
                framework_name="深度分析框架",
                selection_reason="问题复杂度适中，需要多轮深入讨论",
                framework_stages=[
                    FrameworkStageInfo(
                        stage_name="问题分析",
                        stage_description="分析问题的核心要素"
                    )
                ]
            ),
            execution_config=ExecutionConfig(
                total_rounds=3,
                agent_counts={"planner": 2, "auditor": 1, "leader": 1},
                estimated_duration="15-20分钟"
            ),
            summary=PlanSummary(
                title="深度分析方案",
                overview="采用深度分析框架，3轮讨论",
                key_advantages=["系统化分析", "多角度论证"],
                potential_risks=["可能耗时较长"]
            )
        )
        
        # 验证schema字段
        assert plan.analysis.problem_type == "决策类"
        assert plan.analysis.complexity == "中等"
        assert len(plan.role_planning.existing_roles) == 1
        assert len(plan.role_planning.roles_to_create) == 1
        assert plan.framework_selection.framework_id == "deep_analysis"
        assert plan.execution_config.total_rounds == 3
        assert len(plan.summary.key_advantages) == 2
    
    def test_plan_schema_serialization(self):
        """测试Plan schema的序列化"""
        plan = OrchestrationPlan(
            analysis=RequirementAnalysis(
                problem_type="分析类",
                complexity="简单",
                required_capabilities=["归纳总结"],
                reasoning="简单的信息整理任务"
            ),
            role_planning=RolePlanning(
                existing_roles=[],
                roles_to_create=[]
            ),
            framework_selection=FrameworkSelection(
                framework_id="simple_discussion",
                framework_name="简单讨论",
                selection_reason="问题简单",
                framework_stages=[]
            ),
            execution_config=ExecutionConfig(
                total_rounds=2,
                agent_counts={"planner": 1, "leader": 1},
                estimated_duration="5-10分钟"
            ),
            summary=PlanSummary(
                title="简单方案",
                overview="快速讨论",
                key_advantages=["高效"]
            )
        )
        
        # 序列化为dict
        plan_dict = plan.dict()
        assert isinstance(plan_dict, dict)
        assert "analysis" in plan_dict
        assert "framework_selection" in plan_dict
        
        # 反序列化
        plan_restored = OrchestrationPlan(**plan_dict)
        assert plan_restored.analysis.problem_type == "分析类"


class TestMetaOrchestratorMocked:
    """使用Mock测试Meta-Orchestrator（不调用真实LLM）"""
    
    @pytest.fixture
    def mock_model_config(self):
        """Mock模型配置"""
        return {
            "backend": "deepseek",
            "model_name": "deepseek-chat",
            "api_key": "mock_key",
            "temperature": 0.7
        }
    
    @pytest.fixture
    def sample_plan(self):
        """示例规划方案"""
        return OrchestrationPlan(
            analysis=RequirementAnalysis(
                problem_type="综合类",
                complexity="复杂",
                required_capabilities=["系统分析", "批判思维", "创新设计"],
                reasoning="问题涉及多个维度，需要综合考虑"
            ),
            role_planning=RolePlanning(
                existing_roles=[
                    ExistingRoleMatch(
                        name="planner",
                        display_name="策论家",
                        match_score=0.85,
                        match_reason="方案设计能力强",
                        assigned_count=3
                    ),
                    ExistingRoleMatch(
                        name="auditor",
                        display_name="监察官",
                        match_score=0.8,
                        match_reason="批判性审查",
                        assigned_count=2
                    )
                ],
                roles_to_create=[]
            ),
            framework_selection=FrameworkSelection(
                framework_id="deep_analysis",
                framework_name="深度分析框架",
                selection_reason="复杂问题需要多阶段深入分析",
                framework_stages=[
                    FrameworkStageInfo(
                        stage_name="问题分解",
                        stage_description="将复杂问题分解为子问题"
                    ),
                    FrameworkStageInfo(
                        stage_name="方案论证",
                        stage_description="逐个论证各子问题的解决方案"
                    ),
                    FrameworkStageInfo(
                        stage_name="综合整合",
                        stage_description="整合各部分形成完整方案"
                    )
                ]
            ),
            execution_config=ExecutionConfig(
                total_rounds=4,
                agent_counts={"planner": 3, "auditor": 2, "leader": 1},
                estimated_duration="25-35分钟",
                special_instructions="重点关注方案的可行性和风险"
            ),
            summary=PlanSummary(
                title="复杂问题深度分析方案",
                overview="采用深度分析框架，4轮讨论，3阶段执行",
                key_advantages=[
                    "系统性分析，避免遗漏",
                    "多角色协作，充分论证",
                    "阶段性推进，降低复杂度"
                ],
                potential_risks=[
                    "耗时较长，需充足时间预算",
                    "Agent数量较多，协调成本高"
                ]
            )
        )
    
    def test_run_meta_orchestrator_mock(self, mock_model_config, sample_plan):
        """测试run_meta_orchestrator（使用Mock LLM响应）"""
        with patch('src.agents.langchain_agents.call_model_with_retry') as mock_call:
            # Mock LLM返回
            mock_call.return_value = sample_plan.json()
            
            # 调用函数
            result = run_meta_orchestrator(
                user_requirement="如何设计一个高可用的分布式系统？",
                model_config=mock_model_config
            )
            
            # 验证返回的plan
            assert isinstance(result, OrchestrationPlan)
            assert result.analysis.complexity == "复杂"
            assert result.framework_selection.framework_id == "deep_analysis"
            assert result.execution_config.total_rounds == 4
    
    def test_plan_validation_errors(self):
        """测试Plan验证错误"""
        # 测试缺少必需字段
        with pytest.raises(Exception):  # Pydantic ValidationError
            OrchestrationPlan(
                analysis=RequirementAnalysis(
                    problem_type="测试",
                    complexity="简单",
                    required_capabilities=[],
                    reasoning="测试"
                )
                # 缺少其他必需字段
            )
    
    def test_framework_selection_validation(self):
        """测试FrameworkSelection验证"""
        # 有效的framework_id
        valid_selection = FrameworkSelection(
            framework_id="simple_discussion",
            framework_name="简单讨论",
            selection_reason="测试",
            framework_stages=[]
        )
        assert valid_selection.framework_id == "simple_discussion"
        
        # framework_id可以是任意字符串（由工具函数验证）
        custom_selection = FrameworkSelection(
            framework_id="custom_framework",
            framework_name="自定义框架",
            selection_reason="测试自定义",
            framework_stages=[]
        )
        assert custom_selection.framework_id == "custom_framework"


class TestExecutionConfigValidation:
    """测试ExecutionConfig的验证逻辑"""
    
    def test_valid_execution_config(self):
        """测试有效的执行配置"""
        config = ExecutionConfig(
            total_rounds=3,
            agent_counts={"planner": 2, "auditor": 1, "leader": 1},
            estimated_duration="10-15分钟"
        )
        
        assert config.total_rounds == 3
        assert config.agent_counts["planner"] == 2
        assert config.special_instructions is None
    
    def test_execution_config_with_special_instructions(self):
        """测试带特殊说明的配置"""
        config = ExecutionConfig(
            total_rounds=5,
            agent_counts={"planner": 3, "auditor": 2, "leader": 1},
            estimated_duration="30分钟",
            special_instructions="需要特别关注安全性问题"
        )
        
        assert config.special_instructions == "需要特别关注安全性问题"
    
    def test_agent_counts_dict(self):
        """测试agent_counts字典"""
        config = ExecutionConfig(
            total_rounds=2,
            agent_counts={
                "planner": 1,
                "auditor": 1,
                "leader": 1,
                "devils_advocate": 1
            },
            estimated_duration="15分钟"
        )
        
        # 应该支持任意角色名称
        assert "devils_advocate" in config.agent_counts
        assert config.agent_counts["devils_advocate"] == 1


class TestRolePlanningLogic:
    """测试角色规划逻辑"""
    
    def test_existing_roles_only(self):
        """测试仅使用现有角色"""
        planning = RolePlanning(
            existing_roles=[
                ExistingRoleMatch(
                    name="planner",
                    display_name="策论家",
                    match_score=0.9,
                    match_reason="完全匹配",
                    assigned_count=2
                )
            ],
            roles_to_create=[]
        )
        
        assert len(planning.existing_roles) == 1
        assert len(planning.roles_to_create) == 0
    
    def test_create_new_roles(self):
        """测试创建新角色"""
        planning = RolePlanning(
            existing_roles=[],
            roles_to_create=[
                RoleToCreate(
                    capability="数据分析",
                    requirement="需要分析大量数据的能力",
                    assigned_count=1
                ),
                RoleToCreate(
                    capability="可视化设计",
                    requirement="将数据转换为可视化图表",
                    assigned_count=1
                )
            ]
        )
        
        assert len(planning.roles_to_create) == 2
        assert planning.roles_to_create[0].capability == "数据分析"
    
    def test_mixed_role_planning(self):
        """测试混合使用现有角色和新角色"""
        planning = RolePlanning(
            existing_roles=[
                ExistingRoleMatch(
                    name="leader",
                    display_name="议长",
                    match_score=1.0,
                    match_reason="必需角色",
                    assigned_count=1
                )
            ],
            roles_to_create=[
                RoleToCreate(
                    capability="专家顾问",
                    requirement="提供专业领域建议",
                    assigned_count=1
                )
            ]
        )
        
        assert len(planning.existing_roles) == 1
        assert len(planning.roles_to_create) == 1


class TestIntegrationScenarios:
    """测试完整的集成场景"""
    
    def test_simple_problem_scenario(self):
        """测试简单问题场景"""
        # 简单问题应该：
        # 1. 使用simple_discussion框架
        # 2. 轮次较少（1-2轮）
        # 3. Agent数量较少
        
        plan = OrchestrationPlan(
            analysis=RequirementAnalysis(
                problem_type="信息整理",
                complexity="简单",
                required_capabilities=["信息归纳"],
                reasoning="简单的信息整理任务"
            ),
            role_planning=RolePlanning(
                existing_roles=[
                    ExistingRoleMatch(
                        name="planner",
                        display_name="策论家",
                        match_score=0.9,
                        match_reason="基本匹配",
                        assigned_count=1
                    ),
                    ExistingRoleMatch(
                        name="leader",
                        display_name="议长",
                        match_score=1.0,
                        match_reason="必需",
                        assigned_count=1
                    )
                ],
                roles_to_create=[]
            ),
            framework_selection=FrameworkSelection(
                framework_id="simple_discussion",
                framework_name="简单讨论框架",
                selection_reason="问题简单，不需要复杂流程",
                framework_stages=[
                    FrameworkStageInfo(
                        stage_name="Planning",
                        stage_description="快速规划"
                    )
                ]
            ),
            execution_config=ExecutionConfig(
                total_rounds=2,
                agent_counts={"planner": 1, "leader": 1},
                estimated_duration="5-8分钟"
            ),
            summary=PlanSummary(
                title="简单讨论方案",
                overview="快速讨论，2轮完成",
                key_advantages=["高效快速", "流程简单"],
                potential_risks=[]
            )
        )
        
        # 验证简单场景特征
        assert plan.analysis.complexity == "简单"
        assert plan.framework_selection.framework_id == "simple_discussion"
        assert plan.execution_config.total_rounds <= 2
        assert sum(plan.execution_config.agent_counts.values()) <= 3
    
    def test_complex_problem_scenario(self):
        """测试复杂问题场景"""
        # 复杂问题应该：
        # 1. 使用deep_analysis或brainstorming框架
        # 2. 轮次较多（3-5轮）
        # 3. Agent数量较多
        # 4. 可能需要创建新角色
        
        plan = OrchestrationPlan(
            analysis=RequirementAnalysis(
                problem_type="综合决策",
                complexity="复杂",
                required_capabilities=["系统分析", "风险评估", "创新思维"],
                reasoning="问题涉及多个维度，需要深入分析"
            ),
            role_planning=RolePlanning(
                existing_roles=[
                    ExistingRoleMatch(
                        name="planner",
                        display_name="策论家",
                        match_score=0.85,
                        match_reason="方案设计",
                        assigned_count=3
                    ),
                    ExistingRoleMatch(
                        name="auditor",
                        display_name="监察官",
                        match_score=0.8,
                        match_reason="风险评估",
                        assigned_count=2
                    )
                ],
                roles_to_create=[
                    RoleToCreate(
                        capability="技术评审",
                        requirement="评估技术可行性",
                        assigned_count=1
                    )
                ]
            ),
            framework_selection=FrameworkSelection(
                framework_id="deep_analysis",
                framework_name="深度分析框架",
                selection_reason="复杂问题需要多阶段深入分析",
                framework_stages=[
                    FrameworkStageInfo(stage_name="分析", stage_description="问题分析"),
                    FrameworkStageInfo(stage_name="论证", stage_description="方案论证"),
                    FrameworkStageInfo(stage_name="综合", stage_description="综合总结")
                ]
            ),
            execution_config=ExecutionConfig(
                total_rounds=4,
                agent_counts={"planner": 3, "auditor": 2, "leader": 1},
                estimated_duration="30-40分钟",
                special_instructions="重点关注技术可行性和风险"
            ),
            summary=PlanSummary(
                title="复杂问题深度分析",
                overview="3阶段，4轮讨论",
                key_advantages=["系统化", "充分论证", "风险可控"],
                potential_risks=["耗时较长", "协调成本高"]
            )
        )
        
        # 验证复杂场景特征
        assert plan.analysis.complexity == "复杂"
        assert plan.framework_selection.framework_id == "deep_analysis"
        assert plan.execution_config.total_rounds >= 3
        assert sum(plan.execution_config.agent_counts.values()) >= 5
        assert len(plan.role_planning.roles_to_create) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
