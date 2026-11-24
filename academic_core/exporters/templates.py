# -*- coding: utf-8 -*-
"""
出版级 HTML/KaTeX 打印模板、学术卡片/双语排版样式与插图内嵌工具
全新升级：
1. 左右分栏高精度对齐 (Side-by-Side Grid + Line-by-Line Hover Highlight)
2. 经典学术西文衬线 (Charter / Georgia) 与现代中文排版融合
3. 顶部多功能悬浮阅读栏 (左右分栏 / 逐段流式 / 纯中文 / 纯英文)
4. 多主题切换 (明亮 / 深色 / 羊皮纸护眼) 与字号无级缩放
5. 出版级学术三线表 (Booktabs) 与 KaTeX 矢量数学公式无缝渲染
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
            --bg-color: #f8fafc;
            --container-bg: #ffffff;
            --text-color: #0f172a;
            --text-en: #334155;
            --border-color: #e2e8f0;
            --accent-color: #2563eb;
            --orig-bg: #f8fafc;
            --orig-border: #94a3b8;
            --trans-bg: #ffffff;
            --trans-border: #2563eb;
            --card-hover: rgba(37, 99, 235, 0.04);
            --card-hover-border: #93c5fd;
            --base-font-size: 15px;
        }
        body.theme-dark {
            --bg-color: #0b0f19;
            --container-bg: #111827;
            --text-color: #e2e8f0;
            --text-en: #94a3b8;
            --border-color: #1f2937;
            --accent-color: #3b82f6;
            --orig-bg: #161f30;
            --orig-border: #475569;
            --trans-bg: #111827;
            --trans-border: #3b82f6;
            --card-hover: rgba(59, 130, 246, 0.08);
            --card-hover-border: #3b82f6;
        }
        body.theme-sepia {
            --bg-color: #f4ecd8;
            --container-bg: #fcf8ed;
            --text-color: #382c1e;
            --text-en: #5c4b37;
            --border-color: #e6dac1;
            --accent-color: #8c531b;
            --orig-bg: #f4ecdc;
            --orig-border: #b8a389;
            --trans-bg: #fcf8ed;
            --trans-border: #8c531b;
            --card-hover: rgba(140, 83, 27, 0.05);
            --card-hover-border: #c49a6c;
        }

        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            line-height: 1.75;
            color: var(--text-color);
            background: var(--bg-color);
            margin: 0;
            padding: 0;
            font-size: var(--base-font-size);
            transition: background 0.2s, color 0.2s;
        }
        .container {
            max-width: 900px;
            margin: 20px auto 40px auto;
            padding: 40px 52px;
            background: var(--container-bg);
            border-radius: 10px;
            box-shadow: 0 4px 24px -2px rgba(0, 0, 0, 0.05);
            min-height: 90vh;
            transition: max-width 0.25s ease-in-out;
        }

        /* 顶部悬浮控制栏 */
        .toolbar {
            position: sticky;
            top: 0;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.92);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-color);
            padding: 8px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 13px;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
        }
        body.theme-dark .toolbar {
            background: rgba(17, 24, 39, 0.92);
        }
        body.theme-sepia .toolbar {
            background: rgba(252, 248, 237, 0.92);
        }
        .toolbar-title {
            font-weight: 600;
            color: var(--text-color);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 40%;
        }
        .toolbar-controls {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .btn-group {
            display: flex;
            gap: 4px;
            background: rgba(0,0,0,0.04);
            padding: 2px;
            border-radius: 6px;
        }
        .btn-mode, .btn-tool {
            padding: 4px 10px;
            border: 1px solid transparent;
            background: transparent;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            color: var(--text-color);
            transition: all 0.15s;
        }
        .btn-mode:hover, .btn-tool:hover {
            background: rgba(0,0,0,0.06);
        }
        .btn-mode.active {
            background: var(--accent-color);
            color: #ffffff !important;
            font-weight: 600;
        }

        /* 标题体系 */
        h1, h2, h3, h4 {
            color: var(--text-color);
            font-weight: 700;
            margin-top: 1.6em;
            margin-bottom: 0.8em;
            line-height: 1.35;
        }
        h1 { font-size: 1.75em; border-bottom: 2px solid var(--accent-color); padding-bottom: 8px; }
        h2 { font-size: 1.35em; border-bottom: 1px solid var(--border-color); padding-bottom: 6px; }
        h3 { font-size: 1.15em; }

        /* 🌟 核心：双语分栏网格与高保真对齐（高密度紧凑排版） */
        .bilingual-pair {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin: 8px 0;
            align-items: stretch;
            border-radius: 6px;
            padding: 2px;
            transition: all 0.15s ease-in-out;
        }
        .bilingual-pair:hover {
            background-color: var(--card-hover);
        }
        .bilingual-col {
            min-width: 0;
        }
        .bilingual-orig {
            position: relative;
            margin: 0;
            padding: 10px 14px;
            background-color: var(--orig-bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-en);
            font-family: Charter, "Source Serif 4", Georgia, "Times New Roman", serif;
            font-size: 0.93em;
            line-height: 1.62;
            text-align: justify;
            hyphens: auto;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
        }
        .bilingual-trans {
            position: relative;
            margin: 0;
            padding: 10px 14px;
            background-color: var(--trans-bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-color);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
            font-size: 0.95em;
            line-height: 1.65;
            text-align: justify;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
        }

        .bilingual-orig p:first-child, .bilingual-trans p:first-child { margin-top: 0; }
        .bilingual-orig p:last-child, .bilingual-trans p:last-child { margin-bottom: 0; }

        /* 消除双语卡片内标题的重复下划线与大间距 */
        .bilingual-pair h1, .bilingual-pair h2, .bilingual-pair h3 {
            border-bottom: none !important;
            margin: 0 0 4px 0 !important;
            padding: 0 !important;
        }
        .bilingual-orig h1, .bilingual-orig h2, .bilingual-orig h3 {
            color: #475569;
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 1.15em;
        }
        .bilingual-trans h1, .bilingual-trans h2, .bilingual-trans h3 {
            color: var(--text-color);
            font-size: 1.25em;
        }

        /* 视图模式支持 */
        body.mode-side-by-side .container {
            width: 95%;
            max-width: 1600px;
            padding: 20px 32px;
        }
        body.mode-stacked .bilingual-pair {
            display: block;
        }
        body.mode-stacked .bilingual-orig {
            margin-bottom: 8px;
        }
        body.mode-stacked .container {
            max-width: 900px;
        }
        body.mode-trans-only .bilingual-orig {
            display: none !important;
        }
        body.mode-trans-only .bilingual-pair {
            display: block;
        }
        body.mode-trans-only .container {
            max-width: 900px;
        }
        body.mode-orig-only .bilingual-trans {
            display: none !important;
        }
        body.mode-orig-only .bilingual-pair {
            display: block;
        }
        body.mode-orig-only .container {
            max-width: 900px;
        }

        /* 出版级学术三线表 (Booktabs) */
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 22px 0;
            font-size: 0.9em;
            border-top: 2px solid var(--text-color);
            border-bottom: 2px solid var(--text-color);
            background: var(--container-bg);
        }
        th {
            border-bottom: 1.2px solid var(--text-color);
            background-color: var(--orig-bg);
            font-weight: 600;
            padding: 9px 12px;
            text-align: center;
        }
        td {
            border-bottom: 1px solid var(--border-color);
            padding: 8px 12px;
            text-align: center;
        }
        tr:last-child td { border-bottom: none; }

        /* 学术定理卡片 */
        blockquote {
            margin: 18px 0;
            padding: 12px 20px;
            background-color: var(--orig-bg);
            border-left: 4px solid var(--accent-color);
            border-radius: 4px;
            color: var(--text-color);
        }

        /* 图片居中与图注 */
        img {
            max-width: 94%;
            height: auto;
            display: block;
            margin: 18px auto;
            border-radius: 6px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        }

        pre {
            background-color: var(--orig-bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 12px 16px;
            overflow-x: auto;
            font-size: 0.9em;
            line-height: 1.5;
        }
        code {
            font-family: "JetBrains Mono", Consolas, monospace;
            font-size: 0.9em;
        }

        .math-block-container {
            margin: 1.2em 0;
            overflow-x: visible !important;
            text-align: center;
        }
        .katex-display {
            overflow-x: visible !important;
            overflow-y: hidden;
            font-size: 0.95em !important;
            margin: 0.6em 0 !important;
        }

        @media (max-width: 960px) {
            .bilingual-pair {
                grid-template-columns: 1fr !important;
                gap: 10px;
            }
            .container {
                max-width: 100% !important;
                padding: 16px !important;
                margin: 0 !important;
                border-radius: 0 !important;
            }
            .toolbar-title {
                display: none;
            }
        }

        @media print {
            body { background: #fff !important; }
            .toolbar { display: none !important; }
            .container {
                max-width: 100% !important;
                padding: 0 !important;
                margin: 0 !important;
                box-shadow: none !important;
            }
            @page {
                size: A4;
                margin: 18mm 15mm 18mm 15mm;
            }
            .bilingual-pair {
                grid-template-columns: 1fr 1fr;
                gap: 16px;
                page-break-inside: avoid;
                break-inside: avoid;
            }
            table, blockquote, img {
                page-break-inside: avoid;
                break-inside: avoid;
            }
            h1, h2, h3 {
                page-break-after: avoid;
                break-after: avoid;
            }
        }
    </style>
</head>
<body class="mode-side-by-side">
    <div class="toolbar" id="toolbar" style="display:none;">
        <div class="toolbar-title">__TITLE__</div>
        <div class="toolbar-controls">
            <div class="btn-group">
                <button class="btn-mode active" id="btn-side" onclick="setViewMode('side-by-side')">📖 左右分栏</button>
                <button class="btn-mode" id="btn-stack" onclick="setViewMode('stacked')">📄 逐段流式</button>
                <button class="btn-mode" id="btn-trans" onclick="setViewMode('trans-only')">🇨🇳 仅看译文</button>
                <button class="btn-mode" id="btn-orig" onclick="setViewMode('orig-only')">🇬🇧 仅看原文</button>
            </div>
            <div class="btn-group">
                <button class="btn-tool" onclick="setTheme('light')" title="浅色明亮">☀️</button>
                <button class="btn-tool" onclick="setTheme('sepia')" title="羊皮纸护眼">📜</button>
                <button class="btn-tool" onclick="setTheme('dark')" title="深色夜间">🌙</button>
            </div>
            <div class="btn-group">
                <button class="btn-tool" onclick="changeFontSize(-1)" title="缩小字号">A-</button>
                <button class="btn-tool" onclick="changeFontSize(1)" title="放大字号">A+</button>
            </div>
        </div>
    </div>
    <div class="container" id="content"></div>
    <script id="raw-markdown" type="application/json">__RAW_MD_PLACEHOLDER__</script>
    <script>
        let currentFontSize = 15;

        function setViewMode(mode) {
            const currentTheme = document.body.className.match(/theme-\\w+/)?.[0] || '';
            document.body.className = `mode-${mode} ${currentTheme}`.trim();
            ['side', 'stack', 'trans', 'orig'].forEach(k => {
                const btn = document.getElementById(`btn-${k}`);
                if (btn) btn.classList.remove('active');
            });
            if (mode === 'side-by-side') document.getElementById('btn-side')?.classList.add('active');
            if (mode === 'stacked') document.getElementById('btn-stack')?.classList.add('active');
            if (mode === 'trans-only') document.getElementById('btn-trans')?.classList.add('active');
            if (mode === 'orig-only') document.getElementById('btn-orig')?.classList.add('active');
        }

        function setTheme(theme) {
            const currentMode = document.body.className.match(/mode-[\\w-]+/)?.[0] || 'mode-side-by-side';
            if (theme === 'light') {
                document.body.className = currentMode;
            } else {
                document.body.className = `${currentMode} theme-${theme}`.trim();
            }
        }

        function changeFontSize(delta) {
            currentFontSize = Math.max(13, Math.min(20, currentFontSize + delta));
            document.documentElement.style.setProperty('--base-font-size', `${currentFontSize}px`);
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

            // 保护未包裹定界符的裸 LaTeX 数学环境 (如未加 $ 的 \\begin{array} ... \\end{array})
            processed = processed.replace(/(?<!\\$)\\\\begin\\{(aligned|array|matrix|pmatrix|bmatrix|vmatrix|cases|gather|equation\\*?)\\}([\\s\\S]*?)\\\\end\\{\\1\\}(?!\\$)/g, (m) => {
                // 简化冗余单格 array: \\begin{array}{r}{\\sigma(x)=...}\\end{array} -> \\sigma(x)=...
                const simplified = m.replace(/\\\\begin\\{array\\}\\s*\\{[ \\t]*[rcl][ \\t]*\\}\\s*\\{([\\s\\S]*?)\\}\\s*\\\\end\\{array\\}/, '$1');
                const id = `MATHINLINE${mathTokens.length}ZZZ`;
                try {
                    const rendered = katex.renderToString(simplified.trim(), { displayMode: false, throwOnError: false });
                    mathTokens.push(rendered);
                } catch(e) {
                    try {
                        const rendered = katex.renderToString(m.trim(), { displayMode: false, throwOnError: false });
                        mathTokens.push(rendered);
                    } catch(e2) {
                        mathTokens.push(`$${m}$`);
                    }
                }
                return id;
            });

            // 保护行内 $...$
            processed = processed.replace(/(?<!\\$)\\$([^\\$\\n]+?)\\$(?!\\$)/g, (m, code) => {
                // 如果行内公式包含单格 array 冗余包裹，自动解包简化
                const simplified = code.replace(/\\\\begin\\{array\\}\\s*\\{[ \\t]*[rcl][ \\t]*\\}\\s*\\{([\\s\\S]*?)\\}\\s*\\\\end\\{array\\}/, '$1');
                const id = `MATHINLINE${mathTokens.length}ZZZ`;
                try {
                    const rendered = katex.renderToString(simplified.trim(), { displayMode: false, throwOnError: false });
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

            // 自动检测双语元素
            const hasBilingual = contentEl.querySelector('.bilingual-pair, .bilingual-orig');
            if (hasBilingual) {
                document.getElementById('toolbar').style.display = 'flex';

                // 兼容：若存在未包裹在 .bilingual-pair 内的 .bilingual-orig，自动与后续兄弟节点成对封装
                const rawOrigs = Array.from(contentEl.querySelectorAll('.bilingual-orig'));
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
                            colRight.innerHTML = nextEl.outerHTML;

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
