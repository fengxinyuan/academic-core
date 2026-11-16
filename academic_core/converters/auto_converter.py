# -*- coding: utf-8 -*-
"""
格式归一化转换器统一门面 (Auto Converter)
按优先级智能侦测并分发至对应转换器
"""

import os
from academic_core.converters.base import NormalizedDocument, BaseConverter
from academic_core.converters.zip_converter import ZipConverter
from academic_core.converters.pdf_converter import PDFConverter
from academic_core.converters.onenote_converter import OneNoteConverter
from academic_core.converters.word_converter import WordConverter
from academic_core.converters.ppt_converter import PPTConverter
from academic_core.converters.ipynb_converter import IPYNBConverter
from academic_core.converters.epub_converter import EPUBConverter
from academic_core.converters.text_converter import TextConverter
from academic_core.converters.image_converter import ImageConverter

# 转换器优先级列表
CONVERTERS: list[BaseConverter] = [
    ZipConverter(),       # 压缩包自解包 (zip, tar, tgz)
    PDFConverter(),       # PDF 矢量切片 / 原生文字直提
    OneNoteConverter(),   # OneNote 笔记 (.one)
    WordConverter(),      # Word 文档 (.docx, .doc)
    PPTConverter(),       # PowerPoint 课件 (.pptx, .ppt)
    IPYNBConverter(),     # Jupyter Notebook (.ipynb)
    EPUBConverter(),      # EPUB 电子书 (.epub)
    TextConverter(),      # 纯文本、Markdown、LaTeX 源码 (.tex), HTML
    ImageConverter(),     # 单张图片与手机连拍照片目录
]

def convert_to_normalized(file_or_dir_path: str, **kwargs) -> NormalizedDocument:
    """
    自动识别任意输入源，转换为标准的 NormalizedDocument
    """
    if not os.path.exists(file_or_dir_path):
        raise FileNotFoundError(f"输入路径不存在: {file_or_dir_path}")

    for conv in CONVERTERS:
        if conv.can_convert(file_or_dir_path):
            return conv.convert(file_or_dir_path)

    raise ValueError(f"暂不支持的文件格式类型: {file_or_dir_path}")
