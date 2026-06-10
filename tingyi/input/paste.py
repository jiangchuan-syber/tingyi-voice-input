# -*- coding: utf-8 -*-
"""将识别结果注入当前输入焦点。"""

from __future__ import annotations

import time


def paste_to_focus(text: str) -> None:
    """复制到剪贴板并模拟 Ctrl+V 粘贴到当前焦点窗口。"""
    if not text:
        return

    import keyboard
    import pyperclip

    pyperclip.copy(text)
    time.sleep(0.08)
    keyboard.send("ctrl+v")
