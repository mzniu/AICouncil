"""角色管理器 - 负责加载和管理所有角色定义"""
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import shutil
import sys
from functools import lru_cache
from dataclasses import dataclass, field

def get_roles_directory() -> Path:
    """获取roles目录路径（优先用户目录，支持打包环境）"""
    # 1. 检查用户目录中的roles（可编辑）
    if sys.platform == 'win32':
        user_data_dir = Path.home() / "AppData" / "Local" / "AICouncil"
    elif sys.platform == 'darwin':
        user_data_dir = Path.home() / "Library" / "Application Support" / "AICouncil"
    else:
        user_data_dir = Path.home() / ".aicouncil"
    
    user_roles_dir = user_data_dir / "roles"
    
    # 2. 获取内置roles目录（只读模板）
    if getattr(sys, 'frozen', False):
        # 打包环境：从exe旁边的_internal目录读取
        builtin_roles = Path(sys._MEIPASS) / "src" / "agents" / "roles"
    else:
        # 开发环境
        builtin_roles = Path(__file__).parent / "roles"
    
    # 3. 如果用户目录不存在，从内置模板复制
    if not user_roles_dir.exists():
        print(f"[RoleManager] 初始化用户roles目录: {user_roles_dir}")
        user_roles_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制所有内置角色配置
        if builtin_roles.exists():
            for item in builtin_roles.glob('*'):
                if item.name != 'backups':  # 跳过备份目录
                    dest = user_roles_dir / item.name
                    if item.is_file():
                        shutil.copy2(item, dest)
            print(f"[RoleManager] 已从内置模板复制 {len(list(user_roles_dir.glob('*.yaml')))} 个角色")
        else:
            print(f"[RoleManager] ⚠️ 警告：未找到内置roles模板目录")
    
    return user_roles_dir

ROLES_DIR = get_roles_directory()

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
    
    # === 角色编辑功能 ===
    
    def get_role_yaml_content(self, role_name: str) -> str:
        """获取角色的原始YAML内容"""
        yaml_file = ROLES_DIR / f"{role_name}.yaml"
        if not yaml_file.exists():
            raise FileNotFoundError(f"角色文件不存在: {yaml_file}")
        return yaml_file.read_text(encoding='utf-8')
    
    def get_role_prompts(self, role_name: str) -> Dict[str, str]:
        """获取角色所有阶段的prompt内容"""
        role = self.get_role(role_name)
        prompts = {}
        for stage_name, stage in role.stages.items():
            prompt_file = ROLES_DIR / stage.prompt_file
            if prompt_file.exists():
                prompts[stage_name] = prompt_file.read_text(encoding='utf-8')
        return prompts
    
    def validate_role_config(self, yaml_content: str) -> tuple[bool, Optional[str]]:
        """验证YAML配置是否合法
        
        Returns:
            (is_valid, error_message)
        """
        try:
            data = yaml.safe_load(yaml_content)
            
            # 检查必需字段
            required_fields = ['name', 'display_name', 'version', 'description', 'stages']
            for field in required_fields:
                if field not in data:
                    return False, f"缺少必需字段: {field}"
            
            # 验证stages格式
            if not isinstance(data['stages'], dict):
                return False, "stages必须是字典格式"
            
            for stage_name, stage_data in data['stages'].items():
                if not isinstance(stage_data, dict):
                    return False, f"阶段 {stage_name} 配置格式错误"
                if 'prompt_file' not in stage_data:
                    return False, f"阶段 {stage_name} 缺少prompt_file字段"
                if 'schema' not in stage_data:
                    return False, f"阶段 {stage_name} 缺少schema字段"
            
            return True, None
            
        except yaml.YAMLError as e:
            return False, f"YAML语法错误: {str(e)}"
        except Exception as e:
            return False, f"验证失败: {str(e)}"
    
    def save_role_config(self, role_name: str, yaml_content: str, prompts: Dict[str, str]) -> tuple[bool, Optional[str]]:
        """保存角色配置
        
        Args:
            role_name: 角色名称
            yaml_content: YAML配置内容
            prompts: {stage_name: prompt_content}
        
        Returns:
            (success, error_message)
        """
        import shutil
        from datetime import datetime
        
        try:
            # 1. 验证配置
            is_valid, error = self.validate_role_config(yaml_content)
            if not is_valid:
                return False, error
            
            # 2. 备份原文件
            yaml_file = ROLES_DIR / f"{role_name}.yaml"
            if yaml_file.exists():
                backup_dir = ROLES_DIR / "backups"
                backup_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = backup_dir / f"{role_name}_{timestamp}.yaml"
                shutil.copy2(yaml_file, backup_file)
            
            # 3. 保存YAML配置
            yaml_file.write_text(yaml_content, encoding='utf-8')
            
            # 4. 保存prompt文件
            parsed_data = yaml.safe_load(yaml_content)
            for stage_name, prompt_content in prompts.items():
                if stage_name in parsed_data['stages']:
                    prompt_file_name = parsed_data['stages'][stage_name]['prompt_file']
                    prompt_file = ROLES_DIR / prompt_file_name
                    
                    # 备份prompt文件
                    if prompt_file.exists():
                        backup_prompt = backup_dir / f"{prompt_file.stem}_{timestamp}{prompt_file.suffix}"
                        shutil.copy2(prompt_file, backup_prompt)
                    
                    prompt_file.write_text(prompt_content, encoding='utf-8')
            
            # 5. 热重载角色
            self.reload_role(role_name)
            
            return True, None
            
        except Exception as e:
            return False, f"保存失败: {str(e)}"
    
    # === 角色设计师功能 ===
    
    def generate_yaml_from_design(self, design: 'RoleDesignOutput') -> str:
        """从RoleDesignOutput生成YAML配置
        
        Args:
            design: 角色设计输出（Pydantic模型）
        
        Returns:
            YAML配置字符串
        """
        yaml_dict = {
            'name': design.role_name,
            'display_name': design.display_name,
            'version': '1.0.0',
            'description': design.role_description,
            'stages': {},
            'default_model': 'deepseek-reasoner',
            'parameters': {
                'max_retries': 2,
                'temperature': 0.7,
                'max_tokens': 3000
            },
            'tags': ['auto_generated'],
            'ui': {}
        }
        
        # 转换stages
        for idx, stage in enumerate(design.stages):
            stage_key = f"stage_{idx + 1}" if len(design.stages) > 1 else "main"
            prompt_filename = f"{design.role_name}_{stage_key}.md"
            
            yaml_dict['stages'][stage_key] = {
                'prompt_file': prompt_filename,
                'schema': stage.output_schema,
                'input_vars': ['issue', 'round']  # 默认变量，可后续调整
            }
        
        return yaml.dump(yaml_dict, allow_unicode=True, sort_keys=False)
    
    def generate_prompt_from_design(self, design: 'RoleDesignOutput', stage: 'RoleStageDefinition') -> str:
        """从阶段定义生成prompt内容
        
        Args:
            design: 角色设计输出
            stage: 具体阶段定义
        
        Returns:
            Prompt模板内容
        """
        # 生成人物原型部分
        personas_section = ""
        if design.recommended_personas:
            personas_section = "\n## 推荐人物原型\n"
            for persona in design.recommended_personas:
                traits_str = "、".join(persona.traits)
                personas_section += f"- **{persona.name}**: {persona.reason}\n  - 关键特质：{traits_str}\n"
        
        # 生成职责清单
        responsibilities_list = "\n".join([f"{i+1}. {resp}" for i, resp in enumerate(stage.responsibilities)])
        
        prompt_template = f"""# {design.display_name} - {stage.stage_name}

## 你的身份
你是{design.display_name}，{design.role_description}
{personas_section}
## 你的职责
在本阶段，你需要完成以下任务：
{responsibilities_list}

## 思维方式
采用**{stage.thinking_style}**进行分析和推理。

## 当前议题
{{{{issue}}}}

## 当前轮次
第{{{{round}}}}轮讨论

## 输出要求
{stage.output_format}

**CRITICAL**: 你的输出必须是严格的JSON，直接对应`{stage.output_schema}` Schema，NO ADDITIONAL TEXT！

---
请开始你的分析和输出。
"""
        return prompt_template
    
    def create_new_role(self, design: 'RoleDesignOutput') -> tuple[bool, Optional[str]]:
        """创建新角色
        
        Args:
            design: 角色设计输出（Pydantic模型）
        
        Returns:
            (success, error_message)
        """
        try:
            # 1. 检查重名
            if self.has_role(design.role_name):
                return False, f"角色 {design.role_name} 已存在，请使用不同的名称"
            
            yaml_file = ROLES_DIR / f"{design.role_name}.yaml"
            if yaml_file.exists():
                return False, f"角色文件 {yaml_file.name} 已存在"
            
            # 2. 生成YAML配置
            yaml_content = self.generate_yaml_from_design(design)
            
            # 3. 保存YAML文件
            yaml_file.write_text(yaml_content, encoding='utf-8')
            
            # 4. 生成并保存prompt文件
            for idx, stage in enumerate(design.stages):
                stage_key = f"stage_{idx + 1}" if len(design.stages) > 1 else "main"
                prompt_filename = f"{design.role_name}_{stage_key}.md"
                prompt_file = ROLES_DIR / prompt_filename
                
                prompt_content = self.generate_prompt_from_design(design, stage)
                prompt_file.write_text(prompt_content, encoding='utf-8')
            
            # 5. 加载新角色到内存
            self.reload_role(design.role_name)
            
            print(f"[RoleManager] ✅ 成功创建角色: {design.display_name}")
            return True, None
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"[RoleManager] ❌ 创建角色失败: {error_detail}")
            return False, f"创建失败: {str(e)}"
    
    def get_roles_directory(self) -> Path:
        """获取roles目录路径（供外部使用）"""
        return ROLES_DIR

