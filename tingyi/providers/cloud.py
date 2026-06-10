# -*- coding: utf-8 -*-
"""云端 ASR：OpenAI 兼容 Whisper API。"""

from __future__ import annotations

import time
from pathlib import Path

from tingyi.providers.base import AsrProvider, TranscribeResult
from tingyi.settings import CloudAsrConfig


class CloudAsrProvider(AsrProvider):
    def __init__(self, config: CloudAsrConfig) -> None:
        self.config = config
        self.name = f"cloud:{config.provider.value}"

    def is_available(self) -> bool:
        return bool(self.config.api_key.strip())

    def transcribe(self, audio_path: Path, language: str = "zh") -> TranscribeResult:
        if not self.is_available():
            raise RuntimeError("未配置云端 API Key（TINGYI_CLOUD_API_KEY 或 OPENAI_API_KEY）")
        if not audio_path.exists():
            raise FileNotFoundError(audio_path)

        started = time.perf_counter()
        # TODO: openai.Audio.transcriptions.create 或 httpx 直调兼容端点
        text = self._stub_transcribe(audio_path, language)
        elapsed = (time.perf_counter() - started) * 1000
        return TranscribeResult(text=text, provider=self.name, latency_ms=elapsed)

    def _stub_transcribe(self, audio_path: Path, language: str) -> str:
        return (
            f"[云端识别占位 · {self.config.provider.value} · {self.config.model}] "
            f"音频={audio_path.name}，lang={language}。"
        )
