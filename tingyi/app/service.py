# -*- coding: utf-8 -*-
"""桌面语音输入：录音 → 识别 → 粘贴。"""

from __future__ import annotations

import logging
import threading
from typing import Callable

from tingyi.audio.vad import record_with_vad
from tingyi.input.paste import paste_to_focus
from tingyi.pipeline import TingyiPipeline
from tingyi.settings import AppSettings, AsrMode, LocalEngine

logger = logging.getLogger(__name__)


class VoiceInputService:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or AppSettings.from_env()
        self.settings.asr_mode = AsrMode.LOCAL
        self.settings.local.engine = LocalEngine.SENSEVOICE
        self.pipeline = TingyiPipeline(self.settings)
        self._lock = threading.Lock()
        self._notify: Callable[[str, str | None], None] | None = None

    def set_notifier(self, callback: Callable[[str, str | None], None]) -> None:
        self._notify = callback

    def is_ready(self) -> bool:
        return self.pipeline.asr.local.is_available()

    def hotkey_label(self) -> str:
        return self.settings.input.hotkey_record

    def _notify_user(self, title: str, message: str | None = None) -> None:
        if self._notify:
            self._notify(title, message)
        else:
            logger.info("%s %s", title, message or "")

    def run_once(self) -> None:
        if not self._lock.acquire(blocking=False):
            self._notify_user("听译", "正在处理上一段语音…")
            return

        threading.Thread(target=self._run_once_worker, daemon=True).start()

    def _run_once_worker(self) -> None:
        try:
            if not self.is_ready():
                self._notify_user("听译", "SenseVoice 模型未就绪，请检查 models 目录。")
                return

            self._notify_user("听译", f"请说话…（停顿约 {self.settings.vad.min_silence_ms / 1000:g} 秒自动结束）")

            samples, sample_rate = record_with_vad(
                config=self.settings.vad,
                quiet=True,
                on_listening=lambda: self._notify_user("听译", "正在听…"),
            )

            self._notify_user("听译", "识别中…")
            result = self.pipeline.asr.local.transcribe_samples(samples, sample_rate)
            text = (result.text or "").strip()

            if not text:
                self._notify_user("听译", "未识别到文字")
                return

            if self.settings.input.auto_paste:
                paste_to_focus(text)
                self._notify_user("听译", f"已输入：{text[:40]}{'…' if len(text) > 40 else ''}")
            else:
                self._notify_user("听译", text)

        except TimeoutError as exc:
            self._notify_user("听译", str(exc))
        except Exception as exc:
            logger.exception("voice input failed")
            self._notify_user("听译", f"失败：{exc}")
        finally:
            self._lock.release()
