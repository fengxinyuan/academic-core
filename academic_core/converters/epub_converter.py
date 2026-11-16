# -*- coding: utf-8 -*-
"""
EPUB 电子专著 (.epub) 归一化转换器：
学术经典教材、O'Reilly、Springer 常见电子书格式。
零依赖基于标准库 (zipfile + XML) 逐章解析 XHTML 结构并转为标准页面流。
"""

import os
import re
import zipfile
import xml.etree.ElementTree as ET
from academic_core.converters.base import BaseConverter, NormalizedDocument, PageData

class EPUBConverter(BaseConverter):
    def can_convert(self, file_path: str) -> bool:
        return file_path.lower().endswith(".epub")

    def convert(self, file_path: str) -> NormalizedDocument:
        doc_name = os.path.splitext(os.path.basename(file_path))[0]
        pages = []

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                # 收集所有 XHTML / HTML 章节文件
                html_files = [
                    f for f in zf.namelist()
                    if f.lower().endswith((".xhtml", ".html", ".htm"))
                    and not os.path.basename(f).startswith("toc")
                    and not os.path.basename(f).startswith("cover")
                ]
                html_files.sort()

                for idx, hf in enumerate(html_files, start=1):
                    raw_bytes = zf.read(hf)
                    raw_text = raw_bytes.decode("utf-8", errors="ignore")

                    # 基础转义与标头替换
                    text = re.sub(r'<h1[^>]*>([\s\S]*?)</h1>', r'\n# \1\n', raw_text, flags=re.I)
                    text = re.sub(r'<h2[^>]*>([\s\S]*?)</h2>', r'\n## \1\n', text, flags=re.I)
                    text = re.sub(r'<h3[^>]*>([\s\S]*?)</h3>', r'\n### \1\n', text, flags=re.I)
                    text = re.sub(r'<p[^>]*>([\s\S]*?)</p>', r'\1\n\n', text, flags=re.I)
                    text = re.sub(r'<[^>]+>', '', text)
                    text = re.sub(r'\n{3,}', '\n\n', text).strip()

                    if text:
                        pages.append(PageData(page_num=idx, text=text))

        except Exception as e:
            pages = [PageData(page_num=1, text=f"# {doc_name}\n\nEPUB 提取异常: {e}")]

        if not pages:
            pages = [PageData(page_num=1, text=f"# {doc_name}\n\n(EPUB 解析完成，正文无文字)")]

        return NormalizedDocument(
            source_path=file_path,
            doc_name=doc_name,
            pages=pages,
            is_text_only=True,
            metadata={"format": "epub", "converter": "EPUBConverter", "chapters": len(pages)}
        )
