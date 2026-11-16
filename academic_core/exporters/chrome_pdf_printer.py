# -*- coding: utf-8 -*-
"""
无头 Chrome 矢量 PDF 打印引擎 (Headless Chrome Vector PDF Printer)
基于无头 Chrome / Edge 实现出版级精准分页、KaTeX 矢量公式渲染与防截断处理。
"""

import os
import tempfile
import subprocess
from academic_core.config import find_chrome_executable
from academic_core.exporters.templates import build_html_template

class ChromePDFPrinter:
    def __init__(self, browser_executable: str = ""):
        self.browser = browser_executable or find_chrome_executable()
        if not self.browser:
            raise RuntimeError("未检测到 Chrome 或 Edge 浏览器可执行程序！")

    def print_markdown(
        self,
        markdown_text: str,
        output_pdf_path: str,
        title: str = "Academic Document",
        show_page_numbers: bool = True
    ) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        html = build_html_template(markdown_text, title=title)
        temp_html = output_pdf_path + ".temp.html"

        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(html)

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as user_data_dir:
            cmd = [
                self.browser,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                f"--user-data-dir={user_data_dir}",
                "--allow-file-access-from-files",
                "--enable-local-file-accesses",
                "--virtual-time-budget=6000",
                f"--print-to-pdf={os.path.abspath(output_pdf_path)}",
            ]

            if show_page_numbers:
                header_footer_flags = [
                    "--print-to-pdf-no-header=false",
                    '--header-template=<span></span>',
                    '--footer-template=<div style="width: 100%; font-size: 8.5pt; font-family: sans-serif; color: #718096; text-align: center; border-top: 0.5px solid #e2e8f0; padding-top: 4px; margin-top: 10px;">'
                    '<span class="pageNumber"></span> / <span class="totalPages"></span></div>',
                ]
                cmd.extend(header_footer_flags)
            else:
                cmd.append("--no-pdf-header-footer")

            cmd.append(f"file:///{os.path.abspath(temp_html).replace(os.sep, '/')}")

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode != 0:
                raise RuntimeError(f"Chrome 打印失败 (code {res.returncode}): {res.stderr}")

        if os.path.exists(temp_html):
            try:
                os.remove(temp_html)
            except Exception:
                pass

        return output_pdf_path
