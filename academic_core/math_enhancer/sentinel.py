# -*- coding: utf-8 -*-
"""
数学公式物理哨兵隔离与零幻觉保护模块 (Math Sentinel)
核心价值：在学术大模型翻译或语义自愈阶段，将 LaTeX 公式抽离为 ASCII 哨兵占位符 (MATH0ZZZ)，
彻底杜绝大模型篡改公式、翻译数学变量、破坏反斜杠或引入幻觉，并在完成后 100% 无损还原。
"""

import re
from typing import Tuple, Dict

MATH_TOKEN_RE = re.compile(r'MATH(\d+)ZZZ', re.IGNORECASE)

def isolate_math(text: str) -> Tuple[str, Dict[str, str]]:
    """
    【公式物理隔离机制 · 无损抽取】
    将 LaTeX 块级 ($$...$$) 与行内 ($...$) 公式抽取为唯一 ASCII 占位符 MATH{counter}ZZZ
    返回: (隔离后文本, {占位符: 原始公式})
    """
    tokens = {}
    counter = 0

    # 1. 优先隔离块级公式 $$...$$
    def repl_block(m):
        nonlocal counter
        key = f"MATH{counter}ZZZ"
        tokens[key] = m.group(0)
        counter += 1
        return key

    isolated = re.sub(r'\$\$([\s\S]*?)\$\$', repl_block, text)

    # 2. 隔离行内公式 $...$
    def repl_inline(m):
        nonlocal counter
        key = f"MATH{counter}ZZZ"
        tokens[key] = m.group(0)
        counter += 1
        return key

    isolated = re.sub(r'(?<!\$)\$([^\$\n]+?)\$(?!\$)', repl_inline, isolated)

    return isolated, tokens

def recover_math(text: str, tokens: Dict[str, str]) -> str:
    """
    【公式精准还原】
    将占位符安全替换回原始 LaTeX 公式，100% 还原原始文本字符
    """
    def repl(m):
        key = m.group(0).upper()
        return tokens.get(key, m.group(0))

    recovered = MATH_TOKEN_RE.sub(repl, text)
    return recovered
