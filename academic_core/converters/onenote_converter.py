# -*- coding: utf-8 -*-
"""
OneNote 归一化转换器：
将 .one 手写笔记本矢量解包并转化为标准页面流
"""

import os
import subprocess
from academic_core.converters.base import BaseConverter, NormalizedDocument
from academic_core.converters.pdf_converter import PDFConverter

class OneNoteConverter(BaseConverter):
    def __init__(self, cache_dir: str = "pdf_exports"):
        self.cache_dir = cache_dir

    def can_convert(self, file_path: str) -> bool:
        return file_path.lower().endswith(".one")

    def convert(self, file_path: str) -> NormalizedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"OneNote 文件未找到: {file_path}")

        abs_one = os.path.abspath(file_path)
        doc_name = os.path.splitext(os.path.basename(file_path))[0]
        os.makedirs(self.cache_dir, exist_ok=True)
        out_pdf = os.path.abspath(os.path.join(self.cache_dir, f"{doc_name}.pdf"))

        # COM 原生发布
        if not (os.path.exists(out_pdf) and os.path.getsize(out_pdf) > 1000):
            ps_code = f"""
            $one = New-Object -ComObject OneNote.Application
            $absOne = '{abs_one}'
            $outPdf = '{out_pdf}'
            $secId = ""
            $one.OpenHierarchy($absOne, $null, [ref]$secId, 0)
            $one.Publish($secId, $outPdf, 3, '')
            """
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_code], check=True)

        norm_doc = PDFConverter(dpi=200, mode="vision").convert(out_pdf)
        norm_doc.source_path = file_path
        norm_doc.doc_name = doc_name
        norm_doc.metadata["format"] = "onenote"
        return norm_doc

