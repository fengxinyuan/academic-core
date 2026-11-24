# -*- coding: utf-8 -*-
"""
academic_core 核心统一流水线 (Orchestrator)
解耦串接：格式归一化 -> 视觉/文档提取 -> 长文并发推理与公式哨兵 -> LaTeX 语法自愈 -> 多格式出版交付 -> 专著合订
"""

import os
import glob
import re
import logging
from typing import List, Optional, Dict, Union
from concurrent.futures import ThreadPoolExecutor

from academic_core.converters import convert_to_normalized
from academic_core.vision_ocr import get_vision_engine
from academic_core.llm_reasoning import AcademicLLMEngine
from academic_core.math_enhancer import LatexCleaner, sanitize_and_repair_markdown
from academic_core.exporters import ChromePDFPrinter, HTMLExporter, MarkdownExporter
from academic_core.monograph import MonographBinder
from academic_core.checkpoint import TaskTracker

logger = logging.getLogger("academic_core.pipeline")


class AcademicPipeline:
    def __init__(
        self,
        llm_provider: str = "dashscope",
        llm_model: str = "qwen-plus",
        vision_engine_name: str = "qwen-vl-ocr",
        task: str = "note",
        auto_fix_latex: bool = True,
        checkpoint_file: str = ".academic_checkpoint.json",
        base_url: Optional[str] = None,
        target_lang: str = "zh-CN",
        use_llm: bool = True,
        pdf_mode: str = "vision",
        pdf_dpi: int = 200,
        enhance_image: bool = False,
        max_chunk_chars: int = 5000,
        max_workers: int = 4,
    ):
        self.task = task
        self.auto_fix_latex = auto_fix_latex
        self.target_lang = target_lang
        self.use_llm = use_llm
        self.pdf_mode = "mineru" if vision_engine_name.lower() == "mineru" else pdf_mode
        self.pdf_dpi = pdf_dpi
        self.enhance_image = enhance_image
        self.max_workers = max(1, int(max_workers))

        self.llm = AcademicLLMEngine(
            provider=llm_provider,
            model=llm_model,
            base_url=base_url,
            max_chunk_chars=max_chunk_chars,
            max_workers=max_workers,
        ) if use_llm else None
        self.vision = get_vision_engine(engine_name=vision_engine_name)
        self.pdf_printer = ChromePDFPrinter()
        self.html_exporter = HTMLExporter()
        self.md_exporter = MarkdownExporter()
        self.binder = MonographBinder(printer=self.pdf_printer)
        self.tracker = TaskTracker(checkpoint_file=checkpoint_file)

    def _normalize_export_formats(self, export_formats: Union[str, List[str]]) -> List[str]:
        if isinstance(export_formats, str):
            if export_formats.lower().strip() == "all":
                return ["pdf", "html", "md"]
            return [f.strip().lower() for f in export_formats.split(",") if f.strip()]
        return [f.strip().lower() for f in export_formats if f.strip()]

    def process_one(
        self,
        input_path: str,
        output_dir: str = "dist",
        export_formats: Union[str, List[str]] = "pdf",
        glossary: Optional[dict] = None,
        bilingual: bool = False,
        ensure_md_for_merge: bool = False,
        auto_glossary: bool = False,
        resume: bool = True,
    ) -> Dict[str, str]:
        """
        处理单一输入（支持 .pdf, .one, .docx, .pptx, .epub, .ipynb, .tex, .md, .zip/.tar, 照片或照片目录），
        并支持多格式出版级交付 (PDF, HTML, Markdown)。
        """
        fmts = self._normalize_export_formats(export_formats)
        if ensure_md_for_merge and "md" not in fmts and "markdown" not in fmts:
            fmts.append("md")

        # 1. 独立格式归一化转换
        norm_doc = convert_to_normalized(
            input_path,
            pdf_mode=self.pdf_mode,
            pdf_dpi=self.pdf_dpi,
            enhance_image=self.enhance_image,
        )
        base_name = norm_doc.doc_name
        assets_dir = norm_doc.assets_dir

        # 2. 提取文本流（原生结构/MinerU/纯文本直接透传；扫描件/手写/照片并发视觉 OCR）
        extracted_pages: List[str] = []
        if norm_doc.is_text_only:
            extracted_pages = [p.text or "" for p in norm_doc.pages]
        else:
            total_p = norm_doc.total_pages
            if total_p <= 1:
                if norm_doc.pages and norm_doc.pages[0].image_bytes:
                    p = norm_doc.pages[0]
                    extracted_pages = [self.vision.extract_page_latex(p.image_bytes, 1, 1)]
            else:
                def _extract(p_item):
                    return p_item.page_num, self.vision.extract_page_latex(
                        p_item.image_bytes, p_item.page_num, total_p
                    )

                results: Dict[int, str] = {}
                valid_pages = [p for p in norm_doc.pages if p.image_bytes]
                with ThreadPoolExecutor(max_workers=min(self.max_workers, len(valid_pages))) as executor:
                    for p_num, text in executor.map(_extract, valid_pages):
                        results[p_num] = text
                extracted_pages = [results[i + 1] for i in range(total_p) if (i + 1) in results]

        raw_latex = "\n\n---\n\n".join(p for p in extracted_pages if p.strip())

        # 3. 术语自动预对齐与长文并发翻译
        if auto_glossary and self.use_llm and self.llm is not None:
            from academic_core.llm_reasoning.glossary import GlossaryManager
            glossary = GlossaryManager.generate_glossary(
                self.llm,
                raw_latex,
                target_lang=self.target_lang,
                existing_glossary=glossary,
            )
            try:
                g_path = os.path.join(output_dir, f"{base_name}_glossary.json")
                with open(g_path, "w", encoding="utf-8") as gfp:
                    json.dump(glossary, gfp, ensure_ascii=False, indent=2)
            except Exception:
                pass

        if self.use_llm and self.llm is not None:
            healed_text = self.llm.process_academic_task(
                raw_latex,
                task=self.task,
                doc_name=base_name,
                glossary=glossary,
                bilingual=bilingual,
                target_lang=self.target_lang,
                resume=resume,
            )
        else:
            healed_text = raw_latex

        # 4. 数学公式与排版语法全自动自愈 (LaTeX Enhancer + 结构清洗)
        if self.auto_fix_latex:
            healed_text = sanitize_and_repair_markdown(healed_text)
            healed_text = LatexCleaner.clean(healed_text)

        title_m = re.search(r'^#\s+(.+)$', healed_text, flags=re.MULTILINE)
        doc_title = title_m.group(1).strip() if title_m else base_name

        output_files: Dict[str, str] = {}

        # 5. 多格式出版级交付（透传 assets_dir 保证论文/教材插图零裂图）
        if "md" in fmts or "markdown" in fmts:
            md_dir = os.path.join(output_dir, "md")
            out_md = os.path.join(md_dir, f"{base_name}.md")
            self.md_exporter.export(
                healed_text,
                out_md,
                title=doc_title,
                metadata={"task": self.task, "target_lang": self.target_lang},
                assets_dir=assets_dir,
            )
            output_files["md"] = out_md

        if "html" in fmts:
            html_dir = os.path.join(output_dir, "html")
            out_html = os.path.join(html_dir, f"{base_name}.html")
            self.html_exporter.export(
                healed_text,
                out_html,
                title=doc_title,
                assets_dir=assets_dir,
                embed_images=True,
            )
            output_files["html"] = out_html

        if "pdf" in fmts:
            pdf_dir = os.path.join(output_dir, "pdf")
            out_pdf = os.path.join(pdf_dir, f"{base_name}.pdf")
            self.pdf_printer.print_markdown(
                healed_text,
                out_pdf,
                title=doc_title,
                assets_dir=assets_dir,
            )
            output_files["pdf"] = out_pdf

        primary_out = output_files.get("pdf") or output_files.get("html") or output_files.get("md") or ""
        self.tracker.mark_completed(
            base_name,
            primary_out,
            metadata={"formats": list(output_files.keys()), "md_path": output_files.get("md", "")},
        )

        return output_files

    @staticmethod
    def _strip_frontmatter(md_text: str) -> str:
        """合订本拼接前剥离单章 YAML Frontmatter，避免正文出现杂乱元数据"""
        if md_text.startswith("---"):
            parts = md_text.split("---", 2)
            if len(parts) == 3:
                return parts[2].strip()
        return md_text

    def process_all(
        self,
        input_pattern: str,
        output_dir: str = "dist",
        export_formats: Union[str, List[str]] = "pdf",
        merge_monograph: bool = False,
        monograph_title: str = "学术讲义合订本",
        glossary: Optional[dict] = None,
        bilingual: bool = False,
        resume: bool = True,
        auto_glossary: bool = False,
    ) -> List[Dict[str, str]]:
        """
        批量处理多个输入（支持通配符、单文件或照片目录），支持断点续传与无漏章专著大合订本
        """
        if os.path.exists(input_pattern) and not any(ch in input_pattern for ch in ("*", "?", "[")):
            files = [input_pattern]
        else:
            files = sorted(glob.glob(input_pattern))

        if not files:
            logger.warning(f"未找到匹配的输入路径: {input_pattern}")
            return []

        results: List[Dict[str, str]] = []
        sections: List[Dict[str, str]] = []

        logger.info(f"=== academic_core 启动流水线 (共 {len(files)} 项任务, 交付格式: {export_formats}) ===")
        for i, fpath in enumerate(files):
            fname = os.path.basename(os.path.abspath(fpath))
            base_name = fname if os.path.isdir(fpath) else os.path.splitext(fname)[0]
            default_md_path = os.path.join(output_dir, "md", f"{base_name}.md")

            if resume and self.tracker.is_completed(base_name):
                logger.info(f"[{i + 1}/{len(files)}] 命中已完成检查点，跳过: {fname}")
                if merge_monograph:
                    ck_meta = self.tracker.state.get("completed", {}).get(base_name, {}).get("metadata", {})
                    saved_md = ck_meta.get("md_path") or default_md_path
                    if saved_md and os.path.exists(saved_md):
                        with open(saved_md, "r", encoding="utf-8-sig") as fp:
                            sections.append({"title": base_name, "content": self._strip_frontmatter(fp.read())})
                continue

            logger.info(f"[{i + 1}/{len(files)}] 正在处理: {fname}...")
            try:
                out_dict = self.process_one(
                    fpath,
                    output_dir=output_dir,
                    export_formats=export_formats,
                    glossary=glossary,
                    bilingual=bilingual,
                    ensure_md_for_merge=merge_monograph,
                    auto_glossary=auto_glossary,
                    resume=resume,
                )
                results.append(out_dict)

                if merge_monograph:
                    md_path = out_dict.get("md") or default_md_path
                    if md_path and os.path.exists(md_path):
                        with open(md_path, "r", encoding="utf-8-sig") as fp:
                            sections.append({"title": base_name, "content": self._strip_frontmatter(fp.read())})
            except Exception as e:
                logger.error(f"处理失败 {fname}: {e}")
                self.tracker.mark_failed(base_name, str(e))

        if merge_monograph and sections:
            logger.info(f"正在构建专著大合订本 ({len(sections)} 篇): {monograph_title}...")
            book_pdf = os.path.join(output_dir, f"{monograph_title}.pdf")
            self.binder.bind_to_book(sections, book_pdf, book_title=monograph_title)
            logger.info(f"专著大合订本已生成: {book_pdf}")

        return results
