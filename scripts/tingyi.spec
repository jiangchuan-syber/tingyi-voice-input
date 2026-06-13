# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [(os.path.join(ROOT, "dictionary.json"), ".")]
binaries = []
hiddenimports = [
    "tingyi",
    "tingyi.app",
    "tingyi.app.tray",
    "tingyi.app.service",
    "tingyi.app.hotkey",
    "tingyi.input.paste",
    "tingyi.text",
    "tingyi.text.dictionary",
    "tingyi.text.refine",
    "tingyi.text.refine_llm",
    "tingyi.text.pipeline",
    "tingyi.log_config",
    "openai",
    "tingyi.models",
    "tingyi.models.download",
    "tingyi.models.paths",
    "sounddevice",
    "soundfile",
    "pystray",
    "PIL",
    "keyboard",
    "pyperclip",
    "numpy",
    "dotenv",
]

for pkg in ("sherpa_onnx", "numpy"):
    tmp = collect_all(pkg)
    datas += tmp[0]
    binaries += tmp[1]
    hiddenimports += tmp[2]

a = Analysis(
    [os.path.join(ROOT, "tingyi", "__main__.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["faster_whisper", "torch", "tensorflow"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Tingyi",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Tingyi",
)
