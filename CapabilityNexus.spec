# -*- mode: python ; coding: utf-8 -*-
# CapabilityNexus PyInstaller spec (one-dir, windowed GUI)
#
# Data source: CNX_DATA_DIR (set by tools/build_release.py). It points to the
# freshly built source-distribution directory whose config/profiles/packages
# are already sanitized (caches, active_profile, profiles/local removed).
#
# This keeps a distributed exe self-contained with clean defaults only.

import os


def _data_dir():
    data_dir = os.environ.get("CNX_DATA_DIR") or os.getcwd()
    print(f"[Spec] CNX_DATA_DIR = {data_dir}")
    return data_dir


data_dir = _data_dir()

datas = [
    (os.path.join(data_dir, 'config'), 'config'),
    (os.path.join(data_dir, 'profiles'), 'profiles'),
    (os.path.join(data_dir, 'packages'), 'packages'),
    (os.path.join(data_dir, 'tools', 'game_library'), 'tools/game_library'),
]

a = Analysis(
    ['tools/cnx_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='CapabilityNexus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CapabilityNexus',
)
