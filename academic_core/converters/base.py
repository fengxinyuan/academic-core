# -*- coding: utf-8 -*-
"""
格式归一化转换器基类与数据结构定义
无论输入是 .one, .docx, .pptx, .epub, .ipynb, .tex, 图片包还是 PDF，
转换器都将其解构为标准的 NormalizedDocument，供下游 OCR/LLM/导出器无缝消费。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod


@dataclass
class PageData:
    page_num: int
    image_bytes: Optional[bytes] = None  # 用于视觉/OCR 识别的标准图像数据 (PNG)
    text: Optional[str] = None           # 若原始文件为可直接提取的纯文本/结构化 Markdown


@dataclass
class NormalizedDocument:
    source_path: str
    doc_name: str
    pages: List[PageData] = field(default_factory=list)
    is_text_only: bool = False
    assets_dir: Optional[str] = None     # 文档关联的插图/媒体目录（供 PDF/HTML 导出无损解析）
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_pages(self) -> int:
        return len(self.pages)


class BaseConverter(ABC):
    @abstractmethod
    def can_convert(self, file_path: str) -> bool:
        pass

    @abstractmethod
    def convert(self, file_path: str) -> NormalizedDocument:
        pass
