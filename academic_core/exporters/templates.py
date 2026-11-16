# -*- coding: utf-8 -*-
"""
出版级 HTML/KaTeX 打印模板与排版样式
"""

import json

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
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid var(--border-color);
            padding: 10px 14px;
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
            .math-block-container, table, blockquote {
                page-break-inside: avoid;
                break-inside: avoid;
            }
        }
    </style>
</head>
<body>
    <div class="container" id="content"></div>
    <script id="raw-markdown" type="application/json">__RAW_MD_PLACEHOLDER__</script>
    <script>
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
            
            document.getElementById('content').innerHTML = html;
        });
    </script>
</body>
</html>
"""

def build_html_template(markdown_text: str, title: str = "学术讲义") -> str:
    """
    根据 Markdown 文本构建带有完整 KaTeX 动态渲染的自包含 HTML 文档
    """
    json_str = (json.dumps(markdown_text, ensure_ascii=False)
                .replace('<', '\\u003c')
                .replace('\u2028', '\\u2028')
                .replace('\u2029', '\\u2029'))
    return BASE_HTML_TEMPLATE.replace('__TITLE__', title).replace('__RAW_MD_PLACEHOLDER__', json_str)
