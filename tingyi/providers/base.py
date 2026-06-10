# -*- coding: utf-8 -*-
"""ASR 提供方抽象：本地与云端统一接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranscribeResult:
    text: str
    provider: str  # local:sensevoice | cloud:openai 等
    latency_ms: float = 0.0
    is_fallback: bool = False


class AsrProvider(ABC):
    name: str

    @abstractmethod
    def is_available(self) -> bool:
        """模型/API 是否可用。"""

    @abstractmethod
    def transcribe(self, audio_path: Path, language: str = "zh") -> TranscribeResult:
        """对整段音频文件做识别（Phase 1：batch，非流式）。"""
