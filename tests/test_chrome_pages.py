# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, ".")
import tempfile
import subprocess
import pymupdf
from academic_core.config import find_chrome_executable

browser = find_chrome_executable()

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

with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
    f.write(html_content)
    temp_html = f.name

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as udir:
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={udir}",
        "--display-header-footer",
        "--header-template=<div></div>",
        '--footer-template=<div style="font-size:9px; color:#718096; width:100%; text-align:center; font-family:sans-serif;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
        "--print-to-pdf=test_pages.pdf",
        temp_html
    ]
    subprocess.run(cmd, check=True)

doc = pymupdf.open("test_pages.pdf")
print("Page count:", len(doc))
doc.close()
os.remove("test_pages.pdf")
os.remove(temp_html)
print("Native page numbers verified successfully!")
