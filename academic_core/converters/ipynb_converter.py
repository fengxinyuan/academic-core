# -*- coding: utf-8 -*-
"""
Jupyter Notebook (.ipynb) 归一化转换器：
计算机、应用数学与数据科学学术讲义的核心载体。
零依赖解析 JSON 结构，将 Markdown 单元格与代码/公式单元格结构化转为标准页面流。
"""

import os
import json
from academic_core.converters.base import BaseConverter, NormalizedDocument, PageData

class IPYNBConverter(BaseConverter):
    def can_convert(self, file_path: str) -> bool:
        return file_path.lower().endswith(".ipynb")

    def convert(self, file_path: str) -> NormalizedDocument:
        doc_name = os.path.splitext(os.path.basename(file_path))[0]

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                nb_data = json.load(f)
        except Exception as e:
            raise ValueError(f"Jupyter Notebook 解析失败: {e}")

        cells = nb_data.get("cells", [])
        blocks = []

        for c in cells:
            cell_type = c.get("cell_type", "")
            source_lines = c.get("source", [])
            source_text = "".join(source_lines) if isinstance(source_lines, list) else str(source_lines)

            if not source_text.strip():
                continue

            if cell_type == "markdown":
                blocks.append(source_text.strip())
            elif cell_type == "code":
                blocks.append(f"```python\n{source_text.strip()}\n```")
            elif cell_type == "raw":
                blocks.append(source_text.strip())

        full_text = "\n\n".join(blocks)
        if not full_text.strip():
            full_text = f"# {doc_name}\n\n(Notebook 单元格无有效文本内容)"

        return NormalizedDocument(
            source_path=file_path,
            doc_name=doc_name,
            pages=[PageData(page_num=1, text=full_text)],
            is_text_only=True,
            metadata={"format": "ipynb", "converter": "IPYNBConverter"}
        )
