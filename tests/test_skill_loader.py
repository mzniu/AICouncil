"""
Unit tests for SkillLoader
Tests loading, parsing, and filtering of skills
"""

import pytest
from pathlib import Path
from src.skills.loader import SkillLoader, Skill, load_builtin_skills


class TestSkillLoader:
    """Test SkillLoader functionality"""
    
    def test_loader_initialization(self):
        """Test SkillLoader initializes with correct default path"""
        loader = SkillLoader()
        assert loader.builtin_skills_dir.exists()
        assert loader.builtin_skills_dir.name == "builtin"
    
    def test_load_all_builtin_skills(self):
        """Test loading all builtin skills"""
        loader = SkillLoader()
        skills = loader.load_all_builtin_skills()
        
        # Should have 5 builtin skills
        assert len(skills) == 5
        
        # Check skill names
        skill_names = {s.name for s in skills}
        expected_names = {
            'policy_analysis',
            'tech_evaluation',
            'stakeholder_analysis',
            'risk_assessment',
            'cost_benefit'
        }
        assert skill_names == expected_names
    
    def test_skill_metadata_parsing(self):
        """Test that skill metadata is correctly parsed"""
        loader = SkillLoader()
        skill = loader.load_skill_by_name('policy_analysis')
        
        assert skill is not None
        assert skill.name == 'policy_analysis'
        assert skill.display_name == '政策分析专家'
        assert skill.version == '1.0.0'
        assert skill.category == 'analysis'  # Actual category in SKILL.md
        assert 'PEST' in skill.tags or 'policy' in skill.tags
        assert skill.author == 'AICouncil Team'
        assert '策论家' in skill.applicable_roles or '监察官' in skill.applicable_roles
    
    def test_skill_content_loaded(self):
        """Test that skill content is loaded"""
        loader = SkillLoader()
        skill = loader.load_skill_by_name('tech_evaluation')
        
        assert skill is not None
        assert len(skill.content) > 1000  # Should have substantial content
        assert 'TRL' in skill.content or '技术就绪度' in skill.content
    
    def test_load_skill_by_name(self):
        """Test loading specific skill by name"""
        loader = SkillLoader()
        
        # Load existing skill
        skill = loader.load_skill_by_name('risk_assessment')
        assert skill is not None
        assert skill.name == 'risk_assessment'
        
        # Try loading non-existent skill
        non_existent = loader.load_skill_by_name('non_existent_skill')
        assert non_existent is None
    
    def test_filter_skills_by_category(self):
        """Test filtering skills by category"""
        loader = SkillLoader()
        skills = loader.load_all_builtin_skills()
        
        # Filter by actual categories in Skills
        analysis_skills = loader.get_skills_by_category('analysis', skills)
        financial_skills = loader.get_skills_by_category('financial', skills)
        technical_skills = loader.get_skills_by_category('technical', skills)
        
        # Verify filtering
        assert len(analysis_skills) >= 1
        assert all(s.category == 'analysis' for s in analysis_skills)
        
        assert len(financial_skills) >= 1
        assert all(s.category == 'financial' for s in financial_skills)
    
    def test_filter_skills_by_role(self):
        """Test filtering skills by applicable role"""
        loader = SkillLoader()
        skills = loader.load_all_builtin_skills()
        
        # Filter by role
        planner_skills = loader.get_skills_by_role('策论家', skills)
        auditor_skills = loader.get_skills_by_role('监察官', skills)
        
        # All builtin skills should be applicable to both roles
        assert len(planner_skills) == 5
        assert len(auditor_skills) == 5
    
    def test_format_skill_for_prompt_with_metadata(self):
        """Test formatting skill for prompt injection with metadata"""
        loader = SkillLoader()
        skill = loader.load_skill_by_name('cost_benefit')
        
        formatted = loader.format_skill_for_prompt(skill, include_metadata=True)
        
        # Should include metadata header
        assert skill.display_name in formatted
        assert skill.version in formatted
        assert skill.category in formatted
        
        # Should include content
        assert 'TCO' in formatted or '成本' in formatted
    
    def test_format_skill_for_prompt_without_metadata(self):
        """Test formatting skill for prompt injection without metadata"""
        loader = SkillLoader()
        skill = loader.load_skill_by_name('stakeholder_analysis')
        
        formatted = loader.format_skill_for_prompt(skill, include_metadata=False)
        
        # Should be just the content
        assert formatted == skill.content
        assert '版本' not in formatted  # Metadata keywords should not appear
    
    def test_convenience_function(self):
        """Test convenience function for loading builtin skills"""
        skills = load_builtin_skills()
        
        assert len(skills) == 5
        assert all(isinstance(s, Skill) for s in skills)


class TestSkillDataclass:
    """Test Skill dataclass"""
    
    def test_skill_creation(self):
        """Test creating a Skill instance"""
        skill = Skill(
            name='test_skill',
            display_name='测试技能',
            version='1.0.0',
            category='test',
            tags=['test'],
            author='Test Author',
            created='2026-01-20',
            updated='2026-01-20',
            description='测试技能描述',
            requirements={'context': '测试上下文'},
            applicable_roles=['策论家'],
            content='# 测试内容',
            file_path='/path/to/skill.md'
        )
        
        assert skill.name == 'test_skill'
        assert skill.display_name == '测试技能'
        assert skill.dependencies == []  # Default empty list
        assert skill.examples == []  # Default empty list


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
