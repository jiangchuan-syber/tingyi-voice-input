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
        from tingyi.log_config import setup_logging

        setup_logging()
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
        "--test-dictionary",
        type=str,
        metavar="TEXT",
        help="测试个人词典替换",
    )
    parser.add_argument(
        "--test-refine",
        type=str,
        metavar="TEXT",
        help="测试规则润色（含词典）",
    )
    parser.add_argument(
        "--listen",
        nargs="?",
        const=0.0,
        type=float,
        metavar="SECONDS",
        help="麦克风录音并识别；不带参数则 VAD 自动检测说话结束，带数字则固定秒数",
    )
    parser.add_argument(
        "--show-log",
        nargs="?",
        const=80,
        type=int,
        metavar="LINES",
        help="查看日志文件末尾 N 行（默认 80）",
    )
    parser.add_argument(
        "--open-log",
        action="store_true",
        help="打开日志文件",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="",
        help="日志级别：DEBUG / INFO / WARNING（也可设 TINGYI_LOG_LEVEL）",
    )
    args = parser.parse_args()

    if args.log_level:
        os.environ["TINGYI_LOG_LEVEL"] = args.log_level.upper()

    if args.show_log is not None and args.open_log:
        parser.error("--show-log 与 --open-log 不能同时使用")

    if args.show_log is not None:
        from tingyi.log_config import setup_logging, tail_log

        setup_logging(console=False)
        print(tail_log(args.show_log))
        return

    if args.open_log:
        from tingyi.log_config import open_log_file, setup_logging

        setup_logging(console=False)
        path = open_log_file()
        print(f"已打开日志：{path}")
        return

    if args.app:
        from tingyi.app.tray import run_desktop_app

        run_desktop_app()
        return

    if args.test_dictionary:
        from tingyi.text.dictionary import apply_dictionary, load_dictionary

        entries = load_dictionary()
        print(apply_dictionary(args.test_dictionary, entries))
        return

    if args.test_refine:
        from tingyi.text.pipeline import TextPostProcessor

        proc = TextPostProcessor()
        print(proc.process_draft_only(args.test_refine))
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
        print("  热键默认 F9 → 开关持续监听；停顿 0.5 秒自动识别并粘贴，可连续多句")
        print("体验 SenseVoice（自动检测说话）：python -m tingyi --listen")
        print("调试：python -m tingyi --transcribe path/to/audio.wav")


if __name__ == "__main__":
    main()
