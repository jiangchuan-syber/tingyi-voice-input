# -*- coding: utf-8 -*-
"""系统托盘桌面应用。"""

from __future__ import annotations

import logging
import sys

from tingyi import __version__
from tingyi.app.hotkey import HotkeyManager
from tingyi.app.service import VoiceInputService
from tingyi.log_config import get_log_file, open_log_file, setup_logging
from tingyi.settings import ROOT

logger = logging.getLogger(__name__)


def _make_icon():
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, size - 4, size - 4), fill=(66, 133, 244, 255))
    draw.rounded_rectangle((22, 18, 42, 46), radius=10, fill=(255, 255, 255, 240))
    draw.line((32, 46, 32, 54), fill=(255, 255, 255, 240), width=3)
    draw.line((26, 54, 38, 54), fill=(255, 255, 255, 240), width=3)
    return img


def run_desktop_app() -> None:
    log_path = setup_logging()

    service = VoiceInputService()
    if not service.is_ready():
        print("SenseVoice 未就绪。请确保 models/ 目录完整，或运行 python -m tingyi --download-models")
        sys.exit(1)

    import pystray

    hotkey_mgr = HotkeyManager(service.hotkey_label(), service.toggle_listening)
    hotkey_mgr.start()

    icon_holder: dict[str, pystray.Icon | None] = {"icon": None}

    def notify(title: str, message: str | None) -> None:
        icon = icon_holder["icon"]
        if icon is not None:
            icon.notify(message or title, title)

    service.set_notifier(notify)

    hotkey = service.hotkey_label()

    def on_quit(icon: pystray.Icon, _item) -> None:
        if service.is_listening():
            service.toggle_listening()
        hotkey_mgr.stop()
        icon.stop()

    def on_open_log(icon: pystray.Icon, _item) -> None:
        try:
            open_log_file()
        except Exception:
            logger.exception("open log failed")
            notify("听译", f"日志路径：{get_log_file()}")

    menu = pystray.Menu(
        pystray.MenuItem(
            f"听译 v{__version__}（{hotkey}）",
            lambda *_: None,
            enabled=False,
        ),
        pystray.MenuItem(
            "开启/关闭持续监听",
            lambda *_: service.toggle_listening(),
        ),
        pystray.MenuItem(
            "打开日志",
            on_open_log,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", on_quit),
    )

    icon = pystray.Icon(
        "tingyi",
        _make_icon(),
        f"听译 · {hotkey} 开关监听",
        menu,
    )
    icon_holder["icon"] = icon

    logger.info("Desktop app started. ROOT=%s hotkey=%s log=%s", ROOT, hotkey, log_path)
    icon.run()
