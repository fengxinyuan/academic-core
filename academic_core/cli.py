# -*- coding: utf-8 -*-
"""
academic_core 统一通用学术文献数字化命令行工具 (Universal CLI)
用法示例：
  # 1. 手写讲义笔记数字化并导出专著大合订本
  python -m academic_core.cli --input "./raw_onenote/*.one" --task note --merge --title "高等代数讲义全书"

  # 2. 学术前沿论文或课件全格式交付 (PDF + HTML + Markdown)
  python -m academic_core.cli --input "./papers/*.pdf" --task paper --export all --bilingual

  # 3. 极速离线测试或 CI 验证 (Mock 零 Token 模式)
  python -m academic_core.cli --input "./slides/*.pptx" --task textbook --ocr mock --export md,html
"""

import json
import argparse
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from academic_core.pipeline import AcademicPipeline

def main():
    parser = argparse.ArgumentParser(
        description="academic_core: 解耦型通用学术文献数字化、语义推理与出版级排版引擎"
    )
    parser.add_argument("--input", "-i", required=True,
                        help="输入文件、通配符或目录 (支持: .pdf, .one, .docx, .pptx, .md, .tex, .zip, .tar, 图片包等)")
    parser.add_argument("--output", "-o", default="dist",
                        help="输出主目录 (默认: dist)")
    parser.add_argument("--task", "-t", default="note", choices=["note", "textbook", "paper"],
                        help="学术场景预设: note (板书/手写自愈) / textbook (教材精译) / paper (前沿论文翻译)")
    parser.add_argument("--export", "-e", default="pdf",
                        help="交付格式: pdf, html, md, 或 all (默认: pdf)")
    parser.add_argument("--ocr", default="qwen-vl-ocr",
                        help="视觉/OCR 引擎: qwen-vl-ocr, openai, gemini, mock (默认: qwen-vl-ocr)")
    parser.add_argument("--llm", default="qwen-plus",
                        help="推理模型名称 (默认: qwen-plus)")
    parser.add_argument("--provider", default="dashscope", choices=["dashscope", "deepseek", "openai"],
                        help="大模型服务商: dashscope, deepseek, openai (默认: dashscope)")
    parser.add_argument("--bilingual", action="store_true",
                        help="是否启用英汉双语段落对照排版模式")
    parser.add_argument("--glossary", default="",
                        help="专业术语对齐约束字典 JSON (例如: '{\"eigenvalue\": \"特征值\"}')")
    parser.add_argument("--merge", "-m", action="store_true",
                        help="是否一键编译专著大合订本 (含全局目录与跳转锚点)")
    parser.add_argument("--title", default="学术讲义全书",
                        help="专著合订本标题 (默认: 学术讲义全书)")
    parser.add_argument("--no-latex-fix", action="store_true",
                        help="禁用自动 LaTeX 公式与标点自愈修复")
    parser.add_argument("--no-resume", action="store_true",
                        help="禁用断点续传检查点，强制从头重跑全部文件")
    parser.add_argument("--reset-checkpoint", action="store_true",
                        help="清空已有断点续传缓存文件")

    args = parser.parse_args()

    checkpoint_file = os.path.join(args.output, ".checkpoint.json")
    if args.reset_checkpoint and os.path.exists(checkpoint_file):
        try:
            os.remove(checkpoint_file)
            print("🧹 已重置断点续传检查点。")
        except Exception:
            pass

    glossary_dict = None
    if args.glossary:
        try:
            glossary_dict = json.loads(args.glossary)
        except Exception:
            print("⚠️ 术语表 JSON 解析失败，已忽略自定义术语。")

    pipeline = AcademicPipeline(
        llm_provider=args.provider,
        llm_model=args.llm,
        vision_engine_name=args.ocr,
        task=args.task,
        auto_fix_latex=not args.no_latex_fix,
        checkpoint_file=checkpoint_file
    )

    pipeline.process_all(
        input_pattern=args.input,
        output_dir=args.output,
        export_formats=args.export,
        merge_monograph=args.merge,
        monograph_title=args.title,
        glossary=glossary_dict,
        bilingual=args.bilingual,
        resume=not args.no_resume
    )

if __name__ == "__main__":
    main()
