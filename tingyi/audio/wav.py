# -*- coding: utf-8 -*-
"""读取音频为 16kHz float32 单声道（SenseVoice 等需要）。"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def read_wav_mono_16k(path: Path) -> tuple[np.ndarray, int]:
    """返回 (samples float32 [-1,1], sample_rate)。"""
    try:
        import soundfile as sf  # type: ignore[import-untyped]

        data, sr = sf.read(str(path), dtype="float32", always_2d=False)
    except ImportError:
        data, sr = _read_wav_stdlib(path)

    if data.ndim > 1:
        data = data.mean(axis=1)

    if sr != 16000:
        data = _resample(data, sr, 16000)
        sr = 16000

    return data.astype(np.float32), sr


def _read_wav_stdlib(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        n = wf.getnframes()
        raw = wf.readframes(n)
        width = wf.getsampwidth()
        channels = wf.getnchannels()

    if width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif width == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"不支持的 WAV 位深: {width} bytes")

    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, sr


def _resample(data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return data
    duration = len(data) / orig_sr
    target_len = int(duration * target_sr)
    x_old = np.linspace(0, 1, num=len(data), endpoint=False)
    x_new = np.linspace(0, 1, num=target_len, endpoint=False)
    return np.interp(x_new, x_old, data).astype(np.float32)
