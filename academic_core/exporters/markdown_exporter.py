# -*- coding: utf-8 -*-
"""
规范化 Markdown 导出器 (MarkdownExporter)
输出包含 YAML Frontmatter 元数据、标准 KaTeX 公式、自动伴随迁移插图目录，适配 Obsidian/Typora/GitHub。
"""

import os
import re
import shutil
import datetime
from typing import Optional


class MarkdownExporter:
    def export(
        self,
        markdown_text: str,
        output_path: str,
        title: str = "",
        metadata: Optional[dict] = None,
        assets_dir: Optional[str] = None,
    ) -> str:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(out_dir, exist_ok=True)

        if not title:
            title_m = re.search(r'^#\s+(.+)$', markdown_text, flags=re.MULTILINE)
            title = title_m.group(1).strip() if title_m else os.path.splitext(os.path.basename(output_path))[0]

        meta_dict = metadata or {}
        yaml_lines = [
            "---",
            f'title: "{title}"',
            f'date: "{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"',
        ]
        for k, v in meta_dict.items():
            yaml_lines.append(f'{k}: "{v}"')
        yaml_lines.append("---\n\n")

        full_text = markdown_text
        if not full_text.startswith("---"):
            full_text = "\n".join(yaml_lines) + full_text

        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write(full_text)

        # 若文档关联了插图目录 (如 MinerU 裁剪出的 images/)，同步复制到输出目录旁以保证 Markdown 编辑器可读
        if assets_dir:
            src_imgs = os.path.join(assets_dir, "images")
            if os.path.isdir(src_imgs):
                dst_imgs = os.path.join(out_dir, "images")
                os.makedirs(dst_imgs, exist_ok=True)
                for fn in os.listdir(src_imgs):
                    sp = os.path.join(src_imgs, fn)
                    dp = os.path.join(dst_imgs, fn)
                    if os.path.isfile(sp) and not os.path.exists(dp):
                        try:
                            shutil.copy2(sp, dp)
                        except Exception:
                            pass

        return output_path
