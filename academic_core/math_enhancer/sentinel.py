# -*- coding: utf-8 -*-
"""
工业级数学公式哨兵隔离与双语段落对齐保护模块 (Math Sentinel & Paragraph Anchors)
核心价值：
1. 彻底防止大模型在翻译或排版时篡改公式、破坏下划线、吞噬符号或误译数学变量；
2. 零丢失校验：若大模型漏掉某个占位符，自动检测并兜底找回；
3. 段落对齐锚点 (PARAxZZZ)：支持 1:1 零幻觉英汉/多语对照，既省一半 Token 又保证原文一字不改。
"""

import re
from typing import Tuple, Dict, List, Optional

MATH_TOKEN_RE = re.compile(r'MATH(\d+)ZZZ', re.IGNORECASE)
PARA_ANCHOR_RE = re.compile(r'PARA(\d+)ZZZ', re.IGNORECASE)


def _math_token(counter: int) -> str:
    return f"MATH{counter}ZZZ"


def _para_anchor(counter: int) -> str:
    return f"PARA{counter}ZZZ"


def isolate_math(text: str) -> Tuple[str, Dict[str, str]]:
    """
    【公式物理隔离机制 · 无损版】
    将 LaTeX 块级 ($$...$$) 与行内 ($...$) 公式抽取为 ASCII 哨兵占位符 MATHxZZZ。
    自动保护代码块 (```...``` / `...`) 与转义货币符 (\\$)，防止误隔离。
    返回: (隔离后文本, {占位符: 原始含$定界符的公式})
    """
    tokens: Dict[str, str] = {}
    code_tokens: Dict[str, str] = {}
    counter = 0
    code_counter = 0

    def _mask_code(m):
        nonlocal code_counter
        ck = f"CODEMASK{code_counter}ZZZ"
        code_tokens[ck] = m.group(0)
        code_counter += 1
        return ck

    def repl_block(m):
        nonlocal counter
        key = _math_token(counter)
        tokens[key] = m.group(0)
        counter += 1
        return key

    def repl_inline(m):
        nonlocal counter
        key = _math_token(counter)
        tokens[key] = m.group(0)
        counter += 1
        return key

    # 0. 先保护代码块与行内代码
    t0 = re.sub(r'```[\s\S]*?```', _mask_code, text)
    t0 = re.sub(r'`[^`\n]+`', _mask_code, t0)

    # 1. 先提取块级公式 $$ ... $$
    t1 = re.sub(r'\$\$([\s\S]*?)\$\$', repl_block, t0)
    # 2. 再提取行内公式 $ ... $ (忽略转义 \$)
    t2 = re.sub(r'(?<!\\)(?<!\$)\$(?!\$)([^\$\n\r]+?)(?<!\\)(?<!\$)\$(?!\$)', repl_inline, t1)

    # 3. 还原代码块占位符
    for ck, cv in code_tokens.items():
        t2 = t2.replace(ck, cv)

    return t2, tokens


def recover_math(text: str, tokens: Dict[str, str]) -> str:
    """
    【公式无损回填】
    将文本中的 MATHxZZZ 占位符精确还原为原始 LaTeX 公式。
    """
    def repl(m):
        key = _math_token(int(m.group(1)))
        return tokens.get(key, m.group(0))

    res = MATH_TOKEN_RE.sub(repl, text)
    for key, math_code in tokens.items():
        if key in res:
            res = res.replace(key, math_code)
    return res


def verify_and_recover_math(translated: str, tokens: Dict[str, str]) -> Tuple[str, int]:
    """
    【定界符零丢失校验与自愈】
    检查模型是否漏掉了某些公式占位符；若有遗漏，自动在末尾兜底补回，保证公式零丢失。
    返回: (已回填补全的译文, 丢失公式数)
    """
    restored = recover_math(translated, tokens)
    present_ids = {int(n) for n in MATH_TOKEN_RE.findall(translated)}

    missing = []
    for key, math_code in tokens.items():
        m = MATH_TOKEN_RE.match(key)
        if m and int(m.group(1)) in present_ids:
            continue
        if math_code in restored:
            continue
        missing.append((key, math_code))

    if missing:
        recovery = "\n\n".join(mc for _, mc in missing)
        restored = restored.rstrip() + "\n\n" + recovery + "\n\n"

    return restored, len(missing)


def formula_fingerprint(latex: str) -> str:
    """计算公式归一化指纹，用于跨系统公式去重与匹配"""
    if not latex:
        return ""
    s = re.sub(r'\s+', '', latex)
    s = s.replace('\\left', '').replace('\\right', '')
    s = s.replace('{', '').replace('}', '')
    return s


def sanitize_and_repair_markdown(text: str) -> str:
    """
    【结构安全清洗】
    1) 剔除空公式块 $$ $$ 与行内空公式 $ $
    2) 保守包裹裸露的 LaTeX 块级矩阵环境 (\\begin{array}, \\begin{pmatrix} 等)
    3) 规范连续空行
    """
    lines = text.split('\n')
    out = []
    i = 0
    in_math = False
    while i < len(lines):
        if lines[i].strip() == '$$':
            if not in_math:
                # 仅在数学块外部检测空公式对 ($$ 紧跟空行后闭合 $$)
                j = i + 1
                while j < len(lines) and lines[j].strip() == '':
                    j += 1
                if j < len(lines) and lines[j].strip() == '$$':
                    i = j + 1
                    continue
                in_math = True
                out.append(lines[i])
            else:
                # 正在数学块内部，当前 $$ 为闭合符，绝不与下一块的起始 $$ 误合并
                in_math = False
                out.append(lines[i])
            i += 1
            continue
        out.append(lines[i])
        i += 1
    text = '\n'.join(out)

    text = re.sub(r'(?<![\$\\])\$[ \t]+\$(?!\$)', '', text)

    def _looks_like_naked_formula(seg: str) -> bool:
        s = seg.strip()
        if not s or '$' in s:
            return False
        if re.search(r'[\u4e00-\u9fa5]', s):
            return False
        if any(env in s for env in ('\\begin{array}', '\\begin{matrix}', '\\begin{pmatrix}', '\\begin{bmatrix}')):
            return True
        if re.search(r'\\left[\[\(\|]', s) and re.search(r'\\right[\]\)\|]', s):
            return True
        return False

    paragraphs = text.split("\n\n")
    wrapped = ["$$\n" + p.strip() + "\n$$" if _looks_like_naked_formula(p) else p for p in paragraphs]
    text = "\n\n".join(wrapped)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text


def inject_paragraph_anchors(text: str) -> Tuple[str, List[str]]:
    """
    【双语对齐锚点注入】
    在每个原文段落（以空行分隔的块）前插入 ASCII 锚点 PARAxZZZ。
    返回: (带锚点文本, 原文非空段落列表)
    """
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    out = [f"{_para_anchor(idx)}\n{blk}" for idx, blk in enumerate(blocks)]
    return "\n\n".join(out), blocks


def split_by_paragraph_anchors(text: str, expected: int) -> Optional[List[str]]:
    """
    【按对齐锚点切分译文】
    若恢复出的段数与 expected 完全一致则返回 List[str]，否则返回 None 交由上层降级。
    """
    if expected <= 0:
        return None

    matches = list(PARA_ANCHOR_RE.finditer(text))
    if not matches:
        return None

    segments: Dict[int, str] = {}
    for idx, m in enumerate(matches):
        tid = int(m.group(1))
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        seg = text[start:end].strip()
        if tid not in segments:
            segments[tid] = seg

    if set(segments.keys()) != set(range(expected)):
        return None

    return [segments[i] for i in range(expected)]


def strip_paragraph_anchors(text: str) -> str:
    """移除残留的 PARAxZZZ 锚点"""
    text = PARA_ANCHOR_RE.sub("", text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
