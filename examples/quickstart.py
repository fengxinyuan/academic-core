# -*- coding: utf-8 -*-
"""
academic_core 极速上手示例 (Quickstart Demo)
展示无需配置任何 API Key 即可使用 Mock 引擎体验全链路：
LaTeX 源码解析 -> 结构化语义推理 -> LaTeX 语法自愈 -> 矢量 A4 PDF + 响应式 HTML + Markdown 全格式交付
"""

import os
from academic_core import AcademicPipeline

def main():
    print("🚀 启动 academic_core 快速体验示例...")

    # 1. 实例化流水线 (使用本地 Mock 引擎体验全套排版能力，零网络开销)
    pipeline = AcademicPipeline(
        llm_provider="mock",
        vision_engine_name="mock",
        task="note",
        auto_fix_latex=True
    )

    # 2. 转换示例学术文件
    input_file = os.path.join(os.path.dirname(__file__), "sample_linear_algebra.tex")
    output_dir = os.path.join(os.path.dirname(__file__), "dist_demo")

    print(f"📄 正在处理: {input_file}")
    outputs = pipeline.process_one(
        input_path=input_file,
        output_dir=output_dir,
        export_formats=["pdf", "html", "md"],
        glossary={"eigenspace": "特征子空间"}
    )

    print("🎉 交付文件生成成功：")
    for fmt, path in outputs.items():
        print(f"  [{fmt.upper()}] -> {path}")

if __name__ == "__main__":
    main()
