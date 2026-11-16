# -*- coding: utf-8 -*-
"""
图像与黑板连拍包归一化转换器：
将单张或多张黑板照片、手机课本翻拍 (.jpg, .png, .jpeg, .webp, .bmp) 归一化为标准页流。
支持 EXIF 重力感应自动正立旋转，及黑板字迹弱对比度自动增强 (Autocontrast / Contrast boost)。
"""

import os
import glob
import io
import re
from typing import List, Union
from PIL import Image, ImageOps, ImageEnhance
from academic_core.converters.base import BaseConverter, NormalizedDocument, PageData

SUPPORTED_IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")

def _normalize_image_bytes(data: bytes, enhance: bool = False) -> bytes:
    """自动矫正手机拍照 EXIF 旋转角度，可选黑板字迹对比度拉伸"""
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)

        # 针对手机微距/黑板粉笔/铅笔浅淡字迹进行自动对比度增强
        if enhance:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img = ImageOps.autocontrast(img, cutoff=1)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return data

class ImageConverter(BaseConverter):
    def __init__(self, auto_enhance: bool = False):
        self.auto_enhance = auto_enhance

    def can_convert(self, file_path: str) -> bool:
        if os.path.isdir(file_path):
            return True
        return os.path.splitext(file_path)[1].lower() in SUPPORTED_IMG_EXTS

    def convert(self, file_or_dir: str) -> NormalizedDocument:
        if os.path.isdir(file_or_dir):
            # 目录：按文件名自然数字排序打包所有图片
            doc_name = os.path.basename(os.path.abspath(file_or_dir))
            all_imgs = []
            for ext in SUPPORTED_IMG_EXTS:
                all_imgs.extend(glob.glob(os.path.join(file_or_dir, f"*{ext}")))
                all_imgs.extend(glob.glob(os.path.join(file_or_dir, f"*{ext.upper()}")))
            # 自然排序 (e.g. 1.jpg, 2.jpg, 10.jpg)
            def _nat_key(s):
                return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
            all_imgs = sorted(list(set(all_imgs)), key=_nat_key)

            if not all_imgs:
                raise ValueError(f"目录中未找到支持的图片文件: {file_or_dir}")

            pages = []
            for idx, img_p in enumerate(all_imgs):
                with open(img_p, "rb") as f:
                    raw_b = f.read()
                pages.append(PageData(page_num=idx + 1, image_bytes=_normalize_image_bytes(raw_b, self.auto_enhance)))

            return NormalizedDocument(
                source_path=file_or_dir,
                doc_name=doc_name,
                pages=pages,
                is_text_only=False,
                metadata={"format": "image_folder", "count": len(pages)}
            )
        else:
            # 单张图片
            doc_name = os.path.splitext(os.path.basename(file_or_dir))[0]
            with open(file_or_dir, "rb") as f:
                data = f.read()
            norm_b = _normalize_image_bytes(data, self.auto_enhance)
            return NormalizedDocument(
                source_path=file_or_dir,
                doc_name=doc_name,
                pages=[PageData(page_num=1, image_bytes=norm_b)],
                is_text_only=False,
                metadata={"format": "single_image"}
            )
