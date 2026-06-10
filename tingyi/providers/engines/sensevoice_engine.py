# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from tingyi.audio.wav import read_wav_mono_16k
from tingyi.models.paths import sensevoice_model_files
from tingyi.settings import ROOT, LocalAsrConfig


def _sherpa_path(path: Path) -> str:
    """sherpa-onnx 在 Windows 上对含中文等非 ASCII 的绝对路径支持不佳，改用相对路径。"""
    try:
        rel = path.relative_to(ROOT)
        return rel.as_posix()
    except ValueError:
        return path.as_posix()


class SenseVoiceEngine:
    def __init__(self, config: LocalAsrConfig) -> None:
        self.config = config
        self._recognizer = None

    @staticmethod
    def is_installed() -> bool:
        try:
            import sherpa_onnx  # noqa: F401

            return True
        except ImportError:
            return False

    @staticmethod
    def has_model() -> bool:
        return sensevoice_model_files() is not None

    def _get_recognizer(self):
        if self._recognizer is not None:
            return self._recognizer

        files = sensevoice_model_files()
        if not files:
            raise FileNotFoundError(
                "未找到 SenseVoice 模型。请运行: python -m tingyi.models.download --sensevoice"
            )

        import sherpa_onnx

        model_path, tokens_path = files
        lang = "" if self.config.language in ("auto", "") else self.config.language
        self._recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=_sherpa_path(model_path),
            tokens=_sherpa_path(tokens_path),
            num_threads=2,
            use_itn=True,
            language=lang,
        )
        return self._recognizer

    def transcribe(self, audio_path: Path, language: str) -> str:
        recognizer = self._get_recognizer()
        samples, sample_rate = read_wav_mono_16k(audio_path)
        stream = recognizer.create_stream()
        stream.accept_waveform(sample_rate, samples)
        recognizer.decode_stream(stream)
        return stream.result.text.strip()
