# -*- coding: utf-8 -*-
"""
独立单文件 HTML 导出器 (HTMLExporter)
生成带有 KaTeX 实时公式渲染、内嵌插图 (Base64) 与响应式视口的独立学术网页。
"""

import os
from typing import Optional
from academic_core.exporters.templates import build_html_template


class HTMLExporter:
    def export(
        self,
        markdown_text: str,
        output_path: str,
        title: str = "学术文档",
        assets_dir: Optional[str] = None,
        embed_images: bool = True,
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        html_content = build_html_template(
            markdown_text,
            title=title,
            assets_dir=assets_dir,
            embed_images=embed_images,
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return output_path
