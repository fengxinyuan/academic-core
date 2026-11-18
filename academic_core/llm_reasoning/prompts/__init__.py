# -*- coding: utf-8 -*-
from academic_core.llm_reasoning.prompts.note_task import NOTE_TASK_PROMPT
from academic_core.llm_reasoning.prompts.textbook_task import TEXTBOOK_TASK_PROMPT
from academic_core.llm_reasoning.prompts.paper_task import PAPER_TASK_PROMPT

TASK_PROMPTS = {
    "note": NOTE_TASK_PROMPT,
    "handwritten_notes": NOTE_TASK_PROMPT,
    "textbook": TEXTBOOK_TASK_PROMPT,
    "textbook_translation": TEXTBOOK_TASK_PROMPT,
    "paper": PAPER_TASK_PROMPT,
    "academic_paper": PAPER_TASK_PROMPT,
}

LANG_LABELS = {
    "zh-cn": "简体中文 (Simplified Chinese)",
    "zh": "简体中文 (Simplified Chinese)",
    "zh-tw": "繁体中文 (Traditional Chinese)",
    "en": "Academic English",
    "ja": "日本語 (Academic Japanese)",
    "ko": "한국어 (Academic Korean)",
    "fr": "Français académique",
    "de": "Wissenschaftliches Deutsch",
}


def get_task_prompt(task_name: str, target_lang: str = "zh-CN") -> str:
    template = TASK_PROMPTS.get(task_name.lower(), NOTE_TASK_PROMPT)
    lang_display = LANG_LABELS.get(target_lang.lower(), target_lang)
    return template.format(target_lang=lang_display)
