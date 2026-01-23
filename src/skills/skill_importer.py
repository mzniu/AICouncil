"""
Skills导入工具 - 支持GitHub raw URL和Anthropic预设库导入
"""
import re
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from src.utils.logger import setup_logger
from src.skills.security_scanner import scan_skill_content

logger = setup_logger(__name__)


@dataclass
class SkillImportResult:
    """技能导入结果"""
    success: bool
    skill_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    security_score: Optional[float] = None
    security_issues: Optional[Dict] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'skill_data': self.skill_data,
            'error': self.error,
            'security_score': self.security_score,
            'security_issues': self.security_issues
        }


# Anthropic官方预设Skills库（手动维护）
ANTHROPIC_PRESETS = [
    {
        'id': 'anthropic_policy_analysis',
        'name': '政策分析 (Anthropic官方)',
        'description': 'Anthropic官方政策分析Skill模板',
        'category': 'policy',
        'url': 'https://raw.githubusercontent.com/anthropics/anthropic-cookbook/main/skills/policy_analysis.md',
        'source': 'anthropic'
    },
    {
        'id': 'anthropic_tech_evaluation',
        'name': '技术评估 (Anthropic官方)',
        'description': 'Anthropic官方技术评估Skill模板',
        'category': 'technical',
        'url': 'https://raw.githubusercontent.com/anthropics/anthropic-cookbook/main/skills/tech_evaluation.md',
        'source': 'anthropic'
    },
    {
        'id': 'anthropic_research_synthesis',
        'name': '研究综合 (Anthropic官方)',
        'description': 'Anthropic官方研究综合Skill模板',
        'category': 'research',
        'url': 'https://raw.githubusercontent.com/anthropics/anthropic-cookbook/main/skills/research_synthesis.md',
        'source': 'anthropic'
    },
    {
        'id': 'anthropic_stakeholder_analysis',
        'name': '利益相关者分析 (Anthropic官方)',
        'description': 'Anthropic官方利益相关者分析Skill模板',
        'category': 'strategy',
        'url': 'https://raw.githubusercontent.com/anthropics/anthropic-cookbook/main/skills/stakeholder_analysis.md',
        'source': 'anthropic'
    },
    {
        'id': 'anthropic_risk_assessment',
        'name': '风险评估 (Anthropic官方)',
        'description': 'Anthropic官方风险评估Skill模板',
        'category': 'risk',
        'url': 'https://raw.githubusercontent.com/anthropics/anthropic-cookbook/main/skills/risk_assessment.md',
        'source': 'anthropic'
    }
]


class SkillImporter:
    """技能导入器 - 支持URL导入和预设库"""
    
    def __init__(self, timeout: int = 30):
        """
        初始化导入器
        
        Args:
            timeout: HTTP请求超时时间（秒）
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AICouncil-SkillImporter/1.0'
        })
    
    def get_anthropic_presets(self) -> List[Dict[str, Any]]:
        """
        获取Anthropic预设Skills列表
        
        Returns:
            预设Skills列表
        """
        return ANTHROPIC_PRESETS.copy()
    
    def import_from_url(self, url: str, strict_security: bool = False) -> SkillImportResult:
        """
        从URL导入Skill（GitHub raw URL或其他Markdown URL）
        
        Args:
            url: Markdown文件URL
            strict_security: 是否启用严格安全模式
        
        Returns:
            SkillImportResult导入结果
        """
        try:
            logger.info(f"开始从URL导入Skill: {url}")
            
            # 验证URL格式
            if not self._is_valid_url(url):
                return SkillImportResult(
                    success=False,
                    error=f"无效的URL格式: {url}"
                )
            
            # 下载Markdown内容
            content = self._download_content(url)
            if not content:
                return SkillImportResult(
                    success=False,
                    error="无法下载Skill内容或内容为空"
                )
            
            # 解析Markdown并提取元数据
            skill_data = self.parse_markdown_skill(content, url)
            if not skill_data:
                return SkillImportResult(
                    success=False,
                    error="Markdown解析失败：无法提取有效元数据"
                )
            
            # 安全扫描
            scan_result = scan_skill_content(skill_data['content'], strict_mode=strict_security)
            if not scan_result.is_safe:
                logger.warning(f"URL导入安全扫描失败: {url}, score={scan_result.security_score}")
                return SkillImportResult(
                    success=False,
                    error="内容未通过安全检查",
                    security_score=scan_result.security_score,
                    security_issues=scan_result.to_dict()
                )
            
            logger.info(f"URL导入成功: {skill_data['name']} (score={scan_result.security_score})")
            return SkillImportResult(
                success=True,
                skill_data=skill_data,
                security_score=scan_result.security_score
            )
            
        except requests.RequestException as e:
            logger.error(f"网络请求失败: {url}, error={str(e)}")
            return SkillImportResult(
                success=False,
                error=f"网络请求失败: {str(e)}"
            )
        except Exception as e:
            logger.error(f"导入过程异常: {url}, error={str(e)}")
            return SkillImportResult(
                success=False,
                error=f"导入异常: {str(e)}"
            )
    
    def import_batch(self, urls: List[str], strict_security: bool = False) -> List[SkillImportResult]:
        """
        批量导入Skills
        
        Args:
            urls: URL列表
            strict_security: 是否启用严格安全模式
        
        Returns:
            导入结果列表
        """
        results = []
        for url in urls:
            result = self.import_from_url(url, strict_security)
            results.append(result)
        
        success_count = sum(1 for r in results if r.success)
        logger.info(f"批量导入完成: {success_count}/{len(urls)} 成功")
        return results
    
    def parse_markdown_skill(self, content: str, source_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        解析Markdown格式的Skill并提取元数据
        
        支持的格式：
        1. YAML Front Matter (---开头的YAML块)
        2. 第一行作为标题（# Title格式）
        3. 第二段作为描述
        
        Args:
            content: Markdown内容
            source_url: 来源URL（可选）
        
        Returns:
            包含name, description, content, category等的字典，失败返回None
        """
        if not content or not content.strip():
            return None
        
        lines = content.split('\n')
        metadata = {
            'content': content,
            'source_url': source_url
        }
        
        # 尝试解析YAML Front Matter
        if content.strip().startswith('---'):
            yaml_end = content.find('---', 3)
            if yaml_end > 0:
                yaml_block = content[3:yaml_end].strip()
                yaml_metadata = self._parse_yaml_metadata(yaml_block)
                metadata.update(yaml_metadata)
                # 移除YAML块后的内容作为实际content
                metadata['content'] = content[yaml_end + 3:].strip()
        
        # 如果没有从YAML提取到name，尝试从第一行标题提取
        if 'name' not in metadata:
            for line in lines:
                line = line.strip()
                if line.startswith('#'):
                    # 提取标题（去除#号和前后空格）
                    title = line.lstrip('#').strip()
                    if title:
                        metadata['name'] = title
                        break
        
        # 如果没有提取到description，尝试从第一段非标题内容提取
        if 'description' not in metadata:
            in_content = False
            description_lines = []
            for line in lines:
                stripped = line.strip()
                # 跳过YAML块和标题
                if stripped.startswith('---') or stripped.startswith('#'):
                    in_content = True
                    continue
                if in_content and stripped:
                    description_lines.append(stripped)
                    # 提取前100个字符作为描述
                    if len(' '.join(description_lines)) > 100:
                        break
            
            if description_lines:
                desc = ' '.join(description_lines)
                metadata['description'] = desc[:200] + '...' if len(desc) > 200 else desc
        
        # 默认值填充
        if 'name' not in metadata:
            # 如果source_url存在，尝试从URL提取文件名
            if source_url:
                filename = source_url.split('/')[-1].replace('.md', '').replace('_', ' ').title()
                metadata['name'] = filename
            else:
                metadata['name'] = "Imported Skill"
        
        if 'description' not in metadata:
            metadata['description'] = f"从外部源导入的Skill"
        
        if 'category' not in metadata:
            metadata['category'] = 'custom'
        
        # 确保is_builtin为False（外部导入的技能）
        metadata['is_builtin'] = False
        
        return metadata
    
    def _is_valid_url(self, url: str) -> bool:
        """
        验证URL格式
        
        Args:
            url: 待验证的URL
        
        Returns:
            是否为有效URL
        """
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))
    
    def _download_content(self, url: str) -> Optional[str]:
        """
        下载URL内容
        
        Args:
            url: 目标URL
        
        Returns:
            下载的文本内容，失败返回None
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 检查Content-Type（应该是text/plain或text/markdown）
            content_type = response.headers.get('Content-Type', '')
            if 'text' not in content_type and 'markdown' not in content_type:
                logger.warning(f"URL返回非文本内容: {content_type}")
            
            content = response.text
            if not content or len(content.strip()) < 10:
                logger.warning(f"URL内容过短: {len(content)} bytes")
                return None
            
            return content
            
        except requests.RequestException as e:
            logger.error(f"下载失败: {url}, error={str(e)}")
            return None
    
    def _parse_yaml_metadata(self, yaml_block: str) -> Dict[str, Any]:
        """
        解析YAML Front Matter元数据（简化版，无需pyyaml依赖）
        
        支持的格式：
        key: value
        key: "value with spaces"
        
        Args:
            yaml_block: YAML文本块
        
        Returns:
            元数据字典
        """
        metadata = {}
        
        for line in yaml_block.split('\n'):
            line = line.strip()
            if ':' not in line:
                continue
            
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            
            # 映射常见字段
            if key.lower() in ['name', 'title']:
                metadata['name'] = value
            elif key.lower() in ['description', 'desc']:
                metadata['description'] = value
            elif key.lower() in ['category', 'type']:
                metadata['category'] = value
            elif key.lower() in ['tags']:
                # 简单解析tags（假设是逗号分隔）
                metadata['tags'] = [t.strip() for t in value.split(',')]
        
        return metadata


def import_skill_from_url(url: str, strict_security: bool = False) -> SkillImportResult:
    """
    便捷函数：从URL导入单个Skill
    
    Args:
        url: Skill的URL
        strict_security: 是否启用严格安全模式
    
    Returns:
        SkillImportResult
    """
    importer = SkillImporter()
    return importer.import_from_url(url, strict_security)


def get_preset_skills() -> List[Dict[str, Any]]:
    """
    便捷函数：获取预设Skills列表
    
    Returns:
        预设Skills列表
    """
    importer = SkillImporter()
    return importer.get_anthropic_presets()
