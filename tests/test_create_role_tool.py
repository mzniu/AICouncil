"""
测试 create_role 工具函数
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agents.meta_tools import create_role
from src.utils.logger import logger

def test_create_role():
    """测试创建角色功能"""
    
    # 测试需求：创建一个数据分析专家
    requirement = """
需要一位精通数据分析与可视化的数据科学家，能够从海量数据中提取洞察，
构建预测模型，并清晰地向非技术受众解释复杂的分析结果。

核心能力：
- 统计分析与假设检验
- 机器学习建模（回归、分类、聚类）
- 数据可视化（图表设计、仪表板构建）
- 商业洞察提取

工作方式：
在讨论中提供数据驱动的见解，构建预测模型评估各种方案的可行性，
使用可视化方法解释复杂的分析结果，帮助团队做出基于数据的决策。
    """
    
    print("=" * 80)
    print("测试 create_role() 函数")
    print("=" * 80)
    
    print("\n📝 需求描述:")
    print(requirement)
    
    print("\n🔧 开始创建角色...")
    result = create_role(requirement)
    
    print("\n" + "=" * 80)
    print("📊 创建结果:")
    print("=" * 80)
    
    if result.get("success"):
        print("✅ 创建成功!")
        print(f"   角色名称: {result['role_name']}")
        print(f"   显示名称: {result['role_info']['display_name']}")
        print(f"   描述: {result['role_info']['description']}")
        print(f"   核心能力: {result['role_info']['capabilities']}")
        print(f"   阶段数: {len(result['role_info']['stages'])}")
        
        print("\n   阶段详情:")
        for i, stage in enumerate(result['role_info']['stages'], 1):
            print(f"      Stage {i}: {stage['name']}")
            print(f"         目标: {', '.join(stage['goals'][:2])}")
    else:
        print("❌ 创建失败!")
        print(f"   错误信息: {result.get('error')}")
    
    print("\n" + "=" * 80)
    return result

if __name__ == "__main__":
    test_create_role()
