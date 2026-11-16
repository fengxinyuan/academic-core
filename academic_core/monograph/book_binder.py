# -*- coding: utf-8 -*-
"""
专著合订本与全局目录编排引擎 (Monograph Binder)
"""

import os
import re
from typing import List, Dict
from academic_core.exporters.chrome_pdf_printer import ChromePDFPrinter

class MonographBinder:
    def __init__(self, printer: ChromePDFPrinter = None):
        self.printer = printer or ChromePDFPrinter()

    def bind_to_book(
        self,
        sections: List[Dict[str, str]],
        output_pdf_path: str,
        book_title: str = "高等学术讲义全集",
        book_subtitle: str = ""
    ) -> str:
        """
        sections: [{"title": "第一讲...", "content": "..."}, ...]
        """
        book_md = []
        book_md.append(f"# {book_title}\n")
        if book_subtitle:
            book_md.append(f"*{book_subtitle}*\n")
        book_md.append("\n---\n")

        # 生成带页面内跳转锚点的全局总目录 (Table of Contents)
        book_md.append("## 📖 全书总目录 (Table of Contents)\n")
        for i, sec in enumerate(sections):
            t = sec.get("title", f"第 {i+1} 部分")
            book_md.append(f"- **第 {i+1:02d} 部分**：<a href=\"#section-{i+1}\" style=\"text-decoration:none; color:#2b6cb0;\">{t}</a>")
        book_md.append("\n---\n")

        # 拼接各篇章并注入打印分页与锚点标记
        for i, sec in enumerate(sections):
            book_md.append(f'\n\n<div id="section-{i+1}" style="page-break-before: always; padding-top: 2px;"></div>\n\n')
            book_md.append(sec["content"].strip())
            book_md.append("\n\n---\n")

        full_content = "\n".join(book_md)
        return self.printer.print_markdown(full_content, output_pdf_path, title=book_title)

