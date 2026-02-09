"""
AI Skill Generator - 使用LLM从描述生成高质量SKILL.md
支持参考已有skill作为few-shot示例
"""
import re
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import requests
from requests.exceptions import RequestException

from src.utils.logger import setup_logger
from src.skills.security_scanner import scan_skill_content
from src import config_manager as config

logger = setup_logger(__name__)


@dataclass
class SkillGenerationResult:
    """Skill生成结果"""
    success: bool
    skill_md: Optional[str] = None  # 完整的SKILL.md内容
    skill_data: Optional[Dict[str, Any]] = None  # 解析后的元数据
    error: Optional[str] = None
    security_score: Optional[float] = None
    generation_time: Optional[float] = None  # 生成耗时（秒）

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'skill_md': self.skill_md,
            'skill_data': self.skill_data,
            'error': self.error,
            'security_score': self.security_score,
            'generation_time': self.generation_time
        }


# Meta-prompt：指导LLM生成高质量Skill
SKILL_GENERATION_PROMPT = """你是一个专业的 Agent Skill 创建者，需要为 AICouncil 元老院系统创建分析框架 Skill。

## 设计原则（来自 Anthropic Agent Skills 标准）

1. **简洁至上**：只包含 AI 不已经知道的领域专业知识，避免常识性内容
2. **渐进式披露**：SKILL.md 主体控制在 200-400 行，重点是框架和模板
3. **适当自由度**：给出分析框架但留有灵活应用空间
4. **量化导向**：提供评分矩阵、量化指标、结构化模板
5. **可操作性**：每个框架都配有示例分析结构和检查清单

## 输出格式要求

生成一个完整的 SKILL.md 文件，必须包含以下部分：

### YAML Frontmatter（必须以 --- 开始和结束）
```yaml
---
name: {skill_name_kebab_case}
displayName: {中文显示名称}
version: 1.0.0
category: {category}
tags: [{相关标签}]
author: AICouncil Generator
created: {today_date}
updated: {today_date}
description: {一句话描述skill的功能和使用场景}
requirements:
  context: {使用该skill需要什么输入信息}
  output: {skill会产出什么类型的结果}
applicable_roles: {applicable_roles}
---
```

### Markdown Body（按以下结构）
1. **核心能力**：1-2段描述该skill的专业定位
2. **分析框架**：至少3个维度，每个维度包含：
   - 子项（4-6个分析要素）
   - 示例分析结构（用代码块展示格式）
3. **评分标准**：量化的评分矩阵（1-5分或百分制）
4. **输出模板**：标准的分析报告结构模板
5. **质量标准**：✅ 必须遵守 和 ❌ 禁止事项

## 参考信息

**生成主题**：{topic}
**详细描述**：{description}
**分类**：{category}
**适用角色**：{applicable_roles}

{reference_skills_section}

## 重要提示
- 直接输出 SKILL.md 的完整内容，以 `---` 开头的 YAML frontmatter 开始
- 不要添加任何额外解释或前言
- 确保 YAML frontmatter 格式正确（注意冒号后的空格、列表格式）
- name 字段使用小写字母和连字符（kebab-case）
- 内容至少200行，确保分析框架有足够深度
"""

REFERENCE_SKILL_TEMPLATE = """
### 参考Skill示例：{skill_name}
以下是一个已有的高质量Skill，请参考其结构和风格：

```markdown
{skill_content_preview}
```
"""


class SkillGenerator:
    """AI驱动的Skill生成器"""

    def __init__(self, backend: str = None, model: str = None, timeout: int = 120):
        """
        初始化生成器

        Args:
            backend: 模型后端 (deepseek/openai/aliyun/openrouter)
            model: 模型名称，None则使用默认
            timeout: API超时时间
        """
        self.backend = backend or getattr(config, 'DEFAULT_BACKEND', 'deepseek')
        self.model = model
        self.timeout = timeout

    def generate(
        self,
        topic: str,
        description: str,
        category: str = "analysis",
        applicable_roles: Optional[List[str]] = None,
        reference_skills: Optional[List[Dict[str, str]]] = None,
        today_date: Optional[str] = None
    ) -> SkillGenerationResult:
        """
        从描述生成完整的 SKILL.md

        Args:
            topic: 主题（如"供应链风险评估"）
            description: 详细需求描述
            category: 分类
            applicable_roles: 适用角色列表
            reference_skills: 参考skill列表 [{"name": "xxx", "content": "..."}]
            today_date: 日期，默认当天

        Returns:
            SkillGenerationResult
        """
        start_time = time.time()

        try:
            if not topic or not topic.strip():
                return SkillGenerationResult(success=False, error="主题不能为空")
            if not description or not description.strip():
                return SkillGenerationResult(success=False, error="描述不能为空")

            if applicable_roles is None:
                applicable_roles = ["策论家", "监察官"]
            if today_date is None:
                from datetime import date
                today_date = date.today().isoformat()

            # 构建参考skill部分
            reference_section = ""
            if reference_skills:
                parts = []
                for ref in reference_skills[:2]:  # 最多2个参考
                    preview = ref.get('content', '')[:2000]  # 截取前2000字符
                    parts.append(REFERENCE_SKILL_TEMPLATE.format(
                        skill_name=ref.get('name', 'unknown'),
                        skill_content_preview=preview
                    ))
                reference_section = "\n".join(parts)

            # 生成 skill name (kebab-case)
            skill_name = self._generate_skill_name(topic)

            # 构建prompt
            prompt = SKILL_GENERATION_PROMPT.format(
                topic=topic,
                description=description,
                category=category,
                applicable_roles=json.dumps(applicable_roles, ensure_ascii=False),
                reference_skills_section=reference_section or "（无参考skill，请自行设计最佳结构）",
                skill_name_kebab_case=skill_name,
                today_date=today_date
            )

            logger.info(f"[skill_generator] 开始生成Skill: topic='{topic}', backend={self.backend}, prompt_length={len(prompt)}")

            # 调用LLM
            raw_output = self._call_llm(prompt)
            if not raw_output or not raw_output.strip():
                return SkillGenerationResult(
                    success=False,
                    error="LLM返回空内容",
                    generation_time=time.time() - start_time
                )

            # 清理输出（去掉可能的代码围栏）
            skill_md = self._clean_output(raw_output)

            # 验证格式
            validation_error = self._validate_skill_md(skill_md)
            if validation_error:
                return SkillGenerationResult(
                    success=False,
                    error=f"生成的Skill格式不合规: {validation_error}",
                    skill_md=skill_md,  # 仍然返回内容供调试
                    generation_time=time.time() - start_time
                )

            # 解析元数据
            skill_data = self._parse_frontmatter(skill_md)

            # 安全扫描
            scan_result = scan_skill_content(skill_md, strict_mode=False)

            gen_time = time.time() - start_time
            logger.info(f"[skill_generator] 生成完成: name='{skill_data.get('name', 'unknown')}', "
                       f"lines={len(skill_md.splitlines())}, security_score={scan_result.security_score}, "
                       f"time={gen_time:.1f}s")

            return SkillGenerationResult(
                success=True,
                skill_md=skill_md,
                skill_data=skill_data,
                security_score=scan_result.security_score,
                generation_time=gen_time
            )

        except Exception as e:
            logger.error(f"[skill_generator] 生成异常: {e}", exc_info=True)
            return SkillGenerationResult(
                success=False,
                error=f"生成过程异常: {str(e)}",
                generation_time=time.time() - start_time
            )

    def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""
        backend = self.backend.lower()

        if backend == 'deepseek':
            return self._call_deepseek(prompt)
        elif backend == 'openai':
            return self._call_openai_compatible(
                prompt,
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_BASE_URL,
                model=self.model or getattr(config, 'OPENAI_MODEL', 'gpt-4o')
            )
        elif backend == 'aliyun':
            return self._call_openai_compatible(
                prompt,
                api_key=config.ALIYUN_API_KEY,
                base_url=config.ALIYUN_BASE_URL,
                model=self.model or getattr(config, 'ALIYUN_MODEL', 'qwen-plus')
            )
        elif backend == 'openrouter':
            return self._call_openai_compatible(
                prompt,
                api_key=config.OPENROUTER_API_KEY,
                base_url=getattr(config, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
                model=self.model or getattr(config, 'OPENROUTER_MODEL', 'anthropic/claude-3.5-sonnet')
            )
        else:
            raise ValueError(f"不支持的后端: {backend}")

    def _call_deepseek(self, prompt: str) -> str:
        """调用DeepSeek API"""
        url = f"{config.DEEPSEEK_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        # 生成skill用chat模型而非reasoner，速度更快
        model = self.model or getattr(config, 'DEEPSEEK_CHAT_MODEL', None) or 'deepseek-chat'
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 8192
        }

        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except RequestException as e:
                logger.warning(f"DeepSeek attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))

        raise RuntimeError("DeepSeek API 调用失败（3次重试）")

    def _call_openai_compatible(self, prompt: str, api_key: str, base_url: str, model: str) -> str:
        """调用OpenAI兼容API"""
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 8192
        }

        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except RequestException as e:
                logger.warning(f"API attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))

        raise RuntimeError(f"API 调用失败（3次重试），base_url={base_url}")

    def _generate_skill_name(self, topic: str) -> str:
        """从主题生成kebab-case的skill名称"""
        # 简单映射：用拼音或英文
        # 优先尝试从topic中提取英文部分
        english_parts = re.findall(r'[a-zA-Z]+', topic)
        if english_parts:
            name = '-'.join(w.lower() for w in english_parts)
        else:
            # 中文主题：生成简短hash + 前缀
            import hashlib
            h = hashlib.md5(topic.encode()).hexdigest()[:6]
            name = f"custom-skill-{h}"

        # 确保合规
        name = re.sub(r'[^a-z0-9-]', '-', name.lower())
        name = re.sub(r'-+', '-', name).strip('-')
        return name[:64]

    def _clean_output(self, raw: str) -> str:
        """清理LLM输出"""
        text = raw.strip()
        # 移除markdown代码围栏
        if text.startswith('```'):
            lines = text.split('\n')
            # 去掉第一行（```markdown 或 ```yaml 等）
            lines = lines[1:]
            # 去掉最后一行如果是 ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            text = '\n'.join(lines)

        # 确保以 --- 开头
        if not text.startswith('---'):
            # 尝试找到 --- 的位置
            idx = text.find('---')
            if idx >= 0:
                text = text[idx:]
            else:
                logger.warning("[skill_generator] 输出不包含YAML frontmatter")

        return text.strip()

    def _validate_skill_md(self, content: str) -> Optional[str]:
        """验证SKILL.md格式，返回错误信息或None"""
        if not content.startswith('---'):
            return "缺少YAML frontmatter（应以 --- 开头）"

        # 检查frontmatter结束标记
        second_marker = content.find('---', 3)
        if second_marker < 0:
            return "YAML frontmatter未正确关闭（缺少结束 ---）"

        frontmatter = content[3:second_marker].strip()
        if not frontmatter:
            return "YAML frontmatter为空"

        # 检查必须字段
        if 'name:' not in frontmatter:
            return "YAML frontmatter缺少 name 字段"
        if 'description:' not in frontmatter:
            return "YAML frontmatter缺少 description 字段"

        # 检查body
        body = content[second_marker + 3:].strip()
        if len(body) < 100:
            return f"Skill内容过短（body仅{len(body)}个字符，至少需要100个）"

        return None

    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """解析YAML frontmatter为字典"""
        result = {}
        try:
            second_marker = content.find('---', 3)
            if second_marker < 0:
                return result
            frontmatter = content[3:second_marker].strip()
            body = content[second_marker + 3:].strip()

            # 简单YAML解析（避免外部依赖）
            for line in frontmatter.split('\n'):
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    key, _, value = line.partition(':')
                    key = key.strip()
                    value = value.strip()

                    # 处理列表
                    if value.startswith('[') and value.endswith(']'):
                        items = value[1:-1].split(',')
                        result[key] = [item.strip().strip('"\'') for item in items if item.strip()]
                    elif value.startswith('{'):
                        # 简单dict不解析，原样保留
                        result[key] = value
                    else:
                        result[key] = value.strip('"\'')

            result['content'] = body

        except Exception as e:
            logger.warning(f"[skill_generator] Frontmatter解析异常: {e}")

        return result
