# -*- coding: utf-8 -*-
"""
OpenAI Compatible 视觉大模型引擎
支持 GPT-4o, GPT-4o-mini, 以及本地部署的 vLLM / Ollama (Qwen2-VL, DeepSeek-VL 等)
"""

import os
import base64
import time
import requests
from academic_core.vision_ocr.base import BaseVisionEngine
from academic_core.config import OPENAI_API_KEY

class OpenAIVisionEngine(BaseVisionEngine):
    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: str = None,
        base_url: str = "https://api.openai.com/v1",
        cache_dir: str = "cache_ocr"
    ):
        super().__init__(cache_dir=cache_dir)
        self.model_name = model_name
        self.api_key = api_key or OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")

    def extract_page_latex(self, image_bytes: bytes, page_num: int = 1, total_pages: int = 1) -> str:
        cache_path = self._get_cache_path(image_bytes, self.model_name)
        cached = self._load_cache(cache_path)
        if cached:
            return cached

        if not self.api_key:
            raise ValueError("未配置 OpenAI API Key，请设置 OPENAI_API_KEY 或在构造函数中指定！")

        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        prompt = (
            f"You are an expert academic mathematical document OCR system. "
            f"This is page {page_num} of {total_pages}. "
            f"Accurately transcribe all mathematical definitions, theorems, formulas, matrices, "
            f"and explanations from this image into clean GitHub Flavored Markdown with KaTeX math syntax "
            f"($...$ for inline formulas, $$...$$ for block formulas). "
            f"Output raw markdown only, with no commentary."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_img}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.1
        }

        url = f"{self.base_url}/chat/completions"
        content = None
        for attempt in range(3):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=(15, 90))
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"].strip()
                    break
                elif resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(3 * (attempt + 1))
                else:
                    raise RuntimeError(f"OpenAI Vision API HTTP {resp.status_code}: {resp.text}")
            except requests.exceptions.RequestException as e:
                if attempt == 2:
                    raise e
                time.sleep(3 * (attempt + 1))

        if not content:
            raise RuntimeError(f"OpenAI Vision 提取失败: 第 {page_num} 页返回空内容")

        # 剥离代码围栏
        if content.startswith("```markdown"): content = content[11:].strip()
        elif content.startswith("```"): content = content[3:].strip()
        if content.endswith("```"): content = content[:-3].strip()

        cleaned = self._clean_repetitive_lines(content)
        self._save_cache(cache_path, cleaned)
        return cleaned

