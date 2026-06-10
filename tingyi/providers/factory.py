# -*- coding: utf-8 -*-
"""按配置组装识别管线：本地为主，云端可选 / 回退。"""

from __future__ import annotations

from pathlib import Path

from tingyi.providers.base import AsrProvider, TranscribeResult
from tingyi.providers.cloud import CloudAsrProvider
from tingyi.providers.local import LocalAsrProvider
from tingyi.settings import AppSettings, AsrMode


class HybridAsrPipeline:
    """本地优先；HYBRID 模式下本地失败且云端可用时回退。"""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.local = LocalAsrProvider(settings.local)
        self.cloud = CloudAsrProvider(settings.cloud)

    def transcribe(self, audio_path: Path) -> TranscribeResult:
        mode = self.settings.asr_mode
        lang = self.settings.local.language

        if mode == AsrMode.CLOUD:
            return self._transcribe_cloud(audio_path, lang, fallback=False)

        if mode == AsrMode.LOCAL:
            return self._transcribe_local(audio_path, lang)

        # HYBRID
        if self.local.is_available():
            try:
                return self._transcribe_local(audio_path, lang)
            except Exception:
                if self.cloud.is_available():
                    return self._transcribe_cloud(audio_path, lang, fallback=True)
                raise

        if self.cloud.is_available():
            return self._transcribe_cloud(audio_path, lang, fallback=False)

        raise RuntimeError(
            "无可用识别引擎：请下载本地模型到 models/，或在 .env 中配置云端 API Key。"
        )

    def _transcribe_local(self, audio_path: Path, lang: str) -> TranscribeResult:
        return self.local.transcribe(audio_path, language=lang)

    def _transcribe_cloud(
        self, audio_path: Path, lang: str, *, fallback: bool
    ) -> TranscribeResult:
        result = self.cloud.transcribe(audio_path, language=lang)
        if fallback:
            result.is_fallback = True
        return result


def create_asr_pipeline(settings: AppSettings | None = None) -> AsrProvider | HybridAsrPipeline:
    settings = settings or AppSettings.from_env()
    return HybridAsrPipeline(settings)
