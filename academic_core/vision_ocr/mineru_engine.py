# -*- coding: utf-8 -*-
"""
MinerU (OpenDataLab) 官方云端文档解析引擎驱动 (Cloud API v4)
专为复杂学术论文与长篇专著设计：
- 原生恢复双栏/多栏自然阅读流
- 高精度提取复杂数学公式、表格
- 自动裁剪并保留文中的几何插图、实验图表 (images/*.jpg)
"""

import os
import glob
import json
import time
import zipfile
import hashlib
import logging
import requests
from typing import Tuple, Dict, Optional, Callable

from academic_core.config import MINERU_TOKEN
from academic_core.math_enhancer.sentinel import formula_fingerprint
from academic_core.vision_ocr.base import BaseVisionEngine

logger = logging.getLogger("academic_core.mineru")

MINERU_API_BASE = "https://mineru.net/api/v4"
MINERU_POLL_TIMEOUT = int(os.getenv("MINERU_POLL_TIMEOUT", "1800"))


class MinerUClient:
    """
    MinerU 官方 OpenAPI v4 客户端，支持整篇 PDF 云端解析与本地缓存复用
    """
    def __init__(self, token: Optional[str] = None):
        self.token = token or MINERU_TOKEN or os.environ.get("MINERU_TOKEN", "")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def extract_pdf(
        self,
        pdf_path: str,
        output_dir: str,
        log_cb: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        调用 MinerU 提取 PDF 内容并解压到 output_dir。
        若 output_dir 下已存在解析好的 content_list.json，则自动跳过上传直接复用缓存。
        """
        os.makedirs(output_dir, exist_ok=True)
        pdf_name = os.path.basename(pdf_path)

        def _log(msg: str):
            if log_cb:
                log_cb(msg)
            else:
                logger.info(f"[MinerU] {msg}")

        existing_lists = glob.glob(os.path.join(output_dir, "*content_list*.json"))
        if existing_lists:
            _log(f"命中 MinerU 本地缓存: {existing_lists[0]}，直接复用。")
            return output_dir

        if not self.token:
            raise ValueError("未检测到 MINERU_TOKEN，请在 .env 或环境变量中配置 MinerU API 密钥！")

        _log(f"正在向 MinerU 申请上传凭证: {pdf_name} ...")
        batch_url = f"{MINERU_API_BASE}/file-urls/batch"
        resp = requests.post(batch_url, headers=self.headers, json={"files": [{"name": pdf_name}]}, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"请求 MinerU 上传凭证失败 (HTTP {resp.status_code}): {resp.text}")

        res_json = resp.json()
        if res_json.get("code") != 0:
            raise RuntimeError(f"MinerU 业务错误: {res_json.get('msg', res_json)}")

        batch_id = res_json["data"]["batch_id"]
        file_urls = res_json["data"].get("file_urls", [])
        if not file_urls:
            raise RuntimeError(f"MinerU 返回的上传链接为空: {res_json}")

        first_url = file_urls[0]
        upload_url = first_url if isinstance(first_url, str) else first_url.get("upload_url", first_url.get("url"))

        _log(f"正在上传 PDF 文件流 ({os.path.getsize(pdf_path) / 1024 / 1024:.2f} MB)...")
        with open(pdf_path, "rb") as f:
            put_resp = requests.put(upload_url, data=f, timeout=180)
            if put_resp.status_code not in (200, 201):
                raise RuntimeError(f"上传 PDF 至 MinerU 存储桶失败 (HTTP {put_resp.status_code}): {put_resp.text}")

        _log("上传成功，等待 MinerU 版面分析与公式/图表提取...")
        query_url = f"{MINERU_API_BASE}/extract-results/batch/{batch_id}"
        poll_start = time.time()
        poll_count = 0

        while True:
            if time.time() - poll_start > MINERU_POLL_TIMEOUT:
                raise RuntimeError(f"MinerU 解析超时（超过 {MINERU_POLL_TIMEOUT} 秒）。")

            time.sleep(4)
            poll_count += 1
            q_resp = requests.get(query_url, headers=self.headers, timeout=30)
            if q_resp.status_code != 200:
                continue

            q_data = q_resp.json()
            extract_result = q_data.get("data", {}).get("extract_result", [])
            if not extract_result:
                continue

            item = extract_result[0]
            state = item.get("state")
            if poll_count % 3 == 0:
                _log(f"解析任务状态: {state} ...")

            if state == "done":
                zip_url = item.get("full_zip_url")
                if not zip_url:
                    raise RuntimeError("MinerU 提取完成但未返回 zip 下载地址！")
                _log("解析完成，正在下载并解压结构化成果包...")
                zip_path = os.path.join(output_dir, "result.zip")
                r_zip = requests.get(zip_url, timeout=180)
                with open(zip_path, "wb") as zf:
                    zf.write(r_zip.content)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(output_dir)
                _log(f"解压就绪: {output_dir}")
                return output_dir
            elif state in ("failed", "error"):
                raise RuntimeError(f"MinerU 提取失败: {item.get('err_msg', '未知错误')}")


def assemble_mineru_markdown(
    extracted_dir: str,
    start_page: int = 1,
    include_page_markers: bool = False,
) -> Tuple[str, Dict[str, str]]:
    """
    基于 MinerU 输出的 content_list.json 结构化数据，
    按自然阅读流装配双栏正文、公式、表格与插图路径。
    返回: (assembled_markdown, equation_image_map)
    """
    cl_files = glob.glob(os.path.join(extracted_dir, "*content_list*.json"))
    eq_img_map: Dict[str, str] = {}

    if not cl_files:
        full_md_path = os.path.join(extracted_dir, "full.md")
        if os.path.exists(full_md_path):
            with open(full_md_path, "r", encoding="utf-8") as f:
                return f.read(), eq_img_map
        return "", eq_img_map

    # 优先选择不带 _v2 的标准 content_list.json（若只有 v2 则兼容使用）
    cl_files.sort(key=lambda p: ("_v2" in os.path.basename(p), len(p)))
    with open(cl_files[0], "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        full_md_path = os.path.join(extracted_dir, "full.md")
        if os.path.exists(full_md_path):
            with open(full_md_path, "r", encoding="utf-8") as f:
                return f.read(), eq_img_map
        return "", eq_img_map

    page_num_map: Dict[int, str] = {}
    for b in data:
        if isinstance(b, dict) and b.get("type") == "page_number" and b.get("text"):
            page_num_map[b.get("page_idx")] = b.get("text").strip()

    pieces = []
    current_page_idx = -1

    for b in data:
        if not isinstance(b, dict):
            continue
        p_idx = b.get("page_idx", -1)
        b_type = b.get("type", "")

        if include_page_markers and p_idx != current_page_idx and p_idx >= 0:
            current_page_idx = p_idx
            disp_page = page_num_map.get(p_idx, str(start_page + p_idx))
            pieces.append(f'\n\n<div class="page-marker" id="page-{disp_page}"><span>── 第 {disp_page} 页 ──</span></div>\n\n')

        if b_type in ("header", "footer", "page_number", "page_footnote"):
            continue

        if b_type == "text":
            level = b.get("text_level", 0)
            text = b.get("text", "").strip()
            if text:
                if level and level in (1, 2, 3, 4, 5):
                    pieces.append(f"\n\n{'#' * level} {text}\n\n")
                else:
                    pieces.append(f"\n\n{text}\n\n")

        elif b_type == "equation":
            text = b.get("text", "").strip()
            img_path = b.get("img_path", "")
            if text:
                fp = formula_fingerprint(text)
                if fp and img_path:
                    eq_img_map[fp] = os.path.join("images", os.path.basename(img_path)).replace("\\", "/")
                pieces.append(f"\n\n$$\n{text}\n$$\n\n")

        elif b_type in ("image", "chart"):
            img_path = b.get("img_path", "")
            caption_raw = (
                b.get("image_caption")
                or b.get("chart_caption")
                or b.get("image_title")
                or b.get("caption")
                or ""
            )
            caption = " ".join(caption_raw) if isinstance(caption_raw, list) else str(caption_raw)
            caption = caption.strip()
            if img_path:
                rel_img = os.path.join("images", os.path.basename(img_path)).replace("\\", "/")
                pieces.append(f"\n\n![{caption}]({rel_img})\n\n")

        elif b_type == "table":
            table_body = (b.get("table_body", "") or b.get("text", "")).strip()
            img_path = b.get("img_path", "")
            caption_raw = b.get("table_caption") or ""
            caption = " ".join(caption_raw) if isinstance(caption_raw, list) else str(caption_raw)
            if caption.strip():
                pieces.append(f"\n\n*{caption.strip()}*\n\n")
            if table_body:
                pieces.append(f"\n\n{table_body}\n\n")
            elif img_path:
                rel_img = os.path.join("images", os.path.basename(img_path)).replace("\\", "/")
                pieces.append(f"\n\n![{caption.strip()}]({rel_img})\n\n")

        elif b_type == "code":
            code_body = (b.get("code_body", "") or b.get("text", "")).strip()
            caption_raw = b.get("code_caption") or ""
            caption = " ".join(caption_raw) if isinstance(caption_raw, list) else str(caption_raw)
            if caption.strip():
                pieces.append(f"\n\n**{caption.strip()}**\n\n")
            if code_body:
                if not code_body.startswith("```"):
                    code_body = f"```\n{code_body}\n```"
                pieces.append(f"\n\n{code_body}\n\n")

        elif b_type == "list":
            items = b.get("list_items") or []
            if items:
                formatted = "\n".join(f"- {str(it).strip()}" for it in items if str(it).strip())
                if formatted:
                    pieces.append(f"\n\n{formatted}\n\n")

    return "".join(pieces).strip(), eq_img_map


class MinerUEngine(BaseVisionEngine):
    """
    MinerU 引擎统一封装：
    - 整篇 PDF 推荐使用 extract_pdf_document()，直接保留双栏阅读流、表格与全部插图；
    - 单页图像调用 extract_page_latex() 时，将单图封装为单页 PDF 上传或回退到视觉大模型。
    """
    def __init__(self, token: Optional[str] = None, cache_dir: str = "cache_mineru"):
        super().__init__(cache_dir=cache_dir)
        self.token = token or MINERU_TOKEN or os.environ.get("MINERU_TOKEN", "")
        self.client = MinerUClient(token=self.token)

    def extract_pdf_document(self, pdf_path: str, include_page_markers: bool = False) -> Tuple[str, str]:
        """
        整文档解析接口：返回 (structured_markdown, extracted_assets_dir)
        """
        with open(pdf_path, "rb") as f:
            pdf_hash = hashlib.md5(f.read()).hexdigest()[:12]
        doc_name = os.path.splitext(os.path.basename(pdf_path))[0]
        out_dir = os.path.join(self.cache_dir, f"{doc_name}_{pdf_hash}")

        extracted_dir = self.client.extract_pdf(pdf_path, out_dir)
        md_text, _ = assemble_mineru_markdown(extracted_dir, include_page_markers=include_page_markers)
        return md_text, extracted_dir

    def extract_page_latex(self, image_bytes: bytes, page_num: int = 1, total_pages: int = 1) -> str:
        cache_path = self._get_cache_path(image_bytes, "mineru")
        cached = self._load_cache(cache_path)
        if cached:
            return cached

        if self.token:
            import tempfile
            import pymupdf

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_pdf = os.path.join(tmpdir, f"page_{page_num}.pdf")
                doc = pymupdf.open()
                img_doc = pymupdf.open("png", image_bytes)
                rect = img_doc[0].rect
                page = doc.new_page(width=rect.width, height=rect.height)
                page.insert_image(rect, stream=image_bytes)
                doc.save(tmp_pdf)
                doc.close()
                img_doc.close()

                md_text, _ = self.extract_pdf_document(tmp_pdf, include_page_markers=False)
                cleaned = self._clean_repetitive_lines(md_text)
                self._save_cache(cache_path, cleaned)
                return cleaned

        from academic_core.vision_ocr.qwen_vl_engine import QwenVLEngine
        return QwenVLEngine(cache_dir=self.cache_dir).extract_page_latex(image_bytes, page_num, total_pages)
