# -*- coding: utf-8 -*-
"""
任务状态与断点续传管理中心 (Task Tracker & Checkpoint Engine)
支持大批量多文档、长篇教材处理过程中的进度持久化与秒级断点续传。
"""

import os
import json
import time
from typing import Dict, Any, List

class TaskTracker:
    def __init__(self, checkpoint_file: str = ".academic_checkpoint.json"):
        self.checkpoint_file = checkpoint_file
        self.state: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {"completed": {}, "failed": {}, "last_updated": time.time()}
        return {"completed": {}, "failed": {}, "last_updated": time.time()}

    def _save(self):
        self.state["last_updated"] = time.time()
        try:
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def is_completed(self, doc_key: str) -> bool:
        return doc_key in self.state.get("completed", {})

    def mark_completed(self, doc_key: str, output_path: str, metadata: dict = None):
        if "completed" not in self.state:
            self.state["completed"] = {}
        self.state["completed"][doc_key] = {
            "output_path": output_path,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        if "failed" in self.state and doc_key in self.state["failed"]:
            del self.state["failed"][doc_key]
        self._save()

    def mark_failed(self, doc_key: str, error: str):
        if "failed" not in self.state:
            self.state["failed"] = {}
        self.state["failed"][doc_key] = {
            "error": error,
            "timestamp": time.time()
        }
        self._save()

    def get_progress(self, all_keys: List[str]) -> Dict[str, Any]:
        total = len(all_keys)
        done = sum(1 for k in all_keys if self.is_completed(k))
        return {
            "total": total,
            "done": done,
            "remaining": total - done,
            "percent": round((done / max(1, total)) * 100, 1)
        }

    def reset(self):
        self.state = {"completed": {}, "failed": {}, "last_updated": time.time()}
        if os.path.exists(self.checkpoint_file):
            try:
                os.remove(self.checkpoint_file)
            except Exception:
                pass

