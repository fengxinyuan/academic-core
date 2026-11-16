# -*- coding: utf-8 -*-
"""
学术语义大模型推理中枢 (Academic LLM Engine)
支持 Qwen (DashScope) / DeepSeek / OpenAI / Claude 及离线 Mock 引擎
"""

import time
import requests
import re
from academic_core.config import DASHSCOPE_API_KEY, DEEPSEEK_API_KEY, OPENAI_API_KEY
from academic_core.llm_reasoning.prompts import get_task_prompt

class AcademicLLMEngine:
    def __init__(self, provider: str = "dashscope", model: str = "qwen-plus"):
        self.provider = provider.lower()
        self.model = model

        if self.provider in ("mock", "test"):
            self.api_url = ""
            self.api_key = "mock-key"
        elif self.provider == "dashscope":
            self.api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            self.api_key = DASHSCOPE_API_KEY
        elif self.provider == "deepseek":
            self.api_url = "https://api.deepseek.com/v1/chat/completions"
            self.api_key = DEEPSEEK_API_KEY
        elif self.provider == "openai":
            self.api_url = "https://api.openai.com/v1/chat/completions"
            self.api_key = OPENAI_API_KEY
        else:
            raise ValueError(f"未知的 LLM Provider: {provider} (支持: dashscope, deepseek, openai, mock)")

        if not self.api_key and self.provider not in ("mock", "test"):
            raise ValueError(f"未配置 {provider} 的 API 凭据，请检查 .env！")

    def process_academic_task(
        self,
        raw_content: str,
        task: str = "note",
        doc_name: str = "",
        glossary: dict = None,
        bilingual: bool = False
    ) -> str:
        # Mock 离线仿真分支
        if self.provider in ("mock", "test"):
            return (
                f"# {doc_name or '学术核心讲义'}\n\n"
                f"> **体裁模式**：{task} | 术语对齐约束: {bool(glossary)} | 双语模式: {bilingual}\n\n"
                f"### 1. 核心数学定理与结构推导\n\n"
                f"{raw_content}\n\n"
                f"### 📚 本讲核心要点小结 (Summary)\n\n"
                f"1. 严格建立了代数映射与空间维数结构。\n"
                f"2. 矩阵表示与线性变换自然自洽。"
            )

        prompt_sys = get_task_prompt(task)

        # 注入专业术语表约束
        if glossary:
            terms_lines = "\n".join([f"- {k} -> {v}" for k, v in glossary.items()])
            prompt_sys += f"\n\n【专业术语强制规范表（必须严格遵循，不得擅自发挥）】：\n{terms_lines}"

        # 注入双语对照指令
        if bilingual:
            prompt_sys += "\n\n【输出排版要求】：采用双语段落对照模式，每一段先给出英文原文，随后紧跟严谨的中文学术精译。"

        user_message = f"{prompt_sys}\n\n=== 原始学术素材（标题/文件名：{doc_name}） ===\n{raw_content}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.1
        }

        content = None
        for attempt in range(3):
            try:
                resp = requests.post(self.api_url, headers=headers, json=payload, timeout=(15, 120))
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"].strip()
                    break
                elif resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(3 * (attempt + 1))
                else:
                    raise RuntimeError(f"LLM HTTP {resp.status_code}: {resp.text}")
            except requests.exceptions.RequestException as e:
                if attempt == 2:
                    raise e
                time.sleep(3 * (attempt + 1))

        if not content:
            raise RuntimeError("大模型返回空学术内容！")

        # 剥离 Markdown 代码围栏
        if content.startswith("```markdown"): content = content[11:].strip()
        elif content.startswith("```"): content = content[3:].strip()
        if content.endswith("```"): content = content[:-3].strip()

        # 清洗套话大词与冗余标记
        content = re.sub(r'^#\s*高等代数(?:讲义)?[：:]\s*', '# ', content, flags=re.MULTILINE)
        content = re.sub(r'>\s*\*\*课程主题\*\*[\s\S]*?---\s*\n', '', content)
        content = re.sub(r'>\s*📝\s*\*\*下节预告\*\*.*', '', content)
        content = re.sub(r'（?讲义完）?', '', content)
        content = re.sub(r'\*（?讲义完）?\*', '', content)

        return content
