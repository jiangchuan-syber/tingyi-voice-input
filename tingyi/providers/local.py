# -*- coding: utf-8 -*-
"""本地 ASR：SenseVoice（首选）/ faster-whisper（备选）。"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from tingyi.providers.base import AsrProvider, TranscribeResult
from tingyi.providers.engines.faster_whisper_engine import FasterWhisperEngine
from tingyi.providers.engines.sensevoice_engine import SenseVoiceEngine
from tingyi.settings import LocalAsrConfig, LocalEngine


class LocalAsrProvider(AsrProvider):
    def __init__(self, config: LocalAsrConfig) -> None:
        self.config = config
        self.name = f"local:{config.engine.value}"
        self._sensevoice = SenseVoiceEngine(config)
        self._faster_whisper = FasterWhisperEngine(config)

    def is_available(self) -> bool:
        if self.config.engine == LocalEngine.SENSEVOICE:
            return SenseVoiceEngine.is_installed() and SenseVoiceEngine.has_model()
        return FasterWhisperEngine.is_installed()

    def transcribe(self, audio_path: Path, language: str = "zh") -> TranscribeResult:
        if not audio_path.exists():
            raise FileNotFoundError(audio_path)

        started = time.perf_counter()
        lang = language or self.config.language

        if self.config.engine == LocalEngine.SENSEVOICE:
            text = self._sensevoice.transcribe(audio_path, lang)
        else:
            text = self._faster_whisper.transcribe(audio_path, lang)

        elapsed = (time.perf_counter() - started) * 1000
        return TranscribeResult(text=text, provider=self.name, latency_ms=elapsed)

    def transcribe_samples(
        self, samples: np.ndarray, sample_rate: int = 16000, language: str = "zh"
    ) -> TranscribeResult:
        started = time.perf_counter()
        lang = language or self.config.language

        if self.config.engine == LocalEngine.SENSEVOICE:
            text = self._sensevoice.transcribe_samples(samples, sample_rate, lang)
        else:
            raise NotImplementedError("faster-whisper 暂不支持内存流式，请使用文件识别。")

        elapsed = (time.perf_counter() - started) * 1000
        return TranscribeResult(text=text, provider=self.name, latency_ms=elapsed)
