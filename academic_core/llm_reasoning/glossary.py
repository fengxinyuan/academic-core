# -*- coding: utf-8 -*-
"""
学术专有名词提取与全局一致性对齐中枢 (Academic Glossary Manager)
提供：
1. 启发式核心术语候选词提取（基于大写复合专有名词、LaTeX 数学算子、高频学术短语）
2. 大模型首轮轻量级术语表自动预扫描与生成 (Auto-Glossary)
3. 术语与用户自定义术语优先级合并，确保全书/全篇长文跨章节用词 100% 一致
4. 导出 glossary.json 供出版审校
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("academic_core.glossary")


class GlossaryManager:
    @staticmethod
    def extract_candidate_terms(text: str, max_candidates: int = 30) -> List[str]:
        """
        从学术原文中提取高价值专有名词候选列表
        """
        candidates = set()

        # 1. 匹配 2-4 个连续大写开头的英文专有名词 (如 Adjoint Operator, Optimal Compute, Vector Space)
        caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b', text)
        for c in caps:
            if len(c) > 4 and not c.startswith(("Figure", "Table", "Section", "Chapter", "Lemma", "Theorem", "Proposition", "Proof")):
                candidates.add(c.strip())

        # 2. 匹配常见学术复合词 / 连字符术语 (如 test-time, best-of-n, self-adjoint, inner-product)
        hyphen_terms = re.findall(r'\b[a-z]{3,}-(?:[a-z]{3,}-)?[a-z]{3,}\b', text, re.IGNORECASE)
        for h in hyphen_terms:
            candidates.add(h.lower())

        # 3. 常见数学/学术关键字
        math_keywords = [
            "eigenvalue", "eigenvector", "nullspace", "kernel", "inner product",
            "orthogonal complement", "unitary", "hermitian", "isomorphism",
            "homomorphism", "linear map", "linear operator", "trace", "determinant",
            "spectral decomposition", "singular value", "manifold", "surjective", "injective"
        ]
        text_lower = text.lower()
        for kw in math_keywords:
            if kw in text_lower:
                candidates.add(kw)

        res = sorted(list(candidates), key=lambda x: (-len(x), x))
        return res[:max_candidates]

    @staticmethod
    def generate_glossary(
        engine,
        raw_text: str,
        target_lang: str = "zh-CN",
        existing_glossary: Optional[dict] = None,
    ) -> Dict[str, str]:
        """
        利用大模型对文档核心概念做轻量级前置预扫描，生成规范的术语对齐表
        """
        merged = dict(existing_glossary or {})

        if engine is None or engine.provider in ("mock", "test"):
            # Mock 模式返回基础术语
            merged.setdefault("eigenvalue", "特征值")
            merged.setdefault("linear operator", "线性算子")
            return merged

        sample_snippet = raw_text[:3500]
        candidates = GlossaryManager.extract_candidate_terms(sample_snippet, max_candidates=20)
        cands_str = ", ".join(candidates) if candidates else "根据文本自动提取"

        prompt = (
            f"你是一位资深学术出版审校专家。请从以下学术文本中提炼 10 到 20 个最核心、最关键的专业领域学术术语，"
            f"并给出规范、权威的目标语言（{target_lang}）统一译名。\n\n"
            f"参考候选术语：{cands_str}\n\n"
            f"【要求】：\n"
            f"1. 仅输出一个标准的 JSON 对象，格式如：{{\"术语原文\": \"权威译名\"}}，例如 {{\"eigenvalue\": \"特征值\"}}；\n"
            f"2. 严禁任何额外文字、解释或代码块标记；\n"
            f"3. 保持术语键名简洁、标准化（英文通常小写或公认首字母大写）。"
        )

        try:
            logger.info("正在执行前置学术术语统一预对齐 (Auto-Glossary Pre-Scan)...")
            res_text = engine._call_llm_raw("You are a professional terminology extraction specialist.", f"{prompt}\n\n=== 原文素材 ===\n{sample_snippet}")
            cleaned = re.sub(r'^```(?:json)?', '', res_text.strip(), flags=re.MULTILINE)
            cleaned = re.sub(r'```$', '', cleaned.strip(), flags=re.MULTILINE).strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    if isinstance(k, str) and isinstance(v, str):
                        if k not in merged:
                            merged[k] = v
                logger.info(f"术语表自动预对齐完成，共确定 {len(merged)} 项核心术语约束。")
        except Exception as e:
            logger.warning(f"自动术语生成异常，回退使用基础术语: {e}")

        return merged
