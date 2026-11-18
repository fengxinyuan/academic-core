# -*- coding: utf-8 -*-
"""
academic_core 2.1 全模块综合质检与全自动化端到端测试套件
涵盖：
1. 九大多态格式转换器 (Markdown, TXT, LaTeX, DOCX, PPTX, IPYNB, EPUB, PDF 多模式, 图像增强, Archive)
2. 多视觉 OCR 与 MinerU 结构化文档装配引擎 (Qwen-VL, OpenAI Vision, Gemini Vision, MinerU, Mock)
3. 长文档语义分块、截断自愈、1:1 段落锚点双语对照、多目标语言与多网关支持
4. 数学公式语法自愈引擎 (LatexCleaner) 与 Math Sentinel 物理隔离零丢失找回
5. 多格式出版级交付与论文插图无损闭环 (Chrome 矢量 PDF, Base64 自包含 HTML, 伴随图片 Markdown)
6. 任务断点续传中心与专著大合订本（含仅 PDF 导出合订 & 断点续传合订无漏章验证）
7. AcademicPipeline 全链路闭环（常规模式 + 双语模式 + --no-llm 纯排版模式）
"""

import os
import sys
import tempfile
import zipfile
import shutil
import io
import json
import pymupdf
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from academic_core.converters import (
    convert_to_normalized,
    PDFConverter,
)
from academic_core.vision_ocr import (
    get_vision_engine,
    QwenVLEngine,
    OpenAIVisionEngine,
    GeminiVisionEngine,
    MinerUEngine,
    MockVisionEngine,
)
from academic_core.vision_ocr.mineru_engine import assemble_mineru_markdown
from academic_core.llm_reasoning import AcademicLLMEngine
from academic_core.llm_reasoning.prompts import get_task_prompt
from academic_core.math_enhancer import (
    LatexCleaner,
    isolate_math,
    recover_math,
    verify_and_recover_math,
    inject_paragraph_anchors,
    split_by_paragraph_anchors,
    sanitize_and_repair_markdown,
)
from academic_core.exporters import (
    ChromePDFPrinter,
    HTMLExporter,
    MarkdownExporter,
    get_exporter,
)
from academic_core.monograph import MonographBinder
from academic_core.checkpoint import TaskTracker
from academic_core.pipeline import AcademicPipeline


def test_1_converters():
    print("[测试 1/8] 独立格式归一化转换器 (Converters)...", flush=True)

    # 1.1 Markdown
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# 线性映射\n定义 $f: V \\to W$ 为线性映射。")
        temp_md = f.name
    try:
        norm_md = convert_to_normalized(temp_md)
        assert norm_md.is_text_only is True
        assert norm_md.assets_dir == os.path.dirname(os.path.abspath(temp_md))
        assert "线性映射" in norm_md.pages[0].text
    finally:
        os.remove(temp_md)

    # 1.2 LaTeX (.tex)
    with tempfile.NamedTemporaryFile("w", suffix=".tex", delete=False, encoding="utf-8") as f:
        f.write(r"""\documentclass{article}
\title{General Relativity Notes}
\begin{document}
\section{Einstein Field Equations}
\begin{equation}
G_{\mu\nu} + \Lambda g_{\mu\nu} = \kappa T_{\mu\nu}
\end{equation}
\end{document}""")
        temp_tex = f.name
    try:
        norm_tex = convert_to_normalized(temp_tex)
        assert norm_tex.is_text_only is True
        assert "Einstein Field Equations" in norm_tex.pages[0].text
        assert "$$G_{\\mu\\nu} + \\Lambda g_{\\mu\\nu} = \\kappa T_{\\mu\\nu}$$" in norm_tex.pages[0].text.replace("\n", "")
    finally:
        os.remove(temp_tex)

    # 1.3 Word (.docx)
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        temp_docx = f.name
    with zipfile.ZipFile(temp_docx, "w") as z:
        z.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>量子力学波函数坍缩原理</w:t></w:r></w:p></w:body></w:document>'
        )
    try:
        norm_docx = convert_to_normalized(temp_docx)
        assert norm_docx.is_text_only is True
        assert "量子力学波函数坍缩原理" in norm_docx.pages[0].text
    finally:
        os.remove(temp_docx)

    # 1.4 PowerPoint (.pptx)
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
        temp_pptx = f.name
    with zipfile.ZipFile(temp_pptx, "w") as z:
        z.writestr(
            "ppt/slides/slide1.xml",
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>Transformer Attention Mechanism</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>'
        )
    try:
        norm_pptx = convert_to_normalized(temp_pptx)
        assert norm_pptx.is_text_only is True
        assert "Transformer Attention Mechanism" in norm_pptx.pages[0].text
    finally:
        os.remove(temp_pptx)

    # 1.5 Jupyter Notebook (.ipynb)
    with tempfile.NamedTemporaryFile("w", suffix=".ipynb", delete=False, encoding="utf-8") as f:
        json.dump({
            "cells": [
                {"cell_type": "markdown", "source": ["# SGD Optimization\n", "Update: $\\theta \\leftarrow \\theta - \\eta \\nabla L$"]},
                {"cell_type": "code", "source": ["import torch\n", "x = torch.randn(3)"]},
            ]
        }, f)
        temp_ipynb = f.name
    try:
        norm_ipynb = convert_to_normalized(temp_ipynb)
        assert norm_ipynb.is_text_only is True
        assert "SGD Optimization" in norm_ipynb.pages[0].text
        assert "import torch" in norm_ipynb.pages[0].text
    finally:
        os.remove(temp_ipynb)

    # 1.6 EPUB (.epub)
    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        temp_epub = f.name
    with zipfile.ZipFile(temp_epub, "w") as z:
        z.writestr("ch1.xhtml", "<html><body><h1>Chapter 1 Topology</h1><p>Open sets define a topology.</p></body></html>")
    try:
        norm_epub = convert_to_normalized(temp_epub)
        assert norm_epub.is_text_only is True
        assert "Chapter 1 Topology" in norm_epub.pages[0].text
    finally:
        os.remove(temp_epub)

    # 1.7 Image + Contrast Enhancement
    img = Image.new("RGB", (200, 300), color=(230, 230, 230))
    with tempfile.NamedTemporaryFile("wb", suffix=".png", delete=False) as f:
        img.save(f, format="PNG")
        temp_img = f.name
    try:
        norm_img = convert_to_normalized(temp_img, enhance_image=True)
        assert norm_img.is_text_only is False
        assert len(norm_img.pages) == 1
        assert len(norm_img.pages[0].image_bytes) > 100
    finally:
        os.remove(temp_img)

    # 1.8 Self-contained synthetic PDF (vision mode & text mode)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_pdf = f.name
    pdf_doc = pymupdf.open()
    pg = pdf_doc.new_page()
    pg.insert_text((50, 80), "Academic Core Synthetic PDF Page Content " * 10)
    pdf_doc.save(temp_pdf)
    pdf_doc.close()
    try:
        norm_pdf_vision = PDFConverter(dpi=120, mode="vision").convert(temp_pdf)
        assert norm_pdf_vision.is_text_only is False
        assert norm_pdf_vision.total_pages == 1
        assert norm_pdf_vision.pages[0].image_bytes is not None

        norm_pdf_text = PDFConverter(mode="text").convert(temp_pdf)
        assert norm_pdf_text.is_text_only is True
        assert "Academic Core Synthetic PDF" in norm_pdf_text.pages[0].text
    finally:
        os.remove(temp_pdf)

    # 1.9 ZIP archive of photos
    with tempfile.NamedTemporaryFile("wb", suffix=".zip", delete=False) as f:
        temp_zip = f.name
    with zipfile.ZipFile(temp_zip, "w") as z:
        for idx in [1, 2]:
            sub_img = Image.new("RGB", (80, 80), color=(idx * 60, 200, 200))
            bio = io.BytesIO()
            sub_img.save(bio, format="JPEG")
            z.writestr(f"board_p{idx}.jpg", bio.getvalue())
    try:
        norm_zip = convert_to_normalized(temp_zip)
        assert norm_zip.is_text_only is False
        assert norm_zip.total_pages == 2
    finally:
        os.remove(temp_zip)


def test_2_vision_ocr_and_mineru_assembly():
    print("\n[测试 2/8] 视觉 OCR 多引擎路由与 MinerU 结构化装配...", flush=True)

    qwen_eng = QwenVLEngine(cache_dir="tests/temp_cache")
    repeated = "$E = mc^2$\n$E = mc^2$\n能量守恒\n能量守恒"
    assert qwen_eng._clean_repetitive_lines(repeated) == "$E = mc^2$\n能量守恒"

    assert isinstance(get_vision_engine("mock"), MockVisionEngine)
    assert isinstance(get_vision_engine("qwen-vl-ocr"), QwenVLEngine)
    assert isinstance(get_vision_engine("gpt-4o", api_key="k"), OpenAIVisionEngine)
    assert isinstance(get_vision_engine("gemini-1.5-flash", api_key="k"), GeminiVisionEngine)
    assert isinstance(get_vision_engine("mineru"), MinerUEngine)

    # 验证 MinerU content_list.json 整文档结构装配（含双栏标题、公式、插图与表格）
    tmp_dir = tempfile.mkdtemp(prefix="test_mineru_")
    try:
        cl = [
            {"type": "text", "text_level": 1, "text": "Attention Is All You Need", "page_idx": 0},
            {"type": "text", "text": "We propose a new simple network architecture.", "page_idx": 0},
            {"type": "equation", "text": "\\text{Attention}(Q,K,V)=\\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V", "img_path": "images/eq1.jpg", "page_idx": 0},
            {"type": "image", "img_path": "images/arch.jpg", "image_caption": ["Figure 1: Model Architecture."], "page_idx": 1},
            {"type": "chart", "img_path": "images/plot.jpg", "chart_caption": ["Figure 2: Accuracy Curve."], "page_idx": 1},
            {"type": "code", "code_body": "Algorithm 1: SGD\n1: init theta", "page_idx": 1},
            {"type": "list", "list_items": ["Ref [1] Vaswani et al. 2017"], "page_idx": 1},
            {"type": "table", "table_caption": ["Table 1: BLEU scores."], "table_body": "<table><tr><th>Model</th><th>BLEU</th></tr><tr><td>Transformer</td><td>28.4</td></tr></table>", "page_idx": 1},
        ]
        with open(os.path.join(tmp_dir, "sample_content_list.json"), "w", encoding="utf-8") as f:
            json.dump(cl, f)

        md_out, eq_map = assemble_mineru_markdown(tmp_dir, include_page_markers=True)
        assert "# Attention Is All You Need" in md_out
        assert "![Figure 1: Model Architecture.](images/arch.jpg)" in md_out
        assert "![Figure 2: Accuracy Curve.](images/plot.jpg)" in md_out
        assert "Algorithm 1: SGD" in md_out
        assert "- Ref [1] Vaswani et al. 2017" in md_out
        assert "<table>" in md_out
        assert len(eq_map) == 1
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_3_llm_chunking_bilingual_and_prompts():
    print("\n[测试 3/8] 全学科提示词、长文安全分块与精准双语对照...", flush=True)

    # 全学科与多语言提示词校验（无特定学科硬编码）
    p_note = get_task_prompt("note", target_lang="en")
    p_paper = get_task_prompt("paper", target_lang="zh-CN")
    p_book = get_task_prompt("textbook", target_lang="ja")
    assert "Academic English" in p_note
    assert "高等代数" not in p_note
    assert "MATH0ZZZ" in p_paper and "PARA0ZZZ" in p_paper
    assert "日本語" in p_book

    # 长文档语义分块：严禁切断多行 $$ 公式块或代码块
    long_doc = "\n\n".join([
        f"Paragraph {i}: " + ("This is an academic sentence about scientific modeling. " * 20)
        for i in range(6)
    ])
    long_doc += "\n\n$$\n\\begin{aligned}\na &= b + c \\\\\nd &= e + f\n\\end{aligned}\n$$\n\nFinal conclusion paragraph."
    chunks = AcademicLLMEngine._split_into_chunks(long_doc, max_chars=1500)
    assert len(chunks) >= 3
    for ch in chunks:
        assert ch.count("$$") % 2 == 0, "分块意外切断了多行公式块！"

    # 验证多网关 / Gemini / Mock 实例化无报错
    assert AcademicLLMEngine(provider="openai", base_url="http://localhost:11434/v1", model="qwen2.5").api_url.endswith("/chat/completions")
    assert AcademicLLMEngine(provider="gemini", model="gemini-1.5-pro").provider == "gemini"

    # Mock 双语对照：跳过纯公式块重复、仅对正文段落生成双语块
    mock_llm = AcademicLLMEngine(provider="mock")
    bilingual_out = mock_llm.process_academic_task(
        "This paper proves a theorem.\n\n$$\nx^2 + y^2 = z^2\n$$\n\nThe proof is complete.",
        task="paper",
        bilingual=True,
    )
    assert '<div class="bilingual-orig">' in bilingual_out
    assert bilingual_out.count("x^2 + y^2 = z^2") == 1  # 纯公式不重复渲染两次


def test_4_math_enhancer_and_sentinel():
    print("\n[测试 4/8] 数学公式自愈引擎与哨兵零丢失保护...", flush=True)

    # LatexCleaner
    assert LatexCleaner.fix_chinese_punctuation_in_math("设 $f(x) = x^2+1，$ 且 $g(x) = \\sin x。$") == "设 $f(x) = x^2+1$，且 $g(x) = \\sin x$。"
    assert "\\begin{aligned}" in LatexCleaner.fix_align_environments("$$\\begin{align}\nx &= 1\n\\end{align}$$")
    assert "a_1" in LatexCleaner.fix_subscript_superscript("a_ 1")
    assert "\\alpha 与 \\beta" in LatexCleaner.fix_command_spacing("设\\alpha与\\beta")
    assert "\\right." in LatexCleaner.balance_left_right("$$\\left( \\frac{a}{b} $$")

    # Sentinel 物理隔离 + 丢失自动找回
    raw_mixed = "设矩阵 $A \\in \\mathbb{R}^{n \\times n}$，特征方程为：\n\n$$\n\\det(\\lambda I - A) = 0\n$$\n\n解得 $\\lambda$。"
    isolated, tokens = isolate_math(raw_mixed)
    assert "MATH0ZZZ" in isolated and "MATH1ZZZ" in isolated and "MATH2ZZZ" in isolated
    assert recover_math(isolated, tokens) == raw_mixed

    # 模拟模型不小心吞掉了 MATH2ZZZ -> verify_and_recover_math 自动找回
    corrupted_by_llm = isolated.replace("MATH2ZZZ", "")
    repaired, missing_cnt = verify_and_recover_math(corrupted_by_llm, tokens)
    assert missing_cnt == 1
    assert "$\\lambda$" in repaired

    # 段落锚点 1:1 切分
    anchored, orig_blocks = inject_paragraph_anchors("Para A\n\nPara B\n\nPara C")
    assert len(orig_blocks) == 3
    fake_trans = anchored.replace("Para A", "甲").replace("Para B", "乙").replace("Para C", "丙")
    segs = split_by_paragraph_anchors(fake_trans, 3)
    assert segs == ["甲", "乙", "丙"]

    # 裸露矩阵自动包裹 + 连续两个独立公式块不得被误合并
    naked = "前文说明。\n\n$$\nx = 1\n$$\n\n\\begin{pmatrix} 1 & 0 \\\\ 0 & 1 \\end{pmatrix}\n\n后文。"
    repaired_naked = LatexCleaner.clean(sanitize_and_repair_markdown(naked))
    assert repaired_naked.count("$$") == 4, f"连续公式块被误合并: {repaired_naked}"
    assert "$$\n\\begin{pmatrix}" in repaired_naked


def test_5_exporters_and_figure_closure():
    print("\n[测试 5/8] 出版级多格式导出与论文插图无损闭环...", flush=True)
    temp_dir = tempfile.mkdtemp(prefix="test_export_fig_")
    assets_dir = os.path.join(temp_dir, "assets")
    os.makedirs(os.path.join(assets_dir, "images"), exist_ok=True)

    # 创建一张真实插图
    fig_path = os.path.join(assets_dir, "images", "fig1.png")
    Image.new("RGB", (120, 60), color=(40, 120, 200)).save(fig_path, format="PNG")

    test_md = "# 论文图表测试\n\n如图 1 所示：\n\n![实验架构图](images/fig1.png)\n\n公式：\n$$\nA = Q \\Lambda Q^T\n$$"

    try:
        # 5.1 Markdown 伴随复制 images/
        out_md = os.path.join(temp_dir, "out_md", "paper.md")
        get_exporter("md").export(test_md, out_md, title="论文图表测试", assets_dir=assets_dir)
        assert os.path.exists(out_md)
        assert os.path.exists(os.path.join(temp_dir, "out_md", "images", "fig1.png"))

        # 5.2 独立 HTML 自动 Base64 内嵌插图（单文件移动永不裂图）
        out_html = os.path.join(temp_dir, "out_html", "paper.html")
        get_exporter("html").export(test_md, out_html, title="论文图表测试", assets_dir=assets_dir)
        with open(out_html, "r", encoding="utf-8") as fp:
            html_str = fp.read()
            assert "data:image/png;base64," in html_str

        # 5.3 矢量 PDF 打印（带插图）
        out_pdf = os.path.join(temp_dir, "out_pdf", "paper.pdf")
        ChromePDFPrinter().print_markdown(test_md, out_pdf, title="论文图表测试", assets_dir=assets_dir)
        doc = pymupdf.open(out_pdf)
        assert len(doc) >= 1
        doc.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_6_checkpoint_and_resumed_monograph():
    print("\n[测试 6/8] 断点续传与合订本无漏章验证...", flush=True)
    temp_dir = tempfile.mkdtemp(prefix="test_merge_resume_")
    in_dir = os.path.join(temp_dir, "inputs")
    out_dir = os.path.join(temp_dir, "dist")
    os.makedirs(in_dir, exist_ok=True)

    for idx in (1, 2):
        with open(os.path.join(in_dir, f"ch0{idx}.md"), "w", encoding="utf-8") as f:
            f.write(f"# 第 {idx} 章 核心理论\n\n正文推导 $x_{idx} = {idx}$。")

    try:
        ck_file = os.path.join(out_dir, ".ck.json")
        # 仅指定 export_formats="pdf" + merge_monograph=True，验证合订本仍能成功生成（修复旧 Bug 1）
        pipe = AcademicPipeline(llm_provider="mock", vision_engine_name="mock", checkpoint_file=ck_file)
        pipe.process_all(
            input_pattern=os.path.join(in_dir, "*.md"),
            output_dir=out_dir,
            export_formats="pdf",
            merge_monograph=True,
            monograph_title="测试全书",
            resume=True,
        )
        book_pdf = os.path.join(out_dir, "测试全书.pdf")
        assert os.path.exists(book_pdf)
        doc1 = pymupdf.open(book_pdf)
        pages_first = len(doc1)
        doc1.close()
        assert pages_first >= 2

        # 二次运行命中 resume=True 跳过全部单篇，验证合订本依然加载所有已完成章节无漏章（修复旧 Bug 2）
        os.remove(book_pdf)
        pipe.process_all(
            input_pattern=os.path.join(in_dir, "*.md"),
            output_dir=out_dir,
            export_formats="pdf",
            merge_monograph=True,
            monograph_title="测试全书",
            resume=True,
        )
        assert os.path.exists(book_pdf)
        doc2 = pymupdf.open(book_pdf)
        assert len(doc2) == pages_first
        doc2.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_7_no_llm_fast_typeset_mode():
    print("\n[测试 7/8] --no-llm 纯转换与公式自愈直出排版模式...", flush=True)
    temp_dir = tempfile.mkdtemp(prefix="test_no_llm_")
    tex_file = os.path.join(temp_dir, "fast_paper.tex")
    with open(tex_file, "w", encoding="utf-8") as f:
        f.write(r"\title{Fast Typeset}\begin{document}\section{Intro}Formula $x_ 1 = 2，$ end.\end{document}")

    try:
        pipe = AcademicPipeline(use_llm=False, vision_engine_name="mock", checkpoint_file=os.path.join(temp_dir, ".ck.json"))
        outputs = pipe.process_one(tex_file, output_dir=os.path.join(temp_dir, "dist"), export_formats=["md", "html", "pdf"])
        assert os.path.exists(outputs["pdf"])
        assert os.path.exists(outputs["html"])
        with open(outputs["md"], "r", encoding="utf-8-sig") as fp:
            md_txt = fp.read()
            assert "$x_1 = 2$，" in md_txt  # 验证未走 LLM 但 LatexCleaner 依然生效
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_8_pipeline_e2e_bilingual_paper():
    print("\n[测试 8/8] AcademicPipeline 端到端双语论文全格式交付...", flush=True)
    temp_dir = tempfile.mkdtemp(prefix="test_e2e_bilingual_")
    docx_file = os.path.join(temp_dir, "arxiv_sample.docx")
    with zipfile.ZipFile(docx_file, "w") as z:
        z.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t># Scaling Laws for Neural Language Models\n\nWe study empirical scaling laws for language model performance $L(N)$.</w:t></w:r></w:p></w:body></w:document>'
        )

    try:
        pipeline = AcademicPipeline(
            llm_provider="mock",
            vision_engine_name="mock",
            task="paper",
            target_lang="zh-CN",
            checkpoint_file=os.path.join(temp_dir, ".ck.json"),
        )
        outputs = pipeline.process_one(
            input_path=docx_file,
            output_dir=os.path.join(temp_dir, "dist"),
            export_formats="all",
            glossary={"scaling law": "缩放定律"},
            bilingual=True,
        )
        assert os.path.exists(outputs["pdf"])
        assert os.path.exists(outputs["html"])
        assert os.path.exists(outputs["md"])
        with open(outputs["html"], "r", encoding="utf-8") as fp:
            assert "bilingual-orig" in fp.read()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_1_converters()
    test_2_vision_ocr_and_mineru_assembly()
    test_3_llm_chunking_bilingual_and_prompts()
    test_4_math_enhancer_and_sentinel()
    test_5_exporters_and_figure_closure()
    test_6_checkpoint_and_resumed_monograph()
    test_7_no_llm_fast_typeset_mode()
    test_8_pipeline_e2e_bilingual_paper()
    print("\n🎉 academic_core 2.1 全部 8 大核心端到端测试通过，0 缺陷！")
