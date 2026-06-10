# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from tingyi.settings import LocalAsrConfig


class FasterWhisperEngine:
    def __init__(self, config: LocalAsrConfig) -> None:
        self.config = config
        self._model = None

    @staticmethod
    def is_installed() -> bool:
        try:
            import faster_whisper  # noqa: F401

            return True
        except ImportError:
            return False

    def _get_model(self):
        if self._model is not None:
            return self._model
        from faster_whisper import WhisperModel

        device = self.config.device
        if device == "cuda":
            compute = self.config.compute_type if self.config.compute_type != "int8" else "float16"
        else:
            compute = self.config.compute_type

        self._model = WhisperModel(
            self.config.model_size,
            device=device,
            compute_type=compute,
            download_root=str(self.config.model_dir / "faster-whisper"),
        )
        return self._model

    def transcribe(self, audio_path: Path, language: str) -> str:
        model = self._get_model()
        lang = None if language in ("auto", "") else language
        segments, _info = model.transcribe(
            str(audio_path),
            language=lang,
            vad_filter=True,
            beam_size=1,
        )
        return "".join(seg.text for seg in segments).strip()
