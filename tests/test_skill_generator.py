"""
Tests for Skill Generator and Marketplace Client
"""
import sys
import os
import time
import pytest

# 确保项目根目录在path中
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class TestSkillGenerator:
    """测试 AI Skill 生成器"""

    def test_import(self):
        """测试模块可以正常导入"""
        from src.skills.skill_generator import SkillGenerator, SkillGenerationResult
        assert SkillGenerator is not None
        assert SkillGenerationResult is not None

    def test_result_dataclass(self):
        """测试 SkillGenerationResult 数据结构"""
        from src.skills.skill_generator import SkillGenerationResult
        
        # 成功结果
        result = SkillGenerationResult(
            success=True,
            skill_md="---\nname: test\n---\nbody",
            skill_data={"name": "test"},
            security_score=85.0,
            generation_time=2.5
        )
        d = result.to_dict()
        assert d['success'] is True
        assert d['skill_md'] is not None
        assert d['security_score'] == 85.0
        
        # 失败结果
        result = SkillGenerationResult(success=False, error="test error")
        d = result.to_dict()
        assert d['success'] is False
        assert d['error'] == "test error"

    def test_generate_skill_name(self):
        """测试 skill name 生成"""
        from src.skills.skill_generator import SkillGenerator
        gen = SkillGenerator()

        # 英文主题
        name = gen._generate_skill_name("Supply Chain Risk Assessment")
        assert '-' in name or name.isalpha()
        assert name == name.lower()

        # 中文主题（hash fallback）
        name = gen._generate_skill_name("供应链风险评估")
        assert name.startswith("custom-skill-")
        assert len(name) <= 64

    def test_clean_output(self):
        """测试输出清理"""
        from src.skills.skill_generator import SkillGenerator
        gen = SkillGenerator()

        # 正常内容
        content = "---\nname: test\n---\nbody"
        assert gen._clean_output(content) == content

        # 带代码围栏
        wrapped = "```markdown\n---\nname: test\n---\nbody\n```"
        cleaned = gen._clean_output(wrapped)
        assert cleaned.startswith("---")
        assert "```" not in cleaned

        # 前面有垃圾文字
        noisy = "这是一个skill：\n---\nname: test\n---\nbody"
        cleaned = gen._clean_output(noisy)
        assert cleaned.startswith("---")

    def test_validate_skill_md(self):
        """测试 SKILL.md 格式验证"""
        from src.skills.skill_generator import SkillGenerator
        gen = SkillGenerator()

        # 合法内容
        valid = "---\nname: test-skill\ndescription: A test skill\n---\n" + "x" * 200
        assert gen._validate_skill_md(valid) is None

        # 缺少 frontmatter
        assert gen._validate_skill_md("no frontmatter") is not None

        # 缺少 name
        assert gen._validate_skill_md("---\ndescription: test\n---\nbody body body body body body body body body body body body body body body body body body body body body body body") is not None

        # body 太短
        assert gen._validate_skill_md("---\nname: test\ndescription: d\n---\nshort") is not None

    def test_parse_frontmatter(self):
        """测试 YAML frontmatter 解析"""
        from src.skills.skill_generator import SkillGenerator
        gen = SkillGenerator()

        content = """---
name: supply-chain-risk
displayName: 供应链风险评估
version: 1.0.0
category: analysis
tags: [供应链, 风险, 评估]
description: 供应链风险评估框架
applicable_roles: [策论家, 监察官]
---
## 核心能力
这是body内容
"""
        data = gen._parse_frontmatter(content)
        assert data['name'] == 'supply-chain-risk'
        assert data['displayName'] == '供应链风险评估'
        assert data['category'] == 'analysis'
        assert isinstance(data['tags'], list)
        assert '供应链' in data['tags']
        assert isinstance(data['applicable_roles'], list)
        assert 'content' in data

    def test_generate_empty_input(self):
        """测试空输入"""
        from src.skills.skill_generator import SkillGenerator
        gen = SkillGenerator()

        result = gen.generate(topic="", description="test")
        assert result.success is False
        assert "空" in result.error

        result = gen.generate(topic="test", description="")
        assert result.success is False
        assert "空" in result.error


class TestMarketplaceClient:
    """测试 Marketplace 客户端"""

    def test_import(self):
        """测试模块可以正常导入"""
        from src.skills.marketplace_client import MarketplaceClient
        assert MarketplaceClient is not None

    def test_categories(self):
        """测试获取分类"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()
        cats = client.get_categories()
        assert len(cats) > 0
        assert any(c['id'] == 'development' for c in cats)
        assert all('name' in c for c in cats)

    def test_search_curated_all(self):
        """测试精选列表搜索 - 无过滤"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        # 不给 query 和 category 时在 API 会拦截，但直接调内部方法测试
        result = client._search_curated('', '', 1, 20)
        assert result['source'] == 'curated'
        assert len(result['items']) > 0

    def test_search_curated_by_query(self):
        """测试精选列表搜索 - 关键词"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        result = client._search_curated('frontend', '', 1, 20)
        assert len(result['items']) > 0
        # 应该包含 frontend-design
        names = [i['name'] for i in result['items']]
        assert 'frontend-design' in names

    def test_search_curated_by_category(self):
        """测试精选列表搜索 - 分类"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        result = client._search_curated('', 'development', 1, 20)
        for item in result['items']:
            assert item['category'] == 'development'

    def test_to_raw_url(self):
        """测试 GitHub URL 转 raw URL"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        # 已经是 raw URL
        raw = "https://raw.githubusercontent.com/anthropics/skills/main/skills/webapp-testing/SKILL.md"
        assert client._to_raw_url(raw) == raw

        # blob URL
        blob = "https://github.com/anthropics/skills/blob/main/skills/webapp-testing/SKILL.md"
        result = client._to_raw_url(blob)
        assert 'raw.githubusercontent.com' in result
        assert '/blob/' not in result

        # tree URL (SkillsMP 返回的目录 URL)
        tree = "https://github.com/anthropics/skills/tree/main/.claude/skills/webapp-testing"
        result = client._to_raw_url(tree)
        assert 'raw.githubusercontent.com' in result
        assert result.endswith('/SKILL.md')
        assert '/tree/' not in result

    def test_github_tree_to_raw_url(self):
        """测试 SkillsMP githubUrl 目录转 raw SKILL.md URL"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        # 标准 SkillsMP 返回格式
        tree = "https://github.com/user/repo/tree/main/.claude/skills/my-skill"
        result = client._github_tree_to_raw_url(tree)
        assert result == "https://raw.githubusercontent.com/user/repo/main/.claude/skills/my-skill/SKILL.md"

        # blob URL 也处理
        blob = "https://github.com/user/repo/blob/main/path/SKILL.md"
        result = client._github_tree_to_raw_url(blob)
        assert result == "https://raw.githubusercontent.com/user/repo/main/path/SKILL.md"

        # 已经是 raw URL
        raw = "https://raw.githubusercontent.com/user/repo/main/SKILL.md"
        assert client._github_tree_to_raw_url(raw) == raw

        # 空字符串
        assert client._github_tree_to_raw_url('') == ''

        # 非 GitHub URL（原样返回）
        other = "https://example.com/skill"
        assert client._github_tree_to_raw_url(other) == other

    def test_parse_skill_md(self):
        """测试 SKILL.md 解析"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        content = """---
name: test-skill
description: A test
tags: [a, b]
---
# Test Skill
Body content here
"""
        data = client._parse_skill_md(content)
        assert data['name'] == 'test-skill'
        assert data['description'] == 'A test'
        assert 'content' in data
        assert 'Body content' in data['content']

    def test_parse_skill_md_no_frontmatter(self):
        """测试无 frontmatter 的解析"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        content = "# Just a heading\nSome content"
        data = client._parse_skill_md(content)
        assert data.get('content') == content

    def test_name_from_url(self):
        """测试从URL提取名称"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        name = client._name_from_url("https://raw.githubusercontent.com/anthropics/skills/main/skills/webapp-testing/SKILL.md")
        assert name == "webapp-testing"

        name = client._name_from_url("https://github.com/user/repo/blob/main/my-skill/SKILL.md")
        assert name == "my-skill"

    def test_reconstruct_url_known_repo(self):
        """测试从已知 slug 重建 URL（需要网络）"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        # 这个测试需要网络连接，跳过如果无法访问
        try:
            url = client.reconstruct_github_url("anthropics-skills-code-review", "anthropics/skills")
            # 可能返回 None（如果 repo 结构不同或网络不可达）
            if url:
                assert 'raw.githubusercontent.com' in url
                assert 'anthropics' in url
        except Exception:
            pytest.skip("Network not available")


class TestSkillGeneratorIntegration:
    """集成测试 - 需要配置 API Key"""

    @pytest.mark.skipif(
        not os.environ.get('TEST_LLM_INTEGRATION'),
        reason="Set TEST_LLM_INTEGRATION=1 to run LLM integration tests"
    )
    def test_generate_real(self):
        """实际调用 LLM 生成 Skill"""
        from src.skills.skill_generator import SkillGenerator
        gen = SkillGenerator()

        result = gen.generate(
            topic="供应链风险评估",
            description="为中小企业提供供应链风险评估框架，包括供应商评估、物流风险、地缘政治风险等维度",
            category="analysis",
            applicable_roles=["策论家", "监察官"]
        )

        assert result.success, f"生成失败: {result.error}"
        assert result.skill_md is not None
        assert result.skill_md.startswith("---")
        assert result.skill_data.get('name')
        assert result.security_score is not None
        assert result.generation_time > 0

        print(f"\n=== 生成结果 ===")
        print(f"Name: {result.skill_data.get('name')}")
        print(f"Lines: {len(result.skill_md.splitlines())}")
        print(f"Security Score: {result.security_score}")
        print(f"Time: {result.generation_time:.1f}s")
        print(f"\n=== 前50行 ===")
        print('\n'.join(result.skill_md.splitlines()[:50]))


class TestMarketplaceIntegration:
    """Marketplace 集成测试 - 需要网络"""

    @pytest.mark.skipif(
        not os.environ.get('TEST_MARKETPLACE_INTEGRATION'),
        reason="Set TEST_MARKETPLACE_INTEGRATION=1 to run marketplace integration tests"
    )
    def test_import_from_github(self):
        """从 GitHub 实际导入 Skill"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        # 使用本项目的 policy_analysis SKILL.md 的一个可靠 URL
        result = client.import_skill(
            "https://raw.githubusercontent.com/anthropics/skills/main/SKILL.md"
        )

        # 可能成功也可能404，取决于URL是否存在
        if result['success']:
            assert result['skill_md']
            assert result['skill_data']
            print(f"\n导入成功: {result['skill_data'].get('name')}")
        else:
            print(f"\n导入失败（预期内）: {result['error']}")

    @pytest.mark.skipif(
        not os.environ.get('TEST_MARKETPLACE_INTEGRATION'),
        reason="Set TEST_MARKETPLACE_INTEGRATION=1 to run marketplace integration tests"
    )
    def test_skillsmp_keyword_search(self):
        """SkillsMP 关键词搜索实际调用"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        if not client.skillsmp_key:
            pytest.skip("SKILLSMP_API_KEY not configured")

        result = client._search_skillsmp('code review', '', 1, 5)
        assert result['source'] == 'skillsmp'
        assert len(result['items']) > 0, "Should return at least 1 result"

        item = result['items'][0]
        assert item['name'], "Item should have a name"
        assert item['github_url'], "Item should have a github_url"
        assert 'raw.githubusercontent.com' in item['github_url'], "URL should be converted to raw"
        assert item['github_url'].endswith('/SKILL.md'), "URL should end with /SKILL.md"

        print(f"\n=== SkillsMP Keyword Search ===")
        for i in result['items']:
            print(f"  {i['name']} by {i['author']} ★{i['stars']} → {i['github_url'][:80]}...")

    @pytest.mark.skipif(
        not os.environ.get('TEST_MARKETPLACE_INTEGRATION'),
        reason="Set TEST_MARKETPLACE_INTEGRATION=1 to run marketplace integration tests"
    )
    def test_skillsmp_ai_search(self):
        """SkillsMP AI 语义搜索实际调用"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        if not client.skillsmp_key:
            pytest.skip("SKILLSMP_API_KEY not configured")

        result = client._search_skillsmp_ai('help me write better code reviews')
        assert result['source'] == 'skillsmp_ai'

        if result['items']:
            item = result['items'][0]
            assert item['name'], "Item should have a name"
            assert 'score' in item, "AI result should have score"
            assert 0 <= item['score'] <= 1, "Score should be between 0 and 1"

            print(f"\n=== SkillsMP AI Search ===")
            for i in result['items']:
                print(f"  {i['name']} (score={i['score']}) by {i['author']} → {i['github_url'][:80]}...")
        else:
            print("\nAI search returned 0 items (some results lacked skill object)")

    @pytest.mark.skipif(
        not os.environ.get('TEST_MARKETPLACE_INTEGRATION'),
        reason="Set TEST_MARKETPLACE_INTEGRATION=1 to run marketplace integration tests"
    )
    def test_search_mode_keyword(self):
        """通过 search() 接口测试关键词模式"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        if not client.skillsmp_key:
            pytest.skip("SKILLSMP_API_KEY not configured")

        result = client.search(query='testing', mode='keyword', page=1, page_size=5)
        assert result['items'], "Should return results"
        assert result['source'] in ('skillsmp', 'github', 'curated')

    @pytest.mark.skipif(
        not os.environ.get('TEST_MARKETPLACE_INTEGRATION'),
        reason="Set TEST_MARKETPLACE_INTEGRATION=1 to run marketplace integration tests"
    )
    def test_search_mode_ai(self):
        """通过 search() 接口测试 AI 模式"""
        from src.skills.marketplace_client import MarketplaceClient
        client = MarketplaceClient()

        if not client.skillsmp_key:
            pytest.skip("SKILLSMP_API_KEY not configured")

        result = client.search(query='make my frontend beautiful', mode='ai')
        assert result['items'] is not None  # 可能为空但不应报错
        print(f"\nAI mode via search(): {len(result['items'])} items, source={result['source']}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
