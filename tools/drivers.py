"""Driver management for ViGEmBus and HidHide.

Detects, installs and uninstalls the Windows drivers used by CapabilityNexus.
Driver operations require administrator rights; a UAC prompt is raised via
ShellExecute "runas" when the current process is not elevated.

Driver file locations are resolved in this order:

  - a bundled drivers/ directory next to the release (source dist or exe)
  - a user-provided path (--drivers-dir / drivers_dir)

The bundled ViGEmBus driver package (from the release) is installed through
nefconw.exe --install-driver. HidHide is a setup program and is launched for
the user to confirm.
"""

import ctypes
import os
import subprocess
import sys


def is_admin():
    """检查当前进程是否以管理员权限运行。"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _elevate(cmd):
    """通过 UAC 提权运行命令行，等待完成并返回退出码。

    cmd: 字符串形式，交由 cmd.exe /c 执行。
    """
    if is_admin():
        result = subprocess.run(
            ["cmd.exe", "/c", cmd],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr

    import tempfile
    import time

    temp_dir = tempfile.mkdtemp(prefix="cnx-drv-")
    out_file = os.path.join(temp_dir, "out.txt")
    err_file = os.path.join(temp_dir, "err.txt")
    done_file = os.path.join(temp_dir, "done.txt")

    wrapped = (
        f'cmd.exe /c ""{cmd} > "{out_file}" 2> "{err_file}"'
        f'& echo %errorlevel% > "{temp_dir}\\rc.txt"'
        f'& echo done > "{done_file}""'
    )

    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "cmd.exe",
            f"/c {wrapped}",
            None,
            0,
        )
    except Exception as error:
        return -1, "", f"elevation failed: {error}"

    if result <= 32:
        return result, "", "UAC elevation cancelled or failed"

    deadline = time.time() + 180
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
        stderr += "elevated command timed out"
    else:
        try:
            rc_path = os.path.join(temp_dir, "rc.txt")
            with open(rc_path, "r", encoding="utf-8", errors="replace") as f:
                returncode = int((f.read().strip() or "0").split()[-1])
        except (OSError, ValueError):
            returncode = 0

    return returncode, stdout, stderr


#
# 检测
#


def check_vigembus():
    """返回 ViGEmBus 驱动是否安装。"""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Services\ViGEmBus",
        ):
            return True
    except (ImportError, OSError):
        pass

    return _service_exists(("ViGEmBus", "NefariusVirtualGamepadEmulationBus"))


def check_hidhide():
    """返回 HidHide 是否安装。"""
    try:
        import winreg
        keys = (
            r"SOFTWARE\Nefarius Software Solutions e.U.\Nefarius Software Solutions e.U. HidHide",
            r"Installer\Dependencies\NSS.Drivers.HidHide.x64",
        )
        for path in keys:
            for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CLASSES_ROOT):
                try:
                    with winreg.OpenKey(root, path):
                        return True
                except FileNotFoundError:
                    continue
    except (ImportError, OSError):
        pass

    return _service_exists(("HidHide",))


def _service_exists(names):
    for name in names:
        try:
            result = subprocess.run(
                ["sc.exe", "query", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=3,
            )
            if result.returncode == 0:
                return True
        except (OSError, subprocess.SubprocessError):
            pass
    return False


def driver_status():
    """返回 (vigembus_installed, hidhide_installed)。"""
    return check_vigembus(), check_hidhide()


#
# 路径定位
#


def _project_root():
    # 源码运行：app 所在目录的上一级
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find_bundled_drivers_dir():
    """在发布包 / 项目里定位 drivers/ 目录。"""
    candidates = []

    # exe 运行时：_MEIPASS 或 exe 所在目录的上级
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.abspath(os.path.join(exe_dir, "..", "..", "drivers")))
        candidates.append(os.path.abspath(os.path.join(exe_dir, "..", "drivers")))
        candidates.append(os.path.abspath(os.path.join(exe_dir, "drivers")))

    # 源码运行：项目根 / dist 下
    root = _project_root()
    candidates.append(os.path.join(root, "drivers"))

    # 扫描 dist/CapabilityNexus-*/drivers
    dist_dir = os.path.join(root, "dist")
    if os.path.isdir(dist_dir):
        for name in sorted(os.listdir(dist_dir), reverse=True):
            candidate = os.path.join(dist_dir, name, "drivers")
            if os.path.isdir(candidate):
                candidates.append(candidate)

    for path in candidates:
        if os.path.isdir(path):
            return path
    return None


def find_vigembus_inf(drivers_dir=None):
    """定位 ViGEmBus 驱动 inf 文件（x64 优先）。"""
    base = drivers_dir or _find_bundled_drivers_dir()
    if not base:
        return None

    for arch in ("x64", "x86"):
        inf = os.path.join(base, "ViGEmBus", arch, "ViGEmBus.inf")
        if os.path.exists(inf):
            return inf
    return None


def find_vigembus_nefconw(drivers_dir=None):
    """定位 ViGEmBus 目录下的 nefconw.exe 安装工具。"""
    base = drivers_dir or _find_bundled_drivers_dir()
    if not base:
        return None

    for arch in ("x64", "x86"):
        exe = os.path.join(base, "ViGEmBus", arch, "nefconw.exe")
        if os.path.exists(exe):
            return exe
    return None


def find_hidhide_installer(drivers_dir=None):
    """定位 HidHide 安装程序。"""
    base = drivers_dir or _find_bundled_drivers_dir()
    if not base:
        return None

    for name in os.listdir(base):
        if name.lower().startswith("hidhide") and name.lower().endswith(".exe"):
            return os.path.join(base, name)
    return None


#
# 安装 / 卸载
#


def install_vigembus(drivers_dir=None):
    """安装 ViGEmBus 驱动。返回 (ok, message)。"""
    nefconw = find_vigembus_nefconw(drivers_dir)
    inf = find_vigembus_inf(drivers_dir)

    if not nefconw or not inf:
        return False, "ViGEmBus 驱动文件未找到（发布包 drivers/ 目录缺失）"

    cmd = f'"{nefconw}" --install-driver --inf-path "{inf}"'
    code, stdout, stderr = _elevate(cmd)
    if code != 0:
        return False, stderr or stdout or f"install failed ({code})"
    return True, ""


def uninstall_vigembus(drivers_dir=None):
    """卸载 ViGEmBus 驱动。返回 (ok, message)。"""
    nefconw = find_vigembus_nefconw(drivers_dir)
    inf = find_vigembus_inf(drivers_dir)

    if not nefconw or not inf:
        return False, "ViGEmBus 驱动文件未找到"

    cmd = f'"{nefconw}" --uninstall-driver --inf-path "{inf}"'
    code, stdout, stderr = _elevate(cmd)
    if code != 0:
        return False, stderr or stdout or f"uninstall failed ({code})"
    return True, ""


def install_hidhide(drivers_dir=None):
    """启动 HidHide 安装程序（UAC 提权，用户确认）。"""
    installer = find_hidhide_installer(drivers_dir)
    if not installer:
        return False, "HidHide 安装程序未找到"

    if is_admin():
        try:
            result = subprocess.run(
                [installer],
                timeout=10,
                check=False,
            )
            return True, ""
        except (OSError, subprocess.SubprocessError) as error:
            return False, str(error)

    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", installer, "", None, 1
        )
    except Exception as error:
        return False, f"elevation failed: {error}"

    if result <= 32:
        return False, "UAC elevation cancelled or failed"
    return True, ""


def uninstall_hidhide():
    """卸载 HidHide。返回 (ok, message)。"""
    # HidHide 提供自己的卸载机制；调用其安装程序进入卸载流程
    install_dir = None
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Nefarius Software Solutions e.U.\Nefarius Software Solutions e.U. HidHide",
        ) as key:
            install_dir, _ = winreg.QueryValueEx(key, "Path")
    except (ImportError, OSError):
        pass

    uninstaller = None
    if install_dir:
        candidate = os.path.join(install_dir, "x64", "uninstall.cmd")
        if os.path.exists(candidate):
            uninstaller = candidate

    if uninstaller is None:
        return False, "未找到 HidHide 卸载程序"

    code, stdout, stderr = _elevate(f'"{uninstaller}"')
    if code != 0:
        return False, stderr or stdout or f"uninstall failed ({code})"
    return True, ""
