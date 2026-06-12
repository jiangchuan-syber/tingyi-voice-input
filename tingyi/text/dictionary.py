# -*- coding: utf-8 -*-
"""个人词典：ASR 误识别 → 标准写法。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from tingyi.settings import ROOT


@dataclass(frozen=True)
class DictionaryEntry:
    canonical: str
    aliases: tuple[str, ...]


def default_dictionary_path() -> Path:
    user_path = Path.home() / ".tingyi" / "dictionary.json"
    if user_path.is_file():
        return user_path
    return ROOT / "dictionary.json"


def load_dictionary(path: Path | None = None) -> list[DictionaryEntry]:
    dict_path = path or default_dictionary_path()
    if not dict_path.is_file():
        return []

    data = json.loads(dict_path.read_text(encoding="utf-8"))
    entries: list[DictionaryEntry] = []
    for item in data.get("terms", []):
        canonical = (item.get("canonical") or "").strip()
        if not canonical:
            continue
        raw_aliases = item.get("aliases") or []
        aliases = tuple(a.strip() for a in raw_aliases if a and str(a).strip())
        entries.append(DictionaryEntry(canonical=canonical, aliases=aliases))
    return entries


def _replacement_pairs(entries: list[DictionaryEntry]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for entry in entries:
        for alias in entry.aliases:
            if alias and alias != entry.canonical:
                pairs.append((alias, entry.canonical))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs


def _is_ascii_word(text: str) -> bool:
    return bool(text) and all(ord(c) < 128 for c in text.replace(" ", "").replace("-", ""))


def apply_dictionary(text: str, entries: list[DictionaryEntry] | None = None) -> str:
    if not text or not text.strip():
        return text

    pairs = _replacement_pairs(entries or load_dictionary())
    if not pairs:
        return text

    result = text
    for alias, canonical in pairs:
        if _is_ascii_word(alias):
            pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(alias)}(?![A-Za-z0-9_])", re.I)
            result = pattern.sub(canonical, result)
        else:
            result = result.replace(alias, canonical)
    return result
