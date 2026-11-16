# -*- coding: utf-8 -*-
"""
academic_core: 解耦型通用学术文献数字化、语义自愈与全格式出版引擎
"""

from academic_core.pipeline import AcademicPipeline
from academic_core.converters import convert_to_normalized, BaseConverter, NormalizedDocument, PageData
from academic_core.vision_ocr import get_vision_engine, BaseVisionEngine
from academic_core.llm_reasoning import AcademicLLMEngine
from academic_core.math_enhancer import LatexCleaner
from academic_core.exporters import ChromePDFPrinter, HTMLExporter, MarkdownExporter, get_exporter
from academic_core.monograph import MonographBinder
from academic_core.checkpoint import TaskTracker
from academic_core.registry import CONVERTER_REGISTRY, VISION_ENGINE_REGISTRY, EXPORTER_REGISTRY

__version__ = "2.0.0"
__all__ = [
    "AcademicPipeline",
    "convert_to_normalized",
    "BaseConverter",
    "NormalizedDocument",
    "PageData",
    "get_vision_engine",
    "BaseVisionEngine",
    "AcademicLLMEngine",
    "LatexCleaner",
    "ChromePDFPrinter",
    "HTMLExporter",
    "MarkdownExporter",
    "get_exporter",
    "MonographBinder",
    "TaskTracker",
    "CONVERTER_REGISTRY",
    "VISION_ENGINE_REGISTRY",
    "EXPORTER_REGISTRY",
]
