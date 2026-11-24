# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import subprocess
import pytest
import pymupdf
from academic_core.config import find_chrome_executable


def test_chrome_native_page_numbers():
    browser = find_chrome_executable()
    if not browser:
        pytest.skip("No Chrome/Edge browser found")

    html_content = """<!DOCTYPE html><html>
<head><style>
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
body { font-family: sans-serif; font-size: 15px; line-height: 1.6; }
</style></head>
<body>
<h1>第一页：测试原生页码</h1><p>正文内容测试</p>
<div style="page-break-before: always;"></div>
<h1>第二页：继续测试</h1><p>第二页内容</p>
</body></html>"""

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as udir:
        temp_html = os.path.join(udir, "temp.html")
        temp_pdf = os.path.join(udir, "test_pages.pdf")
        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--user-data-dir={udir}",
            "--display-header-footer",
            "--header-template=<div></div>",
            '--footer-template=<div style="font-size:9px; color:#718096; width:100%; text-align:center; font-family:sans-serif;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
            f"--print-to-pdf={temp_pdf}",
            temp_html,
        ]
        subprocess.run(cmd, check=True)

        assert os.path.exists(temp_pdf)
        doc = pymupdf.open(temp_pdf)
        assert len(doc) == 2
        doc.close()

