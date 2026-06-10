# -*- coding: utf-8 -*-
"""
端到端管线（Phase 1）：
  热键录音 → VAD 切分（可选）→ ASR → 预览/粘贴

当前仅串联配置与识别，录音/热键待下一迭代实现。
"""

from __future__ import annotations

from pathlib import Path

from tingyi.providers.factory import HybridAsrPipeline, create_asr_pipeline
from tingyi.providers.base import TranscribeResult
from tingyi.settings import AppSettings


class TingyiPipeline:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or AppSettings.from_env()
        self.asr: HybridAsrPipeline = create_asr_pipeline(self.settings)  # type: ignore[assignment]

    def transcribe_file(self, audio_path: Path) -> TranscribeResult:
        return self.asr.transcribe(audio_path)

    def status_summary(self) -> str:
        s = self.settings
        local_ok = self.asr.local.is_available()
        cloud_ok = self.asr.cloud.is_available()
        return (
            f"模式={s.asr_mode.value} | "
            f"本地({s.local.engine.value})={'可用' if local_ok else '待装模型'} | "
            f"云端({'已配置' if cloud_ok else '未配置'})"
        )
