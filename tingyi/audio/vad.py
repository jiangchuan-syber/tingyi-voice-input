# -*- coding: utf-8 -*-
"""Silero VAD：检测说话开始/结束，自动截断录音。"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

import numpy as np

from tingyi.audio.record import default_input_device_label
from tingyi.models.download import download_silero_vad
from tingyi.models.paths import sherpa_relative_path, silero_vad_model_file
from tingyi.settings import VadConfig

SAMPLE_RATE = 16000

SegmentCallback = Callable[[np.ndarray, int], None]


def _open_mic_stream(sample_rate: int = SAMPLE_RATE):
    import sounddevice as sd

    try:
        return sd.InputStream(channels=1, dtype="float32", samplerate=sample_rate)
    except Exception as exc:
        raise RuntimeError(
            "无法打开麦克风。请检查 Windows 隐私设置 → 麦克风是否允许本程序访问。"
        ) from exc


def _create_vad(config: VadConfig, *, max_record_seconds: float = 60.0):
    import sherpa_onnx

    model_path = silero_vad_model_file()
    if model_path is None:
        model_path = download_silero_vad()

    vad_config = sherpa_onnx.VadModelConfig()
    vad_config.silero_vad.model = sherpa_relative_path(model_path)
    vad_config.silero_vad.threshold = config.threshold
    vad_config.silero_vad.min_speech_duration = config.min_speech_ms / 1000.0
    silence_s = (config.min_silence_ms + config.hangover_ms) / 1000.0
    vad_config.silero_vad.min_silence_duration = silence_s
    vad_config.silero_vad.max_speech_duration = max_record_seconds
    vad_config.sample_rate = config.sample_rate

    return sherpa_onnx.VoiceActivityDetector(vad_config, buffer_size_in_seconds=60)


def _vad_listen_loop(
    *,
    config: VadConfig,
    on_segment: SegmentCallback,
    should_stop: Callable[[], bool],
    max_record_seconds: float = 60.0,
    on_speech_start: Callable[[], None] | None = None,
    quiet: bool = False,
    continuous: bool = False,
    max_wait_seconds: float = 20.0,
) -> None:
    """VAD 主循环；continuous=True 时每段结束后继续监听下一句。"""
    vad_cfg = config
    sample_rate = vad_cfg.sample_rate

    vad = _create_vad(vad_cfg, max_record_seconds=max_record_seconds)
    window_size = vad.config.silero_vad.window_size
    chunk_samples = int(0.1 * sample_rate)

    if not quiet:
        print(f"麦克风：{default_input_device_label()}")
        silence_s = (vad_cfg.min_silence_ms + vad_cfg.hangover_ms) / 1000
        if continuous:
            print(f"持续监听中（停顿约 {silence_s:g} 秒后自动识别每一段）…")
        else:
            print(f"请开始说话（检测到语音后自动录音，停顿约 {silence_s:g} 秒后结束）…")

    speech_started = False
    wait_started = time.monotonic()
    speech_started_at: float | None = None
    offset = 0
    buffer = np.array([], dtype=np.float32)
    max_pre_roll = int(vad_cfg.speech_pad_ms / 1000.0 * sample_rate)
    pre_roll_buffer = np.array([], dtype=np.float32)
    segment_prefix = np.array([], dtype=np.float32)

    with _open_mic_stream(sample_rate) as stream:
        while not should_stop():
            if (
                not continuous
                and not speech_started
                and time.monotonic() - wait_started > max_wait_seconds
            ):
                raise TimeoutError("等待超时：未检测到语音，请检查麦克风或提高音量。")

            if speech_started and speech_started_at is not None:
                if time.monotonic() - speech_started_at > max_record_seconds:
                    if continuous:
                        speech_started = False
                        speech_started_at = None
                        continue
                    raise TimeoutError("录音过长，已自动停止。请缩短单次说话长度。")

            samples, _ = stream.read(chunk_samples)
            chunk = samples.reshape(-1).astype(np.float32, copy=False)
            buffer = np.concatenate([buffer, chunk])
            pre_roll_buffer = np.concatenate([pre_roll_buffer, chunk])
            if pre_roll_buffer.size > max_pre_roll:
                pre_roll_buffer = pre_roll_buffer[-max_pre_roll:]

            while offset + window_size <= len(buffer):
                vad.accept_waveform(buffer[offset : offset + window_size])
                offset += window_size

                if vad.is_speech_detected() and not speech_started:
                    speech_started = True
                    speech_started_at = time.monotonic()
                    segment_prefix = pre_roll_buffer.copy()
                    if on_speech_start:
                        on_speech_start()
                    elif not quiet:
                        print("正在听…")

                if speech_started and not vad.empty():
                    raw_segment = np.array(vad.front.samples, dtype=np.float32)
                    vad.pop()
                    if raw_segment.size == 0:
                        if continuous:
                            speech_started = False
                            speech_started_at = None
                            segment_prefix = np.array([], dtype=np.float32)
                            continue
                        raise RuntimeError("未录到有效语音，请重试。")
                    if segment_prefix.size:
                        segment = np.concatenate([segment_prefix, raw_segment])
                    else:
                        segment = raw_segment
                    segment_prefix = np.array([], dtype=np.float32)
                    if not quiet:
                        print("检测到停顿，提交识别。")
                    on_segment(segment, sample_rate)
                    speech_started = False
                    speech_started_at = None
                    wait_started = time.monotonic()
                    if not continuous:
                        return

            if not speech_started and len(buffer) > 10 * window_size:
                offset -= len(buffer) - 10 * window_size
                buffer = buffer[-10 * window_size :]


class ContinuousVadCapture:
    """持续监听：每段静音结束后回调 on_segment，不阻塞麦克风。"""

    def __init__(
        self,
        config: VadConfig | None = None,
        *,
        max_record_seconds: float = 60.0,
    ) -> None:
        self.config = config or VadConfig()
        self.max_record_seconds = max_record_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(
        self,
        on_segment: SegmentCallback,
        *,
        on_speech_start: Callable[[], None] | None = None,
        quiet: bool = True,
    ) -> None:
        if self.is_running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(on_segment, on_speech_start, quiet),
            daemon=True,
            name="tingyi-vad-capture",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _run(
        self,
        on_segment: SegmentCallback,
        on_speech_start: Callable[[], None] | None,
        quiet: bool,
    ) -> None:
        try:
            _vad_listen_loop(
                config=self.config,
                on_segment=on_segment,
                should_stop=self._stop.is_set,
                max_record_seconds=self.max_record_seconds,
                on_speech_start=on_speech_start,
                quiet=quiet,
                continuous=True,
            )
        except Exception:
            if not self._stop.is_set():
                raise


def record_with_vad(
    *,
    config: VadConfig | None = None,
    max_wait_seconds: float = 20.0,
    max_record_seconds: float = 60.0,
    on_listening: Callable[[], None] | None = None,
    quiet: bool = False,
) -> tuple[np.ndarray, int]:
    """等待用户开口，说完（静音）后返回 (samples, sample_rate)。"""
    result: dict[str, np.ndarray | int] = {}

    def _capture(segment: np.ndarray, sample_rate: int) -> None:
        result["samples"] = segment
        result["sample_rate"] = sample_rate

    _vad_listen_loop(
        config=config or VadConfig(),
        on_segment=_capture,
        should_stop=lambda: "samples" in result,
        max_record_seconds=max_record_seconds,
        on_speech_start=on_listening,
        quiet=quiet,
        continuous=False,
        max_wait_seconds=max_wait_seconds,
    )
    return result["samples"], int(result["sample_rate"])  # type: ignore[return-value]


def record_with_vad_to_wav(
    path: Path,
    *,
    config: VadConfig | None = None,
    max_wait_seconds: float = 20.0,
    max_record_seconds: float = 60.0,
) -> Path:
    """等待用户开口，说完（静音）后自动结束并保存 WAV。"""
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    segment, sample_rate = record_with_vad(
        config=config,
        max_wait_seconds=max_wait_seconds,
        max_record_seconds=max_record_seconds,
    )
    sf.write(str(path), segment, sample_rate)
    return path
