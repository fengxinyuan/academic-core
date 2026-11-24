# -*- coding: utf-8 -*-
"""
学术数学公式自愈与语法校验引擎 (Math & LaTeX Enhancer)
针对 OCR 视觉抽取中的高频排版缺陷进行全自动语法自愈：
1. 剥离行内公式内部的中文标点 ($f(x)，$ -> $f(x)$，)
2. 修复 KaTeX/MathJax 无法容忍的 \\left 与 \\right 不匹配语法崩溃
3. 自动转换 \\begin{align} 为 \\begin{aligned} 兼容模式
4. 修复中英文与 LaTeX 命令的粘连 (\\alpha与\\beta -> \\alpha 与 \\beta)
5. 修复上下标与底数脱节 (a_ 1 -> a_1, x^ 2 -> x^2)
6. 规范化学术定理、定义、命题环境的排版层级
"""

import re

class LatexCleaner:
    @staticmethod
    def fix_chinese_punctuation_in_math(text: str) -> str:
        """
        修复公式内部首尾的中文标点符号，防止 KaTeX 解析崩溃或排版错位：
        $f(x)，$ -> $f(x)$，
        $A = B。$ -> $A = B$。
        """
        punct = "，。；：！？、"
        def _fix_inline(m):
            content = m.group(1)
            prefix = ""
            suffix = ""
            while content and content[0] in punct:
                prefix += content[0]
                content = content[1:]
            while content and content[-1] in punct:
                suffix = content[-1] + suffix
                content = content[:-1]
            if not content:
                return prefix + suffix
            return f"{prefix}${content}${suffix}"

        res = re.sub(r'(?<!\$)\$([^\$\n]+?)\$(?!\$)', _fix_inline, text)
        # 消除全角标点后紧随的多余水平半角空格（注意不能吞掉 \n 换行）
        res = re.sub(r'([，。；：！？、])[ \t]+', r'\1', res)
        return res

    @staticmethod
    def simplify_single_cell_arrays(text: str) -> str:
        """
        消除 OCR 视觉抽取中把简单行内公式伪装成单列 array 矩阵的冗余语法：
        \\begin{array} { r } { \\sigma(x) = ... } \\end{array} -> \\sigma(x) = ...
        若原 array 缺失 $ 定界符，自动补充 $，确保 KaTeX 正常渲染
        """
        def _repl(m):
            inner = m.group(1).strip()
            start = m.start()
            end = m.end()
            has_pre = (start > 0 and text[start - 1] == '$')
            has_post = (end < len(text) and text[end] == '$')
            if has_pre and has_post:
                return f" {inner} "
            return f"${inner}$"

        return re.sub(
            r'\\begin\{array\}\s*\{[ \t]*[rcl][ \t]*\}\s*\{([\s\S]*?)\}\s*\\end\{array\}',
            _repl,
            text
        )

    @staticmethod
    def wrap_bare_latex_environments(text: str) -> str:
        """
        自愈未包裹 $ 或 $$ 定界符的裸 LaTeX 数学环境 (如 \\begin{aligned}, \\begin{cases}, \\begin{matrix})
        防止其在 Markdown 中无法被 KaTeX 识别而直接裸露为原始代码
        """
        env_pattern = re.compile(
            r'\\begin\{(aligned|array|matrix|pmatrix|bmatrix|vmatrix|cases|gather|equation\*?)\}'
            r'([\s\S]*?)'
            r'\\end\{\1\}'
        )

        def _is_inside_math(pos: int) -> bool:
            prefix = text[:pos]
            if prefix.count('$$') % 2 == 1:
                return True
            without_blocks = prefix.replace('$$', '')
            return (without_blocks.count('$') % 2 == 1)

        def _wrap(m):
            if _is_inside_math(m.start()):
                return m.group(0)
            code = m.group(0).strip()
            if "\n" in code:
                return f"\n\n$${code}$$\n\n"
            return f"${code}$"

        return env_pattern.sub(_wrap, text)

    @staticmethod
    def fix_align_environments(text: str) -> str:
        """
        KaTeX 在 Markdown 中默认不支持顶级 align 环境，必须使用 aligned 环境
        """
        text = re.sub(r'\\begin\{align\*?\}', r'\\begin{aligned}', text)
        text = re.sub(r'\\end\{align\*?\}', r'\\end{aligned}', text)
        return text

    @staticmethod
    def fix_subscript_superscript(text: str) -> str:
        """
        修复 OCR 产生的下标/上标空格脱离：
        a_ 1 -> a_1
        x^ 2 -> x^2
        """
        text = re.sub(r'([a-zA-Z0-9_\}\)]+)\s*_\s*([a-zA-Z0-9]+)', r'\1_\2', text)
        text = re.sub(r'([a-zA-Z0-9_\}\)]+)\s*\^\s*([a-zA-Z0-9]+)', r'\1^\2', text)
        return text

    @staticmethod
    def fix_command_spacing(text: str) -> str:
        """
        修复 LaTeX 命令与紧随的中文字符粘连：
        \\alpha与\\beta -> \\alpha 与 \\beta
        """
        text = re.sub(r'(\\[a-zA-Z]+)([\u4e00-\u9fa5])', r'\1 \2', text)
        text = re.sub(r'([\u4e00-\u9fa5])(\\[a-zA-Z]+)', r'\1 \2', text)
        return text

    @staticmethod
    def balance_left_right(text: str) -> str:
        """
        扫描公式块，自愈未闭合的 \\left( ... ) 或 \\left[ ... ]
        """
        def _repair_formula(formula: str) -> str:
            left_count = len(re.findall(r'\\left[\(\[\{\.\|]', formula))
            right_count = len(re.findall(r'\\right[\)\]\}\.\|]', formula))
            if left_count > right_count:
                pad = r" \right." * (left_count - right_count)
                # 若公式以 \end{aligned} 等环境收尾，将 \right. 补在环境内部，避免 KaTeX 环境错位
                end_m = re.search(r'(\\end\{[a-zA-Z*]+\}\s*)$', formula)
                if end_m:
                    formula = formula[:end_m.start()] + pad + "\n" + end_m.group(1)
                else:
                    formula += pad
            elif right_count > left_count:
                formula = (r"\left. " * (right_count - left_count)) + formula
            return formula

        # 处理块级公式 $$ ... $$
        def _replace_block(m):
            return "$$" + _repair_formula(m.group(1)) + "$$"
        text = re.sub(r'\$\$([\s\S]*?)\$\$', _replace_block, text)

        # 处理行内公式 $ ... $
        def _replace_inline(m):
            return "$" + _repair_formula(m.group(1)) + "$"
        text = re.sub(r'(?<!\$)\$([^\$\n]+?)\$(?!\$)', _replace_inline, text)

        return text

    @classmethod
    def clean(cls, markdown_text: str) -> str:
        """
        全套自愈增强流水线
        """
        if not markdown_text:
            return ""

        res = markdown_text
        res = cls.simplify_single_cell_arrays(res)
        res = cls.wrap_bare_latex_environments(res)
        res = cls.fix_chinese_punctuation_in_math(res)
        res = cls.fix_align_environments(res)
        res = cls.fix_subscript_superscript(res)
        res = cls.fix_command_spacing(res)
        res = cls.balance_left_right(res)
        return res
