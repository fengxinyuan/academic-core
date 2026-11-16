# -*- coding: utf-8 -*-
"""
PowerPoint 幻灯片 (.pptx) 归一化转换器：
学术课程课件常见格式。支持按幻灯片分页提取文本、图表信息与备注。
支持 python-pptx 库及纯标准库 (zipfile + XML) 双引擎解析。
"""

import os
import re
import zipfile
import xml.etree.ElementTree as ET
from academic_core.converters.base import BaseConverter, NormalizedDocument, PageData

class PPTConverter(BaseConverter):
    SUPPORTED_EXTENSIONS = {".pptx", ".ppt"}

    def can_convert(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def _extract_via_python_pptx(self, file_path: str) -> list[PageData]:
        from pptx import Presentation
        prs = Presentation(file_path)
        pages = []
        for idx, slide in enumerate(prs.slides, start=1):
            slide_texts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        txt = "".join(run.text for run in paragraph.runs).strip()
                        if txt:
                            slide_texts.append(txt)
            # 备注
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                note_text = slide.notes_slide.notes_text_frame.text.strip()
                if note_text:
                    slide_texts.append(f"> 讲师备注: {note_text}")

            content = "\n\n".join(slide_texts)
            pages.append(PageData(page_num=idx, text=content))
        return pages

    def _extract_via_native_xml(self, file_path: str) -> list[PageData]:
        """
        零依赖纯标准库解析 .pptx
        """
        pages = []
        with zipfile.ZipFile(file_path) as z:
            slide_files = sorted(
                [f for f in z.namelist() if f.startswith("ppt/slides/slide") and f.endswith(".xml")],
                key=lambda x: int(re.search(r'slide(\d+)\.xml', x).group(1)) if re.search(r'slide(\d+)\.xml', x) else 0
            )
            ns = {
                'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
                'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'
            }
            for idx, sf in enumerate(slide_files, start=1):
                xml_content = z.read(sf)
                root = ET.fromstring(xml_content)
                paras = []
                for p in root.findall('.//a:p', ns):
                    texts = [t.text for t in p.findall('.//a:t', ns) if t.text]
                    if texts:
                        paras.append("".join(texts))
                content = "\n\n".join(paras)
                pages.append(PageData(page_num=idx, text=content))
        return pages

    def convert(self, file_path: str) -> NormalizedDocument:
        doc_name = os.path.splitext(os.path.basename(file_path))[0]
        pages = []

        try:
            pages = self._extract_via_python_pptx(file_path)
        except Exception:
            try:
                pages = self._extract_via_native_xml(file_path)
            except Exception as e:
                pages = [PageData(page_num=1, text=f"# {doc_name}\n\nPPT 解析异常: {str(e)}")]

        if not pages:
            pages = [PageData(page_num=1, text=f"# {doc_name}\n\n(幻灯片解析完成，无正文文字)")]

        return NormalizedDocument(
            source_path=file_path,
            doc_name=doc_name,
            pages=pages,
            is_text_only=True,
            metadata={"format": "pptx", "converter": "PPTConverter"}
        )

