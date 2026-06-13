# -*- coding: utf-8 -*-
"""桌面语音输入：持续监听 → 分段 → 异步识别 → 词典/润色 → 粘贴。"""

from __future__ import annotations

import logging
import queue
import re
import threading
import time
from dataclasses import dataclass
from typing import Callable

import numpy as np

from tingyi.audio.vad import ContinuousVadCapture
from tingyi.input.paste import paste_to_focus, replace_recent_paste
from tingyi.log_config import (
    TAG_ASR,
    TAG_DEDUPE,
    TAG_LISTEN,
    TAG_PASTE,
    TAG_POST,
    TAG_REFINE,
    TAG_VAD,
    log_event,
)
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
    paste_seq: int


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
        self._paste_seq = 0
        self._last_paste_key = ""
        self._last_paste_at = 0.0
        self._dedupe_window_s = 4.0

    def set_notifier(self, callback: Callable[[str, str | None], None]) -> None:
        self._notify = callback

    def is_ready(self) -> bool:
        return self.pipeline.asr.local.is_available()

    def is_listening(self) -> bool:
        return self._listening

    def hotkey_label(self) -> str:
        return self.settings.input.hotkey_record

    def _paste_dedupe_key(self, text: str) -> str:
        normalized = re.sub(r"\s+", "", (text or "").strip().lower())
        return normalized[:120]

    def _is_duplicate_paste(self, text: str) -> bool:
        key = self._paste_dedupe_key(text)
        if not key:
            return True
        now = time.monotonic()
        if key == self._last_paste_key and now - self._last_paste_at < self._dedupe_window_s:
            return True
        return False

    def _mark_pasted(self, text: str) -> int:
        self._paste_seq += 1
        self._last_paste_key = self._paste_dedupe_key(text)
        self._last_paste_at = time.monotonic()
        return self._paste_seq

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
        log_event(logger, TAG_LISTEN, "on", hotkey=self.hotkey_label())
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

        vad = self.settings.vad
        silence_s = (vad.min_silence_ms + vad.hangover_ms) / 1000
        self._notify_user(
            "听译",
            f"监听已开启（{self.hotkey_label()} 关闭）。停顿约 {silence_s:g} 秒自动识别，录音不中断。",
        )

        self._capture.start(
            on_segment=self._on_segment_ready,
            quiet=True,
        )

    def _stop_listening(self) -> None:
        if not self._listening:
            return

        self._listening = False
        log_event(logger, TAG_LISTEN, "off")
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

        vad = self.settings.vad
        duration_ms = len(samples) / sample_rate * 1000
        peak = float(np.max(np.abs(samples)))
        if duration_ms < vad.min_segment_ms or peak < vad.min_segment_peak:
            log_event(
                logger,
                TAG_VAD,
                "skip segment",
                duration_ms=round(duration_ms),
                peak=round(peak, 4),
                min_ms=vad.min_segment_ms,
            )
            return

        self._segment_queue.put(_AudioSegment(samples=samples, sample_rate=sample_rate))
        log_event(
            logger,
            TAG_VAD,
            "queued",
            duration_ms=round(duration_ms),
            peak=round(peak, 4),
            samples=len(samples),
        )

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
            log_event(
                logger,
                TAG_ASR,
                "done",
                raw=raw,
                latency_ms=round(result.latency_ms),
            )
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

            log_event(
                logger,
                TAG_POST,
                "draft",
                raw=raw,
                draft=to_paste,
                llm_async=use_async_llm,
            )

            if not to_paste:
                self._notify_user("听译", "本段未识别到文字")
                return

            if self._is_duplicate_paste(to_paste):
                log_event(logger, TAG_DEDUPE, "skip", text=to_paste[:80])
                return

            pasted_len = 0
            paste_seq = 0
            restore_cb = self.settings.input.paste_restore_clipboard
            if self.settings.input.auto_paste:
                pasted_len = paste_to_focus(to_paste, restore_clipboard=restore_cb)
                paste_seq = self._mark_pasted(to_paste)
                log_event(
                    logger,
                    TAG_PASTE,
                    "done",
                    text=to_paste,
                    len=pasted_len,
                    restore_clipboard=restore_cb,
                    seq=paste_seq,
                )
                preview = to_paste[:40] + ("…" if len(to_paste) > 40 else "")
                if raw != to_paste:
                    raw_preview = raw[:30] + ("…" if len(raw) > 30 else "")
                    self._notify_user("听译", f"已输入：{preview}\n识别原文：{raw_preview}")
                else:
                    self._notify_user("听译", f"已输入：{preview}")
            else:
                self._notify_user("听译", to_paste)

            if self.settings.input.auto_paste and use_async_llm:
                self._refine_queue.put(
                    _RefineJob(
                        pasted_len=pasted_len,
                        draft=to_paste,
                        raw=raw,
                        paste_seq=paste_seq,
                    )
                )

        except Exception:
            logger.exception("segment recognition failed")
            self._notify_user("听译", "本段识别失败，请重试")

    def _apply_llm_replace(self, job: _RefineJob) -> None:
        try:
            # 用户已继续输入新内容时，放弃替换，避免删错字造成重复/错乱
            if job.paste_seq != self._paste_seq:
                log_event(
                    logger,
                    TAG_REFINE,
                    "skip stale",
                    job_seq=job.paste_seq,
                    current_seq=self._paste_seq,
                )
                return

            from tingyi.text.refine_llm import llm_refine

            refined = llm_refine(job.draft).strip()
            if not refined or refined == job.draft:
                log_event(logger, TAG_REFINE, "unchanged", draft=job.draft)
                return

            min_keep = max(2, len(job.draft) // 3)
            if len(refined) < min_keep:
                log_event(
                    logger,
                    TAG_REFINE,
                    "skip too short",
                    draft=job.draft,
                    refined=refined,
                    min_keep=min_keep,
                )
                return

            if job.paste_seq != self._paste_seq:
                log_event(logger, TAG_REFINE, "skip stale after refine", job_seq=job.paste_seq)
                return

            replace_recent_paste(
                job.pasted_len,
                refined,
                restore_clipboard=self.settings.input.paste_restore_clipboard,
            )
            self._mark_pasted(refined)
            log_event(
                logger,
                TAG_REFINE,
                "replaced",
                draft=job.draft,
                refined=refined,
                backspace=job.pasted_len,
            )
            preview = refined[:40] + ("…" if len(refined) > 40 else "")
            self._notify_user("听译", f"已润色：{preview}")
        except Exception:
            logger.exception("LLM replace failed")

    def run_once(self) -> None:
        self.toggle_listening()
