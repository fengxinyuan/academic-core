# -*- coding: utf-8 -*-
"""
Word 文档 (.docx) 归一化转换器：
支持 python-docx 库及纯标准库 (zipfile + XML) 双引擎自愈解析。
直接提取结构化段落、表格与公式，标记为 is_text_only=True（下游可跳过昂贵的视觉 OCR）。
"""

import os
import zipfile
import xml.etree.ElementTree as ET
from academic_core.converters.base import BaseConverter, NormalizedDocument, PageData

class WordConverter(BaseConverter):
    SUPPORTED_EXTENSIONS = {".docx", ".doc"}

    def can_convert(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def _extract_via_python_docx(self, file_path: str) -> str:
        import docx
        doc = docx.Document(file_path)
        blocks = []
        for p in doc.paragraphs:
            if p.text.strip():
                blocks.append(p.text)
        for t in doc.tables:
            for r in t.rows:
                blocks.append(" | ".join(c.text.strip() for c in r.cells))
        return "\n\n".join(blocks)

    def _extract_via_native_xml(self, file_path: str) -> str:
        """
        零依赖纯标准库解析 .docx (ZIP + XML)
        """
        try:
            with zipfile.ZipFile(file_path) as z:
                if "word/document.xml" not in z.namelist():
                    return ""
                xml_content = z.read("word/document.xml")
                root = ET.fromstring(xml_content)
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                paras = []
                for p in root.findall('.//w:p', ns):
                    texts = [t.text for t in p.findall('.//w:t', ns) if t.text]
                    if texts:
                        paras.append("".join(texts))
                return "\n\n".join(paras)
        except Exception as e:
            return f"DOCX 提取警告: {str(e)}"

    def convert(self, file_path: str) -> NormalizedDocument:
        doc_name = os.path.splitext(os.path.basename(file_path))[0]

        extracted_text = ""
        try:
            extracted_text = self._extract_via_python_docx(file_path)
        except Exception:
            extracted_text = self._extract_via_native_xml(file_path)

        if not extracted_text.strip():
            extracted_text = f"# {doc_name}\n\n(Word 文档已解析，正文内容为空)"

        return NormalizedDocument(
            source_path=file_path,
            doc_name=doc_name,
            pages=[PageData(page_num=1, text=extracted_text)],
            is_text_only=True,
            metadata={"format": "docx", "converter": "WordConverter"}
        )
