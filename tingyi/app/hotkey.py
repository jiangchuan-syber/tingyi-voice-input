# -*- coding: utf-8 -*-
"""全局快捷键。"""

from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)


class HotkeyManager:
    def __init__(self, hotkey: str, on_trigger: Callable[[], None]) -> None:
        self.hotkey = hotkey
        self.on_trigger = on_trigger
        self._hook = None

    def start(self) -> None:
        import keyboard

        keyboard.add_hotkey(self.hotkey, self._safe_trigger, suppress=False)
        logger.info("Hotkey registered: %s", self.hotkey)

    def stop(self) -> None:
        import keyboard

        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            logger.debug("hotkey cleanup", exc_info=True)

    def _safe_trigger(self) -> None:
        try:
            self.on_trigger()
        except Exception:
            logger.exception("hotkey callback failed")
