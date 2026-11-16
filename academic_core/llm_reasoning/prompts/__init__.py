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

def get_task_prompt(task_name: str) -> str:
    return TASK_PROMPTS.get(task_name.lower(), NOTE_TASK_PROMPT)

