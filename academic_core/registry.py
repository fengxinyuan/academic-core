# -*- coding: utf-8 -*-
"""
academic_core 统一动态注册表 (Dynamic Registry)
遵循开闭原则 (Open-Closed Principle)，支持转换器、视觉引擎、导出器的可插拔式扩展。
"""

from typing import Dict, Type, Any, Callable

class Registry:
    def __init__(self, name: str):
        self.name = name
        self._entries: Dict[str, Any] = {}

    def register(self, key: str):
        """
        装饰器注册
        """
        def decorator(cls_or_func):
            self._entries[key.lower()] = cls_or_func
            return cls_or_func
        return decorator

    def get(self, key: str, default: Any = None) -> Any:
        return self._entries.get(key.lower(), default)

    def list_keys(self) -> list[str]:
        return list(self._entries.keys())

    def contains(self, key: str) -> bool:
        return key.lower() in self._entries

# 全局三大多态注册中心
CONVERTER_REGISTRY = Registry("Converters")
VISION_ENGINE_REGISTRY = Registry("VisionEngines")
EXPORTER_REGISTRY = Registry("Exporters")

