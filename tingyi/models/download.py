# -*- coding: utf-8 -*-
"""下载 SenseVoice 本地模型。"""

from __future__ import annotations

import tarfile
import urllib.request
from pathlib import Path

from tingyi.models.paths import (
    SENSEVOICE_DIR,
    SENSEVOICE_URL,
    SILERO_VAD_FILE,
    SILERO_VAD_URL,
    sensevoice_model_files,
    silero_vad_model_file,
)


def download_sensevoice(force: bool = False) -> Path:
    if not force and sensevoice_model_files():
        model, _ = sensevoice_model_files()  # type: ignore[misc]
        print(f"SenseVoice 已存在: {model.parent}")
        return model.parent

    SENSEVOICE_DIR.mkdir(parents=True, exist_ok=True)
    archive = SENSEVOICE_DIR / "sensevoice.tar.bz2"
    print(f"下载 SenseVoice INT8 …\n  {SENSEVOICE_URL}")

    def _progress(block_num: int, block_size: int, total: int) -> None:
        if total > 0:
            pct = min(100, block_num * block_size * 100 // total)
            print(f"\r  进度 {pct}%", end="", flush=True)

    urllib.request.urlretrieve(SENSEVOICE_URL, archive, reporthook=_progress)
    print("\n解压中 …")
    with tarfile.open(archive, "r:bz2") as tf:
        tf.extractall(SENSEVOICE_DIR)
    archive.unlink(missing_ok=True)

    files = sensevoice_model_files()
    if not files:
        raise RuntimeError("解压完成但未找到 model.int8.onnx / tokens.txt")
    print(f"完成: {files[0].parent}")
    return files[0].parent


def download_silero_vad(force: bool = False) -> Path:
    if not force and silero_vad_model_file():
        print(f"Silero VAD 已存在: {SILERO_VAD_FILE}")
        return SILERO_VAD_FILE

    VAD_DIR = SILERO_VAD_FILE.parent
    VAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"下载 Silero VAD …\n  {SILERO_VAD_URL}")

    def _progress(block_num: int, block_size: int, total: int) -> None:
        if total > 0:
            pct = min(100, block_num * block_size * 100 // total)
            print(f"\r  进度 {pct}%", end="", flush=True)

    urllib.request.urlretrieve(SILERO_VAD_URL, SILERO_VAD_FILE, reporthook=_progress)
    print(f"\n完成: {SILERO_VAD_FILE}")
    return SILERO_VAD_FILE


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="下载听译本地 ASR 模型")
    parser.add_argument("--sensevoice", action="store_true", help="下载 SenseVoice INT8")
    parser.add_argument("--silero-vad", action="store_true", help="下载 Silero VAD")
    parser.add_argument("--force", action="store_true", help="强制重新下载")
    args = parser.parse_args()
    if args.silero_vad:
        download_silero_vad(force=args.force)
    if args.sensevoice or not args.silero_vad:
        download_sensevoice(force=args.force)
        download_silero_vad(force=args.force)


if __name__ == "__main__":
    main()
