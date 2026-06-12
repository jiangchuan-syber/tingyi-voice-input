# -*- coding: utf-8 -*-
"""规则润色：去口头语、整理空白（离线）。"""

from __future__ import annotations

import re

# 句首/逗号后常见填充词（保留语义，只删明显口水）
_FILLER_PATTERNS = [
    r"^[嗯呃啊哦哎诶]+[，,、\s]*",
    r"^[那个这个]+[，,、\s]*",
    r"^[就是然后]+[，,、\s]*",
    r"(?<=[，。！？\s])[嗯呃啊哦]+[，,、\s]*",
    r"(?<=[，。！？\s])[那个这个]+[，,、\s]*",
]

_FILLER_RE = [re.compile(p) for p in _FILLER_PATTERNS]


def rule_refine(text: str) -> str:
    if not text or not text.strip():
        return text

    result = text.strip()
    for _ in range(3):
        prev = result
        for pat in _FILLER_RE:
            result = pat.sub("", result)
        result = re.sub(r"[，,]{2,}", "，", result)
        result = re.sub(r"\s{2,}", " ", result)
        if result == prev:
            break

    return result.strip()
