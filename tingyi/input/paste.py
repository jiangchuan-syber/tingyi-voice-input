# -*- coding: utf-8 -*-
"""将识别结果注入当前输入焦点。"""

from __future__ import annotations

import time


def _clipboard_backup():
    import pyperclip

    try:
        return pyperclip.paste()
    except Exception:
        return None


def _clipboard_restore(data) -> None:
    if data is None:
        return
    import pyperclip

    try:
        pyperclip.copy(data)
    except Exception:
        pass


def paste_to_focus(text: str, *, use_shift_insert: bool = False) -> int:
    """复制到剪贴板并粘贴；返回粘贴字符数（供后续替换用）。"""
    if not text:
        return 0

    import keyboard
    import pyperclip

    backup = _clipboard_backup()
    pyperclip.copy(text)
    time.sleep(0.08)
    if use_shift_insert:
        keyboard.send("shift+insert")
    else:
        keyboard.send("ctrl+v")
    time.sleep(0.05)
    _clipboard_restore(backup)
    return len(text)


def replace_recent_paste(char_count: int, new_text: str, *, use_shift_insert: bool = False) -> int:
    """删除刚粘贴的 char_count 个字符，再贴 new_text（LLM 润色替换用）。"""
    if char_count <= 0:
        return paste_to_focus(new_text, use_shift_insert=use_shift_insert)

    import keyboard

    for _ in range(char_count):
        keyboard.send("backspace")
        time.sleep(0.01)
    time.sleep(0.05)
    return paste_to_focus(new_text, use_shift_insert=use_shift_insert)
