"""
Skills导入器单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.skills.skill_importer import SkillImporter, SkillImportResult, ANTHROPIC_PRESETS, get_preset_skills, import_skill_from_url


class TestSkillImporter:
    """SkillImporter核心功能测试"""
    
    def test_init(self):
        """测试导入器初始化"""
        importer = SkillImporter()
        assert importer.timeout == 30
        assert importer.session is not None
        
        importer_custom = SkillImporter(timeout=60)
        assert importer_custom.timeout == 60
    
    def test_get_anthropic_presets(self):
        """测试获取预设列表"""
        importer = SkillImporter()
        presets = importer.get_anthropic_presets()
        
        assert len(presets) == 5  # 应该有5个预设
        assert all('id' in p and 'name' in p and 'url' in p for p in presets)
        assert all('source' in p and p['source'] == 'anthropic' for p in presets)
    
    def test_is_valid_url(self):
        """测试URL验证"""
        importer = SkillImporter()
        
        # 有效URL
        assert importer._is_valid_url('https://example.com/skill.md')
        assert importer._is_valid_url('http://raw.githubusercontent.com/user/repo/main/file.md')
        assert importer._is_valid_url('https://localhost:8000/test.md')
        
        # 无效URL
        assert not importer._is_valid_url('not-a-url')
        assert not importer._is_valid_url('ftp://example.com/file.md')
        assert not importer._is_valid_url('')


class TestMarkdownParsing:
    """Markdown解析测试"""
    
    def test_parse_yaml_front_matter(self):
        """测试YAML front matter解析"""
        content = """---
name: Test Skill
description: A test skill
category: policy
---

# Content here

This is the skill content.
"""
        importer = SkillImporter()
        result = importer.parse_markdown_skill(content)
        
        assert result is not None
        assert result['name'] == 'Test Skill'
        assert result['description'] == 'A test skill'
        assert result['category'] == 'policy'
        assert result['is_builtin'] is False
        assert '# Content here' in result['content']
    
    def test_parse_title_from_heading(self):
        """测试从标题提取技能名称"""
        content = """# Policy Analysis Skill

This is a skill for analyzing policies.

More content here.
"""
        importer = SkillImporter()
        result = importer.parse_markdown_skill(content)
        
        assert result is not None
        assert result['name'] == 'Policy Analysis Skill'
        assert 'analyzing policies' in result['description']
    
    def test_parse_description_extraction(self):
        """测试描述自动提取"""
        content = """# Test Skill

This is a comprehensive description of the test skill. It should be extracted automatically as the description when no YAML front matter is present.

## Section 1

More content...
"""
        importer = SkillImporter()
        result = importer.parse_markdown_skill(content)
        
        assert result is not None
        assert 'comprehensive description' in result['description']
    
    def test_parse_empty_content(self):
        """测试空内容处理"""
        importer = SkillImporter()
        
        assert importer.parse_markdown_skill('') is None
        assert importer.parse_markdown_skill('   ') is None
        assert importer.parse_markdown_skill('\n\n\n') is None
    
    def test_parse_with_source_url(self):
        """测试带source_url的解析"""
        content = "# Test\n\nContent"
        importer = SkillImporter()
        result = importer.parse_markdown_skill(content, source_url='https://example.com/skill.md')
        
        assert result['source_url'] == 'https://example.com/skill.md'
    
    def test_default_category(self):
        """测试默认分类"""
        content = "# Skill\n\nContent without category"
        importer = SkillImporter()
        result = importer.parse_markdown_skill(content)
        
        assert result['category'] == 'custom'


class TestImportFromURL:
    """URL导入测试（使用Mock）"""
    
    @patch('src.skills.skill_importer.SkillImporter._download_content')
    @patch('src.skills.skill_importer.scan_skill_content')
    def test_import_success(self, mock_scan, mock_download):
        """测试成功导入"""
        # Mock下载内容
        mock_download.return_value = """---
name: Test Skill
description: Test description
category: policy
---

# Test Content
"""
        
        # Mock安全扫描
        mock_scan_result = Mock()
        mock_scan_result.is_safe = True
        mock_scan_result.security_score = 95.0
        mock_scan.return_value = mock_scan_result
        
        importer = SkillImporter()
        result = importer.import_from_url('https://example.com/skill.md')
        
        assert result.success is True
        assert result.skill_data['name'] == 'Test Skill'
        assert result.security_score == 95.0
        mock_download.assert_called_once()
        mock_scan.assert_called_once()
    
    @patch('src.skills.skill_importer.SkillImporter._download_content')
    @patch('src.skills.skill_importer.scan_skill_content')
    def test_import_security_failure(self, mock_scan, mock_download):
        """测试安全扫描失败"""
        mock_download.return_value = "# Malicious Skill\n\nDROP TABLE users;"
        
        # Mock不安全内容
        mock_scan_result = Mock()
        mock_scan_result.is_safe = False
        mock_scan_result.security_score = 30.0
        mock_scan_result.to_dict.return_value = {'issues': ['SQL injection detected']}
        mock_scan.return_value = mock_scan_result
        
        importer = SkillImporter()
        result = importer.import_from_url('https://example.com/skill.md')
        
        assert result.success is False
        assert '安全检查' in result.error
        assert result.security_score == 30.0
    
    def test_import_invalid_url(self):
        """测试无效URL"""
        importer = SkillImporter()
        result = importer.import_from_url('not-a-url')
        
        assert result.success is False
        assert '无效的URL' in result.error
    
    @patch('src.skills.skill_importer.SkillImporter._download_content')
    def test_import_empty_content(self, mock_download):
        """测试空内容"""
        mock_download.return_value = ''
        
        importer = SkillImporter()
        result = importer.import_from_url('https://example.com/empty.md')
        
        assert result.success is False
        assert '无法下载' in result.error or '内容为空' in result.error
    
    @patch('src.skills.skill_importer.SkillImporter._download_content')
    def test_import_parse_failure(self, mock_download):
        """测试解析失败"""
        mock_download.return_value = '\n\n\n'  # 无有效内容
        
        importer = SkillImporter()
        result = importer.import_from_url('https://example.com/invalid.md')
        
        assert result.success is False
        assert '解析失败' in result.error


class TestBatchImport:
    """批量导入测试"""
    
    @patch('src.skills.skill_importer.SkillImporter.import_from_url')
    def test_batch_import_all_success(self, mock_import):
        """测试批量导入全部成功"""
        # Mock所有导入都成功
        mock_import.return_value = SkillImportResult(
            success=True,
            skill_data={'name': 'Test', 'description': 'Test', 'content': 'Test', 'category': 'policy'},
            security_score=90.0
        )
        
        importer = SkillImporter()
        urls = ['https://example.com/skill1.md', 'https://example.com/skill2.md']
        results = importer.import_batch(urls)
        
        assert len(results) == 2
        assert all(r.success for r in results)
        assert mock_import.call_count == 2
    
    @patch('src.skills.skill_importer.SkillImporter.import_from_url')
    def test_batch_import_partial_success(self, mock_import):
        """测试批量导入部分成功"""
        # 第一个成功，第二个失败
        mock_import.side_effect = [
            SkillImportResult(success=True, skill_data={'name': 'OK'}, security_score=90.0),
            SkillImportResult(success=False, error='Failed')
        ]
        
        importer = SkillImporter()
        urls = ['https://example.com/good.md', 'https://example.com/bad.md']
        results = importer.import_batch(urls)
        
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def test_get_preset_skills(self):
        """测试get_preset_skills便捷函数"""
        presets = get_preset_skills()
        assert len(presets) == 5
        assert presets == ANTHROPIC_PRESETS
    
    @patch('src.skills.skill_importer.SkillImporter.import_from_url')
    def test_import_skill_from_url(self, mock_method):
        """测试import_skill_from_url便捷函数"""
        mock_method.return_value = SkillImportResult(success=True)
        
        result = import_skill_from_url('https://example.com/skill.md')
        
        assert result.success is True
        mock_method.assert_called_once()


class TestImportResult:
    """SkillImportResult数据类测试"""
    
    def test_to_dict_success(self):
        """测试成功结果转字典"""
        result = SkillImportResult(
            success=True,
            skill_data={'name': 'Test'},
            security_score=85.0
        )
        
        data = result.to_dict()
        assert data['success'] is True
        assert data['skill_data'] == {'name': 'Test'}
        assert data['security_score'] == 85.0
        assert data['error'] is None
    
    def test_to_dict_failure(self):
        """测试失败结果转字典"""
        result = SkillImportResult(
            success=False,
            error='Test error',
            security_issues={'issues': ['SQL injection']}
        )
        
        data = result.to_dict()
        assert data['success'] is False
        assert data['error'] == 'Test error'
        assert data['security_issues'] == {'issues': ['SQL injection']}
        assert data['skill_data'] is None
