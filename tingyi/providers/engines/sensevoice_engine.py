# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from tingyi.audio.wav import read_wav_mono_16k
from tingyi.models.paths import sensevoice_model_files, sherpa_relative_path
from tingyi.settings import LocalAsrConfig


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
            model=sherpa_relative_path(model_path),
            tokens=sherpa_relative_path(tokens_path),
            num_threads=2,
            use_itn=True,
            language=lang,
        )
        return self._recognizer

    def transcribe(self, audio_path: Path, language: str) -> str:
        samples, sample_rate = read_wav_mono_16k(audio_path)
        return self.transcribe_samples(samples, sample_rate, language)

    def transcribe_samples(
        self, samples, sample_rate: int, language: str
    ) -> str:
        recognizer = self._get_recognizer()
        stream = recognizer.create_stream()
        stream.accept_waveform(sample_rate, samples)
        recognizer.decode_stream(stream)
        return stream.result.text.strip()
