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
VERSION = "1.8.0"

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
    # 默认 profile：手机（phone.*）与基础能力映射到 X360 输出
    default_profile = {
        "mappings": {
            "phone.roll": "right_x",
            "phone.pitch": "right_y",
            "phone.gas": "right_trigger",
            "phone.brake": "left_trigger",
            "phone.button_a": "button_a",
            "phone.button_b": "button_b",
            "phone.button_x": "button_x",
            "phone.button_y": "button_y",
            "phone.dpad_up": "button_dpad_up",
            "phone.dpad_down": "button_dpad_down",
            "phone.dpad_left": "button_dpad_left",
            "phone.dpad_right": "button_dpad_right",
        }
    }

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
        # 把手机页面复制到 exe 同级 web/（websocket_connection 的 _web_dir()
        # 在 frozen 模式下优先读取这里，发布者可替换页面而无需重新打包）
        web_src = os.path.join(out_dir, "web")
        if os.path.isdir(web_src):
            _copy_tree(web_src, os.path.join(exe_src, "web"))

        # 用户数据目录（exe 同级 config/profiles）：填充默认值
        # （frozen 下 config_io 读写这里；保留已存在文件，只补缺省）
        _ensure_user_data(exe_src, out_dir)

        print(f"[Build] Executable: {exe_src}")
        return True

    print("[Build] PyInstaller output not found.")
    return False


def _ensure_user_data(exe_src, out_dir):
    """填充 exe 同级用户数据目录（config/profiles），保留已存在的用户配置。"""
    # 1) 从发布目录 out_dir 复制默认（config/profiles 根，不含 local）
    for rel in ("config", "profiles"):
        user_dir = os.path.join(exe_src, rel)
        built_dir = os.path.join(out_dir, rel)
        if not os.path.isdir(user_dir):
            os.makedirs(user_dir, exist_ok=True)
        if os.path.isdir(built_dir):
            for name in os.listdir(built_dir):
                s = os.path.join(built_dir, name)
                d = os.path.join(user_dir, name)
                if os.path.isfile(s) and not os.path.exists(d):
                    shutil.copy2(s, d)
                elif os.path.isdir(s):
                    if not os.path.isdir(d):
                        shutil.copytree(s, d)

    # 2) 从源码 profiles/local 复制个人调优配置（不含 local 不打包，但用户需要）
    src_local = os.path.join(PROJECT_ROOT, "profiles", "local")
    dst_local = os.path.join(exe_src, "profiles", "local")
    if os.path.isdir(src_local):
        if not os.path.isdir(dst_local):
            os.makedirs(dst_local, exist_ok=True)
        for name in os.listdir(src_local):
            s = os.path.join(src_local, name)
            d = os.path.join(dst_local, name)
            if os.path.isfile(s) and not os.path.exists(d):
                shutil.copy2(s, d)

    # 3) 从源码 config 复制默认配置（active_profile.json 单独处理——
    #    仅当 exe 用户目录还没有时才初始化，避免覆盖用户的运行时选择）
    src_config = os.path.join(PROJECT_ROOT, "config")
    dst_config = os.path.join(exe_src, "config")
    if os.path.isdir(src_config):
        os.makedirs(dst_config, exist_ok=True)
        for name in ("devices.json", "outputs.json", "processors.json", "phone_presets.json"):
            s = os.path.join(src_config, name)
            d = os.path.join(dst_config, name)
            if os.path.isfile(s) and not os.path.exists(d):
                shutil.copy2(s, d)

    # 4) 初始激活配置：若用户目录还没有，且源码有 rushrally3，默认激活它
    active_dst = os.path.join(dst_config, "active_profile.json")
    if not os.path.exists(active_dst):
        src_active = os.path.join(src_config, "active_profile.json")
        if os.path.isfile(src_active):
            shutil.copy2(src_active, active_dst)


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
