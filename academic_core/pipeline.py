# -*- coding: utf-8 -*-
"""
academic_core 核心统一流水线 (Orchestrator)
解耦串接：格式归一化 -> 视觉/文本提取 -> 学术大模型推理 -> LaTeX 公式自愈 -> 多格式出版交付 -> 专著合订
"""

import os
import glob
import re
from typing import List, Optional, Dict, Union
from academic_core.converters import convert_to_normalized
from academic_core.vision_ocr import get_vision_engine
from academic_core.llm_reasoning import AcademicLLMEngine
from academic_core.math_enhancer import LatexCleaner
from academic_core.exporters import ChromePDFPrinter, HTMLExporter, MarkdownExporter
from academic_core.monograph import MonographBinder
from academic_core.checkpoint import TaskTracker

class AcademicPipeline:
    def __init__(
        self,
        llm_provider: str = "dashscope",
        llm_model: str = "qwen-plus",
        vision_engine_name: str = "qwen-vl-ocr",
        task: str = "note",
        auto_fix_latex: bool = True,
        checkpoint_file: str = ".academic_checkpoint.json"
    ):
        self.task = task
        self.auto_fix_latex = auto_fix_latex
        self.llm = AcademicLLMEngine(provider=llm_provider, model=llm_model)
        self.vision = get_vision_engine(engine_name=vision_engine_name)
        self.pdf_printer = ChromePDFPrinter()
        self.html_exporter = HTMLExporter()
        self.md_exporter = MarkdownExporter()
        self.binder = MonographBinder(printer=self.pdf_printer)
        self.tracker = TaskTracker(checkpoint_file=checkpoint_file)

    def process_one(
        self,
        input_path: str,
        output_dir: str = "dist",
        export_formats: Union[str, List[str]] = "pdf",
        glossary: Optional[dict] = None,
        bilingual: bool = False
    ) -> Dict[str, str]:
        """
        处理单一输入（支持 .zip, .tar, .one, .docx, .pptx, .pdf, .md, .tex, 图片包等任意源），
        并支持多格式出版级交付 (PDF, HTML, Markdown)。
        """
        if isinstance(export_formats, str):
            if export_formats.lower() == "all":
                export_formats = ["pdf", "html", "md"]
            else:
                export_formats = [f.strip() for f in export_formats.split(",")]

        # 1. 独立格式归一化转换
        norm_doc = convert_to_normalized(input_path)
        base_name = norm_doc.doc_name

        # 2. 提取文本流（纯文本/原生数字 PDF 直接透传，扫描件/图片走视觉 OCR）
        extracted_pages = []
        if norm_doc.is_text_only:
            extracted_pages = [p.text or "" for p in norm_doc.pages]
        else:
            total_p = norm_doc.total_pages
            if total_p <= 1:
                if norm_doc.pages and norm_doc.pages[0].image_bytes:
                    p = norm_doc.pages[0]
                    extracted_pages = [self.vision.extract_page_latex(p.image_bytes, 1, 1)]
            else:
                from concurrent.futures import ThreadPoolExecutor
                def _extract(p_item):
                    return p_item.page_num, self.vision.extract_page_latex(p_item.image_bytes, p_item.page_num, total_p)

                results = {}
                with ThreadPoolExecutor(max_workers=min(4, total_p)) as executor:
                    for p_num, text in executor.map(_extract, [p for p in norm_doc.pages if p.image_bytes]):
                        results[p_num] = text

                extracted_pages = [results[i + 1] for i in range(total_p) if (i + 1) in results]

        raw_latex = "\n\n---\n\n".join(extracted_pages)

        # 3. 学术语义重构与场景任务自愈 (支持术语表约束与双语对照)
        healed_text = self.llm.process_academic_task(
            raw_latex,
            task=self.task,
            doc_name=base_name,
            glossary=glossary,
            bilingual=bilingual
        )

        # 4. 数学公式与排版语法全自动自愈 (LaTeX Enhancer)
        if self.auto_fix_latex:
            healed_text = LatexCleaner.clean(healed_text)

        title_m = re.search(r'^#\s+(.+)$', healed_text, flags=re.MULTILINE)
        doc_title = title_m.group(1).strip() if title_m else base_name

        output_files = {}

        # 5. 多格式出版交付
        # 5.1 Markdown
        if "md" in export_formats or "markdown" in export_formats:
            md_dir = os.path.join(output_dir, "md")
            out_md = os.path.join(md_dir, f"{base_name}.md")
            self.md_exporter.export(healed_text, out_md, title=doc_title, metadata={"task": self.task})
            output_files["md"] = out_md

        # 5.2 HTML
        if "html" in export_formats:
            html_dir = os.path.join(output_dir, "html")
            out_html = os.path.join(html_dir, f"{base_name}.html")
            self.html_exporter.export(healed_text, out_html, title=doc_title)
            output_files["html"] = out_html

        # 5.3 PDF
        if "pdf" in export_formats:
            pdf_dir = os.path.join(output_dir, "pdf")
            out_pdf = os.path.join(pdf_dir, f"{base_name}.pdf")
            self.pdf_printer.print_markdown(healed_text, out_pdf, title=doc_title)
            output_files["pdf"] = out_pdf

        # 更新断点续传检查点
        primary_out = output_files.get("pdf") or output_files.get("html") or output_files.get("md") or ""
        self.tracker.mark_completed(base_name, primary_out, metadata={"formats": list(output_files.keys())})

        return output_files

    def process_all(
        self,
        input_pattern: str,
        output_dir: str = "dist",
        export_formats: Union[str, List[str]] = "pdf",
        merge_monograph: bool = False,
        monograph_title: str = "学术讲义合订本",
        glossary: Optional[dict] = None,
        bilingual: bool = False,
        resume: bool = True
    ) -> List[Dict[str, str]]:
        """
        批量处理多个输入，支持断点续传与一键合成专著大合订本
        """
        files = sorted(glob.glob(input_pattern))
        if not files:
            print(f"未找到匹配的文件: {input_pattern}")
            return []

        results = []
        sections = []

        print(f"=== academic_core 启动流水线 (共 {len(files)} 项任务, 交付格式: {export_formats}) ===")
        for i, fpath in enumerate(files):
            fname = os.path.basename(fpath)
            base_name = os.path.splitext(fname)[0]

            if resume and self.tracker.is_completed(base_name):
                print(f"[{i+1}/{len(files)}] ⏭️ 命中已完成检查点，跳过: {fname}")
                continue

            print(f"[{i+1}/{len(files)}] 正在处理: {fname}...")
            try:
                out_dict = self.process_one(
                    fpath,
                    output_dir=output_dir,
                    export_formats=export_formats,
                    glossary=glossary,
                    bilingual=bilingual
                )
                results.append(out_dict)

                if merge_monograph:
                    md_path = out_dict.get("md")
                    if not md_path:
                        # 确保有 Markdown 内容供合订本编排
                        md_dir = os.path.join(output_dir, "md")
                        md_path = os.path.join(md_dir, f"{base_name}.md")
                    if os.path.exists(md_path):
                        with open(md_path, "r", encoding="utf-8-sig") as fp:
                            sections.append({"title": base_name, "content": fp.read()})
            except Exception as e:
                print(f"  ❌ 处理失败 {fname}: {e}")
                self.tracker.mark_failed(base_name, str(e))

        # 6. 专著合订本编译
        if merge_monograph and sections:
            print(f"\n正在构建专著大合订本: {monograph_title}...")
            book_pdf = os.path.join(output_dir, f"{monograph_title}.pdf")
            self.binder.bind_to_book(sections, book_pdf, book_title=monograph_title)
            print(f"🎉 专著大合订本已生成: {book_pdf}")

        return results
