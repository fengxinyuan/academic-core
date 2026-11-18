# -*- coding: utf-8 -*-
"""
academic_core 统一通用学术文献数字化命令行工具 (Universal CLI)
用法示例：
  # 1. 手写讲义/照片数字化并一键合订专著全书
  academic-core -i "./photos_folder" --task note --enhance-image --merge --title "课程讲义全书"

  # 2. 英文学术论文精译与 1:1 段落精准双语全格式直出 (MinerU 留图 + 公式哨兵)
  academic-core -i "./paper.pdf" --task paper --pdf-mode mineru --bilingual --export all

  # 3. 外文经典教材/EPUB 长文并发精译 (DeepSeek-V3 + 术语表)
  academic-core -i "./book.epub" --task textbook --provider deepseek --llm deepseek-v3 --glossary '{"manifold": "流形"}'

  # 4. 纯格式转换与公式自愈直出 PDF (跳过大模型 --no-llm)
  academic-core -i "./draft.tex" --no-llm --export pdf,html
"""

import json
import logging
import argparse
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from academic_core.pipeline import AcademicPipeline


def main():
    parser = argparse.ArgumentParser(
        description="academic_core: 解耦型通用学术文献数字化、长文精译与出版级排版引擎"
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="输入文件、通配符或目录 (支持: .pdf, .one, .docx, .pptx, .epub, .ipynb, .tex, .md, .zip, .tar, 照片或照片目录)"
    )
    parser.add_argument("--output", "-o", default="dist", help="输出主目录 (默认: dist)")
    parser.add_argument(
        "--task", "-t", default="note", choices=["note", "textbook", "paper"],
        help="学术场景预设: note (手写/拍照笔记) / textbook (教材精译) / paper (论文翻译)"
    )
    parser.add_argument("--export", "-e", default="pdf", help="交付格式: pdf, html, md, 或 all (默认: pdf)")
    parser.add_argument(
        "--ocr", default="qwen-vl-ocr",
        help="视觉/解析引擎: qwen-vl-ocr, mineru, gpt-4o, gemini-1.5-flash, mock (默认: qwen-vl-ocr)"
    )
    parser.add_argument(
        "--pdf-mode", default="vision", choices=["vision", "mineru", "text", "auto"],
        help="PDF 解析策略: vision (手写/数学切片), mineru (双栏论文留图), text (纯文本直提), auto (自动)"
    )
    parser.add_argument("--dpi", type=int, default=200, help="PDF 视觉切片 DPI 精度 (默认: 200)")
    parser.add_argument("--enhance-image", action="store_true", help="开启照片/黑板浅字迹对比度增强")
    parser.add_argument("--llm", default="qwen-plus", help="推理模型名称 (默认: qwen-plus)")
    parser.add_argument(
        "--provider", default="dashscope", choices=["dashscope", "deepseek", "openai", "gemini", "mock"],
        help="大模型服务商 (默认: dashscope)"
    )
    parser.add_argument("--base-url", default=None, help="自定义 OpenAI 兼容网关地址 (如 OpenRouter / Ollama / vLLM)")
    parser.add_argument("--target-lang", default="zh-CN", help="目标输出语言 (默认: zh-CN，可设 en, ja 等)")
    parser.add_argument("--no-llm", action="store_true", help="跳过大模型语义改写，仅执行格式转换/OCR + 公式自愈并直出排版")
    parser.add_argument("--bilingual", action="store_true", help="开启 1:1 段落精准双语对照排版模式")
    parser.add_argument("--glossary", default="", help="专业术语对齐约束字典 JSON (例如: '{\"eigenvalue\": \"特征值\"}')")
    parser.add_argument("--max-chunk-chars", type=int, default=5000, help="长文分块单块字符上限 (默认: 5000)")
    parser.add_argument("--workers", type=int, default=4, help="多页 OCR 与长文分块并发线程数 (默认: 4)")
    parser.add_argument("--merge", "-m", action="store_true", help="一键编译专著大合订本 (含全局目录与跨页锚点)")
    parser.add_argument("--title", default="学术成果合订本", help="专著合订本标题")
    parser.add_argument("--no-latex-fix", action="store_true", help="禁用自动 LaTeX 公式与标点自愈修复")
    parser.add_argument("--no-resume", action="store_true", help="禁用断点续传检查点，强制重跑全部文件")
    parser.add_argument("--reset-checkpoint", action="store_true", help="清空已有断点续传缓存")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出详细调试日志")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式，仅输出错误日志")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else (logging.ERROR if args.quiet else logging.INFO)
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    os.makedirs(args.output, exist_ok=True)
    checkpoint_file = os.path.join(args.output, ".checkpoint.json")
    if args.reset_checkpoint and os.path.exists(checkpoint_file):
        try:
            os.remove(checkpoint_file)
            logging.info("已重置断点续传检查点。")
        except Exception:
            pass

    glossary_dict = None
    if args.glossary:
        try:
            glossary_dict = json.loads(args.glossary)
        except Exception:
            logging.warning("术语表 JSON 解析失败，已忽略自定义术语。")

    pipeline = AcademicPipeline(
        llm_provider=args.provider,
        llm_model=args.llm,
        vision_engine_name=args.ocr,
        task=args.task,
        auto_fix_latex=not args.no_latex_fix,
        checkpoint_file=checkpoint_file,
        base_url=args.base_url,
        target_lang=args.target_lang,
        use_llm=not args.no_llm,
        pdf_mode=args.pdf_mode,
        pdf_dpi=args.dpi,
        enhance_image=args.enhance_image,
        max_chunk_chars=args.max_chunk_chars,
        max_workers=args.workers,
    )

    pipeline.process_all(
        input_pattern=args.input,
        output_dir=args.output,
        export_formats=args.export,
        merge_monograph=args.merge,
        monograph_title=args.title,
        glossary=glossary_dict,
        bilingual=args.bilingual,
        resume=not args.no_resume,
    )


if __name__ == "__main__":
    main()
