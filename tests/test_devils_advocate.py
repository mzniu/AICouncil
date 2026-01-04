"""
Devil's Advocate Schema单元测试
测试Schema的解析、验证和序列化功能
"""
import pytest
import json
import sys
from pathlib import Path

# 添加项目根目录到sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agents.schemas import (
    ChallengeItem,
    DecompositionChallenge,
    SummaryChallenge,
    DevilsAdvocateSchema
)


class TestChallengeItem:
    """测试ChallengeItem Schema"""
    
    def test_valid_challenge_item(self):
        """测试有效的质疑项"""
        data = {
            "target": "总结中的假设X",
            "challenge_type": "假设挑战",
            "reasoning": "该假设缺乏数据支持",
            "alternative_perspective": "应该考虑Y的情况",
            "severity": "critical"
        }
        item = ChallengeItem(**data)
        
        assert item.target == "总结中的假设X"
        assert item.challenge_type == "假设挑战"
        assert item.severity == "critical"
    
    def test_challenge_item_json_serialization(self):
        """测试JSON序列化"""
        item = ChallengeItem(
            target="测试目标",
            challenge_type="逻辑质疑",
            reasoning="推理过程",
            alternative_perspective="替代视角",
            severity="important"
        )
        
        json_str = item.model_dump_json()
        assert json_str
        
        # 验证可以反序列化
        data = json.loads(json_str)
        reconstructed = ChallengeItem(**data)
        assert reconstructed.target == item.target


class TestDecompositionChallenge:
    """测试DecompositionChallenge Schema"""
    
    def test_valid_decomposition_challenge(self):
        """测试有效的拆解质疑"""
        data = {
            "missing_dimensions": ["时间维度", "风险维度"],
            "hidden_assumptions": ["假设资源充足", "假设环境稳定"],
            "alternative_frameworks": ["按时间线拆解", "按利益相关方拆解"],
            "extreme_scenario_issues": ["极端市场崩溃时失效", "监管突变时无效"]
        }
        challenge = DecompositionChallenge(**data)
        
        assert len(challenge.missing_dimensions) == 2
        assert len(challenge.hidden_assumptions) == 2
        assert "按时间线拆解" in challenge.alternative_frameworks


class TestSummaryChallenge:
    """测试SummaryChallenge Schema"""
    
    def test_valid_summary_challenge(self):
        """测试有效的总结质疑"""
        data = {
            "logical_gaps": ["从A跳到C，缺少B"],
            "missing_points": ["未提及风险X"],
            "inconsistencies": ["第一段说Y，第二段说非Y"],
            "optimism_bias": "过于乐观，未充分考虑失败场景"
        }
        challenge = SummaryChallenge(**data)
        
        assert len(challenge.logical_gaps) == 1
        assert len(challenge.missing_points) == 1
        assert challenge.optimism_bias is not None
    
    def test_summary_challenge_optional_fields(self):
        """测试可选字段"""
        data = {
            "logical_gaps": [],
            "missing_points": [],
            "inconsistencies": []
        }
        challenge = SummaryChallenge(**data)
        
        assert challenge.optimism_bias is None
        assert isinstance(challenge.logical_gaps, list)


class TestDevilsAdvocateSchema:
    """测试DevilsAdvocateSchema"""
    
    def test_valid_devils_advocate_output(self):
        """测试完整的DA输出"""
        data = {
            "round": 1,
            "stage": "summary",
            "summary_challenge": {
                "logical_gaps": ["逻辑缺口1"],
                "missing_points": ["遗漏点1", "遗漏点2"],
                "inconsistencies": [],
                "optimism_bias": None
            },
            "overall_assessment": "总结质量较高，但存在小问题",
            "critical_issues": [],
            "recommendations": ["建议补充X", "建议明确Y"]
        }
        
        da = DevilsAdvocateSchema(**data)
        
        assert da.round == 1
        assert da.stage == "summary"
        assert len(da.summary_challenge.missing_points) == 2
        assert len(da.recommendations) == 2
    
    def test_devils_advocate_with_critical_issues(self):
        """测试包含严重问题的DA输出"""
        data = {
            "round": 2,
            "stage": "summary",
            "summary_challenge": {
                "logical_gaps": ["严重逻辑跳跃"],
                "missing_points": ["未讨论核心问题"],
                "inconsistencies": ["前后矛盾"],
                "optimism_bias": "严重过度乐观"
            },
            "overall_assessment": "总结存在严重问题",
            "critical_issues": [
                "未讨论核心问题",
                "逻辑前后矛盾"
            ],
            "recommendations": ["建议重新总结"]
        }
        
        da = DevilsAdvocateSchema(**data)
        
        assert len(da.critical_issues) > 0
        assert da.summary_challenge.optimism_bias is not None
    
    def test_devils_advocate_json_round_trip(self):
        """测试完整的JSON序列化/反序列化"""
        original = DevilsAdvocateSchema(
            round=1,
            stage="summary",
            summary_challenge=SummaryChallenge(
                logical_gaps=["gap1"],
                missing_points=["miss1"],
                inconsistencies=["inc1"],
                optimism_bias="过于乐观"
            ),
            overall_assessment="评价",
            critical_issues=["issue1"],
            recommendations=["rec1"]
        )
        
        # 序列化
        json_str = original.model_dump_json()
        
        # 反序列化
        data = json.loads(json_str)
        reconstructed = DevilsAdvocateSchema(**data)
        
        # 验证
        assert reconstructed.round == original.round
        assert reconstructed.stage == original.stage
        assert len(reconstructed.critical_issues) == len(original.critical_issues)
    
    def test_devils_advocate_validation(self):
        """测试字段验证"""
        # 缺少必需字段应该失败
        with pytest.raises(Exception):
            DevilsAdvocateSchema(
                round=1
                # 缺少其他必需字段
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
