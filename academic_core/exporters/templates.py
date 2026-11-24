# -*- coding: utf-8 -*-
"""
出版级 HTML/KaTeX 打印模板、学术卡片/双语排版样式与插图内嵌工具
"""

import os
import re
import json
import base64
import mimetypes
from typing import Optional

BASE_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>__TITLE__</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked@4.3.0/marked.min.js"></script>
    <style>
        :root {
            --bg-color: #ffffff;
            --text-color: #1a202c;
            --muted-color: #4a5568;
            --border-color: #e2e8f0;
            --accent-color: #2b6cb0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            line-height: 1.75;
            color: var(--text-color);
            background: var(--bg-color);
            margin: 0;
            padding: 0;
            font-size: 15px;
        }
        .container {
            max-width: 860px;
            margin: 0 auto;
            padding: 36px 48px;
        }
        h1, h2, h3, h4 {
            color: #1a365d;
            font-weight: 700;
            margin-top: 1.6em;
            margin-bottom: 0.8em;
            line-height: 1.35;
        }
        h1 { font-size: 1.85em; border-bottom: 2px solid #3182ce; padding-bottom: 8px; }
        h2 { font-size: 1.4em; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; }
        h3 { font-size: 1.2em; }

        blockquote {
            margin: 16px 0;
            padding: 12px 20px;
            background-color: #f7fafc;
            border-left: 4px solid #3182ce;
            border-radius: 4px;
            color: #2d3748;
        }

        /* 双语分栏对照排版与卡片 */
        .bilingual-pair {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 22px;
            margin: 16px 0;
            align-items: start;
        }
        .bilingual-col {
            min-width: 0;
        }
        .bilingual-orig {
            margin: 0;
            padding: 12px 16px;
            background-color: #f8fafc;
            border-left: 3px solid #cbd5e0;
            border-radius: 4px;
            color: var(--muted-color);
            font-size: 0.93em;
            line-height: 1.6;
        }
        .bilingual-trans {
            margin: 0;
            padding: 12px 16px;
            background-color: #ffffff;
            border-left: 3px solid #3182ce;
            border-radius: 4px;
            color: var(--text-color);
            font-size: 0.98em;
            line-height: 1.7;
        }
        .bilingual-orig p:first-child, .bilingual-trans p:first-child {
            margin-top: 0;
        }
        .bilingual-orig p:last-child, .bilingual-trans p:last-child {
            margin-bottom: 0;
        }

        /* 顶部悬浮阅读控制栏 (左右对照 / 上下流式 / 纯译文 / 纯原文) */
        .toolbar {
            position: sticky;
            top: 0;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid var(--border-color);
            padding: 10px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 13px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .toolbar-title {
            font-weight: 600;
            color: #2d3748;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 45%;
        }
        .toolbar-buttons {
            display: flex;
            gap: 8px;
        }
        .btn-mode {
            padding: 5px 12px;
            border: 1px solid #cbd5e0;
            background: #ffffff;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            color: #4a5568;
            transition: all 0.2s;
        }
        .btn-mode:hover {
            border-color: #3182ce;
            color: #3182ce;
        }
        .btn-mode.active {
            background: #3182ce;
            color: #ffffff;
            border-color: #3182ce;
        }

        /* 视图模式支持 */
        body.mode-side-by-side .container {
            max-width: 1360px;
            padding: 24px 36px;
        }
        body.mode-stacked .bilingual-pair {
            display: block;
        }
        body.mode-stacked .bilingual-orig {
            margin-bottom: 8px;
        }
        body.mode-stacked .container {
            max-width: 860px;
        }
        body.mode-trans-only .bilingual-orig {
            display: none !important;
        }
        body.mode-trans-only .bilingual-pair {
            display: block;
        }
        body.mode-trans-only .container {
            max-width: 860px;
        }
        body.mode-orig-only .bilingual-trans {
            display: none !important;
        }
        body.mode-orig-only .bilingual-pair {
            display: block;
        }
        body.mode-orig-only .container {
            max-width: 860px;
        }

        @media (max-width: 900px) {
            .bilingual-pair {
                grid-template-columns: 1fr !important;
                gap: 10px;
            }
            .container {
                max-width: 100% !important;
                padding: 16px !important;
            }
        }

        /* 原文页码徽标 */
        .page-marker {
            text-align: center;
            margin: 22px 0 14px 0;
            color: #718096;
            font-size: 0.82em;
            letter-spacing: 0.05em;
        }

        /* 论文/教材插图与图表自适应居中 */
        img {
            max-width: 96%;
            height: auto;
            display: block;
            margin: 16px auto;
            border-radius: 4px;
        }

        pre {
            background-color: #f7fafc;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 12px 16px;
            overflow-x: auto;
            font-size: 0.9em;
            line-height: 1.5;
        }
        code {
            font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
            font-size: 0.9em;
        }

        table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            font-size: 0.93em;
        }
        th, td {
            border: 1px solid var(--border-color);
            padding: 8px 12px;
            text-align: left;
        }
        th {
            background-color: #edf2f7;
            font-weight: 600;
        }

        /* 数学公式容器防截断与美化 */
        .math-block-container {
            margin: 1.2em 0;
            overflow-x: visible !important;
            text-align: center;
        }
        .katex-display {
            overflow-x: visible !important;
            overflow-y: hidden;
            font-size: 0.94em !important;
            margin: 0.6em 0 !important;
        }
        .katex {
            font-size: 1.05em;
            text-rendering: auto;
        }

        /* 彻底消除浏览器无头渲染可能带来的侧边/底边滚动条 */
        ::-webkit-scrollbar {
            display: none !important;
            width: 0 !important;
            height: 0 !important;
        }
        * {
            scrollbar-width: none !important;
            -ms-overflow-style: none !important;
        }

        @media print {
            body {
                background: white;
            }
            .container {
                max-width: 100%;
                padding: 0;
            }
            @page {
                size: A4;
                margin: 20mm 15mm 20mm 15mm;
            }
            h1, h2, h3 {
                page-break-after: avoid;
                break-after: avoid;
            }
            .math-block-container, table, blockquote, img, .bilingual-orig {
                page-break-inside: avoid;
                break-inside: avoid;
            }
        }
    </style>
</head>
<body class="mode-side-by-side">
    <div class="toolbar" id="toolbar" style="display:none;">
        <div class="toolbar-title">__TITLE__</div>
        <div class="toolbar-buttons">
            <button class="btn-mode active" id="btn-side" onclick="setViewMode('side-by-side')">📖 左右分栏</button>
            <button class="btn-mode" id="btn-stack" onclick="setViewMode('stacked')">📄 上下流式</button>
            <button class="btn-mode" id="btn-trans" onclick="setViewMode('trans-only')">🇨🇳 仅看译文</button>
            <button class="btn-mode" id="btn-orig" onclick="setViewMode('orig-only')">🇬🇧 仅看原文</button>
        </div>
    </div>
    <div class="container" id="content"></div>
    <script id="raw-markdown" type="application/json">__RAW_MD_PLACEHOLDER__</script>
    <script>
        function setViewMode(mode) {
            document.body.className = `mode-${mode}`;
            ['side', 'stack', 'trans', 'orig'].forEach(k => {
                const btn = document.getElementById(`btn-${k}`);
                if (btn) btn.classList.remove('active');
            });
            if (mode === 'side-by-side') document.getElementById('btn-side')?.classList.add('active');
            if (mode === 'stacked') document.getElementById('btn-stack')?.classList.add('active');
            if (mode === 'trans-only') document.getElementById('btn-trans')?.classList.add('active');
            if (mode === 'orig-only') document.getElementById('btn-orig')?.classList.add('active');
        }

        document.addEventListener('DOMContentLoaded', () => {
            const raw = JSON.parse(document.getElementById('raw-markdown').textContent);
            const mathTokens = [];
            let processed = raw;

            // 保护独立 $$...$$
            processed = processed.replace(/\\$\\$([\\s\\S]*?)\\$\\$/g, (m, code) => {
                const id = `MATHBLOCK${mathTokens.length}ZZZ`;
                try {
                    const rendered = katex.renderToString(code.trim(), { displayMode: true, throwOnError: false });
                    mathTokens.push(`<div class="math-block-container">${rendered}</div>`);
                } catch(e) {
                    mathTokens.push(`<div class="math-block-container">$$${code}$$</div>`);
                }
                return id;
            });

            // 保护行内 $...$
            processed = processed.replace(/(?<!\\$)\\$([^\\$\\n]+?)\\$(?!\\$)/g, (m, code) => {
                const id = `MATHINLINE${mathTokens.length}ZZZ`;
                try {
                    const rendered = katex.renderToString(code.trim(), { displayMode: false, throwOnError: false });
                    mathTokens.push(rendered);
                } catch(e) {
                    mathTokens.push(`$${code}$`);
                }
                return id;
            });

            let html = marked.parse(processed);
            html = html.replace(/MATH(BLOCK|INLINE)(\\d+)ZZZ/g, (m, type, idx) => {
                return mathTokens[parseInt(idx)] || m;
            });

            const contentEl = document.getElementById('content');
            contentEl.innerHTML = html;

            // 自动检测双语元素：若存在双语对照，显示控制工具栏并默认开启左右对照
            const hasBilingual = contentEl.querySelector('.bilingual-pair, .bilingual-orig');
            if (hasBilingual) {
                document.getElementById('toolbar').style.display = 'flex';

                // 兼容旧版：若存在未包裹在 .bilingual-pair 内的 .bilingual-orig，自动与后续兄弟节点成对封装
                const rawOrigs = contentEl.querySelectorAll('.bilingual-orig');
                rawOrigs.forEach(orig => {
                    if (!orig.closest('.bilingual-pair')) {
                        const nextEl = orig.nextElementSibling;
                        if (nextEl && !nextEl.classList.contains('bilingual-orig')) {
                            const pair = document.createElement('div');
                            pair.className = 'bilingual-pair';
                            const colLeft = document.createElement('div');
                            colLeft.className = 'bilingual-col bilingual-orig';
                            colLeft.innerHTML = orig.innerHTML;

                            const colRight = document.createElement('div');
                            colRight.className = 'bilingual-col bilingual-trans';
                            colRight.appendChild(nextEl.cloneNode(true));

                            pair.appendChild(colLeft);
                            pair.appendChild(colRight);

                            orig.parentNode.insertBefore(pair, orig);
                            orig.remove();
                            nextEl.remove();
                        }
                    }
                });
            } else {
                document.body.className = '';
            }
        });
    </script>
</body>

</html>
"""


def _resolve_local_image(img_ref: str, assets_dir: Optional[str]) -> Optional[str]:
    """在 assets_dir 中定位 Markdown 引用的本地插图文件"""
    ref = img_ref.strip().strip('"').strip("'")
    if not ref or ref.startswith(("http://", "https://", "data:")):
        return None
    if os.path.isabs(ref) and os.path.exists(ref):
        return ref
    if assets_dir:
        cand1 = os.path.join(assets_dir, ref)
        if os.path.exists(cand1):
            return cand1
        cand2 = os.path.join(assets_dir, "images", os.path.basename(ref))
        if os.path.exists(cand2):
            return cand2
    return None


def embed_local_images_as_data_uri(markdown_text: str, assets_dir: Optional[str] = None) -> str:
    """
    将 Markdown 中引用的本地插图 (如 MinerU 裁剪的论文图表 ![fig](images/xxx.jpg))
    自动编码为内联 Base64 Data URI，保证导出的独立 HTML 与无头 PDF 永不裂图。
    """
    if not assets_dir or not os.path.exists(assets_dir):
        return markdown_text

    def _to_data_uri(img_path: str) -> str:
        mime, _ = mimetypes.guess_type(img_path)
        mime = mime or "image/png"
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:{mime};base64,{b64}"

    def _repl_md(m):
        alt, ref = m.group(1), m.group(2)
        resolved = _resolve_local_image(ref, assets_dir)
        if resolved:
            try:
                return f"![{alt}]({_to_data_uri(resolved)})"
            except Exception:
                return m.group(0)
        return m.group(0)

    return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _repl_md, markdown_text)


def build_html_template(
    markdown_text: str,
    title: str = "学术讲义",
    assets_dir: Optional[str] = None,
    embed_images: bool = True,
) -> str:
    """
    根据 Markdown 文本构建带有完整 KaTeX 动态渲染与内嵌插图的自包含 HTML 文档
    """
    md_ready = embed_local_images_as_data_uri(markdown_text, assets_dir) if embed_images else markdown_text
    json_str = (
        json.dumps(md_ready, ensure_ascii=False)
        .replace('<', '\\u003c')
        .replace('\u2028', '\\u2028')
        .replace('\u2029', '\\u2029')
    )
    return BASE_HTML_TEMPLATE.replace('__TITLE__', title).replace('__RAW_MD_PLACEHOLDER__', json_str)
