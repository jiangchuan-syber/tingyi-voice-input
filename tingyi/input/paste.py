# -*- coding: utf-8 -*-
"""将识别结果注入当前输入焦点。"""

from __future__ import annotations

import time

# Windows 上目标程序读取剪贴板需要足够时间；过早 restore 会贴成剪贴板里的旧内容
_CLIPBOARD_SETTLE_S = 0.05
_PASTE_COMPLETE_S = 0.15
_KEY_SETTLE_S = 0.02
_BACKSPACE_BURST = 20
_BACKSPACE_BURST_PAUSE_S = 0.008


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


def _send_backspaces(count: int) -> None:
    if count <= 0:
        return

    import keyboard

    for i in range(count):
        keyboard.send("backspace")
        if (i + 1) % _BACKSPACE_BURST == 0:
            time.sleep(_BACKSPACE_BURST_PAUSE_S)


def paste_to_focus(
    text: str,
    *,
    use_shift_insert: bool = False,
    restore_clipboard: bool = False,
) -> int:
    """复制到剪贴板并粘贴；返回粘贴字符数（供后续替换用）。"""
    if not text:
        return 0

    import keyboard
    import pyperclip

    backup = _clipboard_backup() if restore_clipboard else None
    pyperclip.copy(text)
    time.sleep(_CLIPBOARD_SETTLE_S)
    if use_shift_insert:
        keyboard.send("shift+insert")
    else:
        keyboard.send("ctrl+v")
    # 必须等目标窗口读完剪贴板，再 restore；否则常贴出旧剪贴板内容（如单个「开」）
    time.sleep(_PASTE_COMPLETE_S)
    if restore_clipboard:
        _clipboard_restore(backup)
    return len(text)


def replace_recent_paste(
    char_count: int,
    new_text: str,
    *,
    use_shift_insert: bool = False,
    restore_clipboard: bool = False,
) -> int:
    """删除刚粘贴的 char_count 个字符，再贴 new_text（LLM 润色替换用）。"""
    if char_count <= 0:
        return paste_to_focus(
            new_text,
            use_shift_insert=use_shift_insert,
            restore_clipboard=restore_clipboard,
        )

    _send_backspaces(char_count)
    time.sleep(_KEY_SETTLE_S)
    return paste_to_focus(
        new_text,
        use_shift_insert=use_shift_insert,
        restore_clipboard=restore_clipboard,
    )
