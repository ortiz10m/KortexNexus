# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller (--onedir) para Kortex Nexus v2.0 en Windows."""

import os
from PyInstaller.utils.hooks import collect_data_files

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = collect_data_files("customtkinter")
for rel_src, dest_dir in [
    ("icon.ico", "."),
    ("logo_kortex.png", "."),
    ("VERSION", "."),
    (os.path.join("kortex_ui", "fuentes", "Lucide.ttf"), os.path.join("kortex_ui", "fuentes")),
]:
    full = os.path.join(ROOT, rel_src)
    if os.path.exists(full):
        datas.append((full, dest_dir))

hiddenimports = [
    "customtkinter",
    "darkdetect",
    "PIL._tkinter_finder",
    "plyer.platforms.win.notification",
    "cerebro",
    "kortex_comandos",
    "kortex_contexto",
    "kortex_experto",
    "kortex_core.config",
    "kortex_core.platform_hal",
    "kortex_core.cryo",
    "kortex_core.optimizer",
    "kortex_core.predictor",
    "kortex_core.sentinel",
    "kortex_core.files",
    "kortex_core.modes",
    "kortex_ui.installer_wizard",
    "modules.browser.thorium_kiosk",
]

excludes = [
    "g4f",
    "yt_dlp",
    "gtts",
    "speech_recognition",
    "aiohttp",
    "cryptography",
    "Crypto",
    "numpy",
    "scipy",
    "pandas",
    "sklearn",
    "matplotlib",
    "cv2",
    "torch",
    "onnxruntime",
    "rembg",
    "pytest",
    "unittest",
]

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KortexNexus",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=os.path.join(ROOT, "icon.ico") if os.path.exists(os.path.join(ROOT, "icon.ico")) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="KortexNexus",
)
