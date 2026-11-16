# -*- coding: utf-8 -*-
"""
压缩包归一化转换器 (ArchiveConverter)：
自动解包 .zip, .tar, .tar.gz, .tgz 等常见学术资源包（黑板照片连拍包、多讲讲义包），
按自然顺序智能组装为统一的 NormalizedDocument。
"""

import os
import zipfile
import tarfile
import tempfile
import shutil
import re
from academic_core.converters.base import BaseConverter, NormalizedDocument, PageData
from academic_core.converters.image_converter import ImageConverter
from academic_core.converters.pdf_converter import PDFConverter

class ZipConverter(BaseConverter):
    SUPPORTED_EXTS = (".zip", ".tar", ".gz", ".tgz", ".bz2")

    def can_convert(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.SUPPORTED_EXTS or file_path.lower().endswith((".tar.gz", ".tar.bz2"))

    def convert(self, file_path: str) -> NormalizedDocument:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"压缩包未找到: {file_path}")

        doc_name = os.path.splitext(os.path.basename(file_path))[0]
        if doc_name.lower().endswith(".tar"):
            doc_name = os.path.splitext(doc_name)[0]

        temp_extract_dir = tempfile.mkdtemp(prefix="academic_archive_")

        try:
            if file_path.lower().endswith(".zip"):
                with zipfile.ZipFile(file_path, "r") as zf:
                    zf.extractall(temp_extract_dir)
            else:
                with tarfile.open(file_path, "r:*") as tf:
                    tf.extractall(temp_extract_dir)

            # 收集解压出的所有文件
            all_files = []
            for root, _, files in os.walk(temp_extract_dir):
                for f in files:
                    if not f.startswith(".") and not f.startswith("__"):
                        all_files.append(os.path.join(root, f))

            def _nat_key(s):
                return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]
            all_files.sort(key=_nat_key)

            # 1. 优先检查是否包含图片包
            img_conv = ImageConverter()
            img_files = [f for f in all_files if img_conv.can_convert(f)]
            if len(img_files) > 0:
                pages = []
                for idx, img_p in enumerate(img_files):
                    with open(img_p, "rb") as fp:
                        data = fp.read()
                    from academic_core.converters.image_converter import _normalize_image_bytes
                    pages.append(PageData(page_num=idx + 1, image_bytes=_normalize_image_bytes(data)))

                return NormalizedDocument(
                    source_path=file_path,
                    doc_name=doc_name,
                    pages=pages,
                    is_text_only=False,
                    metadata={"format": "archive_images", "extracted_count": len(pages)}
                )

            # 2. 检查是否包含 PDF
            pdf_files = [f for f in all_files if f.lower().endswith(".pdf")]
            if pdf_files:
                return PDFConverter().convert(pdf_files[0])

            # 3. 检查是否包含 Markdown / 文本 / LaTeX / Word
            from academic_core.converters.text_converter import TextConverter
            txt_conv = TextConverter()
            text_files = [f for f in all_files if txt_conv.can_convert(f)]
            if text_files:
                combined_texts = []
                for tf in text_files:
                    norm = txt_conv.convert(tf)
                    combined_texts.append(norm.pages[0].text or "")
                return NormalizedDocument(
                    source_path=file_path,
                    doc_name=doc_name,
                    pages=[PageData(page_num=1, text="\n\n---\n\n".join(combined_texts))],
                    is_text_only=True,
                    metadata={"format": "archive_texts"}
                )

            raise ValueError(f"压缩包内未检测到支持的图像、PDF 或文档内容: {file_path}")

        finally:
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
