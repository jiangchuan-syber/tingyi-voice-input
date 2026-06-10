# -*- coding: utf-8 -*-
"""本地模型路径约定。"""

from __future__ import annotations

from pathlib import Path

from tingyi.settings import ROOT

SENSEVOICE_DIR = ROOT / "models" / "sensevoice"
SENSEVOICE_ARCHIVE_NAME = "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
SENSEVOICE_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    f"{SENSEVOICE_ARCHIVE_NAME}.tar.bz2"
)

VAD_DIR = ROOT / "models" / "vad"
SILERO_VAD_FILE = VAD_DIR / "silero_vad.onnx"
SILERO_VAD_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx"
)


def sherpa_relative_path(path: Path) -> str:
    """sherpa-onnx 在 Windows 上对非 ASCII 绝对路径支持不佳。"""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def silero_vad_model_file() -> Path | None:
    if SILERO_VAD_FILE.is_file():
        return SILERO_VAD_FILE
    return None


def sensevoice_model_files() -> tuple[Path, Path] | None:
    """返回 (model.onnx, tokens.txt)，未安装则 None。"""
    base = SENSEVOICE_DIR / SENSEVOICE_ARCHIVE_NAME
    if not base.is_dir():
        # 解压后目录名可能略有不同，做一次模糊匹配
        if SENSEVOICE_DIR.is_dir():
            for child in SENSEVOICE_DIR.iterdir():
                if child.is_dir() and "sense-voice" in child.name.lower():
                    base = child
                    break
        else:
            return None

    model = base / "model.int8.onnx"
    if not model.exists():
        model = base / "model.onnx"
    tokens = base / "tokens.txt"
    if model.exists() and tokens.exists():
        return model, tokens
    return None
