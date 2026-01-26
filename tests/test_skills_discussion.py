"""
测试Skills Tool Calling - 启动真实讨论验证

选择一个需要专业知识的议题，观察角色是否主动调用Skills工具
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.agents.langchain_agents import run_full_cycle
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

print("=" * 70)
print("Skills Tool Calling 真实讨论测试")
print("=" * 70)
print()

# 选择一个需要多领域专业知识的议题
test_issue = """
某创业公司计划推出一款面向B端企业的SaaS产品，主要功能是项目管理和团队协作。

背景信息：
- 目前市场上已有Jira、Asana、Monday.com等成熟产品
- 公司有200万初始资金，团队15人
- 计划6个月内完成MVP并获得首批付费客户
- 目标是3年内达到年收入5000万

请元老院评估：
1. 这个商业计划的可行性如何？
2. 主要风险点在哪里？
3. 应该采取什么策略来突围？
"""

print("测试议题:")
print("-" * 70)
print(test_issue)
print("-" * 70)
print()

print("启动讨论（1轮，2个策论家，2个监察官）...")
print("预期：策论家和监察官会调用Skills工具获取专业知识")
print()

# 配置
model_config = {
    "type": "deepseek",
    "model": "deepseek-chat"  # 使用便宜的chat模型测试
}

# 启动讨论（简化配置：1轮，避免成本过高）
result = run_full_cycle(
    issue_text=test_issue,
    model_config=model_config,
    max_rounds=1,  # 只运行1轮
    num_planners=2,
    num_auditors=2,
    user_id=1,  # admin用户
    tenant_id=1  # admin的租户
)

print()
print("=" * 70)
print("讨论完成！")
print("=" * 70)
print()

# 分析结果
print("【结果分析】")
print(f"✅ 工作空间: {result.get('workspace_path', 'N/A')}")
print(f"✅ Session ID: {result.get('session_id', 'N/A')}")
print()

# 检查是否有工具调用记录
history = result.get('history', [])
tool_calls_found = False

for round_data in history:
    if 'planners_output' in round_data:
        for planner in round_data['planners_output']:
            if 'tool_calls' in planner and planner['tool_calls']:
                tool_calls_found = True
                print(f"✅ {planner['name']} 调用了 {len(planner['tool_calls'])} 个工具:")
                for tc in planner['tool_calls'][:3]:  # 只显示前3个
                    print(f"   - {tc['tool_name']}")
    
    if 'auditors_output' in round_data:
        for auditor in round_data['auditors_output']:
            if 'tool_calls' in auditor and auditor['tool_calls']:
                tool_calls_found = True
                print(f"✅ {auditor['name']} 调用了 {len(auditor['tool_calls'])} 个工具:")
                for tc in auditor['tool_calls'][:3]:
                    print(f"   - {tc['tool_name']}")

if not tool_calls_found:
    print("⚠️  未检测到工具调用记录（可能Agent没有主动调用，或工具调用记录未保存）")

print()
print("【查看详细日志】")
print(f"日志文件: aicouncil.log")
print(f"搜索关键字: '[skill_tools]' 或 'list_skills' 或 'use_skill'")
print()
print("【查看报告】")
report_path = result.get('workspace_path')
if report_path:
    from pathlib import Path
    report_file = Path(report_path) / "report.html"
    if report_file.exists():
        print(f"✅ 报告已生成: {report_file}")
        print(f"   在浏览器中打开查看完整内容")
    else:
        print(f"⚠️  报告文件未找到: {report_file}")
