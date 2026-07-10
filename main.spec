# -*- mode: python ; coding: utf-8 -*-

import os
import customtkinter

customtkinter_path = os.path.dirname(customtkinter.__file__)

# Common analysis layout used for both builds
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (os.path.join(customtkinter_path, "assets"), "customtkinter/assets"),
        ("press.ico", "."),
        ("imageMagick", "imageMagick"),
        ("jpegli", "jpegli")
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# ================= 1. RELEASE VERSION (No Console) =================
exe_release = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Zmniejszacz Obrazów',       # Standard name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                   # Hides the console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='press.ico',
)

# ================= 2. DEBUG VERSION (With Console) =================
exe_debug = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Zmniejszacz Obrazów Debug', # Custom debug name suffix
    debug=True,                       # Enables bootloader debug logs
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,                    # Shows the console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='press.ico',
)
