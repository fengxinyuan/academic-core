# -*- coding: utf-8 -*-
from academic_core.converters.base import BaseConverter, NormalizedDocument, PageData
from academic_core.converters.auto_converter import convert_to_normalized, CONVERTERS
from academic_core.converters.pdf_converter import PDFConverter
from academic_core.converters.onenote_converter import OneNoteConverter
from academic_core.converters.image_converter import ImageConverter
from academic_core.converters.word_converter import WordConverter
from academic_core.converters.ppt_converter import PPTConverter
from academic_core.converters.ipynb_converter import IPYNBConverter
from academic_core.converters.epub_converter import EPUBConverter
from academic_core.converters.text_converter import TextConverter
from academic_core.converters.zip_converter import ZipConverter

__all__ = [
    "BaseConverter",
    "NormalizedDocument",
    "PageData",
    "convert_to_normalized",
    "CONVERTERS",
    "PDFConverter",
    "OneNoteConverter",
    "ImageConverter",
    "WordConverter",
    "PPTConverter",
    "IPYNBConverter",
    "EPUBConverter",
    "TextConverter",
    "ZipConverter",
]
