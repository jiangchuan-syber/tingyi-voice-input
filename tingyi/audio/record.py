# -*- coding: utf-8 -*-
"""麦克风录音（16kHz 单声道 WAV）。"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def default_input_device_label() -> str:
    import sounddevice as sd

    try:
        dev = sd.query_devices(kind="input")
        return str(dev.get("name", "默认麦克风"))
    except Exception:
        return "默认麦克风"


def record_to_wav(path: Path, seconds: float = 5.0, sample_rate: int = 16000) -> Path:
    import sounddevice as sd
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(seconds * sample_rate)
    print(f"麦克风：{default_input_device_label()}")
    print(f"请对着麦克风说话（{seconds:g} 秒）…")
    try:
        audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="float32")
        sd.wait()
    except Exception as exc:
        raise RuntimeError(
            "无法打开麦克风。请在 Cursor 集成终端或系统 PowerShell 中运行，"
            "并检查 Windows 隐私设置 → 麦克风是否允许终端/Python 访问。"
        ) from exc
    peak = float(np.max(np.abs(audio)))
    if peak < 0.01:
        print("（提示：音量很低，请检查麦克风是否静音或未选对设备）")
    sf.write(str(path), audio, sample_rate)
    return path
