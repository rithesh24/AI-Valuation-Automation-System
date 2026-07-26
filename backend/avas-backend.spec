# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the backend (Phase 9, D21). Build with:
#   pyinstaller avas-backend.spec
# collect_all('playwright') pulls in its driver stub (not the Chromium
# binary itself — that's a separate `playwright install chromium` step, see
# D13/D21). collect_all('uvicorn') is needed because uvicorn's protocol/loop
# implementations are chosen dynamically at runtime, which static analysis
# can't see.
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
for package in ("playwright", "uvicorn"):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

a = Analysis(
    ["run_server.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="avas-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
