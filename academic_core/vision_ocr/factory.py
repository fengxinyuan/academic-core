# -*- coding: utf-8 -*-
"""
OCR / 视觉引擎统一工厂 (Vision Engine Factory)
按模型标识自动路由并实例化对应视觉引擎
"""

from academic_core.vision_ocr.base import BaseVisionEngine
from academic_core.vision_ocr.qwen_vl_engine import QwenVLEngine
from academic_core.vision_ocr.openai_vision_engine import OpenAIVisionEngine
from academic_core.vision_ocr.gemini_vision_engine import GeminiVisionEngine
from academic_core.vision_ocr.mineru_engine import MinerUEngine
from academic_core.vision_ocr.mock_engine import MockVisionEngine
from academic_core.registry import VISION_ENGINE_REGISTRY

# 注册内置引擎
VISION_ENGINE_REGISTRY.register("qwen")(QwenVLEngine)
VISION_ENGINE_REGISTRY.register("qwen-vl-ocr")(QwenVLEngine)
VISION_ENGINE_REGISTRY.register("qwen-vl-max")(QwenVLEngine)
VISION_ENGINE_REGISTRY.register("openai")(OpenAIVisionEngine)
VISION_ENGINE_REGISTRY.register("gpt-4o")(OpenAIVisionEngine)
VISION_ENGINE_REGISTRY.register("gpt-4o-mini")(OpenAIVisionEngine)
VISION_ENGINE_REGISTRY.register("gemini")(GeminiVisionEngine)
VISION_ENGINE_REGISTRY.register("mineru")(MinerUEngine)
VISION_ENGINE_REGISTRY.register("mock")(MockVisionEngine)

def get_vision_engine(engine_name: str = "qwen-vl-ocr", cache_dir: str = "cache_ocr", **kwargs) -> BaseVisionEngine:
    name = engine_name.lower().strip()

    # 1. 优先查动态注册表
    if VISION_ENGINE_REGISTRY.contains(name):
        cls_ = VISION_ENGINE_REGISTRY.get(name)
        if cls_ is MockVisionEngine:
            return MockVisionEngine(cache_dir=cache_dir, **kwargs)
        elif cls_ is QwenVLEngine:
            return QwenVLEngine(model_name=engine_name, cache_dir=cache_dir)
        elif cls_ is OpenAIVisionEngine:
            return OpenAIVisionEngine(model_name=engine_name, cache_dir=cache_dir, **kwargs)
        elif cls_ is GeminiVisionEngine:
            return GeminiVisionEngine(model_name=engine_name, cache_dir=cache_dir, **kwargs)
        elif cls_ is MinerUEngine:
            return MinerUEngine(cache_dir=cache_dir, **kwargs)

    # 2. 启发式模糊匹配
    if "mock" in name or "dummy" in name or "test" in name:
        return MockVisionEngine(cache_dir=cache_dir, **kwargs)
    elif "mineru" in name:
        return MinerUEngine(cache_dir=cache_dir, **kwargs)
    elif "gpt" in name or "openai" in name:
        return OpenAIVisionEngine(model_name=engine_name, cache_dir=cache_dir, **kwargs)
    elif "gemini" in name:
        return GeminiVisionEngine(model_name=engine_name, cache_dir=cache_dir, **kwargs)
    elif "qwen" in name:
        return QwenVLEngine(model_name=engine_name, cache_dir=cache_dir)

    # 默认采用通义千问高精手写数学模型
    return QwenVLEngine(model_name="qwen-vl-ocr", cache_dir=cache_dir)
