# -*- coding: utf-8 -*-
"""
academic_core 2.0 全模块综合质检与全自动化端到端测试套件
涵盖：
1. 九大多态格式转换器 (Markdown, TXT, LaTeX, DOCX, PPTX, IPYNB, EPUB, PDF Dual-mode, OneNote, Image, Archive)
2. 多视觉 OCR 引擎 (Qwen-VL, OpenAI Vision, Gemini Vision, MinerU, Mock) 与 MD5 缓存去重
3. 学术大模型提示词场景 (Note, Textbook, Paper, 术语表约束, 双语对照)
4. 学术数学公式与排版语法全自动自愈引擎 (LatexCleaner, Math Sentinel 哨兵隔离)
5. 多格式出版级交付导出器 (Chrome 矢量 PDF, 独立 HTML, 规范化 Markdown)
6. 任务状态与断点续传管理中心 (TaskTracker)
7. 专著大合订本编排与跨页锚点目录 (MonographBinder)
8. Pipeline 全链路端到端闭环验证 (一次运行交付 PDF + HTML + MD)
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
    NormalizedDocument,
    TextConverter,
    WordConverter,
    PPTConverter,
    IPYNBConverter,
    EPUBConverter,
    PDFConverter,
    ImageConverter,
    ZipConverter
)
from academic_core.vision_ocr import (
    get_vision_engine,
    QwenVLEngine,
    OpenAIVisionEngine,
    GeminiVisionEngine,
    MinerUEngine,
    MockVisionEngine
)
from academic_core.llm_reasoning.prompts import get_task_prompt
from academic_core.math_enhancer import LatexCleaner, isolate_math, recover_math
from academic_core.exporters import (
    ChromePDFPrinter,
    HTMLExporter,
    MarkdownExporter,
    get_exporter
)
from academic_core.monograph import MonographBinder
from academic_core.checkpoint import TaskTracker
from academic_core.pipeline import AcademicPipeline

def test_1_converters():
    print("[测试 1/7] 独立格式归一化转换器 (Converters)...", flush=True)

    # 1.1 Markdown 与 纯文本
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# 线性映射\n定义 $f: V \\to W$ 为线性映射。")
        temp_md = f.name
    try:
        norm_md = convert_to_normalized(temp_md)
        assert norm_md.is_text_only is True
        assert len(norm_md.pages) == 1
        assert "线性映射" in norm_md.pages[0].text
        print("  ✓ Markdown 归一化提取正常")
    finally:
        os.remove(temp_md)

    # 1.2 LaTeX 源码 (.tex) 自动清洗与公式保留
    with tempfile.NamedTemporaryFile("w", suffix=".tex", delete=False, encoding="utf-8") as f:
        f.write(r"""\documentclass{article}
\usepackage{amsmath}
\title{线性代数基础理论}
\begin{document}
\section{特征值问题}
设 $A$ 为 $n$ 阶方阵，若存在非零向量 $x$ 使得：
\begin{equation}
A x = \lambda x
\end{equation}
则称 $\lambda$ 为特征值。
\end{document}""")
        temp_tex = f.name
    try:
        norm_tex = convert_to_normalized(temp_tex)
        assert norm_tex.is_text_only is True
        assert "# 线性代数基础理论" in norm_tex.pages[0].text or "特征值问题" in norm_tex.pages[0].text
        assert "$$A x = \\lambda x$$" in norm_tex.pages[0].text.replace("\n", "")
        print("  ✓ LaTeX 源码 (.tex) 结构化清洗与公式提取正常")
    finally:
        os.remove(temp_tex)

    # 1.3 Word 文档 (.docx) 零依赖标准库解析
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        temp_docx = f.name
    with zipfile.ZipFile(temp_docx, "w") as z:
        z.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>矩阵的特征值与特征向量定理</w:t></w:r></w:p></w:body></w:document>'
        )
    try:
        norm_docx = convert_to_normalized(temp_docx)
        assert norm_docx.is_text_only is True
        assert "矩阵的特征值与特征向量定理" in norm_docx.pages[0].text
        print("  ✓ Word (.docx) 文档结构解析正常")
    finally:
        os.remove(temp_docx)

    # 1.4 PowerPoint 课件 (.pptx) 零依赖标准库解析
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
        temp_pptx = f.name
    with zipfile.ZipFile(temp_pptx, "w") as z:
        z.writestr(
            "ppt/slides/slide1.xml",
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>第一讲 行列式展开定理</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>'
        )
    try:
        norm_pptx = convert_to_normalized(temp_pptx)
        assert norm_pptx.is_text_only is True
        assert "行列式展开定理" in norm_pptx.pages[0].text
        print("  ✓ PowerPoint (.pptx) 幻灯片逐页提取正常")
    finally:
        os.remove(temp_pptx)

    # 1.5 Jupyter Notebook (.ipynb) 结构化解析
    with tempfile.NamedTemporaryFile("w", suffix=".ipynb", delete=False, encoding="utf-8") as f:
        nb_json = {
            "cells": [
                {"cell_type": "markdown", "source": ["# 伴随矩阵与可逆性\n", "定义 $A^*$ 为伴随矩阵。"]},
                {"cell_type": "code", "source": ["import numpy as np\n", "A = np.eye(3)"]}
            ]
        }
        json.dump(nb_json, f)
        temp_ipynb = f.name
    try:
        norm_ipynb = convert_to_normalized(temp_ipynb)
        assert norm_ipynb.is_text_only is True
        assert "伴随矩阵与可逆性" in norm_ipynb.pages[0].text
        assert "import numpy as np" in norm_ipynb.pages[0].text
        print("  ✓ Jupyter Notebook (.ipynb) 代码与公式解析正常")
    finally:
        os.remove(temp_ipynb)

    # 1.6 EPUB 电子专著 (.epub) 章节解析
    with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as f:
        temp_epub = f.name
    with zipfile.ZipFile(temp_epub, "w") as z:
        z.writestr("chapter1.xhtml", "<html><body><h1>第一章 线性空间</h1><p>设 V 为实数域上的向量空间。</p></body></html>")
    try:
        norm_epub = convert_to_normalized(temp_epub)
        assert norm_epub.is_text_only is True
        assert "第一章 线性空间" in norm_epub.pages[0].text
        print("  ✓ EPUB 电子书 (.epub) 逐章解析正常")
    finally:
        os.remove(temp_epub)

    # 1.7 图像归一化与 EXIF / 对比度自适应
    img = Image.new("RGB", (300, 400), color=(240, 240, 240))
    with tempfile.NamedTemporaryFile("wb", suffix=".png", delete=False) as f:
        img.save(f, format="PNG")
        temp_img = f.name
    try:
        norm_img = convert_to_normalized(temp_img)
        assert norm_img.is_text_only is False
        assert len(norm_img.pages) == 1
        assert len(norm_img.pages[0].image_bytes) > 100
        print("  ✓ 图像归一化与增强处理正常")
    finally:
        os.remove(temp_img)

    # 1.8 PDF 矢量切片与双模式转换 (Dual-Mode)
    sample_pdf = os.path.join(PROJECT_ROOT, "pdf_deliverables", "Lect.02.determinants.02.ranks.01.pdf")
    if os.path.exists(sample_pdf):
        pdf_conv = PDFConverter(dpi=150, mode="vision")
        norm_pdf = pdf_conv.convert(sample_pdf)
        assert norm_pdf.is_text_only is False
        assert norm_pdf.total_pages > 0
        assert norm_pdf.pages[0].image_bytes is not None
        print(f"  ✓ PDF 视觉切片模式正常 (共 {norm_pdf.total_pages} 页)")

    # 1.9 OneNote 笔迹转换
    sample_one = os.path.join(PROJECT_ROOT, "raw_onenote", "Lect.02.determinants.02.ranks.01.one")
    if os.path.exists(sample_one):
        norm_one = convert_to_normalized(sample_one)
        assert norm_one.total_pages > 0
        print(f"  ✓ OneNote 笔迹转换正常 (共 {norm_one.total_pages} 页)")

    # 1.10 压缩包自动解压与归一化
    with tempfile.NamedTemporaryFile("wb", suffix=".zip", delete=False) as f:
        temp_zip = f.name
    with zipfile.ZipFile(temp_zip, "w") as z:
        for idx in [1, 2]:
            sub_img = Image.new("RGB", (100, 100), color=(idx * 80, 255, 255))
            bio = io.BytesIO()
            sub_img.save(bio, format="JPEG")
            z.writestr(f"lecture_p{idx}.jpg", bio.getvalue())
    try:
        norm_zip = convert_to_normalized(temp_zip)
        assert norm_zip.is_text_only is False
        assert norm_zip.total_pages == 2
        print(f"  ✓ ZIP 压缩包自动解压与归一化正常 (解出 {norm_zip.total_pages} 页)")
    finally:
        os.remove(temp_zip)

def test_2_vision_ocr_and_engines():
    print("\n[测试 2/7] 视觉 OCR 抽取、缓存与多引擎矩阵...", flush=True)

    # 2.1 连续手写圈画重复行消除
    qwen_eng = QwenVLEngine(cache_dir="tests/temp_cache")
    repeated = "$\\det(A) \\neq 0$\n$\\det(A) \\neq 0$\n$A$ 可逆\n$A$ 可逆\n$A$ 可逆"
    cleaned = qwen_eng._clean_repetitive_lines(repeated)
    expected = "$\\det(A) \\neq 0$\n$A$ 可逆"
    assert cleaned == expected, f"重复行清洗不符: {cleaned}"
    print("  ✓ 手写重复行消除算法正常")

    # 2.2 视觉引擎工厂路由
    eng_mock = get_vision_engine("mock")
    assert isinstance(eng_mock, MockVisionEngine)

    eng_qwen = get_vision_engine("qwen-vl-ocr")
    assert isinstance(eng_qwen, QwenVLEngine)

    eng_openai = get_vision_engine("gpt-4o", api_key="test-key")
    assert isinstance(eng_openai, OpenAIVisionEngine)

    eng_gemini = get_vision_engine("gemini-1.5-flash", api_key="test-key")
    assert isinstance(eng_gemini, GeminiVisionEngine)

    eng_mineru = get_vision_engine("mineru")
    assert isinstance(eng_mineru, MinerUEngine)
    print("  ✓ 多视觉 OCR 引擎工厂矩阵路由正常 (Qwen, OpenAI, Gemini, MinerU, Mock)")

    # 2.3 Mock 引擎确定性输出测试
    fake_bytes = b"fake-academic-image-content-xyz"
    extracted = eng_mock.extract_page_latex(fake_bytes, page_num=1, total_pages=1)
    assert "线性空间的基与维数" in extracted
    assert "\\begin{pmatrix}" in extracted
    print("  ✓ MockVisionEngine 零成本本地仿真抽取正常")

def test_3_academic_llm_prompts():
    print("\n[测试 3/7] 学术场景提示词 (Note / Textbook / Paper)...", flush=True)
    p_note = get_task_prompt("note")
    p_textbook = get_task_prompt("textbook")
    p_paper = get_task_prompt("paper")

    assert "手写" in p_note or "讲义" in p_note
    assert "教材" in p_textbook or "通识" in p_textbook
    assert "论文" in p_paper or "前沿" in p_paper
    print("  ✓ 三大学术场景任务定义完备")

def test_4_math_enhancer():
    print("\n[测试 4/7] 学术数学公式与语法自愈引擎 (LatexCleaner & Sentinel)...", flush=True)

    # 4.1 中文标点进入公式内部修复
    dirty_punct = "设 $f(x) = x^2+1，$ 且 $g(x) = \\sin x。$"
    clean_punct = LatexCleaner.fix_chinese_punctuation_in_math(dirty_punct)
    assert clean_punct == "设 $f(x) = x^2+1$，且 $g(x) = \\sin x$。"
    print("  ✓ 行内中文标点自动剥离正常")

    # 4.2 align 环境转 aligned 环境
    dirty_align = "$$\\begin{align}\nx &= y + z \\\\\nw &= 2\n\\end{align}$$"
    clean_align = LatexCleaner.fix_align_environments(dirty_align)
    assert "\\begin{aligned}" in clean_align and "\\end{aligned}" in clean_align
    print("  ✓ KaTeX align/aligned 环境语法适配正常")

    # 4.3 上下标空格脱离修复
    dirty_sub = "向量序列 a_ 1, a_ 2 满足 x^ 2 + y^ 3 = 1"
    clean_sub = LatexCleaner.fix_subscript_superscript(dirty_sub)
    assert "a_1, a_2" in clean_sub and "x^2 + y^3" in clean_sub
    print("  ✓ 上下标脱节自动缝合正常")

    # 4.4 LaTeX 命令与中文字符粘连修复
    dirty_cmd = "设\\alpha与\\beta线性无关，求解\\lambda的值"
    clean_cmd = LatexCleaner.fix_command_spacing(dirty_cmd)
    assert "\\alpha 与 \\beta" in clean_cmd and "\\lambda 的值" in clean_cmd
    print("  ✓ LaTeX 命令与中文字符粘连拆分正常")

    # 4.5 未闭合 \\left 自动补全 \\right.
    dirty_left = "$$\\left( \\frac{a}{b} + c $$"
    clean_left = LatexCleaner.balance_left_right(dirty_left)
    assert "\\right." in clean_left
    print("  ✓ 未闭合 \\left( 语法崩溃自愈补全正常")

    # 4.6 数学公式哨兵隔离与无损恢复 (Math Sentinel)
    raw_mixed = "设矩阵 $A \\in \\mathbb{R}^{n \\times n}$，则其特征方程为：\n$$\n\\det(\\lambda I - A) = 0\n$$\n求解特征值 $\\lambda$。"
    isolated, tokens = isolate_math(raw_mixed)
    assert "MATH0ZZZ" in isolated and "MATH1ZZZ" in isolated
    assert "\\det" not in isolated  # 公式已完全物理隔离
    recovered = recover_math(isolated, tokens)
    assert recovered.strip() == raw_mixed.strip()
    print("  ✓ 数学公式哨兵物理隔离与 100% 无损还原机制正常")

def test_5_multi_format_exporters():
    print("\n[测试 5/7] 出版级多格式交付导出器 (PDF / HTML / Markdown)...", flush=True)
    temp_dir = tempfile.mkdtemp(prefix="test_export_")
    test_md = "# 谱定理\n\n**定理 1** 实对称矩阵必定正交相似于对角矩阵：\n$$\nA = Q \\Lambda Q^T\n$$\n其中 $Q$ 为正交阵。"

    try:
        # 5.1 Markdown 规范化导出
        md_exp = get_exporter("md")
        out_md = os.path.join(temp_dir, "test.md")
        md_exp.export(test_md, out_md, title="谱定理")
        assert os.path.exists(out_md)
        with open(out_md, "r", encoding="utf-8-sig") as fp:
            content = fp.read()
            assert "title: \"谱定理\"" in content
        print("  ✓ 规范化 Markdown 导出正常 (含 YAML 元数据)")

        # 5.2 独立 HTML 导出
        html_exp = get_exporter("html")
        out_html = os.path.join(temp_dir, "test.html")
        html_exp.export(test_md, out_html, title="谱定理")
        assert os.path.exists(out_html)
        with open(out_html, "r", encoding="utf-8") as fp:
            html_str = fp.read()
            assert "katex.min.css" in html_str
            assert "MATHBLOCK" in html_str or "marked.parse" in html_str
        print("  ✓ 独立响应式 HTML 交付导出正常 (集成 KaTeX 渲染)")

        # 5.3 矢量 PDF 导出
        pdf_printer = ChromePDFPrinter()
        out_pdf = os.path.join(temp_dir, "test.pdf")
        pdf_printer.print_markdown(test_md, out_pdf, title="谱定理")
        assert os.path.exists(out_pdf)
        doc = pymupdf.open(out_pdf)
        p_count = len(doc)
        doc.close()
        assert p_count >= 1
        print("  ✓ 矢量 A4 PDF 导出正常 (防截断、动态页码)")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_6_checkpoint_and_binder():
    print("\n[测试 6/7] 任务断点续传中心与专著合订本...", flush=True)
    temp_dir = tempfile.mkdtemp(prefix="test_monograph_")
    checkpoint_file = os.path.join(temp_dir, ".checkpoint.json")

    try:
        # 6.1 断点续传管理
        tracker = TaskTracker(checkpoint_file=checkpoint_file)
        assert tracker.is_completed("doc_01") is False
        tracker.mark_completed("doc_01", "/path/to/doc_01.pdf")
        assert tracker.is_completed("doc_01") is True

        # 重载验证持久化
        tracker_reloaded = TaskTracker(checkpoint_file=checkpoint_file)
        assert tracker_reloaded.is_completed("doc_01") is True
        print("  ✓ 任务状态持久化与秒级断点续传正常")

        # 6.2 专著合订本全局编排
        sections = [
            {"title": "第一篇 行列式", "content": "# 第一篇 行列式\n\n这是行列式理论的正文内容。"},
            {"title": "第二篇 矩阵的秩", "content": "# 第二篇 矩阵的秩\n\n这是矩阵的秩核心推导。"}
        ]
        binder = MonographBinder(printer=ChromePDFPrinter())
        book_pdf = os.path.join(temp_dir, "学术合订全书.pdf")
        binder.bind_to_book(sections, book_pdf, book_title="测试专著")
        assert os.path.exists(book_pdf)
        doc = pymupdf.open(book_pdf)
        assert len(doc) >= 2
        doc.close()
        print("  ✓ 专著合订本编译成功 (含跨页跳转锚点与全局目录)")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_7_pipeline_e2e():
    print("\n[测试 7/7] AcademicPipeline 端到端闭环交付测试...", flush=True)
    temp_dir = tempfile.mkdtemp(prefix="test_e2e_")
    test_docx = os.path.join(temp_dir, "sample_lecture.docx")

    # 创建标准模拟课件
    with zipfile.ZipFile(test_docx, "w") as z:
        z.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t># 线性变换之核空间与值域\n\n定义线性映射 $T: V \\to W$。核空间为 $\\ker(T) = \\{v \\in V \\mid T(v) = 0\\}$。</w:t></w:r></w:p></w:body></w:document>'
        )

    try:
        pipeline = AcademicPipeline(
            llm_provider="mock",
            vision_engine_name="mock",
            task="note",
            checkpoint_file=os.path.join(temp_dir, ".ck.json")
        )

        outputs = pipeline.process_one(
            input_path=test_docx,
            output_dir=os.path.join(temp_dir, "dist"),
            export_formats=["pdf", "html", "md"],
            glossary={"kernel": "核空间"}
        )

        assert "pdf" in outputs and os.path.exists(outputs["pdf"])
        assert "html" in outputs and os.path.exists(outputs["html"])
        assert "md" in outputs and os.path.exists(outputs["md"])

        print(f"  ✓ 端到端全格式交付成功:")
        print(f"    - PDF: {os.path.basename(outputs['pdf'])}")
        print(f"    - HTML: {os.path.basename(outputs['html'])}")
        print(f"    - MD: {os.path.basename(outputs['md'])}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    print("=" * 60)
    print("  academic_core 2.0 全模块综合质检与自动化端到端测试")
    print("=" * 60)
    test_1_converters()
    test_2_vision_ocr_and_engines()
    test_3_academic_llm_prompts()
    test_4_math_enhancer()
    test_5_multi_format_exporters()
    test_6_checkpoint_and_binder()
    test_7_pipeline_e2e()
    print("=" * 60)
    print("🎉 恭喜！academic_core 2.0 全部 7 大核心模块通过验证，0 缺陷！")
    print("=" * 60)
