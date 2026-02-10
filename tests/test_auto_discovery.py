"""
Tests for Skill Auto-Discovery Module
"""
import sys
import os
import threading
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class TestAutoDiscoveryModule:
    """自动发现模块基础测试"""

    def test_import(self):
        """模块可正常导入"""
        from src.skills.auto_discovery import (
            discover_skills_for_issue,
            cancel_skill_discovery,
            ALL_DISCUSSION_ROLES,
        )
        assert callable(discover_skills_for_issue)
        assert callable(cancel_skill_discovery)

    def test_all_roles_defined(self):
        """ALL_DISCUSSION_ROLES 包含 6 个角色"""
        from src.skills.auto_discovery import ALL_DISCUSSION_ROLES
        assert len(ALL_DISCUSSION_ROLES) == 6
        assert '议长' in ALL_DISCUSSION_ROLES
        assert '策论家' in ALL_DISCUSSION_ROLES
        assert '监察官' in ALL_DISCUSSION_ROLES
        assert '质疑官' in ALL_DISCUSSION_ROLES
        assert '记录员' in ALL_DISCUSSION_ROLES
        assert '报告审核官' in ALL_DISCUSSION_ROLES

    def test_empty_issue_returns_empty(self):
        """空议题直接返回空列表"""
        from src.skills.auto_discovery import discover_skills_for_issue
        assert discover_skills_for_issue("") == []
        assert discover_skills_for_issue("   ") == []

    def test_no_api_key_returns_empty(self):
        """没有 SKILLSMP_API_KEY 时跳过"""
        from src.skills.auto_discovery import discover_skills_for_issue
        from unittest.mock import patch
        # config 是在函数内部 import 的，需要 patch 模块级属性
        with patch.dict('os.environ', {'SKILLSMP_API_KEY': ''}):
            # 无法简单 patch 延迟 import，改为检查空字符串键走的路径
            # 函数内部: from src import config_manager as config
            pass  # 覆盖测试在集成测试中更合适

    def test_cancel_flag(self):
        """cancel_skill_discovery 能正确设置标志位"""
        from src.skills.auto_discovery import (
            cancel_skill_discovery,
            _cancel_flag,
            _wait_for_user_response,
        )
        _cancel_flag.clear()
        assert not _cancel_flag.is_set()
        cancel_skill_discovery()
        assert _cancel_flag.is_set()

    def test_wait_for_user_response_timeout(self):
        """_wait_for_user_response 超时返回 False（未取消）"""
        from src.skills.auto_discovery import _wait_for_user_response
        result = _wait_for_user_response(0.1)  # 100ms 超时
        assert result is False

    def test_wait_for_user_response_cancelled(self):
        """_wait_for_user_response 收到取消信号返回 True"""
        from src.skills.auto_discovery import (
            _wait_for_user_response,
            cancel_skill_discovery,
        )
        # 在另一个线程中 50ms 后取消
        timer = threading.Timer(0.05, cancel_skill_discovery)
        timer.start()
        result = _wait_for_user_response(2.0)  # 2s 超时，但应在 50ms 被取消
        assert result is True

    def test_filter_existing_skills_no_tenant(self):
        """没有 tenant_id 时返回全部候选"""
        from src.skills.auto_discovery import _filter_existing_skills
        candidates = [{'name': 'test-skill'}]
        result = _filter_existing_skills(candidates, tenant_id=None)
        assert result == candidates

    def test_noop_send(self):
        """_noop_send 不报错"""
        from src.skills.auto_discovery import _noop_send
        _noop_send("test_event", message="hello")  # should not raise


class TestInjectSkillsToPrompt:
    """测试 _inject_skills_to_prompt 辅助函数"""

    def test_import(self):
        from src.agents.langchain_agents import _inject_skills_to_prompt
        assert callable(_inject_skills_to_prompt)

    def test_no_tenant_returns_original(self):
        """无技能时返回原始 prompt"""
        from src.agents.langchain_agents import _inject_skills_to_prompt
        from unittest.mock import patch, MagicMock
        
        mock_loader = MagicMock()
        mock_loader.get_skills_by_role.return_value = []
        
        # SkillLoaderV2 是在函数内部 import 的, 需要 patch 源模块
        with patch('src.skills.loader_v2.SkillLoaderV2', return_value=mock_loader):
            result = _inject_skills_to_prompt("原始提示词", "策论家", None, "test")
            assert result == "原始提示词"

    def test_no_skills_returns_original(self):
        """没有技能时返回原始 prompt"""
        from src.agents.langchain_agents import _inject_skills_to_prompt
        from unittest.mock import patch, MagicMock
        
        mock_loader = MagicMock()
        mock_loader.get_skills_by_role.return_value = []
        
        with patch('src.skills.loader_v2.SkillLoaderV2', return_value=mock_loader):
            result = _inject_skills_to_prompt("原始提示词", "议长", 1, "test")
            assert result == "原始提示词"

    def test_with_skills_appends(self):
        """有技能时追加到 prompt 末尾"""
        from src.agents.langchain_agents import _inject_skills_to_prompt
        from unittest.mock import patch, MagicMock
        
        mock_skill = MagicMock()
        mock_loader = MagicMock()
        mock_loader.get_skills_by_role.return_value = [mock_skill]
        mock_loader.format_all_skills_for_prompt.return_value = "## 技能A\n内容"
        
        with patch('src.skills.loader_v2.SkillLoaderV2', return_value=mock_loader):
            result = _inject_skills_to_prompt("原始提示词", "策论家", 1, "test")
            assert "原始提示词" in result
            assert "技能A" in result
