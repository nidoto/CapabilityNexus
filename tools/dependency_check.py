"""Windows runtime dependency checks for the optional virtual-device stack."""

import importlib.util
import os
import subprocess
import sys


def check_dependencies():
    if sys.platform != "win32":
        return {
            "vgamepad": False,
            "vigembus": False,
            "hidhide": False,
            "platform": sys.platform,
        }

    return {
        "vgamepad": importlib.util.find_spec("vgamepad") is not None,
        "vigembus": _service_exists(("ViGEmBus", "NefariusVirtualGamepadEmulationBus")),
        "hidhide": _service_exists(("HidHide",)) or _hidhide_registry_exists(),
        "platform": sys.platform,
    }


def missing_dependencies(status):
    missing = []
    if not status.get("vgamepad"):
        missing.append("Python vgamepad")
    if not status.get("vigembus"):
        missing.append("ViGEmBus（XInput 兼容控制器驱动）")
    if not status.get("hidhide"):
        missing.append("HidHide（游戏独占模式）")
    return missing


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


def _hidhide_registry_exists():
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
    return False
