"""
PDF Skill Extractor - 从 PDF 文件提取内容并生成 SKILL.md

使用 pdfplumber 提取 PDF 文本，通过智能分块后调用 LLM（复用 SkillGenerator 的多后端支持）
将文档内容转换为结构化的分析框架技能。

支持三种生成模式：
- single: 整个 PDF 浓缩为 1 个综合 skill
- multi:  按章节拆分为多个独立 skill
- auto:   LLM 自动判断最佳拆分策略
"""
import re
import io
import time
import json
from typing import Dict, List, Optional, Any, BinaryIO
from dataclasses import dataclass, field

from src.utils.logger import setup_logger
from src.skills.skill_generator import SkillGenerator
from src.skills.security_scanner import scan_skill_content

logger = setup_logger(__name__)

# PDF 限制常量
MAX_PDF_SIZE_MB = 20
MAX_PAGES = 50
MAX_CHUNK_CHARS = 12000  # 每个分块最大字符数
CHUNK_OVERLAP = 200  # 分块重叠字符数


@dataclass
class PDFInfo:
    """PDF 文件信息"""
    pages: int = 0
    chars: int = 0
    chunks: int = 0
    title: str = ""
    truncated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'pages': self.pages,
            'chars': self.chars,
            'chunks': self.chunks,
            'title': self.title,
            'truncated': self.truncated
        }


@dataclass
class PDFSkillResult:
    """PDF 技能提取结果"""
    success: bool
    skills: List[Dict[str, Any]] = field(default_factory=list)
    pdf_info: Optional[PDFInfo] = None
    error: Optional[str] = None
    generation_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'skills': self.skills,
            'pdf_info': self.pdf_info.to_dict() if self.pdf_info else None,
            'error': self.error,
            'generation_time': self.generation_time
        }


# ============================================================================
# Prompt 模板
# ============================================================================

ANALYSIS_PROMPT = """你是一个知识提取专家。以下是从 PDF 文档中提取的文本内容摘要。
请分析文档结构，判断应该生成几个独立的 Skill。

## 文档内容摘要（前3000字符）
{text_preview}

## 分析要求
1. 判断文档涵盖的主要知识领域
2. 决定是生成一个综合性 skill 还是多个独立 skill
3. 如果建议多个，列出每个 skill 的范围

## 输出格式（纯 JSON，不要额外文字）
```json
{{
  "recommendation": "single 或 multi",
  "reason": "判断理由",
  "skill_plan": [
    {{
      "title": "建议的 skill 名称",
      "scope": "该 skill 覆盖的内容范围描述",
      "keywords": ["关键词1", "关键词2"]
    }}
  ]
}}
```
直接输出 JSON，不要添加额外解释。"""


PDF_SKILL_PROMPT = """你是一个专业的 Agent Skill 创建者，需要从文档内容中提炼专业知识并生成 AICouncil 元老院系统可用的分析框架 Skill。

## 重要原则
1. **从文档中提炼**：基于文档的实际专业内容创建 skill，不要凭空创造
2. **简洁至上**：只提取 AI 不已经知道的领域专业知识
3. **量化导向**：提供评分矩阵、量化指标、结构化模板
4. **可操作性**：确保每个框架都有具体的分析步骤和检查清单

## 文档内容
{document_text}

## 生成要求
- 技能主题：{topic}
- 技能范围：{scope}
- 分类：{category}
- 适用角色：{applicable_roles}

## 输出格式要求

生成一个完整的 SKILL.md 文件，必须包含以下部分：

### YAML Frontmatter（必须以 --- 开始和结束）
```yaml
---
name: {{skill_name_kebab_case}}
displayName: {{中文显示名称}}
version: 1.0.0
category: {category}
tags: [{{相关标签}}]
author: PDF Import
created: {today_date}
updated: {today_date}
description: {{一句话描述skill的功能和使用场景}}
requirements:
  context: {{使用该skill需要什么输入信息}}
  output: {{skill会产出什么类型的结果}}
applicable_roles: {applicable_roles}
---
```

### Markdown Body（按以下结构）
1. **核心能力**：1-2段描述该skill的专业定位（源自文档内容）
2. **分析框架**：至少3个维度，每个维度包含子项和示例分析结构
3. **评分标准**：量化的评分矩阵
4. **输出模板**：标准的分析报告结构模板
5. **质量标准**：✅ 必须遵守 和 ❌ 禁止事项

## 重要提示
- 直接输出 SKILL.md 的完整内容，以 `---` 开头的 YAML frontmatter 开始
- 不要添加任何额外解释或前言
- name 字段使用小写字母和连字符（kebab-case）
- 内容要充实，确保分析框架有足够深度
- 所有知识点必须来源于提供的文档内容"""


class PDFSkillExtractor:
    """从 PDF 提取内容并生成 Skill"""

    def __init__(self, backend: str = None, model: str = None, timeout: int = 180):
        self.generator = SkillGenerator(
            backend=backend,
            model=model,
            timeout=timeout
        )

    def extract_text(self, pdf_file: BinaryIO) -> tuple[str, PDFInfo]:
        """
        使用 pdfplumber 提取 PDF 全文

        Args:
            pdf_file: PDF 文件对象（支持 BytesIO 或文件句柄）

        Returns:
            (全文文本, PDF信息)
        """
        try:
            import pdfplumber
        except ImportError:
            raise RuntimeError("缺少 pdfplumber 依赖，请运行: pip install pdfplumber")

        info = PDFInfo()
        pages_text = []

        try:
            with pdfplumber.open(pdf_file) as pdf:
                info.pages = len(pdf.pages)

                # 尝试提取 PDF 元数据标题
                if pdf.metadata and pdf.metadata.get('Title'):
                    info.title = pdf.metadata['Title']

                # 限制页数
                max_pages = min(info.pages, MAX_PAGES)
                if max_pages < info.pages:
                    info.truncated = True
                    logger.warning(f"[pdf_extractor] PDF 共 {info.pages} 页，已截断至前 {max_pages} 页")

                for i, page in enumerate(pdf.pages[:max_pages]):
                    text = page.extract_text()
                    if text:
                        pages_text.append(text.strip())

                        # 提取表格（如果有）
                        tables = page.extract_tables()
                        for table in tables:
                            if table:
                                table_text = self._format_table(table)
                                if table_text:
                                    pages_text.append(table_text)

        except Exception as e:
            raise RuntimeError(f"PDF 解析失败: {str(e)}")

        full_text = '\n\n'.join(pages_text)

        # 清理多余空白
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)
        full_text = re.sub(r' {3,}', ' ', full_text)

        info.chars = len(full_text)

        if info.chars < 100:
            raise ValueError("PDF 内容过少（少于100字符），可能是扫描件或加密文件，建议先进行 OCR 处理")

        logger.info(f"[pdf_extractor] 提取完成: {info.pages}页, {info.chars}字符, title='{info.title}'")
        return full_text, info

    def smart_chunk(self, text: str, max_chars: int = MAX_CHUNK_CHARS) -> List[str]:
        """
        智能分块：按标题/段落边界拆分长文本

        优先在标题行（#、##、第X章）处切分，保留上下文重叠。
        """
        if len(text) <= max_chars:
            return [text]

        chunks = []
        # 识别标题行的正则
        heading_pattern = re.compile(
            r'^(?:#{1,4}\s+|第[一二三四五六七八九十百\d]+[章节篇部]|'
            r'Chapter\s+\d+|Part\s+\d+|CHAPTER\s+\d+)',
            re.MULTILINE
        )

        # 找到所有标题位置
        headings = list(heading_pattern.finditer(text))

        if headings:
            # 按标题切分
            split_points = [h.start() for h in headings]
            split_points.append(len(text))

            for i in range(len(split_points) - 1):
                start = split_points[i]
                end = split_points[i + 1]
                segment = text[start:end].strip()

                if not segment:
                    continue

                # 如果段落超长，进一步按段落切分
                if len(segment) > max_chars:
                    sub_chunks = self._split_by_paragraphs(segment, max_chars)
                    chunks.extend(sub_chunks)
                else:
                    # 小段落合并到前一个 chunk
                    if chunks and len(chunks[-1]) + len(segment) + 2 <= max_chars:
                        chunks[-1] += '\n\n' + segment
                    else:
                        chunks.append(segment)
        else:
            # 无标题，按段落切分
            chunks = self._split_by_paragraphs(text, max_chars)

        # 确保没有空块
        chunks = [c.strip() for c in chunks if c.strip()]
        return chunks

    def _split_by_paragraphs(self, text: str, max_chars: int) -> List[str]:
        """按段落边界拆分文本"""
        paragraphs = text.split('\n\n')
        chunks = []
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current) + len(para) + 2 <= max_chars:
                current = current + '\n\n' + para if current else para
            else:
                if current:
                    chunks.append(current)
                # 如果单段落超长，强制切分
                if len(para) > max_chars:
                    for j in range(0, len(para), max_chars - CHUNK_OVERLAP):
                        chunks.append(para[j:j + max_chars])
                    current = ""
                else:
                    current = para

        if current:
            chunks.append(current)

        return chunks

    def _format_table(self, table: list) -> str:
        """将 pdfplumber 表格转为 Markdown 格式"""
        if not table or not table[0]:
            return ""
        try:
            # 表头
            header = [str(cell or '').strip() for cell in table[0]]
            lines = ['| ' + ' | '.join(header) + ' |']
            lines.append('| ' + ' | '.join(['---'] * len(header)) + ' |')
            # 数据行
            for row in table[1:]:
                cells = [str(cell or '').strip() for cell in row]
                # 补齐列数
                while len(cells) < len(header):
                    cells.append('')
                lines.append('| ' + ' | '.join(cells[:len(header)]) + ' |')
            return '\n'.join(lines)
        except Exception:
            return ""

    def analyze_document(self, text: str) -> Dict[str, Any]:
        """
        分析文档结构，决定生成策略（auto 模式用）

        Returns:
            {"recommendation": "single|multi", "skill_plan": [...]}
        """
        preview = text[:3000]
        prompt = ANALYSIS_PROMPT.format(text_preview=preview)

        try:
            raw = self.generator._call_llm(prompt)
            # 提取 JSON
            raw = raw.strip()
            if raw.startswith('```'):
                lines = raw.split('\n')
                raw = '\n'.join(lines[1:])
                if raw.rstrip().endswith('```'):
                    raw = raw.rstrip()[:-3]

            # 尝试提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                result = json.loads(json_match.group())
                logger.info(f"[pdf_extractor] 文档分析结果: recommendation={result.get('recommendation')}, "
                           f"skills={len(result.get('skill_plan', []))}")
                return result
        except Exception as e:
            logger.warning(f"[pdf_extractor] 文档分析失败，回退到 single 模式: {e}")

        # 回退：默认 single
        return {
            "recommendation": "single",
            "reason": "分析失败，使用默认单 skill 模式",
            "skill_plan": [{"title": "综合分析框架", "scope": "文档全部内容", "keywords": []}]
        }

    def generate_skills(
        self,
        pdf_file: BinaryIO,
        mode: str = "auto",
        topic_hint: str = "",
        category: str = "analysis",
        applicable_roles: Optional[List[str]] = None
    ) -> PDFSkillResult:
        """
        从 PDF 文件生成 Skill

        Args:
            pdf_file: PDF 文件对象
            mode: 生成模式 (auto/single/multi)
            topic_hint: 可选的主题提示
            category: 分类
            applicable_roles: 适用角色

        Returns:
            PDFSkillResult
        """
        start_time = time.time()

        if applicable_roles is None:
            applicable_roles = ["策论家", "监察官"]

        try:
            # 1. 提取 PDF 文本
            logger.info(f"[pdf_extractor] 开始处理 PDF, mode={mode}")
            full_text, pdf_info = self.extract_text(pdf_file)

            # 2. 智能分块
            chunks = self.smart_chunk(full_text)
            pdf_info.chunks = len(chunks)
            logger.info(f"[pdf_extractor] 分块完成: {len(chunks)} 个块")

            # 3. 确定生成策略
            if mode == "auto":
                analysis = self.analyze_document(full_text)
                effective_mode = analysis.get("recommendation", "single")
                skill_plan = analysis.get("skill_plan", [])
            elif mode == "multi":
                effective_mode = "multi"
                # 每个 chunk 一个 skill
                skill_plan = [
                    {"title": f"章节 {i+1}", "scope": chunk[:200], "keywords": []}
                    for i, chunk in enumerate(chunks)
                ]
            else:
                effective_mode = "single"
                skill_plan = [{"title": topic_hint or pdf_info.title or "综合分析框架",
                              "scope": "文档全部内容", "keywords": []}]

            logger.info(f"[pdf_extractor] 生成策略: {effective_mode}, 计划生成 {len(skill_plan)} 个 skill")

            # 4. 按计划生成 skills
            from datetime import date
            today_date = date.today().isoformat()
            skills = []

            if effective_mode == "single":
                # 合并所有文本（截断到合理长度）
                combined = '\n\n'.join(chunks)
                if len(combined) > 30000:
                    combined = combined[:30000] + "\n\n... [文档内容已截断] ..."

                plan = skill_plan[0] if skill_plan else {"title": "分析框架", "scope": "全部内容"}
                topic = topic_hint or plan.get("title", "分析框架")

                skill_result = self._generate_single_skill(
                    document_text=combined,
                    topic=topic,
                    scope=plan.get("scope", "文档全部内容"),
                    category=category,
                    applicable_roles=applicable_roles,
                    today_date=today_date
                )
                if skill_result:
                    skills.append(skill_result)

            else:  # multi
                for i, plan in enumerate(skill_plan):
                    # 选择对应的文本块
                    if i < len(chunks):
                        doc_text = chunks[i]
                    else:
                        # 没有对应块，用关键词匹配
                        keywords = plan.get("keywords", [])
                        doc_text = self._find_relevant_text(full_text, keywords)

                    if len(doc_text) > 20000:
                        doc_text = doc_text[:20000] + "\n\n... [内容已截断] ..."

                    topic = plan.get("title", f"技能 {i+1}")
                    if topic_hint:
                        topic = f"{topic_hint} - {topic}"

                    skill_result = self._generate_single_skill(
                        document_text=doc_text,
                        topic=topic,
                        scope=plan.get("scope", ""),
                        category=category,
                        applicable_roles=applicable_roles,
                        today_date=today_date
                    )
                    if skill_result:
                        skills.append(skill_result)

            gen_time = time.time() - start_time

            if not skills:
                return PDFSkillResult(
                    success=False,
                    error="未能成功生成任何技能，请检查 PDF 内容或调整参数后重试",
                    pdf_info=pdf_info,
                    generation_time=gen_time
                )

            logger.info(f"[pdf_extractor] 生成完成: {len(skills)} 个技能, 耗时 {gen_time:.1f}s")

            return PDFSkillResult(
                success=True,
                skills=skills,
                pdf_info=pdf_info,
                generation_time=gen_time
            )

        except ValueError as e:
            return PDFSkillResult(
                success=False,
                error=str(e),
                generation_time=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"[pdf_extractor] 处理异常: {e}", exc_info=True)
            return PDFSkillResult(
                success=False,
                error=f"PDF 处理失败: {str(e)}",
                generation_time=time.time() - start_time
            )

    def _generate_single_skill(
        self,
        document_text: str,
        topic: str,
        scope: str,
        category: str,
        applicable_roles: List[str],
        today_date: str
    ) -> Optional[Dict[str, Any]]:
        """生成单个 skill"""
        try:
            prompt = PDF_SKILL_PROMPT.format(
                document_text=document_text,
                topic=topic,
                scope=scope,
                category=category,
                applicable_roles=json.dumps(applicable_roles, ensure_ascii=False),
                skill_name_kebab_case=self.generator._generate_skill_name(topic),
                today_date=today_date
            )

            logger.info(f"[pdf_extractor] 生成技能: topic='{topic}', prompt_length={len(prompt)}")

            raw_output = self.generator._call_llm(prompt)
            if not raw_output or not raw_output.strip():
                logger.warning(f"[pdf_extractor] LLM 返回空内容, topic='{topic}'")
                return None

            skill_md = self.generator._clean_output(raw_output)

            # 验证格式
            validation_error = self.generator._validate_skill_md(skill_md)
            if validation_error:
                logger.warning(f"[pdf_extractor] 格式校验失败: {validation_error}, topic='{topic}'")
                # 仍然返回，让用户编辑
                return {
                    'skill_md': skill_md,
                    'skill_data': {'name': self.generator._generate_skill_name(topic), 'warning': validation_error},
                    'security_score': None,
                    'topic': topic
                }

            # 解析元数据
            skill_data = self.generator._parse_frontmatter(skill_md)

            # 安全扫描
            scan_result = scan_skill_content(skill_md, strict_mode=False)

            return {
                'skill_md': skill_md,
                'skill_data': skill_data,
                'security_score': scan_result.security_score,
                'topic': topic
            }

        except Exception as e:
            logger.error(f"[pdf_extractor] 生成失败: topic='{topic}', error={e}")
            return None

    def _find_relevant_text(self, full_text: str, keywords: List[str], max_chars: int = 15000) -> str:
        """根据关键词在全文中查找相关段落"""
        if not keywords:
            return full_text[:max_chars]

        paragraphs = full_text.split('\n\n')
        scored = []

        for para in paragraphs:
            if not para.strip():
                continue
            score = sum(1 for kw in keywords if kw.lower() in para.lower())
            scored.append((score, para))

        # 按相关性排序
        scored.sort(key=lambda x: x[0], reverse=True)

        # 收集文本直到达到限制
        result = []
        total_chars = 0
        for score, para in scored:
            if total_chars + len(para) > max_chars:
                break
            result.append(para)
            total_chars += len(para)

        return '\n\n'.join(result)
