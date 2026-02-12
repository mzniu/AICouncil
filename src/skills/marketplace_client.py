"""
Skill Marketplace Client - 搜索和导入来自 SkillsMP / GitHub 的 Skills

支持三种来源：
1. SkillsMP API (需要 API Key)
2. GitHub Code Search (需要 GitHub Token，可选)
3. 精选列表 (内置 fallback)
"""
import re
import time
import requests
from typing import Dict, List, Optional, Any
from requests.exceptions import RequestException

from src.utils.logger import setup_logger
from src.skills.security_scanner import scan_skill_content
from src import config_manager as config

logger = setup_logger(__name__)

# SkillsMP 分类列表
MARKETPLACE_CATEGORIES = [
    {"id": "tools", "name": "Tools & Utilities", "count": 57000},
    {"id": "development", "name": "Development", "count": 47000},
    {"id": "data-ai", "name": "Data & AI", "count": 33000},
    {"id": "business", "name": "Business", "count": 31000},
    {"id": "devops", "name": "DevOps & Infrastructure", "count": 26000},
    {"id": "writing", "name": "Writing & Documentation", "count": 9000},
    {"id": "design", "name": "Design & Creative", "count": 5000},
    {"id": "education", "name": "Education", "count": 4000},
    {"id": "science", "name": "Science & Research", "count": 3000},
    {"id": "finance", "name": "Finance", "count": 2000},
    {"id": "health", "name": "Health & Medical", "count": 1500},
    {"id": "legal", "name": "Legal & Compliance", "count": 1000},
]

# 精选 GitHub 上高质量的 SKILL.md 列表（fallback 数据源）
# 注意：anthropics/skills 仓库的实际路径是 skills/{name}/SKILL.md
CURATED_SKILLS = [
    {
        "name": "webapp-testing",
        "displayName": "Web App Testing",
        "description": "Comprehensive web application testing with automated browser testing and validation",
        "category": "development",
        "github_url": "https://raw.githubusercontent.com/anthropics/skills/main/skills/webapp-testing/SKILL.md",
        "source": "anthropic"
    },
    {
        "name": "frontend-design",
        "displayName": "Frontend Design",
        "description": "Create polished frontend designs with modern UI/UX patterns and responsive layouts",
        "category": "design",
        "github_url": "https://raw.githubusercontent.com/anthropics/skills/main/skills/frontend-design/SKILL.md",
        "source": "anthropic"
    },
    {
        "name": "brand-guidelines",
        "displayName": "Brand Guidelines",
        "description": "Create and maintain brand guidelines ensuring consistent visual identity",
        "category": "business",
        "github_url": "https://raw.githubusercontent.com/anthropics/skills/main/skills/brand-guidelines/SKILL.md",
        "source": "anthropic"
    },
    {
        "name": "internal-comms",
        "displayName": "Internal Communications",
        "description": "Draft professional internal communications, memos, and announcements",
        "category": "writing",
        "github_url": "https://raw.githubusercontent.com/anthropics/skills/main/skills/internal-comms/SKILL.md",
        "source": "anthropic"
    },
    {
        "name": "mcp-builder",
        "displayName": "MCP Server Builder",
        "description": "Build Model Context Protocol servers for tool integration and AI agent capabilities",
        "category": "development",
        "github_url": "https://raw.githubusercontent.com/anthropics/skills/main/skills/mcp-builder/SKILL.md",
        "source": "anthropic"
    },
    {
        "name": "skill-creator",
        "displayName": "Skill Creator",
        "description": "Create new Agent Skills with proper structure, metadata, and best practices",
        "category": "tools",
        "github_url": "https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md",
        "source": "anthropic"
    },
]


class MarketplaceClient:
    """Skill Marketplace 客户端"""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AICouncil-Marketplace/1.0',
            'Accept': 'application/json'
        })

        # SkillsMP API (可选)
        self.skillsmp_key = getattr(config, 'SKILLSMP_API_KEY', None)
        self.skillsmp_base = 'https://skillsmp.com/api/v1'

        # GitHub Token (可选，提高速率限制)
        self.github_token = getattr(config, 'GITHUB_TOKEN', None)

    def search(self, query: str = '', category: str = '',
               page: int = 1, page_size: int = 20,
               mode: str = 'keyword') -> Dict[str, Any]:
        """
        搜索技能（依次尝试 SkillsMP API → GitHub → 精选列表）

        Args:
            mode: 'keyword' (关键词搜索) | 'ai' (AI 语义搜索)

        Returns:
            {
                "items": [...],
                "total": int,
                "page": int,
                "page_size": int,
                "source": "skillsmp" | "skillsmp_ai" | "github" | "curated"
            }
        """
        # AI 语义搜索模式
        if mode == 'ai' and self.skillsmp_key and query:
            try:
                result = self._search_skillsmp_ai(query)
                if result and result.get('items'):
                    return result
            except Exception as e:
                logger.warning(f"[marketplace] SkillsMP AI search failed: {e}")
            # AI搜索失败，fallback到关键词搜索
            logger.info("[marketplace] AI search failed, falling back to keyword search")

        # 尝试 SkillsMP API 关键词搜索
        if self.skillsmp_key:
            try:
                result = self._search_skillsmp(query, category, page, page_size)
                if result and result.get('items'):
                    return result
            except Exception as e:
                logger.warning(f"[marketplace] SkillsMP search failed: {e}")

        # 尝试 GitHub Code Search
        if self.github_token and query:
            try:
                result = self._search_github(query, page, page_size)
                if result and result.get('items'):
                    return result
            except Exception as e:
                logger.warning(f"[marketplace] GitHub search failed: {e}")

        # Fallback: 精选列表
        return self._search_curated(query, category, page, page_size)

    def get_categories(self) -> List[Dict[str, Any]]:
        """获取 Marketplace 分类列表"""
        return MARKETPLACE_CATEGORIES.copy()

    def import_skill(self, github_url: str) -> Dict[str, Any]:
        """
        从 GitHub URL 下载并解析 Skill，自动尝试 URL 变体

        Returns:
            {"success": bool, "skill_md": str, "skill_data": dict, "error": str}
        """
        try:
            # 构建候选 URL 列表（原始 + 分支/路径变体）
            urls_to_try = self._build_url_variants(github_url)

            content = None
            last_error = None
            for url in urls_to_try:
                try:
                    resp = self.session.get(url, timeout=self.timeout)
                    resp.raise_for_status()
                    if resp.text.strip():
                        content = resp.text
                        break
                except RequestException as e:
                    last_error = e
                    continue

            if content is None:
                logger.error(f"[marketplace] Download failed for all URL variants of: {github_url}, last error: {last_error}")
                return {"success": False, "error": f"Download failed: {str(last_error)}"}

            # 解析 frontmatter
            skill_data = self._parse_skill_md(content)
            if not skill_data.get('name'):
                # 从URL推断name
                skill_data['name'] = self._name_from_url(github_url)

            if not skill_data.get('description'):
                # 取body首行作description
                body = skill_data.get('content', '')
                first_line = body.split('\n')[0].strip('# ').strip() if body else ''
                skill_data['description'] = first_line[:200] or 'Imported from marketplace'

            skill_data['source_url'] = github_url

            return {
                "success": True,
                "skill_md": content,
                "skill_data": skill_data
            }

        except Exception as e:
            logger.error(f"[marketplace] Import error: {github_url}, {e}")
            return {"success": False, "error": f"Import error: {str(e)}"}

    def reconstruct_github_url(self, slug: str, owner_repo: str = None) -> Optional[str]:
        """
        从 SkillsMP slug 重建 GitHub raw URL

        slug 格式示例：
        "anthropics-skills-code-review-skill-md"
        → https://raw.githubusercontent.com/anthropics/skills/main/code-review/SKILL.md

        Args:
            slug: SkillsMP URL slug
            owner_repo: 可选 "owner/repo" 辅助解析
        """
        if not slug:
            return None

        # 移除 -skill-md 后缀
        base = re.sub(r'-skill-md$', '', slug, flags=re.IGNORECASE)
        parts = base.split('-')

        if len(parts) < 3:
            return None

        if owner_repo:
            # 明确给出了 owner/repo
            owner, repo = owner_repo.split('/', 1) if '/' in owner_repo else (parts[0], parts[1])
            path_parts = []
            # 跳过 owner 和 repo 对应的 parts
            skip = 0
            for i, p in enumerate(parts):
                if skip == 0 and p == owner.lower().replace('-', ''):
                    skip = 1
                elif skip == 1 and p in repo.lower().split('-'):
                    skip += 1
                elif skip >= 2 or i >= 2:
                    path_parts.append(p)
            path = '/'.join(path_parts) if path_parts else parts[-1]
        else:
            # 猜测：前两段是 owner/repo
            owner = parts[0]
            repo = parts[1]
            path = '/'.join(parts[2:]) if len(parts) > 2 else ''

        # 尝试 main 分支，失败后 master
        for branch in ['main', 'master']:
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}/SKILL.md"
            try:
                resp = self.session.head(url, timeout=5, allow_redirects=True)
                if resp.status_code == 200:
                    return url
            except RequestException:
                continue

        # 最后尝试 .github/skills 路径（GitHub 官方 skills 结构）
        for branch in ['main', 'master']:
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/.github/skills/{path}/SKILL.md"
            try:
                resp = self.session.head(url, timeout=5, allow_redirects=True)
                if resp.status_code == 200:
                    return url
            except RequestException:
                continue

        logger.warning(f"[marketplace] Cannot reconstruct URL from slug: {slug}")
        return None

    # ========== Private Methods ==========

    def _search_skillsmp(self, query: str, category: str,
                         page: int, page_size: int) -> Dict[str, Any]:
        """调用 SkillsMP API 关键词搜索"""
        headers = {'Authorization': f'Bearer {self.skillsmp_key}'}
        params = {
            'q': query or '*',
            'page': page,
            'limit': min(page_size, 100),
        }
        if category:
            params['category'] = category

        resp = self.session.get(
            f'{self.skillsmp_base}/skills/search',
            params=params, headers=headers, timeout=self.timeout
        )
        resp.raise_for_status()
        body = resp.json()

        if not body.get('success'):
            logger.warning(f"[marketplace] SkillsMP API returned success=false")
            return {'items': [], 'total': 0, 'page': page, 'page_size': page_size, 'source': 'skillsmp'}

        data = body.get('data', {})
        skills_list = data.get('skills', [])
        pagination = data.get('pagination', {})

        items = []
        for skill in skills_list:
            # githubUrl 是目录 URL (github.com/owner/repo/tree/branch/.claude/skills/name)
            # 需要转为 raw SKILL.md URL
            github_url = skill.get('githubUrl', '')
            raw_url = self._github_tree_to_raw_url(github_url) if github_url else ''

            items.append({
                'name': skill.get('name', ''),
                'displayName': skill.get('name', ''),
                'description': skill.get('description', ''),
                'author': skill.get('author', ''),
                'category': '',
                'stars': skill.get('stars', 0),
                'slug': '',
                'github_url': raw_url,
                'skill_url': skill.get('skillUrl', ''),
                'updated_at': skill.get('updatedAt', ''),
                'source': 'skillsmp'
            })

        return {
            'items': items,
            'total': pagination.get('total', len(items)),
            'page': pagination.get('page', page),
            'page_size': pagination.get('limit', page_size),
            'source': 'skillsmp'
        }

    def _search_skillsmp_ai(self, query: str) -> Dict[str, Any]:
        """调用 SkillsMP AI 语义搜索（Cloudflare AI 向量检索）"""
        headers = {'Authorization': f'Bearer {self.skillsmp_key}'}
        params = {'q': query}

        resp = self.session.get(
            f'{self.skillsmp_base}/skills/ai-search',
            params=params, headers=headers, timeout=self.timeout
        )
        resp.raise_for_status()
        body = resp.json()

        if not body.get('success'):
            logger.warning(f"[marketplace] SkillsMP AI search returned success=false")
            return {'items': [], 'total': 0, 'page': 1, 'page_size': 20, 'source': 'skillsmp_ai'}

        data = body.get('data', {})
        results = data.get('data', [])  # data.data[] 是结果数组

        items = []
        for result in results:
            skill = result.get('skill')
            if not skill:
                # 部分结果只有 file_id/filename/score，没有 skill 对象
                continue

            github_url = skill.get('githubUrl', '')
            raw_url = self._github_tree_to_raw_url(github_url) if github_url else ''

            items.append({
                'name': skill.get('name', ''),
                'displayName': skill.get('name', ''),
                'description': skill.get('description', ''),
                'author': skill.get('author', ''),
                'category': '',
                'stars': skill.get('stars', 0),
                'slug': '',
                'github_url': raw_url,
                'skill_url': skill.get('skillUrl', ''),
                'updated_at': skill.get('updatedAt', ''),
                'score': round(result.get('score', 0), 3),
                'source': 'skillsmp_ai'
            })

        return {
            'items': items,
            'total': len(items),
            'page': 1,
            'page_size': len(items),
            'source': 'skillsmp_ai'
        }

    def _search_github(self, query: str, page: int, page_size: int) -> Dict[str, Any]:
        """通过 GitHub Code Search 搜索 SKILL.md 文件"""
        headers = {'Authorization': f'token {self.github_token}'}
        search_query = f'{query} filename:SKILL.md'
        params = {
            'q': search_query,
            'page': page,
            'per_page': min(page_size, 30)  # GitHub限制30
        }

        resp = self.session.get(
            'https://api.github.com/search/code',
            params=params, headers=headers, timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()

        items = []
        for item in data.get('items', []):
            repo = item.get('repository', {})
            html_url = item.get('html_url', '')
            # 构建 raw URL
            raw_url = html_url.replace(
                'github.com', 'raw.githubusercontent.com'
            ).replace('/blob/', '/')

            items.append({
                'name': item.get('name', 'SKILL.md'),
                'displayName': f"{repo.get('full_name', '')} / {item.get('path', '')}",
                'description': repo.get('description', ''),
                'category': '',
                'stars': repo.get('stargazers_count', 0),
                'slug': '',
                'github_url': raw_url,
                'html_url': html_url,
                'source': 'github'
            })

        return {
            'items': items,
            'total': min(data.get('total_count', 0), 1000),
            'page': page,
            'page_size': page_size,
            'source': 'github'
        }

    def _search_curated(self, query: str, category: str,
                        page: int, page_size: int) -> Dict[str, Any]:
        """搜索精选列表"""
        filtered = CURATED_SKILLS.copy()

        if query:
            q_lower = query.lower()
            filtered = [
                s for s in filtered
                if q_lower in s.get('name', '').lower()
                or q_lower in s.get('displayName', '').lower()
                or q_lower in s.get('description', '').lower()
            ]

        if category:
            cat_lower = category.lower()
            filtered = [s for s in filtered if s.get('category', '').lower() == cat_lower]

        # 分页
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = filtered[start:end]

        # 统一格式
        items = []
        for s in page_items:
            items.append({
                'name': s['name'],
                'displayName': s.get('displayName', s['name']),
                'description': s.get('description', ''),
                'category': s.get('category', ''),
                'stars': 0,
                'slug': '',
                'github_url': s.get('github_url', ''),
                'source': 'curated'
            })

        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'source': 'curated'
        }

    def _to_raw_url(self, url: str) -> str:
        """将 GitHub URL 转为 raw URL（支持 blob 和 tree URL）"""
        if 'raw.githubusercontent.com' in url:
            return url
        # https://github.com/owner/repo/blob/branch/path → raw URL
        m = re.match(r'https?://github\.com/([^/]+)/([^/]+)/blob/(.+)', url)
        if m:
            owner, repo, path = m.groups()
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{path}"
        # https://github.com/owner/repo/tree/branch/path → raw URL (目录，追加 /SKILL.md)
        m = re.match(r'https?://github\.com/([^/]+)/([^/]+)/tree/(.+)', url)
        if m:
            owner, repo, path = m.groups()
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{path}/SKILL.md"
        return url

    def _build_url_variants(self, github_url: str) -> List[str]:
        """
        构建候选 URL 列表，用于容错下载。
        针对 raw URL 尝试不同分支和路径变体。
        """
        primary = self._to_raw_url(github_url)
        variants = [primary]

        # 解析 raw URL: raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}
        m = re.match(
            r'https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)',
            primary
        )
        if not m:
            return variants

        owner, repo, branch, path = m.groups()

        # 1) 尝试另一个分支
        alt_branch = 'master' if branch == 'main' else 'main'
        variants.append(f"https://raw.githubusercontent.com/{owner}/{repo}/{alt_branch}/{path}")

        # 2) 如果路径是 skills/xxx/SKILL.md，也尝试 .claude/skills/xxx/SKILL.md
        if path.startswith('skills/') and not path.startswith('.claude/'):
            claude_path = '.claude/' + path
            variants.append(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{claude_path}")
            variants.append(f"https://raw.githubusercontent.com/{owner}/{repo}/{alt_branch}/{claude_path}")

        # 3) 如果路径是 .claude/skills/xxx/SKILL.md，也尝试去掉 .claude/
        if path.startswith('.claude/skills/'):
            short_path = path.replace('.claude/', '', 1)
            variants.append(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{short_path}")
            variants.append(f"https://raw.githubusercontent.com/{owner}/{repo}/{alt_branch}/{short_path}")

        # 去重保序
        seen = set()
        unique = []
        for v in variants:
            if v not in seen:
                seen.add(v)
                unique.append(v)
        return unique

    def _github_tree_to_raw_url(self, github_url: str) -> str:
        """
        将 SkillsMP 返回的 GitHub 目录 URL 转为 raw SKILL.md URL

        输入: https://github.com/owner/repo/tree/main/.claude/skills/name
        输出: https://raw.githubusercontent.com/owner/repo/main/.claude/skills/name/SKILL.md
        """
        if not github_url:
            return ''
        if 'raw.githubusercontent.com' in github_url:
            return github_url

        m = re.match(r'https?://github\.com/([^/]+)/([^/]+)/tree/(.+)', github_url)
        if m:
            owner, repo, path = m.groups()
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{path}/SKILL.md"

        # 如果是 blob URL，也处理
        m = re.match(r'https?://github\.com/([^/]+)/([^/]+)/blob/(.+)', github_url)
        if m:
            owner, repo, path = m.groups()
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{path}"

        logger.warning(f"[marketplace] Cannot convert github URL to raw: {github_url}")
        return github_url

    def _parse_skill_md(self, content: str) -> Dict[str, Any]:
        """解析 SKILL.md 内容为元数据字典"""
        result = {}
        content = content.strip()

        if content.startswith('---'):
            second_marker = content.find('---', 3)
            if second_marker > 0:
                frontmatter = content[3:second_marker].strip()
                body = content[second_marker + 3:].strip()

                for line in frontmatter.split('\n'):
                    line = line.strip()
                    if ':' in line and not line.startswith('#') and not line.startswith('-'):
                        key, _, value = line.partition(':')
                        key = key.strip()
                        value = value.strip()
                        if value.startswith('[') and value.endswith(']'):
                            items = value[1:-1].split(',')
                            result[key] = [i.strip().strip('"\'') for i in items if i.strip()]
                        else:
                            result[key] = value.strip('"\'')

                result['content'] = body
            else:
                result['content'] = content
        else:
            result['content'] = content

        return result

    def _name_from_url(self, url: str) -> str:
        """从URL推断skill名称"""
        # 提取路径中最后一个有意义的目录名
        clean = url.rstrip('/')
        parts = clean.split('/')
        for p in reversed(parts):
            p_lower = p.lower()
            if p_lower not in ('skill.md', 'readme.md', 'main', 'master', 'blob', ''):
                name = re.sub(r'[^a-z0-9-]', '-', p_lower)
                return re.sub(r'-+', '-', name).strip('-')[:64]
        return 'imported-skill'
