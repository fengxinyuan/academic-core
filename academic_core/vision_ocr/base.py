# -*- coding: utf-8 -*-
"""
视觉识别与 OCR 引擎统一基类
只对标准页图像负责，不感知上游是 PDF、OneNote、PPT 还是手机翻拍照片。
提供统一的 MD5 页面级磁盘缓存与连续圈画重复行过滤算法。
"""

import os
import hashlib
from abc import ABC, abstractmethod
from typing import Optional

class BaseVisionEngine(ABC):
    def __init__(self, cache_dir: str = "cache_ocr"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_image_md5(self, image_bytes: bytes) -> str:
        return hashlib.md5(image_bytes).hexdigest()

    def _get_cache_path(self, image_bytes: bytes, model_name: str) -> str:
        h = self._get_image_md5(image_bytes)
        safe_model = model_name.replace("/", "_").replace(":", "_")
        return os.path.join(self.cache_dir, f"{safe_model}_{h}.md")

    def _load_cache(self, cache_path: str) -> Optional[str]:
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def _save_cache(self, cache_path: str, text: str):
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(text)

    def _clean_repetitive_lines(self, text: str) -> str:
        """
        手写板书/讲义圈画去重：过滤黑板反复圈画、多次描红导致的相邻连续完全重复行
        """
        lines = text.splitlines()
        clean = []
        prev = None
        for line in lines:
            s = line.strip()
            if s and s == prev and s != "---":
                continue
            clean.append(line)
            prev = s
        return "\n".join(clean)

    @abstractmethod
    def extract_page_latex(self, image_bytes: bytes, page_num: int = 1, total_pages: int = 1) -> str:
        """
        从单页标准图像提取 Markdown / LaTeX 内容
        """
        pass
