# -*- coding: utf-8 -*-
"""听译入口。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from tingyi import __version__
from tingyi.pipeline import TingyiPipeline
from tingyi.settings import ROOT


def main() -> None:
    # sherpa-onnx 需从项目根目录解析相对模型路径
    os.chdir(ROOT)

    if getattr(sys, "frozen", False) and len(sys.argv) == 1:
        from tingyi.app.tray import run_desktop_app

        run_desktop_app()
        return

    parser = argparse.ArgumentParser(description="听译 · 个人语音转文字输入")
    parser.add_argument(
        "--app",
        action="store_true",
        help="启动桌面版（系统托盘 + 全局热键，识别后粘贴到当前输入框）",
    )
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
    parser.add_argument(
        "--listen",
        nargs="?",
        const=0.0,
        type=float,
        metavar="SECONDS",
        help="麦克风录音并识别；不带参数则 VAD 自动检测说话结束，带数字则固定秒数",
    )
    args = parser.parse_args()

    if args.app:
        from tingyi.app.tray import run_desktop_app

        run_desktop_app()
        return

    if args.download_models:
        from tingyi.models.download import download_sensevoice, download_silero_vad

        download_sensevoice()
        download_silero_vad()
        return

    if args.listen is not None:
        from datetime import datetime

        from tingyi.audio.record import record_to_wav
        from tingyi.audio.vad import record_with_vad_to_wav
        from tingyi.settings import AppSettings, AsrMode, LocalEngine

        settings = AppSettings.from_env()
        settings.asr_mode = AsrMode.LOCAL
        settings.local.engine = LocalEngine.SENSEVOICE
        pipeline = TingyiPipeline(settings)
        if not pipeline.asr.local.is_available():
            print("SenseVoice 不可用，请先运行: python -m tingyi --download-models")
            return

        wav_path = ROOT / "recordings" / f"listen_{datetime.now():%Y%m%d_%H%M%S}.wav"
        try:
            if args.listen <= 0:
                record_with_vad_to_wav(wav_path, config=settings.vad)
            else:
                record_to_wav(wav_path, seconds=args.listen)
        except (TimeoutError, RuntimeError) as exc:
            print(exc)
            return
        result = pipeline.transcribe_file(wav_path)
        print(f"\n[SenseVoice] {result.latency_ms:.0f} ms")
        print(result.text or "（未识别到文字）")
        print(f"\n录音已保存：{wav_path}")
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
        print("\n桌面版（推荐）：python -m tingyi --app")
        print("  热键默认 F9 → 说话 → 自动粘贴到微信/Cursor 等输入框")
        print("体验 SenseVoice（自动检测说话）：python -m tingyi --listen")
        print("调试：python -m tingyi --transcribe path/to/audio.wav")


if __name__ == "__main__":
    main()
