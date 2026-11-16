# -*- coding: utf-8 -*-
"""
纯文本、Markdown、LaTeX 源码与 HTML 归一化转换器
支持多编码自动识别 (UTF-8, GB18030, GBK 等) 及 LaTeX 学术源码语法转译为标准 Markdown
"""

import os
import re
from academic_core.converters.base import BaseConverter, NormalizedDocument, PageData

class TextConverter(BaseConverter):
    SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".tex", ".html", ".htm"}

    def can_convert(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def _read_file_content(self, file_path: str) -> str:
        """
        多重编码自适应读取文本
        """
        encodings = ["utf-8-sig", "utf-8", "gb18030", "gbk", "latin1"]
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, LookupError):
                continue

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def _convert_latex_to_markdown(self, tex_content: str) -> str:
        """
        将 LaTeX 原始源码提取为干净的学术 Markdown，保留数学公式
        """
        text = tex_content

        # 1. 提取文档标题
        title_match = re.search(r'\\title\{([^}]+)\}', text)
        doc_title = title_match.group(1).strip() if title_match else ""

        # 2. 剥离导言区 (Preamble)
        if r"\begin{document}" in text:
            text = text.split(r"\begin{document}", 1)[1]
        if r"\end{document}" in text:
            text = text.split(r"\end{document}", 1)[0]

        # 3. 剥离行内注释 %
        text = re.sub(r'(?<!\\)%.*$', '', text, flags=re.MULTILINE)

        # 4. 转换章节标题
        text = re.sub(r'\\section\*?\{([^}]+)\}', r'# \1', text)
        text = re.sub(r'\\subsection\*?\{([^}]+)\}', r'## \1', text)
        text = re.sub(r'\\subsubsection\*?\{([^}]+)\}', r'### \1', text)

        # 5. 转换摘要 Abstract
        text = re.sub(r'\\begin\{abstract\}([\s\S]*?)\\end\{abstract\}', r'> **摘要**：\1\n', text)

        # 6. 标准化数学环境
        # \begin{equation} -> $$
        text = re.sub(r'\\begin\{(?:equation|displaymath)\*?\}([\s\S]*?)\\end\{(?:equation|displaymath)\*?\}', r'$$\n\1\n$$', text)
        # \begin{align} -> \begin{aligned} 供 KaTeX 渲染
        text = re.sub(r'\\begin\{align\*?\}([\s\S]*?)\\end\{align\*?\}', r'$$\n\\begin{aligned}\1\\end{aligned}\n$$', text)

        # 7. 转换常见粗体斜体
        text = re.sub(r'\\textbf\{([^}]+)\}', r'**\1**', text)
        text = re.sub(r'\\textit\{([^}]+)\}', r'*\1*', text)
        text = re.sub(r'\\emph\{([^}]+)\}', r'*\1*', text)

        # 8. 规范换行
        text = re.sub(r'\n{3,}', '\n\n', text).strip()

        if doc_title and not text.startswith("#"):
            text = f"# {doc_title}\n\n" + text

        return text

    def convert(self, file_path: str) -> NormalizedDocument:
        ext = os.path.splitext(file_path)[1].lower()
        doc_name = os.path.splitext(os.path.basename(file_path))[0]
        raw_text = self._read_file_content(file_path)

        if ext == ".tex":
            converted_text = self._convert_latex_to_markdown(raw_text)
        elif ext in (".html", ".htm"):
            # 基础 HTML 标签清洗
            converted_text = re.sub(r'<[^>]+>', '', raw_text)
        else:
            converted_text = raw_text

        return NormalizedDocument(
            source_path=file_path,
            doc_name=doc_name,
            pages=[PageData(page_num=1, text=converted_text)],
            is_text_only=True,
            metadata={"format": ext, "source_type": "text"}
        )

