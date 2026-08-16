# -*- mode: python ; coding: utf-8 -*-
# CapabilityNexus PyInstaller spec (one-dir, windowed GUI)
#
# Data source: CNX_DATA_DIR (set by tools/build_release.py). It points to the
# freshly built source-distribution directory whose config/profiles/packages
# are already sanitized (caches, active_profile, profiles/local removed).
#
# This keeps a distributed exe self-contained with clean defaults only.

import os

# 解析 vgamepad 的 ViGEmClient.dll（Windows 客户端库）
try:
    import vgamepad
    import vgamepad.win  # noqa: F401
    import vgamepad.win.vigem_client  # noqa: F401

    _vg_dir = os.path.dirname(vgamepad.__file__)
    _vigem_x64 = os.path.join(_vg_dir, "win", "vigem", "client", "x64", "ViGEmClient.dll")
    _vigem_bin = []
    if os.path.exists(_vigem_x64):
        _vigem_bin = [(_vigem_x64, "vgamepad/win/vigem/client/x64")]
    else:
        print("[Spec] ViGEmClient.dll not found - vgamepad XInput backend may not work")
except Exception as error:
    _vigem_bin = []
    print("[Spec] vgamepad not importable:", error)


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
    (os.path.join(data_dir, 'web'), 'web'),
]

a = Analysis(
    ['tools/cnx_gui.py'],
    pathex=['.'],
    binaries=_vigem_bin,
    datas=datas,
    hiddenimports=[
        'cryptography',
        'cryptography.x509',
        'cryptography.hazmat.backends.openssl',
        'cryptography.hazmat.primitives.asymmetric.rsa',
        'cryptography.hazmat.primitives.serialization',
        'asn1crypto',
        'asn1crypto.x509',
        'certifi',
        'vgamepad',
        'vgamepad.win',
        'vgamepad.win.vigem_client',
        'vgamepad.win.vigem_commons',
        'vgamepad.win.virtual_gamepad',
    ],
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
