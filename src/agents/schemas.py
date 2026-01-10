from pydantic import BaseModel
from typing import List, Dict, Optional

# 策论家 schema
class PlanFeasibility(BaseModel):
    advantages: List[str]
    requirements: List[str]

class PlanSchema(BaseModel):
    id: str
    core_idea: str
    steps: List[str]
    feasibility: PlanFeasibility
    limitations: List[str]

# 监察官 schema
class ReviewItem(BaseModel):
    plan_id: str
    issues: List[str]
    suggestions: List[str]
    rating: str

class AuditorSchema(BaseModel):
    auditor_id: str
    reviews: List[ReviewItem]
    summary: str

# 议长 schema
class Decomposition(BaseModel):
    core_goal: str
    key_questions: List[str]
    boundaries: Optional[str]
    report_design: Optional[Dict[str, str]] = None # 报告结构设计：{"模块名": "内容要求"}

class LeaderSummary(BaseModel):
    round: int
    decomposition: Decomposition
    instructions: str
    is_final_round: bool  # 标识是否为最后一轮
    summary: Dict[str, List[str]]
    next_round_focus: Optional[str] = None  # 下一轮讨论重点（仅非最后一轮填充）
    da_feedback_response: Optional[str] = None # 对质疑官反馈的回应（如有）

# Devil's Advocate (质疑官) schema
class ChallengeItem(BaseModel):
    """单个质疑项"""
    target: str  # 质疑目标（假设/结论/分解维度等）
    challenge_type: str  # 类型：假设挑战/逻辑质疑/遗漏识别/反例/极端场景
    reasoning: str  # 质疑的推理过程
    alternative_perspective: str  # 提供的替代视角
    severity: str  # 严重程度：critical/important/minor

class DecompositionChallenge(BaseModel):
    """对问题拆解的质疑"""
    missing_dimensions: List[str]  # 遗漏的维度
    hidden_assumptions: List[str]  # 隐含假设
    alternative_frameworks: List[str]  # 替代的拆解方式
    extreme_scenario_issues: List[str]  # 极端场景下的问题

class SummaryChallenge(BaseModel):
    """对总结的质疑（Phase 1专注于此阶段）"""
    logical_gaps: List[str]  # 逻辑跳跃或缺口
    missing_points: List[str]  # 遗漏的关键观点
    inconsistencies: List[str]  # 前后矛盾之处
    optimism_bias: Optional[str] = None  # 过度乐观/悲观的倾向

class DevilsAdvocateSchema(BaseModel):
    """Devil's Advocate完整输出（支持多阶段）"""
    round: int
    stage: str  # 当前阶段：decomposition/summary
    
    # 不同阶段的质疑（根据stage选择性填充）
    decomposition_challenge: Optional[DecompositionChallenge] = None
    summary_challenge: Optional[SummaryChallenge] = None
    
    overall_assessment: str  # 整体评价
    critical_issues: List[str]  # 必须解决的关键问题
    recommendations: List[str]  # 改进建议


# 报告审核官 schema（用户参与式修订）
class ContentCheck(BaseModel):
    """内容准确性检查"""
    conclusion_consistency: bool  # 结论是否与议长总结一致
    key_points_coverage: bool  # 关键要点是否覆盖
    data_accuracy: bool  # 数据是否来自讨论内容

class StructureCheck(BaseModel):
    """结构完整性检查"""
    follows_report_design: bool  # 是否遵循议长大纲
    logical_coherence: bool  # 逻辑是否连贯

class ReportRevisionResult(BaseModel):
    """报告审核官修订结果"""
    revision_summary: str  # 修订概要（告诉用户改了什么）
    changes_made: List[str]  # 具体修改列表
    unchanged_reasons: Optional[List[str]] = None  # 未修改的原因（如超出范围）
    warnings: Optional[List[str]] = None  # 警告（如偏离原始讨论）
    content_check: ContentCheck  # 内容检查结果
    structure_check: StructureCheck  # 结构检查结果
    revised_html: str  # 修订后的完整HTML


# 角色设计师 schema
from pydantic import field_validator

class RoleStageDefinition(BaseModel):
    """角色阶段定义"""
    stage_name: str  # 阶段名称，如"规划阶段"
    output_schema: str  # 输出Schema名称，如"PlannerOutput"
    responsibilities: List[str]  # 职责列表（至少1项）
    thinking_style: str  # 思维方式，如"批判性思维"、"创造性思维"
    output_format: str  # 输出格式描述
    
    @field_validator('responsibilities')
    @classmethod
    def validate_responsibilities(cls, v):
        if len(v) == 0:
            raise ValueError('至少需要定义1个职责')
        return v


class FamousPersona(BaseModel):
    """推荐的历史/虚构人物"""
    name: str  # 人物名称
    reason: str  # 推荐理由
    traits: List[str]  # 关键特质（至少1个）
    
    @field_validator('traits')
    @classmethod
    def validate_traits(cls, v):
        if len(v) == 0:
            raise ValueError('至少需要提供1个特质')
        return v


class UIConfig(BaseModel):
    """角色UI配置"""
    icon: str  # emoji图标（单个emoji字符）
    color: str  # 主题色（hex格式，如#3B82F6）
    description_short: str  # 简短描述（15-30字）
    
    @field_validator('icon')
    @classmethod
    def validate_icon(cls, v):
        if len(v) > 15:  # 允许组合emoji（如👨‍👩‍👧‍👦），覆盖99%场景
            raise ValueError('icon应为单个emoji字符或组合emoji')
        return v
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v):
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('color必须是hex格式，如#3B82F6')
        return v
    
    @field_validator('description_short')
    @classmethod
    def validate_description_short(cls, v):
        if len(v) < 5 or len(v) > 50:
            raise ValueError('简短描述长度应在5-50字符之间')
        return v


class RoleDesignOutput(BaseModel):
    """角色设计师完整输出"""
    role_name: str  # 角色技术名称（英文+下划线，如strategic_planner）
    display_name: str  # 显示名称（中文）
    role_description: str  # 角色描述（50-200字）
    stages: List[RoleStageDefinition]  # 参与的阶段（至少1个）
    recommended_personas: List[FamousPersona]  # 推荐人物（0-3个）
    ui: UIConfig  # UI配置（图标、颜色、简短描述）
    
    @field_validator('role_name')
    @classmethod
    def validate_role_name(cls, v):
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError('角色名称必须是小写字母、数字和下划线组合，且以字母开头')
        return v
    
    @field_validator('stages')
    @classmethod
    def validate_stages(cls, v):
        if len(v) == 0:
            raise ValueError('至少需要定义1个阶段')
        return v


# ========== Meta-Orchestrator Schemas ==========

class RequirementAnalysis(BaseModel):
    """需求分析结果"""
    problem_type: str  # 问题类型：决策类/论证类/分析类/综合类
    complexity: str  # 复杂度：简单/中等/复杂
    required_capabilities: List[str]  # 所需能力维度
    reasoning: str  # 分析推理过程


class ExistingRoleMatch(BaseModel):
    """现有角色匹配结果"""
    name: str  # 角色ID
    display_name: str  # 角色显示名
    match_score: float  # 匹配度 0.0-1.0
    match_reason: str  # 匹配理由
    assigned_count: int = 1  # 分配该角色的Agent数量


class RoleToCreate(BaseModel):
    """需要创建的新角色"""
    capability: str  # 缺失的能力维度
    requirement: str  # 详细的角色需求描述（给role_designer的输入）
    assigned_count: int = 1  # 分配该角色的Agent数量


class RolePlanning(BaseModel):
    """角色规划结果"""
    existing_roles: List[ExistingRoleMatch]  # 匹配到的现有角色
    roles_to_create: List[RoleToCreate]  # 需要创建的新角色


class FrameworkStageInfo(BaseModel):
    """框架阶段摘要"""
    stage_name: str  # 阶段名称
    stage_description: str  # 阶段说明


class FrameworkSelection(BaseModel):
    """框架选择结果"""
    framework_id: str  # 框架ID：roberts_rules/toulmin_model/critical_thinking
    framework_name: str  # 框架显示名称
    selection_reason: str  # 选择理由
    framework_stages: List[FrameworkStageInfo]  # 框架阶段摘要


class ExecutionConfig(BaseModel):
    """执行配置"""
    total_rounds: int  # 总讨论轮次
    agent_counts: Dict[str, int]  # Agent数量配置，如 {"planner": 2, "auditor": 1, "economist": 1}
    estimated_duration: str  # 预估耗时
    special_instructions: Optional[str] = None  # 特殊注意事项
    role_stage_mapping: Optional[Dict[str, List[str]]] = None  # 专业角色参与的stage映射，如 {"economist": ["证据评估", "替代视角"]}


class PlanSummary(BaseModel):
    """规划方案摘要"""
    title: str  # 方案标题
    overview: str  # 方案总览（2-3句话）
    key_advantages: List[str]  # 关键优势
    potential_risks: Optional[List[str]] = None  # 潜在风险


class OrchestrationPlan(BaseModel):
    """元调度器输出的完整规划方案"""
    analysis: RequirementAnalysis  # 需求分析
    role_planning: RolePlanning  # 角色规划
    framework_selection: FrameworkSelection  # 框架选择
    execution_config: ExecutionConfig  # 执行配置
    summary: PlanSummary  # 方案摘要
