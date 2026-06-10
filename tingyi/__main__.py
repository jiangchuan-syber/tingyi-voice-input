# -*- coding: utf-8 -*-
"""听译入口。"""

from __future__ import annotations

import argparse
from pathlib import Path

import os

from tingyi import __version__
from tingyi.pipeline import TingyiPipeline
from tingyi.settings import ROOT


def main() -> None:
    # sherpa-onnx 需从项目根目录解析相对模型路径
    os.chdir(ROOT)
    parser = argparse.ArgumentParser(description="听译 · 个人语音转文字输入")
    parser.add_argument(
        "--transcribe",
        type=Path,
        help="对已有音频文件做识别（开发调试用）",
    )
    parser.add_argument(
        "--download-models",
        action="store_true",
        help="下载 SenseVoice 本地模型",
    )
    args = parser.parse_args()

    if args.download_models:
        from tingyi.models.download import download_sensevoice

        download_sensevoice()
        return

    pipeline = TingyiPipeline()
    print(f"听译 tingyi-voice-input v{__version__}")
    print(pipeline.status_summary())

    if args.transcribe:
        result = pipeline.transcribe_file(args.transcribe)
        print(f"\n[{result.provider}] {result.latency_ms:.0f} ms")
        if result.is_fallback:
            print("(云端回退)")
        print(result.text)
    else:
        print("\nPhase 1 开发中：热键录音 → 识别 → 粘贴。")
        print("调试：python -m tingyi --transcribe path/to/audio.wav")


if __name__ == "__main__":
    main()
