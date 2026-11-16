# -*- coding: utf-8 -*-
"""
PDF 格式归一化转换器：
支持 Dual-Mode 双模式自适应：
1. 视觉切片模式 (vision): 适用于扫描件、手写板书 PDF，按指定 DPI 渲染高精度矢量图像流供视觉 OCR；
2. 纯数字文本模式 (text): 适用于已具备高质量矢量文字/排版的原生数字 PDF (如 arXiv 论文、LaTeX 生成物)；
3. 智能模式 (auto): 自动探测文字层丰度，有选中文本则零开销直取文本，扫描版则无缝转入视觉切片。
"""

import os
import pymupdf
from academic_core.converters.base import BaseConverter, NormalizedDocument, PageData

class PDFConverter(BaseConverter):
    def __init__(self, dpi: int = 200, mode: str = "auto"):
        self.dpi = dpi
        self.mode = mode.lower()  # "auto", "vision", "text"

    def can_convert(self, file_path: str) -> bool:
        return file_path.lower().endswith(".pdf")

    def convert(self, file_path: str) -> NormalizedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF 文件未找到: {file_path}")

        doc_name = os.path.splitext(os.path.basename(file_path))[0]
        doc = pymupdf.open(file_path)
        total_p = len(doc)

        # 智能判定模式
        use_text_mode = False
        if self.mode == "text":
            use_text_mode = True
        elif self.mode == "auto":
            # 抽样检测前 3 页文本丰度
            sample_count = min(3, total_p)
            total_sample_chars = 0
            for i in range(sample_count):
                total_sample_chars += len(doc[i].get_text().strip())
            avg_chars = total_sample_chars / max(1, sample_count)
            # 若每页平均文字超过 120 字符且有可提取文本层，则自动判定为原生数字 PDF
            if avg_chars >= 120:
                use_text_mode = True

        pages = []
        if use_text_mode:
            for i in range(total_p):
                page_text = doc[i].get_text()
                pages.append(PageData(page_num=i + 1, text=page_text))
            doc.close()
            return NormalizedDocument(
                source_path=file_path,
                doc_name=doc_name,
                pages=pages,
                is_text_only=True,
                metadata={"format": "pdf", "mode": "text", "total_pages": total_p}
            )
        else:
            for i in range(total_p):
                page = doc[i]
                pix = page.get_pixmap(dpi=self.dpi)
                pix_bytes = pix.tobytes("png")
                pages.append(PageData(page_num=i + 1, image_bytes=pix_bytes))
            doc.close()
            return NormalizedDocument(
                source_path=file_path,
                doc_name=doc_name,
                pages=pages,
                is_text_only=False,
                metadata={"format": "pdf", "mode": "vision", "dpi": self.dpi, "total_pages": total_p}
            )
