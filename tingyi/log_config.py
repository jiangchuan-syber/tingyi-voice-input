# -*- coding: utf-8 -*-
"""听译日志：文件轮转 + 可选控制台，便于快速排查识别/粘贴问题。"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from tingyi.settings import ROOT

_CONFIGURED = False
_LOG_PATH: Path | None = None

# 统一事件标签，便于 grep：tingyi.log | findstr "[paste]"
TAG_LISTEN = "listen"
TAG_VAD = "vad"
TAG_ASR = "asr"
TAG_POST = "post"
TAG_PASTE = "paste"
TAG_REFINE = "refine"
TAG_DEDUPE = "dedupe"
TAG_STARTUP = "startup"


def default_log_file() -> Path:
    custom = os.getenv("TINGYI_LOG_FILE", "").strip()
    if custom:
        path = Path(custom)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    app_logs = ROOT / "logs"
    try:
        app_logs.mkdir(parents=True, exist_ok=True)
        probe = app_logs / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return app_logs / "tingyi.log"
    except OSError:
        user_logs = Path.home() / ".tingyi" / "logs"
        user_logs.mkdir(parents=True, exist_ok=True)
        return user_logs / "tingyi.log"


def get_log_file() -> Path:
    global _LOG_PATH
    if _LOG_PATH is None:
        _LOG_PATH = default_log_file()
    return _LOG_PATH


def log_event(logger: logging.Logger, tag: str, message: str, **fields: object) -> None:
    """结构化单行日志，例如：[paste] done len=12 restore=False"""
    if fields:
        detail = " ".join(f"{key}={value!r}" for key, value in fields.items())
        logger.info("[%s] %s %s", tag, message, detail)
    else:
        logger.info("[%s] %s", tag, message)


def tail_log(lines: int = 80) -> str:
    path = get_log_file()
    if not path.is_file():
        return f"（日志文件尚不存在：{path}）"
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return f"无法读取日志：{exc}"
    if not content:
        return f"（日志为空：{path}）"
    tail = content[-lines:]
    header = f"=== 听译日志末尾 {len(tail)} 行 ===\n{path}\n"
    return header + "\n".join(tail)


def open_log_file() -> Path:
    path = get_log_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        import subprocess

        subprocess.Popen(["xdg-open", str(path)])
    return path


def setup_logging(*, console: bool | None = None) -> Path:
    """初始化根日志；桌面版默认写 logs/tingyi.log，开发时可开控制台。"""
    global _CONFIGURED, _LOG_PATH

    if _CONFIGURED:
        return get_log_file()

    level_name = os.getenv("TINGYI_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    if console is None:
        if getattr(sys, "frozen", False):
            console = os.getenv("TINGYI_LOG_CONSOLE", "false").lower() in (
                "1",
                "true",
                "yes",
            )
        else:
            console = os.getenv("TINGYI_LOG_CONSOLE", "true").lower() in (
                "1",
                "true",
                "yes",
            )

    log_path = default_log_file()
    _LOG_PATH = log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=int(os.getenv("TINGYI_LOG_MAX_BYTES", str(2 * 1024 * 1024))),
        backupCount=int(os.getenv("TINGYI_LOG_BACKUP_COUNT", "3")),
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(fmt)
        root.addHandler(stream_handler)

    _CONFIGURED = True
    startup = logging.getLogger("tingyi.startup")
    log_event(
        startup,
        TAG_STARTUP,
        "logging ready",
        path=str(log_path),
        level=level_name,
        console=console,
        root=str(ROOT),
        frozen=getattr(sys, "frozen", False),
    )
    return log_path
