# -*- coding: utf-8 -*-
"""桌面语音输入：持续监听 → 分段 → 异步识别 → 词典/润色 → 粘贴。"""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from typing import Callable

import numpy as np

from tingyi.audio.vad import ContinuousVadCapture
from tingyi.input.paste import paste_to_focus, replace_recent_paste
from tingyi.pipeline import TingyiPipeline
from tingyi.settings import AppSettings, AsrMode, LocalEngine
from tingyi.text.pipeline import TextPostProcessor

logger = logging.getLogger(__name__)


@dataclass
class _AudioSegment:
    samples: np.ndarray
    sample_rate: int


@dataclass
class _RefineJob:
    pasted_len: int
    draft: str
    raw: str


class VoiceInputService:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or AppSettings.from_env()
        self.settings.asr_mode = AsrMode.LOCAL
        self.settings.local.engine = LocalEngine.SENSEVOICE
        self.pipeline = TingyiPipeline(self.settings)
        self.text_processor = TextPostProcessor(
            dictionary_enabled=self.settings.text.dictionary_enabled,
            dictionary_path=self.settings.text.dictionary_path,
            rule_refine_enabled=self.settings.text.rule_refine_enabled,
            llm_refine_enabled=self.settings.text.llm_refine_enabled,
        )

        self._notify: Callable[[str, str | None], None] | None = None
        self._listening = False
        self._capture = ContinuousVadCapture(config=self.settings.vad)
        self._segment_queue: queue.Queue[_AudioSegment | None] = queue.Queue()
        self._refine_queue: queue.Queue[_RefineJob | None] = queue.Queue()
        self._asr_thread: threading.Thread | None = None
        self._refine_thread: threading.Thread | None = None
        self._asr_lock = threading.Lock()

    def set_notifier(self, callback: Callable[[str, str | None], None]) -> None:
        self._notify = callback

    def is_ready(self) -> bool:
        return self.pipeline.asr.local.is_available()

    def is_listening(self) -> bool:
        return self._listening

    def hotkey_label(self) -> str:
        return self.settings.input.hotkey_record

    def _notify_user(self, title: str, message: str | None = None) -> None:
        if self._notify:
            self._notify(title, message)
        else:
            logger.info("%s %s", title, message or "")

    def toggle_listening(self) -> None:
        """F9：开关持续监听（非单次录音）。"""
        if self._listening:
            self._stop_listening()
        else:
            self._start_listening()

    def _start_listening(self) -> None:
        if not self.is_ready():
            self._notify_user("听译", "SenseVoice 模型未就绪，请检查 models 目录。")
            return
        if self._listening:
            return

        self._listening = True
        self._asr_thread = threading.Thread(
            target=self._asr_worker,
            daemon=True,
            name="tingyi-asr-worker",
        )
        self._asr_thread.start()

        if self.text_processor.llm_refine_enabled and self.settings.text.llm_refine_async:
            self._refine_thread = threading.Thread(
                target=self._refine_worker,
                daemon=True,
                name="tingyi-refine-worker",
            )
            self._refine_thread.start()

        silence_s = self.settings.vad.min_silence_ms / 1000
        self._notify_user(
            "听译",
            f"监听已开启（{self.hotkey_label()} 关闭）。停顿 {silence_s:g} 秒自动识别，录音不中断。",
        )

        self._capture.start(
            on_segment=self._on_segment_ready,
            on_speech_start=lambda: self._notify_user("听译", "正在听…"),
            quiet=True,
        )

    def _stop_listening(self) -> None:
        if not self._listening:
            return

        self._listening = False
        self._capture.stop()
        self._segment_queue.put(None)
        self._refine_queue.put(None)

        if self._asr_thread is not None:
            self._asr_thread.join(timeout=30.0)
            self._asr_thread = None
        if self._refine_thread is not None:
            self._refine_thread.join(timeout=60.0)
            self._refine_thread = None

        self._notify_user("听译", "监听已关闭")

    def _on_segment_ready(self, samples: np.ndarray, sample_rate: int) -> None:
        if not self._listening:
            return
        self._segment_queue.put(_AudioSegment(samples=samples, sample_rate=sample_rate))
        self._notify_user("听译", "已切段，识别中…（可继续说话）")

    def _asr_worker(self) -> None:
        while True:
            item = self._segment_queue.get()
            try:
                if item is None:
                    break
                self._recognize_and_paste(item)
            finally:
                self._segment_queue.task_done()

    def _refine_worker(self) -> None:
        while True:
            job = self._refine_queue.get()
            try:
                if job is None:
                    break
                self._apply_llm_replace(job)
            finally:
                self._refine_queue.task_done()

    def _recognize_and_paste(self, segment: _AudioSegment) -> None:
        try:
            with self._asr_lock:
                result = self.pipeline.asr.local.transcribe_samples(
                    segment.samples,
                    segment.sample_rate,
                )
            raw = (result.text or "").strip()
            if not raw:
                self._notify_user("听译", "本段未识别到文字")
                return

            use_async_llm = (
                self.text_processor.llm_refine_enabled
                and self.settings.text.llm_refine_async
            )

            if self.text_processor.llm_refine_enabled and not self.settings.text.llm_refine_async:
                processed = self.text_processor.process(raw)
                to_paste = processed.final or processed.draft
            else:
                to_paste = self.text_processor.process_draft_only(raw)

            if not to_paste:
                self._notify_user("听译", "本段未识别到文字")
                return

            pasted_len = 0
            if self.settings.input.auto_paste:
                pasted_len = paste_to_focus(to_paste)
                preview = to_paste[:40] + ("…" if len(to_paste) > 40 else "")
                self._notify_user("听译", f"已输入：{preview}")
            else:
                self._notify_user("听译", to_paste)

            if self.settings.input.auto_paste and use_async_llm:
                self._refine_queue.put(
                    _RefineJob(pasted_len=pasted_len, draft=to_paste, raw=raw)
                )

        except Exception:
            logger.exception("segment recognition failed")
            self._notify_user("听译", "本段识别失败，请重试")

    def _apply_llm_replace(self, job: _RefineJob) -> None:
        try:
            from tingyi.text.refine_llm import llm_refine

            refined = llm_refine(job.draft).strip()
            if not refined or refined == job.draft:
                return
            replace_recent_paste(job.pasted_len, refined)
            preview = refined[:40] + ("…" if len(refined) > 40 else "")
            self._notify_user("听译", f"已润色：{preview}")
        except Exception:
            logger.exception("LLM replace failed")

    def run_once(self) -> None:
        self.toggle_listening()
