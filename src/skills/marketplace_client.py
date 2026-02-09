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
CURATED_SKILLS = [
    {
        "name": "code-review",
        "displayName": "Code Review Assistant",
        "description": "Systematic code review with security, performance, and maintainability checks",
        "category": "development",
        "github_url": "https://raw.githubusercontent.com/anthropics/skills/main/code-review/SKILL.md",
        "source": "anthropic"
    },
    {
        "name": "python-best-practices",
        "displayName": "Python Best Practices",
        "description": "Python development best practices including testing, typing, and project structure",
        "category": "development",
        "github_url": "https://raw.githubusercontent.com/anthropics/skills/main/python-best-practices/SKILL.md",
        "source": "anthropic"
    },
    {
        "name": "technical-writing",
        "displayName": "Technical Writing",
        "description": "Create clear, well-structured technical documentation",
        "category": "writing",
        "github_url": "https://raw.githubusercontent.com/anthropics/skills/main/technical-writing/SKILL.md",
        "source": "anthropic"
    },
    {
        "name": "api-design",
        "displayName": "API Design",
        "description": "Design RESTful APIs following best practices and OpenAPI specification",
        "category": "development",
        "github_url": "https://raw.githubusercontent.com/anthropics/skills/main/api-design/SKILL.md",
        "source": "anthropic"
    },
    {
        "name": "data-analysis",
        "displayName": "Data Analysis",
        "description": "Structured data analysis framework with statistical methods and visualization",
        "category": "data-ai",
        "github_url": "https://raw.githubusercontent.com/anthropics/skills/main/data-analysis/SKILL.md",
        "source": "anthropic"
    },
    {
        "name": "security-audit",
        "displayName": "Security Audit",
        "description": "Security vulnerability assessment and remediation planning",
        "category": "devops",
        "github_url": "https://raw.githubusercontent.com/anthropics/skills/main/security-audit/SKILL.md",
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
               page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        搜索技能（依次尝试 SkillsMP API → GitHub → 精选列表）

        Returns:
            {
                "items": [...],
                "total": int,
                "page": int,
                "page_size": int,
                "source": "skillsmp" | "github" | "curated"
            }
        """
        # 尝试 SkillsMP API
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
        从 GitHub URL 下载并解析 Skill

        Returns:
            {"success": bool, "skill_md": str, "skill_data": dict, "error": str}
        """
        try:
            # 将 GitHub 页面URL转为 raw URL
            raw_url = self._to_raw_url(github_url)

            resp = self.session.get(raw_url, timeout=self.timeout)
            resp.raise_for_status()
            content = resp.text

            if not content.strip():
                return {"success": False, "error": "Downloaded content is empty"}

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

        except RequestException as e:
            logger.error(f"[marketplace] Download failed: {github_url}, {e}")
            return {"success": False, "error": f"Download failed: {str(e)}"}
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
        """调用 SkillsMP API 搜索"""
        headers = {'Authorization': f'Bearer {self.skillsmp_key}'}
        params = {
            'q': query,
            'page': page,
            'per_page': page_size,
        }
        if category:
            params['category'] = category

        resp = self.session.get(
            f'{self.skillsmp_base}/skills/search',
            params=params, headers=headers, timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()

        # 适配返回格式
        items = []
        for item in data.get('skills', data.get('items', [])):
            items.append({
                'name': item.get('name', ''),
                'displayName': item.get('display_name', item.get('name', '')),
                'description': item.get('description', ''),
                'category': item.get('category', ''),
                'stars': item.get('stars', 0),
                'slug': item.get('slug', ''),
                'github_url': item.get('github_url', ''),
                'source': 'skillsmp'
            })

        return {
            'items': items,
            'total': data.get('total', len(items)),
            'page': page,
            'page_size': page_size,
            'source': 'skillsmp'
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
        """将 GitHub URL 转为 raw URL"""
        if 'raw.githubusercontent.com' in url:
            return url
        # https://github.com/owner/repo/blob/branch/path → raw URL
        m = re.match(r'https?://github\.com/([^/]+)/([^/]+)/blob/(.+)', url)
        if m:
            owner, repo, path = m.groups()
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{path}"
        return url

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
