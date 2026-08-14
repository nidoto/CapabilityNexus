"""Build a distributable CapabilityNexus release directory.

Usage:
    py -3 tools/build_release.py

Produces a fresh folder under `dist/` (e.g. `dist/CapabilityNexus-1.7.0/`)
containing the client source, default config, packages, documentation,
launcher and requirements. It never touches the working tree and it excludes
local-only files (device tuning in profiles/local, caches, __pycache__).

The build is a source distribution, not a frozen executable. End users still
need Python 3.11+ and the drivers from THIRD_PARTY_NOTICES.md.
"""

import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "1.7.0"

# 参与分发的顶层目录 / 文件
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

# 打包时剔除的文件 / 目录（本地私有或缓存）
EXCLUDE_NAMES = {
    "__pycache__",
    ".git",
    "local",  # profiles/local - 个人设备调优
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


def build():
    dist_root = os.path.join(PROJECT_ROOT, "dist")
    out_dir = os.path.join(dist_root, f"CapabilityNexus-{VERSION}")

    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    for directory in INCLUDE_DIRS:
        _copy_tree(
            os.path.join(PROJECT_ROOT, directory),
            os.path.join(out_dir, directory),
        )

    for filename in INCLUDE_FILES:
        src = os.path.join(PROJECT_ROOT, filename)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(out_dir, filename))

    # 配置默认值：空设备、单个虚拟 XInput 输出
    default_config = {
        "devices": [],
    }
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

    import json

    _write_json(os.path.join(out_dir, "config", "devices.json"), default_config)
    _write_json(os.path.join(out_dir, "config", "outputs.json"), default_outputs)
    _write_json(os.path.join(out_dir, "profiles", "default.json"), default_profile)

    print(f"[Build] Release created at:")
    print(f"  {out_dir}")
    print()
    print("Next steps for end users:")
    print("  1. Install Python 3.11+")
    print("  2. py -3 -m pip install -r requirements.txt")
    print("  3. Install drivers (ViGEmBus, HidHide) - see THIRD_PARTY_NOTICES.md")
    print("  4. Double-click start.cmd")


def _write_json(path, data):
    import json

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    build()
