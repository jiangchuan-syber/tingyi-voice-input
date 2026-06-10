# -*- coding: utf-8 -*-
"""Silero VAD：检测说话开始/结束，自动截断录音。"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from tingyi.audio.record import default_input_device_label
from tingyi.models.download import download_silero_vad
from tingyi.models.paths import sherpa_relative_path, silero_vad_model_file
from tingyi.settings import VadConfig

SAMPLE_RATE = 16000


def _open_mic_stream():
    import sounddevice as sd

    try:
        return sd.InputStream(channels=1, dtype="float32", samplerate=SAMPLE_RATE)
    except Exception as exc:
        raise RuntimeError(
            "无法打开麦克风。请在 Cursor 集成终端或系统 PowerShell 中运行，"
            "并检查 Windows 隐私设置 → 麦克风是否允许终端/Python 访问。"
        ) from exc


def _create_vad(config: VadConfig, *, max_record_seconds: float = 60.0):
    import sherpa_onnx

    model_path = silero_vad_model_file()
    if model_path is None:
        model_path = download_silero_vad()

    vad_config = sherpa_onnx.VadModelConfig()
    vad_config.silero_vad.model = sherpa_relative_path(model_path)
    vad_config.silero_vad.threshold = 0.5
    vad_config.silero_vad.min_speech_duration = config.min_speech_ms / 1000.0
    vad_config.silero_vad.min_silence_duration = config.min_silence_ms / 1000.0
    vad_config.silero_vad.max_speech_duration = max_record_seconds
    vad_config.sample_rate = config.sample_rate

    return sherpa_onnx.VoiceActivityDetector(vad_config, buffer_size_in_seconds=60)


def record_with_vad_to_wav(
    path: Path,
    *,
    config: VadConfig | None = None,
    max_wait_seconds: float = 20.0,
    max_record_seconds: float = 60.0,
) -> Path:
    """等待用户开口，说完（静音）后自动结束并保存 WAV。"""
    import soundfile as sf

    vad_cfg = config or VadConfig()
    sample_rate = vad_cfg.sample_rate
    path.parent.mkdir(parents=True, exist_ok=True)

    vad = _create_vad(vad_cfg, max_record_seconds=max_record_seconds)
    window_size = vad.config.silero_vad.window_size
    chunk_samples = int(0.1 * sample_rate)

    print(f"麦克风：{default_input_device_label()}")
    print("请开始说话（检测到语音后自动录音，停顿约 0.5 秒后结束）…")

    speech_started = False
    wait_started = time.monotonic()
    speech_started_at: float | None = None
    offset = 0
    buffer = np.array([], dtype=np.float32)

    with _open_mic_stream() as stream:
        while True:
            if not speech_started and time.monotonic() - wait_started > max_wait_seconds:
                raise TimeoutError("等待超时：未检测到语音，请检查麦克风或提高音量。")

            if speech_started and speech_started_at is not None:
                if time.monotonic() - speech_started_at > max_record_seconds:
                    raise TimeoutError("录音过长，已自动停止。请缩短单次说话长度。")

            samples, _ = stream.read(chunk_samples)
            chunk = samples.reshape(-1).astype(np.float32, copy=False)
            buffer = np.concatenate([buffer, chunk])

            while offset + window_size <= len(buffer):
                vad.accept_waveform(buffer[offset : offset + window_size])
                offset += window_size

                if vad.is_speech_detected() and not speech_started:
                    speech_started = True
                    speech_started_at = time.monotonic()
                    print("正在听…")

                if speech_started and not vad.empty():
                    segment = np.array(vad.front.samples, dtype=np.float32)
                    vad.pop()
                    if segment.size == 0:
                        raise RuntimeError("未录到有效语音，请重试。")
                    peak = float(np.max(np.abs(segment)))
                    if peak < 0.01:
                        print("（提示：音量很低，请检查麦克风是否静音或未选对设备）")
                    sf.write(str(path), segment, sample_rate)
                    print("检测到停顿，录音结束。")
                    return path

            if not speech_started and len(buffer) > 10 * window_size:
                offset -= len(buffer) - 10 * window_size
                buffer = buffer[-10 * window_size :]
