# -*- coding: utf-8 -*-
"""ASR 后处理：词典 → 规则润色 →（可选）LLM 润色。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tingyi.text.dictionary import apply_dictionary, default_dictionary_path, load_dictionary
from tingyi.text.refine import rule_refine
from tingyi.text.refine_llm import llm_refine, llm_refine_available


@dataclass
class ProcessedText:
    raw: str
    draft: str  # 词典 + 规则，用于立刻粘贴
    final: str | None = None  # LLM 润色后（若启用且与 draft 不同）


class TextPostProcessor:
    def __init__(
        self,
        *,
        dictionary_enabled: bool = True,
        dictionary_path: Path | None = None,
        rule_refine_enabled: bool = True,
        llm_refine_enabled: bool | None = None,
    ) -> None:
        self.dictionary_enabled = dictionary_enabled
        self.dictionary_path = dictionary_path or default_dictionary_path()
        self.rule_refine_enabled = rule_refine_enabled
        self.llm_refine_enabled = (
            llm_refine_available() if llm_refine_enabled is None else llm_refine_enabled
        )
        self._entries = load_dictionary(self.dictionary_path) if dictionary_enabled else []

    def process(self, raw: str) -> ProcessedText:
        text = (raw or "").strip()
        if not text:
            return ProcessedText(raw=raw, draft="")

        draft = text
        if self.dictionary_enabled and self._entries:
            draft = apply_dictionary(draft, self._entries)
        if self.rule_refine_enabled:
            draft = rule_refine(draft)

        final: str | None = None
        if self.llm_refine_enabled and draft:
            refined = llm_refine(draft)
            if refined and refined != draft:
                final = refined

        return ProcessedText(raw=text, draft=draft or text, final=final)

    def process_draft_only(self, raw: str) -> str:
        """同步路径：只做到词典+规则，不调用 LLM。"""
        saved = self.llm_refine_enabled
        self.llm_refine_enabled = False
        try:
            return self.process(raw).draft
        finally:
            self.llm_refine_enabled = saved
