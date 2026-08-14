"""Bundle third-party driver installers for a CapabilityNexus release.

Copies verified local driver setups into the release `drivers/` directory so
end users do not need to search for them:

  - ViGEmBus (XInput-compatible controller backend)
  - HidHide (game-exclusive physical-device hiding)

Drivers are never installed silently. The bundled setup programs are the
official builds from the upstream authors (or a locally verified copy) and
require user consent.

ViGEmBus is taken from a local source directory when provided (for example a
vendor bundle such as QKeyMapper that ships a working ViGEmBus driver). The
whole driver package (x64 + x86 .sys/.inf/.cat, nefconw installer and
LICENSE) is copied so a released driver is complete and self-contained.
When no local source is given, the official GitHub release is used instead.

HidHide is always fetched from its official release.

Usage:
    py -3 tools/fetch_drivers.py <release_dir> [--vigembus-src <dir>]

Exit code 0 on success; 1 if a driver is missing.
"""

import os
import shutil
import sys
import urllib.request

HIDHIDE = {
    "name": "HidHide_1.5.230_x64.exe",
    "url": (
        "https://github.com/nefarius/HidHide/releases/download/"
        "v1.5.230.0/HidHide_1.5.230_x64.exe"
    ),
    "license_url": (
        "https://raw.githubusercontent.com/nefarius/HidHide/master/LICENSE"
    ),
}

# 官方 ViGEmBus 安装程序（本地源缺失时回退）
VIGEMBUS_OFFICIAL = {
    "name": "ViGEmBus_1.22.0_x64_x86_arm64.exe",
    "url": (
        "https://github.com/nefarius/ViGEmBus/releases/download/"
        "v1.22.0/ViGEmBus_1.22.0_x64_x86_arm64.exe"
    ),
    "license_url": (
        "https://raw.githubusercontent.com/nefarius/ViGEmBus/master/LICENSE"
    ),
}


def _download(url, dest):
    print(f"[Fetch] {os.path.basename(dest)}")
    print(f"  <- {url}")
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            with open(dest, "wb") as f:
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
    except Exception as error:
        print(f"  [X] download failed: {error}")
        return False
    print(f"  -> {dest} ({os.path.getsize(dest)} bytes)")
    return True


def _copy_file(src, dest):
    print(f"[Fetch] copy {os.path.basename(dest)}")
    print(f"  <- {src}")
    shutil.copy2(src, dest)
    print(f"  -> {dest} ({os.path.getsize(dest)} bytes)")


def _copy_vigembus_package(src_dir, drivers_dir):
    """从本地源目录拷贝完整的 ViGEmBus 驱动分发目录。

    期望布局（QKeyMapper 同款）：
      <src>/x64/{ViGEmBus.sys,ViGEmBus.inf,vigembus.cat,nefconw.exe,LICENSE}
      <src>/x86/{...}

    找不到 x64 时尝试在子目录里定位驱动包根。
    """
    root = src_dir
    if not os.path.isdir(root):
        print(f"[Fetch] ViGEmBus source not a directory: {root}")
        return False

    # 允许传入 ViGEmBusDriver 的父目录或 x64 所在目录
    if not os.path.isdir(os.path.join(root, "x64")):
        # 向上/向下找 x64 目录
        candidates = []
        for base in (root, os.path.dirname(root)):
            if os.path.isdir(os.path.join(base, "x64")):
                candidates.append(base)
        if not candidates:
            for walk_root, dirs, _ in os.walk(root):
                if "x64" in dirs:
                    candidates.append(walk_root)
                    break
        if not candidates:
            print("[Fetch] No ViGEmBus x64 driver directory found in source.")
            return False
        root = candidates[0]

    dest_pkg = os.path.join(drivers_dir, "ViGEmBus")
    os.makedirs(dest_pkg, exist_ok=True)

    copied = False
    for arch in ("x64", "x86"):
        src_arch = os.path.join(root, arch)
        if not os.path.isdir(src_arch):
            continue
        dest_arch = os.path.join(dest_pkg, arch)
        os.makedirs(dest_arch, exist_ok=True)
        for name in os.listdir(src_arch):
            src_file = os.path.join(src_arch, name)
            if os.path.isfile(src_file):
                _copy_file(src_file, os.path.join(dest_arch, name))
                copied = True

    if not copied:
        print("[Fetch] ViGEmBus driver directory was empty.")
        return False

    print(f"[Fetch] ViGEmBus driver package: {dest_pkg}")
    return True


def _copy_official_vigembus(drivers_dir, skip_existing):
    installer = os.path.join(drivers_dir, VIGEMBUS_OFFICIAL["name"])
    license_file = os.path.join(
        drivers_dir,
        os.path.splitext(VIGEMBUS_OFFICIAL["name"])[0] + "_LICENSE",
    )

    if skip_existing and os.path.exists(installer):
        print(f"[Fetch] skip existing: {VIGEMBUS_OFFICIAL['name']}")
    elif not _download(VIGEMBUS_OFFICIAL["url"], installer):
        return False

    if not os.path.exists(license_file):
        if not _download(VIGEMBUS_OFFICIAL["license_url"], license_file):
            return False
    return True


def _fetch_installer(spec, drivers_dir, skip_existing):
    installer = os.path.join(drivers_dir, spec["name"])
    license_file = os.path.join(
        drivers_dir, os.path.splitext(spec["name"])[0] + "_LICENSE"
    )

    if skip_existing and os.path.exists(installer):
        print(f"[Fetch] skip existing: {spec['name']}")
    elif not _download(spec["url"], installer):
        return False

    if not os.path.exists(license_file):
        if not _download(spec["license_url"], license_file):
            return False
    return True


def fetch(release_dir, vigembus_src=None, skip_existing=True):
    drivers_dir = os.path.join(release_dir, "drivers")
    os.makedirs(drivers_dir, exist_ok=True)

    ok = True

    # ---- ViGEmBus ----
    if vigembus_src:
        if not _copy_vigembus_package(vigembus_src, drivers_dir):
            print("[Fetch] Falling back to official ViGEmBus release.")
            if not _copy_official_vigembus(drivers_dir, skip_existing):
                ok = False
    else:
        if not _copy_official_vigembus(drivers_dir, skip_existing):
            ok = False

    # ---- HidHide：始终官方 ----
    if not _fetch_installer(HIDHIDE, drivers_dir, skip_existing):
        ok = False

    print()
    if ok:
        print("[Fetch] All drivers ready.")
    else:
        print("[Fetch] Some drivers are missing. Check the source/network and retry.")
    return ok


def main():
    args = sys.argv[1:]

    if len(args) < 1:
        print(__doc__)
        return 1

    release_dir = args[0]
    vigembus_src = None

    if "--vigembus-src" in args:
        idx = args.index("--vigembus-src")
        if idx + 1 < len(args):
            vigembus_src = args[idx + 1]

    return 0 if fetch(release_dir, vigembus_src) else 1


if __name__ == "__main__":
    sys.exit(main())
