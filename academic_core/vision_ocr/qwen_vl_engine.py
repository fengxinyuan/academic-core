# -*- coding: utf-8 -*-
"""
Qwen-VL-OCR 引擎：专精手写墨迹、黑板推导与高密度数学公式
"""

import os
import time
import base64
import requests
import hashlib
from typing import Optional
from academic_core.vision_ocr.base import BaseVisionEngine
from academic_core.config import DASHSCOPE_API_KEY

class QwenVLEngine(BaseVisionEngine):
    def __init__(self, model_name: str = "qwen-vl-ocr", api_key: Optional[str] = None, cache_dir: str = "cache_ocr"):
        super().__init__(cache_dir=cache_dir)
        self.model_name = model_name
        self.api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.api_key = api_key or DASHSCOPE_API_KEY or os.environ.get("DASHSCOPE_API_KEY", "")

    def extract_page_latex(self, image_bytes: bytes, page_num: int = 1, total_pages: int = 1) -> str:
        img_hash = hashlib.md5(image_bytes).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"{img_hash}.md")

        if os.path.exists(cache_file) and os.path.getsize(cache_file) > 20:
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()

        if not self.api_key:
            raise ValueError("未配置 DASHSCOPE_API_KEY，无法调用云端视觉 OCR 接口！请在环境变量中设置或使用 mock 引擎。")

        b64_img = base64.b64encode(image_bytes).decode("utf-8")

        prompt = (
            f"你是一位精通高等代数、线性代数与大学数学推导的高级审稿专家。\n"
            f"当前正在识别一份学术讲义的第 {page_num} 页（共 {total_pages} 页）。\n\n"
            f"【核心任务要求】：\n"
            f"1. 高精度转写：将图片中的所有手写笔迹、推导公式、表格与文字完全提取为严谨的 GitHub 风格 Markdown。\n"
            f"2. 数学公式标准：所有单行独立公式使用标准 KaTeX 块级公式 `$$...$$`，行内符号严格使用 `$...$`。\n"
            f"3. 抵制幻觉：严禁凭空编造不存在的内容，保持论证符号的严密性与原作者思路一致。\n"
            f"4. 纯净输出：仅返回解析后的 Markdown 内容，严禁任何客套说明。"
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
            "temperature": 0.1
        }

        content = None
        for attempt in range(3):
            try:
                resp = requests.post(self.api_url, headers=headers, json=payload, timeout=(15, 90))
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"].strip()
                    break
                elif resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(3 * (attempt + 1))
                else:
                    raise RuntimeError(f"Qwen-VL HTTP {resp.status_code}: {resp.text}")
            except requests.exceptions.RequestException as e:
                if attempt == 2:
                    raise e
                time.sleep(3 * (attempt + 1))

        if not content:
            raise RuntimeError(f"第 {page_num} 页 Qwen-VL 提取内容为空！")

        # 剥离 Markdown 代码围栏
        if content.startswith("```markdown"): content = content[11:].strip()
        elif content.startswith("```"): content = content[3:].strip()
        if content.endswith("```"): content = content[:-3].strip()

        # 过滤连续圈画重复行
        clean_content = self._clean_repetitive_lines(content)

        # 写入缓存
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(clean_content)

        return clean_content
