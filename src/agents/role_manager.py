"""角色管理器 - 负责加载和管理所有角色定义"""
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from functools import lru_cache
from dataclasses import dataclass, field

ROLES_DIR = Path(__file__).parent / "roles"

@dataclass
class RoleStage:
    """角色的单个阶段配置"""
    prompt_file: str
    schema: str
    input_vars: List[str]

@dataclass
class RoleConfig:
    """角色配置数据类"""
    name: str
    display_name: str
    version: str
    description: str
    stages: Dict[str, RoleStage]
    default_model: Dict = field(default_factory=dict)
    parameters: Dict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    ui: Dict = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> 'RoleConfig':
        """从YAML文件加载"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 转换stages为RoleStage对象
        stages = {
            name: RoleStage(**stage_data) 
            for name, stage_data in data.get('stages', {}).items()
        }
        
        return cls(
            name=data['name'],
            display_name=data['display_name'],
            version=data['version'],
            description=data['description'],
            stages=stages,
            default_model=data.get('default_model', {}),
            parameters=data.get('parameters', {}),
            tags=data.get('tags', []),
            ui=data.get('ui', {})
        )

class RoleManager:
    """角色管理器 - 单例模式"""
    _instance: Optional['RoleManager'] = None
    _roles: Dict[str, RoleConfig] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._roles = {}
            cls._instance._load_all_roles()
        return cls._instance
    
    def _load_all_roles(self):
        """扫描roles目录，加载所有YAML定义的角色"""
        if not ROLES_DIR.exists():
            ROLES_DIR.mkdir(parents=True, exist_ok=True)
            return
        
        for yaml_file in ROLES_DIR.glob("*.yaml"):
            try:
                role_config = RoleConfig.from_yaml(yaml_file)
                self._roles[role_config.name] = role_config
                print(f"[RoleManager] 加载角色: {role_config.display_name} v{role_config.version}")
            except Exception as e:
                print(f"[RoleManager] 加载失败 {yaml_file.name}: {e}")
    
    def get_role(self, name: str) -> RoleConfig:
        """获取角色配置"""
        if name not in self._roles:
            raise ValueError(f"角色未找到: {name}")
        return self._roles[name]
    
    def has_role(self, name: str) -> bool:
        """检查角色是否存在"""
        return name in self._roles
    
    def list_roles(self, tag: Optional[str] = None) -> List[RoleConfig]:
        """列出所有角色（可按标签过滤）"""
        roles = list(self._roles.values())
        if tag:
            roles = [r for r in roles if tag in r.tags]
        return roles
    
    @lru_cache(maxsize=128)
    def load_prompt(self, role_name: str, stage: str) -> str:
        """加载Prompt文件（带缓存）"""
        role = self.get_role(role_name)
        if stage not in role.stages:
            raise ValueError(f"角色 {role_name} 没有阶段: {stage}")
        
        prompt_file = ROLES_DIR / role.stages[stage].prompt_file
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt文件不存在: {prompt_file}")
        
        return prompt_file.read_text(encoding='utf-8')
    
    def get_schema_class(self, role_name: str, stage: str):
        """获取Schema类（从schemas.py动态导入）"""
        from src.agents import schemas
        
        role = self.get_role(role_name)
        schema_name = role.stages[stage].schema
        
        # 如果schema为None，直接返回None（例如Reporter角色）
        if schema_name is None:
            return None
        
        if not hasattr(schemas, schema_name):
            raise AttributeError(f"Schema不存在: {schema_name}")
        
        return getattr(schemas, schema_name)
    
    def reload_role(self, role_name: str):
        """热加载单个角色（清除缓存）"""
        yaml_file = ROLES_DIR / f"{role_name}.yaml"
        if not yaml_file.exists():
            raise FileNotFoundError(f"角色文件不存在: {yaml_file}")
        
        role_config = RoleConfig.from_yaml(yaml_file)
        self._roles[role_name] = role_config
        self.load_prompt.cache_clear()
        print(f"[RoleManager] 重新加载角色: {role_config.display_name}")
    
    def clear_cache(self):
        """清除Prompt缓存"""
        self.load_prompt.cache_clear()
