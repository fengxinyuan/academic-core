# -*- coding: utf-8 -*-
"""
导出器工厂 (Exporter Factory)
统一调度 PDF, HTML, Markdown 等多格式交付
"""

from typing import Union
from academic_core.exporters.chrome_pdf_printer import ChromePDFPrinter
from academic_core.exporters.html_exporter import HTMLExporter
from academic_core.exporters.markdown_exporter import MarkdownExporter
from academic_core.registry import EXPORTER_REGISTRY

EXPORTER_REGISTRY.register("pdf")(ChromePDFPrinter)
EXPORTER_REGISTRY.register("html")(HTMLExporter)
EXPORTER_REGISTRY.register("md")(MarkdownExporter)
EXPORTER_REGISTRY.register("markdown")(MarkdownExporter)

def get_exporter(export_format: str = "pdf", **kwargs):
    fmt = export_format.lower().strip()
    if fmt == "pdf":
        return ChromePDFPrinter(**kwargs)
    elif fmt == "html":
        return HTMLExporter()
    elif fmt in ("md", "markdown"):
        return MarkdownExporter()
    else:
        raise ValueError(f"不支持的导出格式: {export_format} (支持: pdf, html, md)")

