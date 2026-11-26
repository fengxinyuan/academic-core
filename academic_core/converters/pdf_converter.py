# -*- coding: utf-8 -*-
"""
PDF 格式归一化转换器：
支持四模式精准适配不同学术 PDF：
1. vision (推荐用于手写、数学密集扫描件/混合批注 PDF): 高精度矢量渲染 PNG 图像流供视觉 OCR；
2. mineru (推荐用于英文双栏学术论文、带图表教材): 调用 MinerU 云端整文档解析，保留双栏顺序、公式、表格与全部插图；
3. text (适用于纯文字数字 PDF): 零开销直接通过 PyMuPDF 提取文本层；
4. auto: 若配置了 MINERU_TOKEN 自动走 mineru；否则无文字层或高比例图像走 vision，纯文本走 text。
"""

import os
import pymupdf
from academic_core.config import MINERU_TOKEN
from academic_core.converters.base import BaseConverter, NormalizedDocument, PageData


class PDFConverter(BaseConverter):
    def __init__(self, dpi: int = 200, mode: str = "vision", mineru_cache_dir: str = "cache_mineru"):
        self.dpi = dpi
        self.mode = mode.lower()
        self.mineru_cache_dir = mineru_cache_dir

    def can_convert(self, file_path: str) -> bool:
        return file_path.lower().endswith(".pdf")

    def _convert_via_mineru(self, file_path: str, doc_name: str) -> NormalizedDocument:
        from academic_core.vision_ocr.mineru_engine import MinerUEngine
        engine = MinerUEngine(cache_dir=self.mineru_cache_dir)
        md_text, extracted_dir = engine.extract_pdf_document(file_path, include_page_markers=False)
        return NormalizedDocument(
            source_path=file_path,
            doc_name=doc_name,
            pages=[PageData(page_num=1, text=md_text)],
            is_text_only=True,
            assets_dir=extracted_dir,
            metadata={"format": "pdf", "mode": "mineru"},
        )

    def convert(self, file_path: str) -> NormalizedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF 文件未找到: {file_path}")

        doc_name = os.path.splitext(os.path.basename(file_path))[0]
        resolved_mode = self.mode

        if resolved_mode == "auto":
            if MINERU_TOKEN or os.environ.get("MINERU_TOKEN"):
                resolved_mode = "mineru"
            else:
                with pymupdf.open(file_path) as doc:
                    total_p = len(doc)
                    sample_count = min(3, total_p)
                    total_chars = sum(len(doc[i].get_text().strip()) for i in range(sample_count))
                    total_imgs = sum(len(doc[i].get_images()) for i in range(sample_count))
                avg_chars = total_chars / max(1, sample_count)
                # 仅当文字丰度高且几乎没有扫描底图时采用纯文本直提，防止丢失公式/手写墨迹
                resolved_mode = "text" if (avg_chars >= 200 and total_imgs == 0) else "vision"

        if resolved_mode == "mineru":
            return self._convert_via_mineru(file_path, doc_name)

        pages = []
        with pymupdf.open(file_path) as doc:
            total_p = len(doc)
            if resolved_mode == "text":
                for i in range(total_p):
                    pages.append(PageData(page_num=i + 1, text=doc[i].get_text()))
                return NormalizedDocument(
                    source_path=file_path,
                    doc_name=doc_name,
                    pages=pages,
                    is_text_only=True,
                    metadata={"format": "pdf", "mode": "text", "total_pages": total_p},
                )

            # 默认 vision 切片模式
            for i in range(total_p):
                pix = doc[i].get_pixmap(dpi=self.dpi)
                pages.append(PageData(page_num=i + 1, image_bytes=pix.tobytes("png")))

        return NormalizedDocument(
            source_path=file_path,
            doc_name=doc_name,
            pages=pages,
            is_text_only=False,
            metadata={"format": "pdf", "mode": "vision", "dpi": self.dpi, "total_pages": total_p},
        )
