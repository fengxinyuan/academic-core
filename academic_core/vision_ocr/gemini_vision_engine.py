# -*- coding: utf-8 -*-
"""
Google Gemini 视觉模型引擎
支持 gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash 等高精数学视觉提取
"""

import os
import base64
import time
import requests
from academic_core.vision_ocr.base import BaseVisionEngine

class GeminiVisionEngine(BaseVisionEngine):
    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",
        api_key: str = None,
        cache_dir: str = "cache_ocr"
    ):
        super().__init__(cache_dir=cache_dir)
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

    def extract_page_latex(self, image_bytes: bytes, page_num: int = 1, total_pages: int = 1) -> str:
        cache_path = self._get_cache_path(image_bytes, self.model_name)
        cached = self._load_cache(cache_path)
        if cached:
            return cached

        if not self.api_key:
            raise ValueError("未配置 GEMINI_API_KEY，请在环境变量或参数中设置！")

        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        prompt = (
            f"You are an expert academic mathematical document OCR system. "
            f"Accurately transcribe all mathematical formulas, theorems, matrices, and text "
            f"from this page into standard Markdown with KaTeX math syntax ($...$ and $$...$$). "
            f"Output raw markdown only."
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": b64_img
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.1
            }
        }

        content = None
        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, timeout=(15, 90))
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            content = parts[0].get("text", "").strip()
                            break
                elif resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(3 * (attempt + 1))
                else:
                    raise RuntimeError(f"Gemini API HTTP {resp.status_code}: {resp.text}")
            except requests.exceptions.RequestException as e:
                if attempt == 2:
                    raise e
                time.sleep(3 * (attempt + 1))

        if not content:
            raise RuntimeError(f"Gemini 视觉模型提取失败: 第 {page_num} 页无内容")

        # 剥离代码围栏
        if content.startswith("```markdown"): content = content[11:].strip()
        elif content.startswith("```"): content = content[3:].strip()
        if content.endswith("```"): content = content[:-3].strip()

        cleaned = self._clean_repetitive_lines(content)
        self._save_cache(cache_path, cleaned)
        return cleaned

