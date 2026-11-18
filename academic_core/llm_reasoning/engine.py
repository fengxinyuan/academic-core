# -*- coding: utf-8 -*-
"""
学术语义大模型推理与长文翻译中枢 (Academic LLM Engine)
支持：
- 多服务商：Qwen (DashScope) / DeepSeek / OpenAI (含自定义 base_url: OpenRouter, OneAPI, Ollama, vLLM) / Gemini / Mock
- 长文档智能分块 + 多线程并发 + 输出截断自动折半重试
- 数学公式物理哨兵隔离 (Math Sentinel) 防篡改、零幻觉
- 1:1 段落锚点精准双语对照 (PARAxZZZ)
"""

import os
import re
import time
import logging
import requests
from typing import Optional, List, Dict
from concurrent.futures import ThreadPoolExecutor

from academic_core.config import (
    DASHSCOPE_API_KEY,
    DEEPSEEK_API_KEY,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    GEMINI_API_KEY,
)
from academic_core.llm_reasoning.prompts import get_task_prompt
from academic_core.math_enhancer.sentinel import (
    isolate_math,
    verify_and_recover_math,
    inject_paragraph_anchors,
    split_by_paragraph_anchors,
    strip_paragraph_anchors,
)

logger = logging.getLogger("academic_core.llm")

_NON_RETRYABLE_STATUS = {400, 401, 402, 403, 404}


class LLMTruncatedError(RuntimeError):
    """模型输出因长度限制被截断，触发自动折半分块重试"""


def _is_pure_structural_block(block: str) -> bool:
    """判断是否为纯公式、纯图片或纯分隔符块（双语模式下无需重复展示两次）"""
    s = block.strip()
    if not s:
        return True
    if s in ("---", "***", "___"):
        return True
    if s.startswith("$$") and s.endswith("$$"):
        return True
    if re.match(r'^!\[[^\]]*\]\([^)]+\)$', s):
        return True
    if re.match(r'^<div class="page-marker"', s):
        return True
    return False


class AcademicLLMEngine:
    def __init__(
        self,
        provider: str = "dashscope",
        model: str = "qwen-plus",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_chunk_chars: int = 5000,
        max_workers: int = 4,
    ):
        self.provider = provider.lower().strip()
        self.model = model
        self.max_chunk_chars = max(1000, int(max_chunk_chars))
        self.max_workers = max(1, int(max_workers))

        if self.provider in ("mock", "test"):
            self.api_url = ""
            self.api_key = "mock-key"
        elif self.provider == "dashscope":
            root = (base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
            self.api_url = f"{root}/chat/completions"
            self.api_key = api_key or DASHSCOPE_API_KEY or os.environ.get("DASHSCOPE_API_KEY", "")
        elif self.provider == "deepseek":
            root = (base_url or "https://api.deepseek.com/v1").rstrip("/")
            self.api_url = f"{root}/chat/completions"
            self.api_key = api_key or DEEPSEEK_API_KEY or os.environ.get("DEEPSEEK_API_KEY", "")
        elif self.provider == "openai":
            root = (base_url or OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
            self.api_url = root if root.endswith("/chat/completions") else f"{root}/chat/completions"
            self.api_key = api_key or OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
        elif self.provider == "gemini":
            self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            self.api_key = api_key or GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        else:
            raise ValueError(f"未知的 LLM Provider: {provider} (支持: dashscope, deepseek, openai, gemini, mock)")

    @staticmethod
    def _split_into_chunks(text: str, max_chars: int = 5000) -> List[str]:
        """
        按自然段落安全切分长文档，确保不截断代码块 (```) 与块级公式 ($$)
        """
        text = text.strip()
        if len(text) <= max_chars:
            return [text] if text else []

        # 将文本按空行切分为逻辑块，同时保护多行代码块与 $$ 块
        raw_lines = text.splitlines()
        blocks: List[str] = []
        buf: List[str] = []
        in_code = False
        in_math = False

        for line in raw_lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code = not in_code
            elif stripped == "$$" and not in_code:
                in_math = not in_math

            if stripped == "" and not in_code and not in_math:
                if buf:
                    blocks.append("\n".join(buf))
                    buf = []
            else:
                buf.append(line)
        if buf:
            blocks.append("\n".join(buf))

        chunks: List[str] = []
        cur_blocks: List[str] = []
        cur_len = 0

        for blk in blocks:
            blk_len = len(blk) + 2
            if cur_blocks and (cur_len + blk_len > max_chars):
                chunks.append("\n\n".join(cur_blocks))
                cur_blocks = [blk]
                cur_len = blk_len
            else:
                cur_blocks.append(blk)
                cur_len += blk_len

        if cur_blocks:
            chunks.append("\n\n".join(cur_blocks))

        return chunks

    def _call_llm_raw(self, system_prompt: str, user_text: str) -> str:
        """执行单次大模型请求（带指数退避重试与截断检测）"""
        if not self.api_key:
            raise ValueError(f"未配置 {self.provider} 的 API 密钥，请在 .env 或环境变量中设置！")

        if self.provider == "gemini":
            url = f"{self.api_url}?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_text}"}]}],
                "generationConfig": {"temperature": 0.1},
            }
            for attempt in range(3):
                try:
                    resp = requests.post(url, json=payload, timeout=(15, 150))
                    if resp.status_code == 200:
                        data = resp.json()
                        cand = (data.get("candidates") or [{}])[0]
                        if cand.get("finishReason") == "MAX_TOKENS":
                            raise LLMTruncatedError("Gemini 输出触及 MAX_TOKENS 上限")
                        parts = cand.get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
                        raise RuntimeError("Gemini 返回空内容")
                    elif resp.status_code in _NON_RETRYABLE_STATUS:
                        raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text}")
                    else:
                        time.sleep(3 * (attempt + 1))
                except requests.exceptions.RequestException as e:
                    if attempt == 2:
                        raise e
                    time.sleep(3 * (attempt + 1))
            raise RuntimeError("Gemini 请求重试耗尽")

        # OpenAI / DashScope / DeepSeek 兼容格式
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.1,
        }

        for attempt in range(3):
            try:
                resp = requests.post(self.api_url, headers=headers, json=payload, timeout=(15, 150))
                if resp.status_code == 200:
                    choice = resp.json()["choices"][0]
                    if choice.get("finish_reason") == "length":
                        raise LLMTruncatedError("模型输出达到单次最大长度被截断")
                    content = (choice.get("message", {}).get("content") or "").strip()
                    if content:
                        return content
                    raise RuntimeError("大模型返回空学术内容！")
                elif resp.status_code in _NON_RETRYABLE_STATUS:
                    raise RuntimeError(f"LLM HTTP {resp.status_code}: {resp.text}")
                else:
                    time.sleep(3 * (attempt + 1))
            except requests.exceptions.RequestException as e:
                if attempt == 2:
                    raise e
                time.sleep(3 * (attempt + 1))

        raise RuntimeError("大模型 API 重试 3 次均失败")

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        content = content.strip()
        if content.startswith("```markdown"):
            content = content[11:].strip()
        elif content.startswith("```md"):
            content = content[5:].strip()
        elif content.startswith("```"):
            content = content[3:].strip()
        if content.endswith("```"):
            content = content[:-3].strip()
        return content

    def _process_single_chunk(
        self,
        chunk_text: str,
        system_prompt: str,
        doc_name: str,
        chunk_idx: int,
        total_chunks: int,
        use_math_sentinel: bool,
        bilingual: bool,
        depth: int = 0,
    ) -> str:
        """处理单个语义块：支持公式哨兵隔离、段落锚点双语对齐、以及截断自动折半重试"""
        if self.provider in ("mock", "test"):
            if bilingual:
                blocks = [b.strip() for b in chunk_text.split("\n\n") if b.strip()]
                interleaved = []
                for b in blocks:
                    if _is_pure_structural_block(b):
                        interleaved.append(b)
                    else:
                        interleaved.append(f'<div class="bilingual-orig">\n\n{b}\n\n</div>\n\n[译文] {b}')
                return "\n\n".join(interleaved)
            return chunk_text

        working_text = chunk_text
        orig_blocks: List[str] = []

        # 1. 双语模式注入 1:1 段落对齐锚点（原文本身保存一份纯净副本）
        if bilingual:
            working_text, orig_blocks = inject_paragraph_anchors(working_text)

        # 2. 公式物理哨兵隔离（在锚点之后，防止破坏公式）
        math_tokens: Dict[str, str] = {}
        if use_math_sentinel:
            working_text, math_tokens = isolate_math(working_text)

        chunk_tag = f"（第 {chunk_idx + 1}/{total_chunks} 部分）" if total_chunks > 1 else ""
        user_msg = f"=== 原始学术素材（文档：{doc_name}{chunk_tag}） ===\n{working_text}"

        try:
            out = self._call_llm_raw(system_prompt, user_msg)
        except LLMTruncatedError:
            # 截断自动折半重试（最多递归拆 3 次）
            if depth < 3 and len(chunk_text) > 800:
                logger.warning(f"分块 {chunk_idx + 1} 输出截断，自动折半重试 (depth={depth + 1})...")
                sub_chunks = self._split_into_chunks(chunk_text, max_chars=len(chunk_text) // 2)
                if len(sub_chunks) > 1:
                    parts = [
                        self._process_single_chunk(
                            sc, system_prompt, doc_name, chunk_idx, total_chunks,
                            use_math_sentinel, bilingual, depth + 1
                        )
                        for sc in sub_chunks
                    ]
                    return "\n\n".join(parts)
            raise

        out = self._strip_code_fence(out)

        # 3. 无损回填并校验公式
        if use_math_sentinel and math_tokens:
            out, missing = verify_and_recover_math(out, math_tokens)
            if missing > 0:
                logger.warning(f"分块 {chunk_idx + 1} 检测到 {missing} 处公式被模型遗漏，已自动兜底找回。")

        # 4. 组装 1:1 精准双语对照
        if bilingual and orig_blocks:
            trans_blocks = split_by_paragraph_anchors(out, len(orig_blocks))
            if trans_blocks is not None:
                paired = []
                for orig_b, trans_b in zip(orig_blocks, trans_blocks):
                    if _is_pure_structural_block(orig_b):
                        paired.append(orig_b)
                    else:
                        paired.append(f'<div class="bilingual-orig">\n\n{orig_b}\n\n</div>\n\n{trans_b}')
                return "\n\n".join(paired)
            else:
                # 降级：锚点不完整时做块级对照，保证零内容丢失
                clean_trans = strip_paragraph_anchors(out)
                return f'<div class="bilingual-orig">\n\n{chunk_text}\n\n</div>\n\n{clean_trans}'

        return strip_paragraph_anchors(out)

    def process_academic_task(
        self,
        raw_content: str,
        task: str = "note",
        doc_name: str = "",
        glossary: Optional[dict] = None,
        bilingual: bool = False,
        target_lang: str = "zh-CN",
        use_math_sentinel: Optional[bool] = None,
    ) -> str:
        """
        统一学术语义推理与长文档翻译入口：
        - 短文档自动单块处理；长文档（论文/教材）自动语义分块并发处理。
        - paper/textbook 默认开启公式哨兵物理隔离，note 默认允许大模型修复手写 OCR 断裂公式。
        """
        if not raw_content or not raw_content.strip():
            return ""

        task_key = task.lower().strip()
        if use_math_sentinel is None:
            use_math_sentinel = task_key in ("paper", "academic_paper", "textbook", "textbook_translation")

        # Mock 离线模式快速返回完整结构（同时测试分块和双语逻辑）
        if self.provider in ("mock", "test"):
            chunks = self._split_into_chunks(raw_content, max_chars=self.max_chunk_chars)
            processed_body = "\n\n".join(
                self._process_single_chunk(c, "", doc_name, idx, len(chunks), use_math_sentinel, bilingual)
                for idx, c in enumerate(chunks)
            )
            if processed_body.lstrip().startswith("#"):
                return processed_body
            return f"# {doc_name or '学术文档'}\n\n{processed_body}"

        system_prompt = get_task_prompt(task_key, target_lang=target_lang)

        if glossary:
            terms_lines = "\n".join([f"- {k} -> {v}" for k, v in glossary.items()])
            system_prompt += f"\n\n【专业术语强制规范表（必须严格遵循）】：\n{terms_lines}"

        if bilingual:
            system_prompt += (
                "\n\n【双语锚点规范】：输入文本包含 `PARA0ZZZ`、`PARA1ZZZ` 等段落锚点。"
                "你只需要输出目标语言译文，并在每段译文正上方原样保留对应的 `PARAxZZZ` 锚点，严禁遗漏、合并或复述英文原文。"
            )

        chunks = self._split_into_chunks(raw_content, max_chars=self.max_chunk_chars)
        total_chunks = len(chunks)

        if total_chunks == 1:
            result = self._process_single_chunk(
                chunks[0], system_prompt, doc_name, 0, 1, use_math_sentinel, bilingual
            )
        else:
            logger.info(f"长文档检测到 {len(raw_content)} 字符，已智能切分为 {total_chunks} 块并发推理...")
            def _worker(args):
                idx, txt = args
                return idx, self._process_single_chunk(
                    txt, system_prompt, doc_name, idx, total_chunks, use_math_sentinel, bilingual
                )

            ordered: Dict[int, str] = {}
            with ThreadPoolExecutor(max_workers=min(self.max_workers, total_chunks)) as pool:
                for idx, res in pool.map(_worker, enumerate(chunks)):
                    ordered[idx] = res
            result = "\n\n".join(ordered[i] for i in range(total_chunks))

        # 通用去噪：清除可能残留的客套结束语
        result = re.sub(r'>\s*📝\s*\*\*下节预告\*\*.*', '', result)
        result = re.sub(r'\*?（?讲义完）?\*?', '', result)

        return result.strip()
