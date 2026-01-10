"""
讨论框架库 (Discussion Frameworks Library)

定义各种结构化讨论框架，支持Meta-Orchestrator根据需求动态选择和执行。
每个框架包含多个阶段(stages)，每个阶段定义参与角色、讨论轮次和提示指导。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class FrameworkStage:
    """框架的单个执行阶段"""
    name: str  # 阶段名称，如"动议提出"、"批判审查"
    description: str  # 阶段说明
    roles: List[str]  # 参与的角色类型，如["planner"]、["auditor"]
    min_agents: int = 1  # 该角色的最小Agent数量
    max_agents: int = 3  # 该角色的最大Agent数量
    rounds: int = 1  # 该阶段的讨论轮次
    prompt_suffix: str = ""  # 注入到Agent prompt的阶段特定指导
    output_format: Optional[str] = None  # 输出格式要求（JSON schema或描述）
    depends_on: Optional[List[str]] = None  # 依赖的前置阶段（按name引用）
    
    def __post_init__(self):
        """验证配置的合理性"""
        if self.min_agents > self.max_agents:
            raise ValueError(f"Stage '{self.name}': min_agents不能大于max_agents")
        if self.rounds < 1:
            raise ValueError(f"Stage '{self.name}': rounds必须至少为1")
        if not self.roles:
            raise ValueError(f"Stage '{self.name}': roles不能为空")


@dataclass
class Framework:
    """完整的讨论框架定义"""
    id: str  # 框架唯一标识符（用于代码引用）
    name: str  # 显示名称
    description: str  # 框架说明和适用场景
    stages: List[FrameworkStage]  # 执行阶段列表
    keywords: List[str] = field(default_factory=list)  # 关键词（用于自动匹配）
    final_synthesis: bool = True  # 是否需要Leader做最终综合
    tags: List[str] = field(default_factory=list)  # 标签分类
    
    def __post_init__(self):
        """验证框架完整性"""
        if not self.stages:
            raise ValueError(f"Framework '{self.id}': stages不能为空")
        
        # 验证依赖关系
        stage_names = {stage.name for stage in self.stages}
        for stage in self.stages:
            if stage.depends_on:
                for dep in stage.depends_on:
                    if dep not in stage_names:
                        raise ValueError(
                            f"Stage '{stage.name}' 依赖不存在的阶段: '{dep}'"
                        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "final_synthesis": self.final_synthesis,
            "tags": self.tags,
            "stages": [
                {
                    "name": stage.name,
                    "description": stage.description,
                    "roles": stage.roles,
                    "min_agents": stage.min_agents,
                    "max_agents": stage.max_agents,
                    "rounds": stage.rounds,
                    "prompt_suffix": stage.prompt_suffix,
                    "output_format": stage.output_format,
                    "depends_on": stage.depends_on,
                }
                for stage in self.stages
            ]
        }


# ========== 框架定义 ==========

# 1. 罗伯特议事规则 (Robert's Rules of Order)
ROBERTS_RULES = Framework(
    id="roberts_rules",
    name="罗伯特议事规则",
    description="""
经典议事框架，强调秩序和民主决策。适用于需要结构化讨论和多数表决的场景。
流程：动议提出 → 附议确认 → 正反辩论 → 综合表决
    """.strip(),
    keywords=["决策", "表决", "议事", "提案", "民主", "秩序"],
    tags=["决策类", "结构化", "经典"],
    stages=[
        FrameworkStage(
            name="动议提出",
            description="策论家提出清晰的解决方案动议",
            roles=["planner"],
            min_agents=1,
            max_agents=3,
            rounds=1,
            prompt_suffix="""
【罗伯特议事规则 - 动议提出阶段】
请提出明确、可操作的解决方案动议。每个动议应包含：
1. 动议标题（简洁概括）
2. 具体措施（可执行的步骤）
3. 预期效果（预测结果）
4. 实施条件（前提要求）

要求：动议必须清晰、具体、可表决。避免模糊或过于宽泛的建议。
            """.strip(),
            output_format="包含标题、措施、效果、条件的结构化动议"
        ),
        FrameworkStage(
            name="附议确认",
            description="监察官评估动议的可行性，确认是否值得深入讨论",
            roles=["auditor"],
            min_agents=1,
            max_agents=2,
            rounds=1,
            prompt_suffix="""
【罗伯特议事规则 - 附议确认阶段】
请评估前述动议是否值得深入讨论。评估维度：
1. 相关性：是否切题解决问题
2. 可行性：是否有实施可能
3. 完整性：是否考虑周全
4. 风险性：潜在问题是否可控

判断：每个动议给出"附议"或"反对讨论"的明确意见，并说明理由。
            """.strip(),
            depends_on=["动议提出"]
        ),
        FrameworkStage(
            name="正反辩论",
            description="策论家补充论据，监察官提出质疑，多轮交锋",
            roles=["planner", "auditor"],
            min_agents=2,
            max_agents=4,
            rounds=2,
            prompt_suffix="""
【罗伯特议事规则 - 正反辩论阶段】
策论家：请为你的动议提供更多支撑论据，回应监察官的质疑。
监察官：请深入质询动议的漏洞，提出反例和改进建议。

规则：
- 每轮发言聚焦核心争议点
- 使用事实和逻辑，避免人身攻击
- 可以提出修正案（对原动议的改进）
            """.strip(),
            depends_on=["附议确认"]
        ),
        FrameworkStage(
            name="综合表决",
            description="议长综合各方意见，给出最终决策建议",
            roles=["leader"],
            min_agents=1,
            max_agents=1,
            rounds=1,
            prompt_suffix="""
【罗伯特议事规则 - 综合表决阶段】
请综合前述讨论，对每个动议给出评估和建议：
1. 支持理由：动议的优势和支撑论据
2. 反对理由：动议的风险和不足之处
3. 改进方向：如何优化动议（如有必要）
4. 最终建议：采纳/修改后采纳/暂缓/否决

输出结构化的决策报告，供最终决策参考。
            """.strip(),
            depends_on=["正反辩论"]
        ),
    ],
    final_synthesis=True
)


# 2. 图尔敏论证法 (Toulmin Argument Model)
TOULMIN_MODEL = Framework(
    id="toulmin_model",
    name="图尔敏论证法",
    description="""
结构化论证框架，强调逻辑严密性。适用于需要深度论证和逻辑推理的问题。
流程：主张 → 数据支撑 → 保证连接 → 反驳识别 → 支撑加固 → 限定修正
    """.strip(),
    keywords=["论证", "逻辑", "推理", "证据", "严密"],
    tags=["论证类", "逻辑性强", "学术化"],
    stages=[
        FrameworkStage(
            name="主张提出",
            description="策论家明确提出核心主张",
            roles=["planner"],
            min_agents=1,
            max_agents=2,
            rounds=1,
            prompt_suffix="""
【图尔敏论证法 - 主张(Claim)阶段】
请提出你的核心主张。主张应该：
1. 明确具体：不模糊、不歧义
2. 可论证：有讨论和证明的空间
3. 有意义：对解决问题有实质性帮助

格式：以"我主张…"开头，清晰陈述你的立场。
            """.strip()
        ),
        FrameworkStage(
            name="数据支撑",
            description="策论家提供支持主张的数据和证据",
            roles=["planner"],
            min_agents=1,
            max_agents=2,
            rounds=1,
            prompt_suffix="""
【图尔敏论证法 - 数据(Data)阶段】
请提供支持你主张的数据和证据：
1. 事实数据：统计数字、案例、研究结果
2. 权威引用：专家观点、文献资料
3. 逻辑推演：从已知到主张的推理链

要求：证据必须真实可靠，与主张直接相关。
            """.strip(),
            depends_on=["主张提出"]
        ),
        FrameworkStage(
            name="保证连接",
            description="监察官审查数据与主张之间的逻辑连接",
            roles=["auditor"],
            min_agents=1,
            max_agents=2,
            rounds=1,
            prompt_suffix="""
【图尔敏论证法 - 保证(Warrant)阶段】
请审查"数据→主张"的逻辑连接是否成立：
1. 相关性：数据是否真的支持主张
2. 充分性：证据强度是否足够
3. 逻辑链：推理过程是否严密
4. 隐含假设：是否存在未明说的前提

指出逻辑漏洞，要求策论家解释"为什么这些数据能支持主张"。
            """.strip(),
            depends_on=["数据支撑"]
        ),
        FrameworkStage(
            name="反驳识别",
            description="监察官提出可能的反例和例外情况",
            roles=["auditor"],
            min_agents=1,
            max_agents=2,
            rounds=1,
            prompt_suffix="""
【图尔敏论证法 - 反驳(Rebuttal)阶段】
请识别主张的潜在反例和限制条件：
1. 反例：哪些情况下主张不成立
2. 例外：需要排除的特殊场景
3. 边界：主张的适用范围限制
4. 风险：实施主张可能的负面后果

要求：具体指出，而非泛泛质疑。
            """.strip(),
            depends_on=["保证连接"]
        ),
        FrameworkStage(
            name="支撑加固",
            description="策论家提供深层理由，回应反驳",
            roles=["planner"],
            min_agents=1,
            max_agents=2,
            rounds=1,
            prompt_suffix="""
【图尔敏论证法 - 支撑(Backing)阶段】
请为你的保证提供深层支撑，回应反驳：
1. 理论基础：为什么你的推理逻辑是合理的
2. 回应反驳：如何处理监察官指出的反例
3. 限定条件：主张在哪些条件下成立（Qualifier）
4. 强化论证：补充新证据或理由

目标：构建更严密、更可信的完整论证链。
            """.strip(),
            depends_on=["反驳识别"]
        ),
        FrameworkStage(
            name="论证评估",
            description="议长评估论证的整体质量",
            roles=["leader"],
            min_agents=1,
            max_agents=1,
            rounds=1,
            prompt_suffix="""
【图尔敏论证法 - 评估阶段】
请评估完整论证链的质量：
1. 主张清晰度：主张是否明确可理解
2. 证据充分度：数据支撑是否有力
3. 逻辑严密度：推理链是否完整无漏洞
4. 反驳处理：是否充分回应了质疑
5. 适用范围：限定条件是否合理

输出：论证强度评分（高/中/低）+ 改进建议。
            """.strip(),
            depends_on=["支撑加固"]
        ),
    ],
    final_synthesis=True
)


# 3. 批判性思维框架 (Critical Thinking Framework)
CRITICAL_THINKING = Framework(
    id="critical_thinking",
    name="批判性思维框架",
    description="""
多维度审视框架，强调全面分析和偏见识别。适用于需要深度批判和反思的复杂问题。
流程：假设识别 → 证据评估 → 逻辑推理 → 偏见分析 → 替代视角 → 反思总结
    """.strip(),
    keywords=["批判", "分析", "反思", "偏见", "多角度"],
    tags=["分析类", "深度思考", "反思性"],
    stages=[
        FrameworkStage(
            name="假设识别",
            description="监察官识别问题和解决方案中的隐含假设",
            roles=["auditor"],
            min_agents=1,
            max_agents=2,
            rounds=1,
            prompt_suffix="""
【批判性思维 - 假设识别阶段】
请识别讨论中的隐含假设：
1. 未明说的前提：哪些观点被默认为真
2. 价值观假设：背后的价值取向是什么
3. 因果假设：假定了哪些因果关系
4. 范围假设：问题边界的划定是否合理

目标：让隐含的假设显性化，以便检验。
            """.strip()
        ),
        FrameworkStage(
            name="证据评估",
            description="监察官评估证据的质量和可信度",
            roles=["auditor"],
            min_agents=1,
            max_agents=2,
            rounds=1,
            prompt_suffix="""
【批判性思维 - 证据评估阶段】
请评估论证中使用的证据：
1. 来源可靠性：数据来源是否权威
2. 时效性：信息是否过时
3. 相关性：证据与结论的关联度
4. 代表性：样本是否有偏差
5. 完整性：是否选择性呈现证据

指出证据的薄弱环节，要求补充或替换。
            """.strip(),
            depends_on=["假设识别"]
        ),
        FrameworkStage(
            name="逻辑推理",
            description="策论家检查推理链的逻辑严密性",
            roles=["planner"],
            min_agents=1,
            max_agents=2,
            rounds=1,
            prompt_suffix="""
【批判性思维 - 逻辑推理阶段】
请检查论证的逻辑推理：
1. 演绎推理：前提是否必然推出结论
2. 归纳推理：从个案到一般是否合理
3. 类比推理：比较对象是否可比
4. 逻辑谬误：是否存在常见谬误（如滑坡、稻草人、诉诸权威）

构建更严密的推理链，修正逻辑漏洞。
            """.strip(),
            depends_on=["证据评估"]
        ),
        FrameworkStage(
            name="偏见分析",
            description="监察官识别可能的认知偏见",
            roles=["auditor"],
            min_agents=1,
            max_agents=2,
            rounds=1,
            prompt_suffix="""
【批判性思维 - 偏见分析阶段】
请识别讨论中可能存在的认知偏见：
1. 确认偏见：只寻找支持既有观点的证据
2. 锚定效应：过度依赖第一印象
3. 可得性偏见：高估容易想到的信息的重要性
4. 群体思维：为了和谐而压制异议
5. 幸存者偏差：只看到成功案例，忽略失败

提醒注意这些偏见对结论的影响。
            """.strip(),
            depends_on=["逻辑推理"]
        ),
        FrameworkStage(
            name="替代视角",
            description="策论家从不同角度重新审视问题",
            roles=["planner"],
            min_agents=1,
            max_agents=3,
            rounds=1,
            prompt_suffix="""
【批判性思维 - 替代视角阶段】
请从不同角度重新审视问题：
1. 利益相关者：从不同群体的视角看问题
2. 时间维度：短期vs长期影响
3. 系统层次：个体、组织、社会层面
4. 文化背景：不同文化的解读差异

提出之前被忽视的视角和可能的替代方案。
            """.strip(),
            depends_on=["偏见分析"]
        ),
        FrameworkStage(
            name="反思总结",
            description="议长综合多维度分析，形成深度洞察",
            roles=["leader"],
            min_agents=1,
            max_agents=1,
            rounds=1,
            prompt_suffix="""
【批判性思维 - 反思总结阶段】
请综合前述批判性分析：
1. 核心洞察：经过深度审视后的关键发现
2. 假设检验：哪些假设成立，哪些需要修正
3. 证据缺口：还需要什么信息才能更确定
4. 不确定性：承认我们不知道的部分
5. 行动建议：考虑了多维度分析后的建议

输出：既有批判深度，又有建设性的总结报告。
            """.strip(),
            depends_on=["替代视角"]
        ),
    ],
    final_synthesis=True
)


# ========== 框架注册表 ==========

# 所有可用框架的字典
ALL_FRAMEWORKS: Dict[str, Framework] = {
    "roberts_rules": ROBERTS_RULES,
    "toulmin_model": TOULMIN_MODEL,
    "critical_thinking": CRITICAL_THINKING,
}


# ========== 工具函数 ==========

def get_framework(framework_id: str) -> Optional[Framework]:
    """
    根据ID获取框架
    
    Args:
        framework_id: 框架唯一标识符
        
    Returns:
        Framework对象，如果不存在则返回None
    """
    return ALL_FRAMEWORKS.get(framework_id)


def list_frameworks() -> List[Dict[str, Any]]:
    """
    列出所有可用框架的摘要信息
    
    Returns:
        框架摘要列表，每项包含id、name、description、keywords、tags
    """
    return [
        {
            "id": fw.id,
            "name": fw.name,
            "description": fw.description,
            "keywords": fw.keywords,
            "tags": fw.tags,
            "stage_count": len(fw.stages),
        }
        for fw in ALL_FRAMEWORKS.values()
    ]


def search_frameworks(query: str) -> List[Framework]:
    """
    根据查询关键词搜索匹配的框架
    
    Args:
        query: 搜索关键词（可以是问题描述或特定词汇）
        
    Returns:
        按相关性排序的Framework列表
    """
    query_lower = query.lower()
    scored_frameworks = []
    
    for fw in ALL_FRAMEWORKS.values():
        score = 0
        
        # 检查关键词匹配
        for keyword in fw.keywords:
            if keyword in query_lower:
                score += 3
        
        # 检查标签匹配
        for tag in fw.tags:
            if tag in query_lower:
                score += 2
        
        # 检查名称和描述匹配
        if any(word in query_lower for word in fw.name.split()):
            score += 5
        if any(word in query_lower for word in fw.description.split()):
            score += 1
        
        if score > 0:
            scored_frameworks.append((score, fw))
    
    # 按分数降序排序
    scored_frameworks.sort(key=lambda x: x[0], reverse=True)
    return [fw for _, fw in scored_frameworks]


def validate_framework(framework: Framework) -> List[str]:
    """
    验证框架配置的合理性
    
    Args:
        framework: 要验证的Framework对象
        
    Returns:
        错误信息列表，如果为空则验证通过
    """
    errors = []
    
    try:
        # dataclass的__post_init__会自动验证
        framework.__post_init__()
    except ValueError as e:
        errors.append(str(e))
    
    # 额外验证：检查角色类型是否合法
    valid_role_types = {"leader", "planner", "auditor", "reporter"}
    for stage in framework.stages:
        for role in stage.roles:
            if role not in valid_role_types:
                errors.append(
                    f"Stage '{stage.name}': 无效的角色类型 '{role}'"
                    f"（有效值: {valid_role_types}）"
                )
    
    # 验证依赖关系是否有环
    stage_names = {stage.name for stage in framework.stages}
    visited = set()
    
    def has_cycle(stage_name: str, path: set) -> bool:
        if stage_name in path:
            return True
        if stage_name in visited:
            return False
        
        visited.add(stage_name)
        path.add(stage_name)
        
        stage = next((s for s in framework.stages if s.name == stage_name), None)
        if stage and stage.depends_on:
            for dep in stage.depends_on:
                if has_cycle(dep, path):
                    return True
        
        path.remove(stage_name)
        return False
    
    for stage in framework.stages:
        if has_cycle(stage.name, set()):
            errors.append(f"检测到循环依赖：Stage '{stage.name}' 的依赖链形成环")
            break
    
    return errors


# ========== 模块自检 ==========

if __name__ == "__main__":
    """验证所有内置框架的配置正确性"""
    print("=" * 60)
    print("框架库自检")
    print("=" * 60)
    
    all_valid = True
    for fw_id, fw in ALL_FRAMEWORKS.items():
        print(f"\n检查框架: {fw.name} ({fw_id})")
        errors = validate_framework(fw)
        if errors:
            print("  ❌ 发现错误:")
            for error in errors:
                print(f"    - {error}")
            all_valid = False
        else:
            print(f"  ✅ 验证通过 ({len(fw.stages)}个阶段)")
            for stage in fw.stages:
                print(f"      - {stage.name}: {stage.roles} x{stage.rounds}轮")
    
    print("\n" + "=" * 60)
    if all_valid:
        print("✅ 所有框架配置正确！")
    else:
        print("❌ 部分框架存在问题，请修复后重试。")
    print("=" * 60)
    
    # 测试搜索功能
    print("\n测试搜索功能:")
    test_queries = ["决策", "逻辑论证", "深度分析"]
    for query in test_queries:
        results = search_frameworks(query)
        print(f"  查询 '{query}': 找到 {len(results)} 个匹配框架")
        for fw in results[:2]:  # 只显示前2个
            print(f"    - {fw.name}")
