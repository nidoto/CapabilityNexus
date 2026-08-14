"""HidHide 游戏独占模式管理。

封装 Nefarius HidHide 的命令行工具 HidHideCLI.exe：

  - 定位并调用 CLI
  - 读取 / 切换 cloaking 状态（隐藏生效与否）
  - 枚举 HID 设备（HidHideCLI 的 --dev-all 输出在部分系统上不稳定，
    因此默认用 Windows PnP / SetupAPI 枚举）
  - 隐藏 / 取消隐藏指定设备（device instance path）
  - 应用豁免列表（哪些应用仍可看到被隐藏设备）
  - 管理员提权执行（HidHide 修改操作需要管理员权限）

用法示例（CLI）：
  python tools/hidhide.py status
  python tools/hidhide.py devices
  python tools/hidhide.py hide "<instance path>"
  python tools/hidhide.py unhide "<instance path>"
"""

import ctypes
import os
import re
import subprocess
import sys
import tempfile

DEFAULT_CLI_PATHS = (
    r"C:\Program Files\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe",
    r"C:\Program Files (x86)\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe",
    r"C:\Program Files\Nefarius Software Solutions\HidHide\HidHideCLI.exe",
)

ERROR_ACCESS_DENIED = 0x0005


def find_cli():
    """返回 HidHideCLI.exe 完整路径；未安装返回 None。"""
    for path in DEFAULT_CLI_PATHS:
        if os.path.isfile(path):
            return path

    try:
        import winreg

        key_path = r"SOFTWARE\Nefarius Software Solutions e.U.\Nefarius Software Solutions e.U. HidHide"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            install_dir, _ = winreg.QueryValueEx(key, "InstallLocation")
        candidate = os.path.join(install_dir, "x64", "HidHideCLI.exe")
        if os.path.isfile(candidate):
            return candidate
    except (ImportError, OSError):
        pass

    return None


def is_installed():
    return find_cli() is not None


def is_admin():
    """检查当前进程是否以管理员权限运行。"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run(cli, args, timeout=20):
    try:
        result = subprocess.run(
            [cli] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except (OSError, subprocess.SubprocessError) as error:
        return -1, "", str(error)


def run_cli(args, elevated=False, timeout=60):
    """运行 HidHideCLI。

    elevated=True 且当前非管理员时通过 UAC 提权执行，输出写入临时文件后读取。
    返回 (returncode, stdout, stderr)。
    """
    cli = find_cli()
    if cli is None:
        return -1, "", "HidHide not installed"

    if not elevated or is_admin():
        return _run(cli, args, timeout=timeout)

    return _run_elevated(cli, args, timeout=timeout)


def _run_elevated(cli, args, timeout=60):
    """通过 UAC 提权运行 HidHideCLI，等待完成并读取输出。"""
    temp_dir = tempfile.mkdtemp(prefix="hidhide-")
    out_file = os.path.join(temp_dir, "out.txt")
    err_file = os.path.join(temp_dir, "err.txt")
    done_file = os.path.join(temp_dir, "done.txt")
    code_file = os.path.join(temp_dir, "code.txt")

    args_quoted = " ".join(_quote(arg) for arg in args)
    command = (
        f'cmd.exe /c ""{_quote(cli)}" {args_quoted} '
        f'> "{out_file}" 2> "{err_file}" '
        f'& echo %errorlevel% > "{code_file}"'
        f'& echo done > "{done_file}""'
    )

    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "cmd.exe",
            f"/c {command}",
            None,
            0,
        )
    except Exception as error:
        return -1, "", f"Elevation failed: {error}"

    if result <= 32:
        return result, "", "UAC elevation cancelled or failed"

    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(done_file):
            break
        time.sleep(0.2)

    stdout = ""
    stderr = ""

    try:
        if os.path.exists(out_file):
            with open(out_file, "r", encoding="utf-8", errors="replace") as f:
                stdout = f.read()
    except OSError:
        pass

    try:
        if os.path.exists(err_file):
            with open(err_file, "r", encoding="utf-8", errors="replace") as f:
                stderr = f.read()
    except OSError:
        pass

    returncode = 0
    if not os.path.exists(done_file):
        returncode = -1
        stderr += "HidHide elevated command timed out"
    else:
        try:
            with open(code_file, "r", encoding="utf-8", errors="replace") as f:
                returncode = int((f.read().strip() or "0").split()[-1])
        except (OSError, ValueError):
            returncode = 0

    return returncode, stdout, stderr


def _quote(text):
    return f'"{text}"'


#
# 状态查询（无需管理员）
#


def cloak_state():
    """返回 '--cloak-on' / '--cloak-off' / None。"""
    returncode, stdout, _ = run_cli(["--cloak-state"])
    if returncode != 0:
        return None
    match = re.search(r"(--cloak-(?:on|off))", stdout)
    return match.group(1) if match else None


def cloak_active():
    return cloak_state() == "--cloak-on"


def inverse_state():
    """返回 '--inv-on' / '--inv-off' / None。"""
    returncode, stdout, _ = run_cli(["--inv-state"])
    if returncode != 0:
        return None
    match = re.search(r"(--inv-(?:on|off))", stdout)
    return match.group(1) if match else None


def list_apps():
    """返回已注册的豁免应用路径列表。"""
    returncode, stdout, _ = run_cli(["--app-list"])
    if returncode != 0:
        return []
    return re.findall(r'--app-reg\s+"([^"]+)"', stdout)


def list_hidden():
    """返回当前已隐藏设备的实例路径列表。"""
    returncode, stdout, _ = run_cli(["--dev-list"])
    if returncode != 0:
        return []
    return re.findall(r'--dev-hide\s+"([^"]+)"', stdout)


def is_hidden(instance_path):
    return instance_path in list_hidden()


#
# 设备枚举（使用 Windows PnP，避免 CLI --dev-all 不稳定输出）
#

GAMING_HINTS = (
    "xbox",
    "controller",
    "gamepad",
    "joystick",
    "steam controller",
    "dualshock",
    "dual sense",
    "wheel",
    "xinput",
    "手柄",
    "方向盘",
    "模拟器",
)

# Microsoft Xbox 手柄 PID 前缀（蓝牙 BTHLE / USB HID）
XBOX_VID = "VID&045E"


def list_hid_devices():
    """用 Get-PnpDevice 枚举 HIDClass 与 XUSBClass 设备。

    返回 [{instance_id, friendly_name, class, gaming}]。
    """
    powershell = (
        "Get-PnpDevice -PresentOnly | "
        "Where-Object { $_.Class -eq 'HIDClass' -or $_.Class -eq 'XUSBClass' } | "
        "Select-Object Class, FriendlyName, InstanceId | "
        "ConvertTo-Json -Compress"
    )

    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; " + powershell],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        print("[HidHide] PnP enumeration failed:", error)
        return []

    import json

    try:
        data = json.loads(result.stdout)
    except (ValueError, json.JSONDecodeError):
        return []

    if not isinstance(data, list):
        if isinstance(data, dict):
            data = [data]
        else:
            return []

    devices = []
    for item in data:
        instance_id = item.get("InstanceId") or ""
        friendly = item.get("FriendlyName") or ""
        cls = item.get("Class") or ""
        name = friendly or instance_id
        name_lower = name.lower()
        id_upper = instance_id.upper()
        gaming = (
            any(hint in name_lower for hint in GAMING_HINTS)
            or XBOX_VID in id_upper
        )

        devices.append({
            "instance_id": instance_id,
            "friendly_name": friendly,
            "class": cls,
            "gaming": gaming,
        })

    return devices


def list_gaming_devices():
    """枚举游戏相关 HID 设备（名称命中手柄/方向盘关键词）。"""
    devices = list_hid_devices()
    return [d for d in devices if d.get("gaming")]


#
# 修改操作（均需管理员权限）
#


def set_cloak(on):
    """启用 / 停用隐藏生效状态。返回 (ok, message)。"""
    arg = "--cloak-on" if on else "--cloak-off"
    returncode, stdout, stderr = run_cli([arg], elevated=True)
    if returncode != 0:
        return False, (stderr or stdout or "cloak change failed")
    return True, ""


def hide(instance_path):
    """隐藏指定设备。返回 (ok, message)。"""
    returncode, stdout, stderr = run_cli(
        ["--dev-hide", instance_path],
        elevated=True,
    )
    if returncode != 0:
        return False, (stderr or stdout or "hide failed")
    return True, ""


def unhide(instance_path):
    """取消隐藏指定设备。返回 (ok, message)。"""
    returncode, stdout, stderr = run_cli(
        ["--dev-unhide", instance_path],
        elevated=True,
    )
    if returncode != 0:
        return False, (stderr or stdout or "unhide failed")
    return True, ""


def register_app(path):
    """将应用加入豁免列表（该应用仍可看到被隐藏设备）。"""
    returncode, stdout, stderr = run_cli(
        ["--app-reg", path],
        elevated=True,
    )
    if returncode != 0:
        return False, (stderr or stdout or "app register failed")
    return True, ""


def unregister_app(path):
    """将应用从豁免列表移除。"""
    returncode, stdout, stderr = run_cli(
        ["--app-unreg", path],
        elevated=True,
    )
    if returncode != 0:
        return False, (stderr or stdout or "app unregister failed")
    return True, ""


def set_inverse(on):
    """切换反转应用列表（黑名单模式）。"""
    arg = "--inv-on" if on else "--inv-off"
    returncode, stdout, stderr = run_cli([arg], elevated=True)
    if returncode != 0:
        return False, (stderr or stdout or "inverse change failed")
    return True, ""


#
# 便捷流程
#


def ensure_self_visible():
    """把当前 Python 进程加入豁免列表，保证 CapabilityNexus 自己仍能读取
    被隐藏的物理手柄。返回 (ok, message)。"""
    exe = getattr(sys, "executable", None) or ""
    if not exe:
        return False, "cannot resolve python executable"

    exe = os.path.abspath(exe)

    apps = list_apps()
    if exe.lower() in (a.lower() for a in apps):
        return True, f"already registered: {exe}"

    return register_app(exe)


def hide_all_gaming_devices(with_self_visible=True):
    """隐藏所有游戏 HID 设备，并保持自己可见。

    返回 (ok, message, hidden_count)。
    """
    if with_self_visible:
        ok, message = ensure_self_visible()
        if not ok:
            return False, f"self-register failed: {message}", 0

    hidden = list_hidden()
    hidden_set = set(hidden)

    count = 0
    for device in list_gaming_devices():
        instance_id = device["instance_id"]
        if instance_id in hidden_set:
            continue
        ok, message = hide(instance_id)
        if not ok:
            return False, f"hide failed: {message}", count
        hidden_set.add(instance_id)
        count += 1

    ok, message = set_cloak(True)
    if not ok:
        return False, f"cloak failed: {message}", count

    return True, "", count


def status_text():
    """生成人类可读的状态摘要。"""
    cli = find_cli()
    lines = []

    if cli is None:
        return "HidHide 未安装（缺少 HidHideCLI.exe）"

    lines.append(f"CLI: {cli}")
    lines.append(f"Admin: {'yes' if is_admin() else 'no'}")
    lines.append(f"Cloaking: {cloak_state() or 'unknown'}")
    lines.append(f"Inverse: {inverse_state() or 'unknown'}")

    apps = list_apps()
    lines.append(f"Exempt apps: {len(apps)}")
    for app in apps:
        lines.append(f"  {app}")

    hidden = list_hidden()
    lines.append(f"Hidden devices: {len(hidden)}")
    for path in hidden:
        lines.append(f"  {path}")

    return "\n".join(lines)


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return

    command = args[0]

    if command == "status":
        print(status_text())
    elif command == "devices":
        for device in list_hid_devices():
            tag = "GAMING" if device["gaming"] else "hid   "
            name = device["friendly_name"] or device["instance_id"]
            print(f"[{tag}] {name}  {device['instance_id']}")
    elif command == "hidden":
        for path in list_hidden():
            print(path)
    elif command in ("hide", "unhide") and len(args) >= 2:
        fn = hide if command == "hide" else unhide
        ok, message = fn(args[1])
        print("OK" if ok else f"FAIL: {message}")
    elif command == "cloak-on":
        ok, message = set_cloak(True)
        print("OK" if ok else f"FAIL: {message}")
    elif command == "cloak-off":
        ok, message = set_cloak(False)
        print("OK" if ok else f"FAIL: {message}")
    elif command == "self-visible":
        ok, message = ensure_self_visible()
        print("OK" if ok else f"FAIL: {message}")
    elif command == "apps":
        for app in list_apps():
            print(app)
    elif command == "hide-all":
        ok, message, count = hide_all_gaming_devices()
        print(f"{'OK' if ok else 'FAIL: ' + message} hidden={count}")
    else:
        print("Unknown command:", command)
        print(__doc__)


if __name__ == "__main__":
    main()
