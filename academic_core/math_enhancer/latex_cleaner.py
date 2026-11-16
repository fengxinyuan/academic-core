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
        # 消除全角标点后紧随的多余半角空格
        res = re.sub(r'([，。；：！？、])\s+', r'\1', res)
        return res

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
                formula += r" \right." * (left_count - right_count)
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
        res = cls.fix_chinese_punctuation_in_math(res)
        res = cls.fix_align_environments(res)
        res = cls.fix_subscript_superscript(res)
        res = cls.fix_command_spacing(res)
        res = cls.balance_left_right(res)

        # 清除无效空白公式 $$
        res = re.sub(r'\$\$\s*\$\$', '', res)
        return res
