# -*- coding: utf-8 -*-
"""
规范化 Markdown 导出器 (MarkdownExporter)
输出包含 YAML Frontmatter 元数据、标准 KaTeX 公式、适配 Obsidian/Typora/GitHub 的纯净文档。
"""

import os
import datetime
import re

class MarkdownExporter:
    def export(
        self,
        markdown_text: str,
        output_path: str,
        title: str = "",
        metadata: dict = None
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        if not title:
            title_m = re.search(r'^#\s+(.+)$', markdown_text, flags=re.MULTILINE)
            title = title_m.group(1).strip() if title_m else os.path.splitext(os.path.basename(output_path))[0]

        meta_dict = metadata or {}
        yaml_lines = [
            "---",
            f"title: \"{title}\"",
            f"date: \"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\"",
        ]
        for k, v in meta_dict.items():
            yaml_lines.append(f"{k}: \"{v}\"")
        yaml_lines.append("---\n\n")

        # 若原内容未带 frontmatter 则拼合
        full_text = markdown_text
        if not full_text.startswith("---"):
            full_text = "\n".join(yaml_lines) + full_text

        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write(full_text)

        return output_path

