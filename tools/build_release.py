"""Build a distributable CapabilityNexus release.

Usage:
    py -3 tools/build_release.py                 # full release (exe + drivers)
    py -3 tools/build_release.py --no-exe        # source distribution only
    py -3 tools/build_release.py --no-drivers    # exe but skip driver download

Produces a fresh folder under `dist/` (e.g. `dist/CapabilityNexus-1.7.0/`)
containing:

  - the Python client source + default config + packages + docs + launcher
  - a frozen Windows executable (PyInstaller, one-dir) when PyInstaller is
    available, or when --no-exe is not given
  - bundled official ViGEmBus / HidHide driver installers and their licenses

The build never touches the working tree. Local-only files (device tuning in
profiles/local, caches, __pycache__) are excluded.
"""

import os
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "1.7.0"

INCLUDE_DIRS = (
    "core",
    "devices",
    "mapping",
    "output",
    "packages",
    "processors",
    "protocols",
    "tools",
    "config",
    "docs",
    "profiles",
    "web",
)

INCLUDE_FILES = (
    "app.py",
    "main.py",
    "start.cmd",
    "requirements.txt",
    "LICENSE",
    "README.md",
    "THIRD_PARTY_NOTICES.md",
)

EXCLUDE_NAMES = {
    "__pycache__",
    ".git",
    "local",  # profiles/local - 个人设备调优
    "tests",  # 测试不进发布包
    ".pytest_cache",
}

EXCLUDE_FILE_PATTERNS = (
    "*.pyc",
    "*.pyo",
    "device_library_cache.json",
    "request_library_cache.json",
    "active_profile.json",
)


def _should_exclude(name, full_path):
    if name in EXCLUDE_NAMES:
        return True
    for pattern in EXCLUDE_FILE_PATTERNS:
        if name.endswith(pattern):
            return True
    return False


def _copy_tree(src, dst):
    if not os.path.exists(src):
        return
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        if _should_exclude(name, os.path.join(src, name)):
            continue
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        if os.path.isdir(s):
            _copy_tree(s, d)
        else:
            shutil.copy2(s, d)


def _write_json(path, data):
    import json

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def _pyinstaller_available():
    try:
        import PyInstaller  # noqa: F401
        return True
    except ImportError:
        return False


def build_source(out_dir):
    """复制源码 + 默认配置 + 文档到发布目录。"""
    for directory in INCLUDE_DIRS:
        _copy_tree(
            os.path.join(PROJECT_ROOT, directory),
            os.path.join(out_dir, directory),
        )

    for filename in INCLUDE_FILES:
        src = os.path.join(PROJECT_ROOT, filename)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(out_dir, filename))

    # 驱动安装辅助脚本放到发布根目录
    install_script = os.path.join(PROJECT_ROOT, "tools", "install_drivers.cmd")
    if os.path.exists(install_script):
        shutil.copy2(install_script, os.path.join(out_dir, "install_drivers.cmd"))

    default_config = {"devices": []}
    default_outputs = {
        "outputs": [
            {
                "id": "virtual_xinput",
                "type": "xinput",
                "name": "XInput-compatible Controller",
            }
        ],
    }
    default_profile = {"mappings": {}}

    _write_json(os.path.join(out_dir, "config", "devices.json"), default_config)
    _write_json(os.path.join(out_dir, "config", "outputs.json"), default_outputs)
    _write_json(os.path.join(out_dir, "profiles", "default.json"), default_profile)


def build_exe(out_dir):
    """用 PyInstaller 打包 exe 到发布目录的 windows/ 子目录。"""
    if not _pyinstaller_available():
        print("[Build] PyInstaller not installed - skipping exe build.")
        return False

    windows_dir = os.path.join(out_dir, "windows")
    os.makedirs(windows_dir, exist_ok=True)

    spec_src = os.path.join(PROJECT_ROOT, "CapabilityNexus.spec")
    if not os.path.exists(spec_src):
        print("[Build] No spec file CapabilityNexus.spec - skipping exe.")
        return False

    work_dir = os.path.join(PROJECT_ROOT, "build", "pyinstaller")
    env = dict(os.environ)
    env["CNX_DATA_DIR"] = out_dir
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--workpath", work_dir,
        "--distpath", windows_dir,
        spec_src,
    ]
    print("[Build] Running PyInstaller...")
    try:
        subprocess.run(cmd, cwd=PROJECT_ROOT, check=True, env=env)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"[Build] PyInstaller failed: {error}")
        return False

    # exe 产物位于 windows/CapabilityNexus/
    exe_src = os.path.join(windows_dir, "CapabilityNexus")
    if os.path.exists(exe_src):
        print(f"[Build] Executable: {exe_src}")
        return True

    print("[Build] PyInstaller output not found.")
    return False


def build_drivers(out_dir, vigembus_src=None):
    """捆绑 ViGEmBus / HidHide 安装程序与许可证。"""
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "tools"))
    try:
        from fetch_drivers import fetch
        ok = fetch(out_dir, vigembus_src=vigembus_src)
        return ok
    except ImportError as error:
        print(f"[Build] fetch_drivers import failed: {error}")
        return False


def build():
    args = sys.argv[1:]
    do_exe = "--no-exe" not in args
    do_drivers = "--no-drivers" not in args

    dist_root = os.path.join(PROJECT_ROOT, "dist")
    out_dir = os.path.join(dist_root, f"CapabilityNexus-{VERSION}")

    if os.path.exists(out_dir):
        try:
            shutil.rmtree(out_dir)
        except OSError as error:
            print(f"[Build] Warning: could not clear {out_dir}: {error}")
            print("  Close any running CapabilityNexus.exe and retry.")
            return 1
    os.makedirs(out_dir, exist_ok=True)

    print("[Build] Stage 1/3: source distribution")
    build_source(out_dir)

    if do_exe:
        print()
        print("[Build] Stage 2/3: frozen executable")
        build_exe(out_dir)

    if do_drivers:
        print()
        print("[Build] Stage 3/3: driver installers")
        build_drivers(out_dir)

    print()
    print("[Build] Release created at:")
    print(f"  {out_dir}")
    print()
    print("Contents:")
    print("  - python/      client source (run: py -3 -m pip install -r requirements.txt)")
    print("  - windows/     frozen executable (double-click CapabilityNexus.exe)")
    print("  - drivers/     official ViGEmBus / HidHide installers")
    print()
    print("End users still install the drivers with consent (see THIRD_PARTY_NOTICES.md).")


if __name__ == "__main__":
    build()
