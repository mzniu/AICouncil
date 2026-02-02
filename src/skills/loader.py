"""
Skill Loader for AICouncil
Loads and parses SKILL.md files following Anthropic Agent Skills standard
"""

import os
import re
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class Skill:
    """Represents a loaded skill with metadata and content"""
    
    # Metadata from YAML frontmatter
    name: str
    display_name: str
    version: str
    category: str
    tags: List[str]
    author: str
    created: str
    updated: str
    description: str
    requirements: Dict[str, str]
    applicable_roles: List[str]
    
    # Full skill content (markdown body after frontmatter)
    content: str
    
    # File path where skill was loaded from
    file_path: str
    
    # Optional fields
    dependencies: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


class SkillLoader:
    """
    Loads skills from filesystem (builtin skills in skills/builtin/)
    
    Skills follow Anthropic's SKILL.md standard:
    - YAML frontmatter with metadata
    - Markdown content with frameworks, templates, quality standards
    """
    
    def __init__(self, builtin_skills_dir: Optional[str] = None):
        """
        Initialize SkillLoader
        
        Args:
            builtin_skills_dir: Path to builtin skills directory
                               Defaults to {project_root}/skills/builtin/
        """
        if builtin_skills_dir is None:
            # Default to project_root/skills/builtin/
            project_root = Path(__file__).parent.parent.parent
            builtin_skills_dir = project_root / "skills" / "builtin"
        
        self.builtin_skills_dir = Path(builtin_skills_dir)
        logger.info(f"SkillLoader initialized with builtin_skills_dir: {self.builtin_skills_dir}")
    
    def load_all_builtin_skills(self) -> List[Skill]:
        """
        Load all builtin skills from skills/builtin/ directory
        
        Returns:
            List of Skill objects
        """
        skills = []
        
        if not self.builtin_skills_dir.exists():
            logger.warning(f"Builtin skills directory does not exist: {self.builtin_skills_dir}")
            return skills
        
        # Iterate through all subdirectories looking for SKILL.md files
        for skill_dir in self.builtin_skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                logger.debug(f"No SKILL.md found in {skill_dir}")
                continue
            
            try:
                skill = self.load_skill_from_file(str(skill_file))
                if skill:
                    skills.append(skill)
                    logger.info(f"Loaded skill: {skill.name} v{skill.version} from {skill_dir.name}")
            except Exception as e:
                logger.error(f"Failed to load skill from {skill_file}: {e}", exc_info=True)
        
        logger.info(f"Loaded {len(skills)} builtin skills")
        return skills
    
    def load_skill_by_name(self, skill_name: str) -> Optional[Skill]:
        """
        Load a specific skill by name
        
        Args:
            skill_name: Name of the skill (e.g., "policy_analysis")
        
        Returns:
            Skill object or None if not found
        """
        skill_file = self.builtin_skills_dir / skill_name / "SKILL.md"
        
        if not skill_file.exists():
            logger.warning(f"Skill file not found: {skill_file}")
            return None
        
        return self.load_skill_from_file(str(skill_file))
    
    def load_skill_from_file(self, file_path: str) -> Optional[Skill]:
        """
        Load a skill from a SKILL.md file
        
        Args:
            file_path: Path to SKILL.md file
        
        Returns:
            Skill object or None if parsing fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse frontmatter and content
            metadata, body = self._parse_frontmatter(content)
            
            if not metadata:
                logger.error(f"No YAML frontmatter found in {file_path}")
                return None
            
            # Extract required fields
            skill = Skill(
                name=metadata.get('name', ''),
                display_name=metadata.get('displayName', metadata.get('name', '')),
                version=metadata.get('version', '1.0.0'),
                category=metadata.get('category', 'general'),
                tags=metadata.get('tags', []),
                author=metadata.get('author', 'Unknown'),
                created=metadata.get('created', ''),
                updated=metadata.get('updated', ''),
                description=metadata.get('description', ''),
                requirements=metadata.get('requirements', {}),
                applicable_roles=metadata.get('applicable_roles', []),
                content=body,
                file_path=file_path,
                dependencies=metadata.get('dependencies', []),
                examples=metadata.get('examples', [])
            )
            
            return skill
            
        except Exception as e:
            logger.error(f"Error loading skill from {file_path}: {e}", exc_info=True)
            return None
    
    def _parse_frontmatter(self, content: str) -> tuple[Dict, str]:
        """
        Parse YAML frontmatter from markdown content
        
        Expects format:
        ---
        key: value
        ---
        # Markdown content
        
        Args:
            content: Full file content
        
        Returns:
            Tuple of (metadata_dict, markdown_body)
        """
        # Match YAML frontmatter pattern
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(pattern, content, re.DOTALL)
        
        if not match:
            logger.warning("No YAML frontmatter found")
            return {}, content
        
        yaml_content = match.group(1)
        markdown_body = match.group(2)
        
        # Parse YAML manually (avoid external dependency)
        metadata = self._parse_yaml_simple(yaml_content)
        
        return metadata, markdown_body.strip()
    
    def _parse_yaml_simple(self, yaml_content: str) -> Dict:
        """
        Simple YAML parser for frontmatter
        Supports basic key-value pairs, lists, and nested dicts
        
        Args:
            yaml_content: YAML string
        
        Returns:
            Dictionary of parsed values
        """
        metadata = {}
        current_key = None
        list_mode = False
        dict_mode = False
        nested_dict = {}
        
        for line in yaml_content.split('\n'):
            line = line.rstrip()
            
            if not line or line.startswith('#'):
                continue
            
            # Handle list items
            if line.startswith('  - ') or line.startswith('- '):
                item = line.lstrip('- ').strip()
                if current_key:
                    if current_key not in metadata:
                        metadata[current_key] = []
                    metadata[current_key].append(item)
                list_mode = True
                continue
            
            # Handle nested dict items (for requirements)
            if line.startswith('  ') and ':' in line and dict_mode:
                sub_key, sub_value = line.strip().split(':', 1)
                nested_dict[sub_key.strip()] = sub_value.strip()
                continue
            
            # Handle key-value pairs
            if ':' in line and not line.startswith(' '):
                list_mode = False
                dict_mode = False
                
                # If we have a pending nested dict, save it
                if nested_dict:
                    metadata[current_key] = nested_dict
                    nested_dict = {}
                
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                current_key = key
                
                # Check if value is empty (nested structure follows)
                if not value:
                    dict_mode = True
                    nested_dict = {}
                    continue
                
                # Parse value type
                if value.startswith('[') and value.endswith(']'):
                    # List in single line: [item1, item2]
                    items = value[1:-1].split(',')
                    metadata[key] = [item.strip() for item in items]
                else:
                    # String value
                    metadata[key] = value
        
        # Save any pending nested dict
        if nested_dict and current_key:
            metadata[current_key] = nested_dict
        
        return metadata
    
    def get_skills_by_category(self, category: str, skills: Optional[List[Skill]] = None) -> List[Skill]:
        """
        Filter skills by category
        
        Args:
            category: Category to filter by (e.g., "policy", "technical")
            skills: List of skills to filter (if None, loads all builtin skills)
        
        Returns:
            List of skills matching the category
        """
        if skills is None:
            skills = self.load_all_builtin_skills()
        
        return [s for s in skills if s.category == category]
    
    def get_skills_by_role(self, role: str, skills: Optional[List[Skill]] = None) -> List[Skill]:
        """
        Filter skills by applicable role
        
        Args:
            role: Role name (e.g., "策论家", "监察官")
            skills: List of skills to filter (if None, loads all builtin skills)
        
        Returns:
            List of skills applicable to the role
        """
        if skills is None:
            skills = self.load_all_builtin_skills()
        
        return [s for s in skills if role in s.applicable_roles]
    
    def format_skill_for_prompt(self, skill: Skill, include_metadata: bool = False) -> str:
        """
        Format a skill for injection into agent prompts
        
        Args:
            skill: Skill object
            include_metadata: Whether to include metadata header
        
        Returns:
            Formatted string for prompt injection
        """
        if include_metadata:
            header = f"""
# {skill.display_name} ({skill.name})
**版本**: {skill.version} | **分类**: {skill.category} | **作者**: {skill.author}
**描述**: {skill.description}

"""
            return header + skill.content
        else:
            return skill.content


# Convenience function for quick skill loading
def load_builtin_skills() -> List[Skill]:
    """Load all builtin skills using default loader"""
    loader = SkillLoader()
    return loader.load_all_builtin_skills()
