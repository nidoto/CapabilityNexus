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
        "vigembus": _service_exists_registry(
            ("ViGEmBus", "NefariusVirtualGamepadEmulationBus")
        ),
        "hidhide": _service_exists_registry(("HidHide",)) or _hidhide_registry_exists(),
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


def _service_exists_registry(names):
    """通过注册表 Services 键检测驱动服务（不依赖 sc.exe，exe 环境更可靠）。"""
    try:
        import winreg

        for name in names:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SYSTEM\CurrentControlSet\Services",
                ):
                    with winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        rf"SYSTEM\CurrentControlSet\Services\{name}",
                    ):
                        return True
            except FileNotFoundError:
                continue
            except OSError:
                continue
    except ImportError:
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
