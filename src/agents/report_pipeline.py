"""
多阶段报告生成管线 (Report Pipeline)

将报告生成拆分为三个阶段：
  Stage 1: Blueprint  — 报告架构师设计报告蓝图（JSON）
  Stage 2: Sections   — 逐章节并行生成 HTML 片段
  Stage 3: Assembly   — 组装为完整 HTML 页面

失败时自动回退到单次生成模式。
"""

import json
import uuid
import traceback
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from src.agents import schemas
from src.agents.langchain_agents import (
    send_web_event,
    stream_agent_output,
    clean_json_string,
)
from src.utils.logger import logger


class ReportPipeline:
    """多阶段报告生成管线"""

    def __init__(
        self,
        model_config: Dict[str, Any],
        tenant_id: Optional[int] = None,
        max_parallel_sections: int = 3,
    ):
        self.model_config = model_config
        self.tenant_id = tenant_id
        self.max_parallel_sections = max_parallel_sections

    # ------------------------------------------------------------------
    # 公开入口
    # ------------------------------------------------------------------
    def generate(
        self,
        issue: str,
        final_data: Dict[str, Any],
        search_refs_text: str,
        image_pool_text: str,
        image_pool: list,
    ) -> str:
        """执行完整的三阶段管线。任意阶段失败则回退到单次生成模式。

        Returns:
            report_html (str): 生成的完整 HTML 报告
        """
        try:
            send_web_event("system_status", content="📐 [管线模式] Stage 1: 正在设计报告蓝图...")
            blueprint = self._stage1_blueprint(issue, final_data, search_refs_text)
            if blueprint is None:
                raise RuntimeError("Stage 1 蓝图生成失败")

            send_web_event("system_status", content="🧰 [管线模式] 正在准备设计系统与数据分片...")
            design_system = self._build_design_system(blueprint)
            section_data_map = self._build_section_data(blueprint, final_data)

            send_web_event("system_status", content=f"✍️ [管线模式] Stage 2: 正在并行生成 {len(blueprint.sections)} 个章节...")
            sections_html = self._stage2_sections(
                issue, blueprint, section_data_map, design_system, search_refs_text
            )
            if not sections_html:
                raise RuntimeError("Stage 2 所有章节生成失败")

            send_web_event("system_status", content="🏗️ [管线模式] Stage 3: 正在组装完整报告...")
            report_html = self._stage3_assembly(
                blueprint, sections_html, search_refs_text, image_pool_text
            )
            if not report_html:
                raise RuntimeError("Stage 3 组装失败")

            logger.info(f"[pipeline] ✅ 三阶段管线完成，HTML 长度: {len(report_html)}")
            return report_html

        except Exception as e:
            logger.warning(f"[pipeline] 管线模式失败，回退到单次生成: {e}")
            logger.debug(traceback.format_exc())
            send_web_event("system_status", content="⚠️ 管线模式失败，回退到单次生成模式...")
            return self._fallback_single_pass(issue, final_data, search_refs_text, image_pool_text)

    # ------------------------------------------------------------------
    # Stage 1: Blueprint
    # ------------------------------------------------------------------
    def _stage1_blueprint(
        self, issue: str, final_data: Dict[str, Any], search_refs_text: str
    ) -> Optional[schemas.ReportBlueprint]:
        """生成报告蓝图（JSON）"""
        from src.agents.langchain_agents import make_reporter_blueprint_chain

        chain = make_reporter_blueprint_chain(self.model_config, tenant_id=self.tenant_id)
        max_retries = 2

        for attempt in range(max_retries):
            try:
                raw_output, _ = stream_agent_output(
                    chain,
                    {
                        "issue": issue,
                        "final_data": json.dumps(final_data, ensure_ascii=False),
                        "search_references": search_refs_text,
                    },
                    "报告架构师",
                    "Reporter",
                    event_type="agent_action",
                )

                cleaned = clean_json_string(raw_output)
                if not cleaned:
                    logger.warning(f"[pipeline] Stage 1 尝试 {attempt + 1}: clean_json_string 返回空")
                    continue

                blueprint = schemas.ReportBlueprint.model_validate_json(cleaned)
                logger.info(
                    f"[pipeline] Stage 1 完成: {len(blueprint.sections)} 个章节, "
                    f"风格={blueprint.overall_style}"
                )
                send_web_event(
                    "agent_action",
                    agent_name="报告架构师",
                    role_type="Reporter",
                    content=f"\n\n### 📐 蓝图概览\n\n"
                    f"**标题**: {blueprint.report_title}\n"
                    f"**风格**: {blueprint.overall_style}\n"
                    f"**章节**: {', '.join(s.title for s in blueprint.sections)}\n",
                )
                return blueprint

            except Exception as e:
                logger.warning(f"[pipeline] Stage 1 尝试 {attempt + 1} 失败: {e}")

        return None

    # ------------------------------------------------------------------
    # Tool Layer: 数据分片 & 设计系统准备
    # ------------------------------------------------------------------
    def _build_design_system(self, blueprint: schemas.ReportBlueprint) -> str:
        """根据蓝图构建 CSS 变量和设计系统描述"""
        colors = blueprint.color_scheme or {"primary": "#2563eb", "accent": "#f59e0b"}
        font = blueprint.font_suggestion or "Inter, 'Noto Sans SC', sans-serif"

        css_vars = "\n".join(f"  --{k}: {v};" for k, v in colors.items())
        design = (
            f"## 设计系统\n\n"
            f"**整体风格**: {blueprint.overall_style}\n"
            f"**字体**: {font}\n"
            f"**CSS 变量**:\n```css\n:root {{\n{css_vars}\n}}\n```\n\n"
            f"请在生成 HTML 时使用以上 CSS 变量（var(--primary) 等），"
            f"确保与其它章节视觉一致。\n"
        )
        return design

    def _build_section_data(
        self, blueprint: schemas.ReportBlueprint, final_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """为每个章节提取相关数据切片"""
        full_json = json.dumps(final_data, ensure_ascii=False)
        section_data_map: Dict[str, str] = {}

        for section in blueprint.sections:
            # 尝试按 data_sources 路径提取；如果路径解析失败则给该章节完整数据
            extracted_parts = []
            for src_path in section.data_sources:
                val = self._resolve_data_path(final_data, src_path)
                if val is not None:
                    extracted_parts.append(
                        f"### {src_path}\n{json.dumps(val, ensure_ascii=False, indent=2)}"
                    )

            if extracted_parts:
                section_data_map[section.section_id] = "\n\n".join(extracted_parts)
            else:
                # 回退：给完整数据但限长
                max_len = 12000
                section_data_map[section.section_id] = (
                    full_json[:max_len] + ("..." if len(full_json) > max_len else "")
                )

        return section_data_map

    @staticmethod
    def _resolve_data_path(data: Any, path: str) -> Any:
        """按 '.' 分隔路径解析嵌套字典。如 'decomposition.key_questions'"""
        parts = path.split(".")
        current = data
        for p in parts:
            if isinstance(current, dict) and p in current:
                current = current[p]
            else:
                return None
        return current

    def _extract_refs_subset(self, search_refs_text: str, indices: Optional[List[int]]) -> str:
        """根据章节蓝图中 relevant_ref_indices 提取对应的搜索引用子集"""
        if not indices:
            return search_refs_text  # 无指定则全给

        lines = search_refs_text.split("\n")
        # 搜索结果通常以 "## N." 格式分段
        ref_blocks: List[str] = []
        current_block: List[str] = []
        current_idx = -1

        for line in lines:
            # 检测是否是新引用块的起始
            stripped = line.strip()
            if stripped.startswith("## ") or stripped.startswith("### "):
                # 如果有未保存的块，先保存
                if current_block and current_idx in indices:
                    ref_blocks.append("\n".join(current_block))
                current_block = [line]
                # 尝试提取序号
                import re
                m = re.match(r'##\s*#?\s*(\d+)', stripped)
                if m:
                    current_idx = int(m.group(1))
                else:
                    current_idx = -1
            else:
                current_block.append(line)

        # 别忘了最后一个块
        if current_block and current_idx in indices:
            ref_blocks.append("\n".join(current_block))

        if ref_blocks:
            return "\n\n".join(ref_blocks)

        # 如果索引匹配失败，给前5条
        return "\n".join(lines[:200]) if len(lines) > 200 else search_refs_text

    # ------------------------------------------------------------------
    # Stage 2: Sections (并行)
    # ------------------------------------------------------------------
    def _stage2_sections(
        self,
        issue: str,
        blueprint: schemas.ReportBlueprint,
        section_data_map: Dict[str, str],
        design_system: str,
        search_refs_text: str,
    ) -> Dict[str, str]:
        """并行生成所有章节 HTML 片段"""
        from src.agents.langchain_agents import make_reporter_section_chain

        results: Dict[str, str] = {}
        sections = blueprint.sections

        def _gen_one(sec: schemas.SectionBlueprint) -> tuple:
            """生成单个章节"""
            try:
                chain = make_reporter_section_chain(self.model_config, tenant_id=self.tenant_id)
                refs_subset = self._extract_refs_subset(
                    search_refs_text, sec.relevant_ref_indices
                )
                sec_data = section_data_map.get(sec.section_id, "")

                section_blueprint_json = json.dumps(
                    sec.model_dump(), ensure_ascii=False, indent=2
                )

                html_fragment, _ = stream_agent_output(
                    chain,
                    {
                        "issue": issue,
                        "section_blueprint": section_blueprint_json,
                        "section_data": sec_data,
                        "design_system": design_system,
                        "search_refs_subset": refs_subset,
                    },
                    f"章节撰写-{sec.title}",
                    "Reporter",
                    event_type="agent_action",
                )

                # 清理可能的 markdown 代码块包裹
                html_fragment = html_fragment.strip()
                if html_fragment.startswith("```html"):
                    html_fragment = html_fragment[7:]
                elif html_fragment.startswith("```"):
                    html_fragment = html_fragment[3:]
                if html_fragment.endswith("```"):
                    html_fragment = html_fragment[:-3]
                html_fragment = html_fragment.strip()

                logger.info(
                    f"[pipeline] 章节 '{sec.title}' 生成完成，长度: {len(html_fragment)}"
                )
                return (sec.section_id, html_fragment)

            except Exception as e:
                logger.warning(f"[pipeline] 章节 '{sec.title}' 生成失败: {e}")
                return (sec.section_id, None)

        # 并行执行
        with ThreadPoolExecutor(max_workers=self.max_parallel_sections) as executor:
            futures = {executor.submit(_gen_one, sec): sec for sec in sections}
            for future in as_completed(futures):
                sec = futures[future]
                try:
                    section_id, html = future.result()
                    if html:
                        results[section_id] = html
                    else:
                        logger.warning(f"[pipeline] 章节 '{sec.title}' 返回空内容")
                except Exception as e:
                    logger.warning(f"[pipeline] 章节 '{sec.title}' 执行异常: {e}")

        logger.info(
            f"[pipeline] Stage 2 完成: {len(results)}/{len(sections)} 个章节成功"
        )

        # 至少要有一半章节成功才继续
        if len(results) < len(sections) / 2:
            logger.warning("[pipeline] 成功章节不足一半，放弃管线模式")
            return {}

        return results

    # ------------------------------------------------------------------
    # Stage 3: Assembly
    # ------------------------------------------------------------------
    def _stage3_assembly(
        self,
        blueprint: schemas.ReportBlueprint,
        sections_html: Dict[str, str],
        search_refs_text: str,
        image_pool_text: str,
    ) -> Optional[str]:
        """组装完整 HTML 页面"""
        from src.agents.langchain_agents import make_reporter_assembly_chain

        chain = make_reporter_assembly_chain(self.model_config, tenant_id=self.tenant_id)

        # 按蓝图顺序拼接章节 HTML
        ordered_sections = []
        for sec in blueprint.sections:
            if sec.section_id in sections_html:
                ordered_sections.append(
                    f"<!-- === SECTION: {sec.section_id} - {sec.title} === -->\n"
                    f"{sections_html[sec.section_id]}"
                )
            else:
                # 缺失章节：插入占位
                ordered_sections.append(
                    f'<div class="section" data-section-id="{sec.section_id}">\n'
                    f"  <h2>{sec.title}</h2>\n"
                    f"  <p><em>（此章节生成失败，请参考其他章节内容）</em></p>\n"
                    f"</div>"
                )

        all_sections_html = "\n\n".join(ordered_sections)
        blueprint_json = json.dumps(blueprint.model_dump(), ensure_ascii=False, indent=2)

        max_retries = 2
        for attempt in range(max_retries):
            try:
                report_html, _ = stream_agent_output(
                    chain,
                    {
                        "blueprint_json": blueprint_json,
                        "all_sections_html": all_sections_html,
                        "reference_list": search_refs_text,
                        "image_pool": image_pool_text,
                    },
                    "报告组装",
                    "Reporter",
                    event_type="final_report",
                )

                report_html = report_html.strip()
                if report_html.startswith("```html"):
                    report_html = report_html[7:]
                elif report_html.startswith("```"):
                    report_html = report_html[3:]
                if report_html.endswith("```"):
                    report_html = report_html[:-3]
                report_html = report_html.strip()

                if "<html" in report_html.lower() and "</html>" in report_html.lower():
                    logger.info(f"[pipeline] Stage 3 组装完成，HTML 长度: {len(report_html)}")
                    return report_html
                else:
                    logger.warning(f"[pipeline] Stage 3 尝试 {attempt + 1}: 输出不包含完整 HTML 结构")

            except Exception as e:
                logger.warning(f"[pipeline] Stage 3 尝试 {attempt + 1} 失败: {e}")

        return None

    # ------------------------------------------------------------------
    # Fallback: 单次生成
    # ------------------------------------------------------------------
    def _fallback_single_pass(
        self,
        issue: str,
        final_data: Dict[str, Any],
        search_refs_text: str,
        image_pool_text: str,
    ) -> str:
        """回退到单次生成模式（原始逻辑）"""
        from src.agents.langchain_agents import make_reporter_chain

        logger.info("[pipeline] 启用单次生成回退模式")
        chain = make_reporter_chain(self.model_config, tenant_id=self.tenant_id)

        max_retries = 2
        for attempt in range(max_retries):
            try:
                _issue = final_data.get("issue", "") if isinstance(final_data, dict) else ""
                send_web_event(
                    "system_status",
                    message="📝 正在生成报告（单次模式）...",
                    chunk_id=str(uuid.uuid4())
                )
                report_html, _ = stream_agent_output(
                    chain,
                    {
                        "issue": _issue or issue,
                        "final_data": json.dumps(final_data, ensure_ascii=False),
                        "search_references": search_refs_text,
                        "image_pool": image_pool_text,
                    },
                    "记录员",
                    "reporter",
                    event_type="agent_action",
                )

                report_html = report_html.strip()
                if report_html.startswith("```html"):
                    report_html = report_html[7:]
                elif report_html.startswith("```"):
                    report_html = report_html[3:]
                if report_html.endswith("```"):
                    report_html = report_html[:-3]

                return report_html.strip()

            except Exception as e:
                logger.warning(f"[pipeline] 回退模式尝试 {attempt + 1} 失败: {e}")

        return "报告生成失败"
