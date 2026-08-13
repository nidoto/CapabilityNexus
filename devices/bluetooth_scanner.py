import ctypes
import os
from ctypes import wintypes

BLUETOOTH_MAX_NAME_SIZE = 248


class BLUETOOTH_DEVICE_INFO(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("Address", ctypes.c_ulonglong),
        ("ulClassofDevice", wintypes.DWORD),
        ("fConnected", wintypes.BOOL),
        ("fRemembered", wintypes.BOOL),
        ("fAuthenticated", wintypes.BOOL),
        ("stLastSeen", ctypes.c_byte * 16),
        ("stLastUsed", ctypes.c_byte * 16),
        ("szName", ctypes.c_wchar * BLUETOOTH_MAX_NAME_SIZE),
    ]


class BLUETOOTH_DEVICE_SEARCH_PARAMS(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("fReturnAuthenticated", wintypes.BOOL),
        ("fReturnRemembered", wintypes.BOOL),
        ("fReturnUnknown", wintypes.BOOL),
        ("fReturnConnected", wintypes.BOOL),
        ("fIssueInquiry", wintypes.BOOL),
        ("cTimeoutMultiplier", ctypes.c_ubyte),
        ("hRadio", ctypes.c_void_p),
    ]


def _bth():
    return ctypes.CDLL(
        os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", "bthprops.cpl")
    )


class BluetoothScanner:

    #
    # 枚举 Windows 已配对的蓝牙设备（含连接状态）
    # 以及通过 BLE 广播扫描新设备
    #

    def list_paired(self):
        devices = []

        try:
            dll = _bth()

            search = BLUETOOTH_DEVICE_SEARCH_PARAMS()
            search.dwSize = ctypes.sizeof(search)
            search.fReturnAuthenticated = True
            search.fReturnRemembered = True
            search.fReturnConnected = True
            search.fReturnUnknown = False
            search.fIssueInquiry = False
            search.cTimeoutMultiplier = 1

            handle = dll.BluetoothFindFirstDevice(ctypes.byref(search), None)

            if not handle:
                return devices

            while True:
                info = BLUETOOTH_DEVICE_INFO()
                info.dwSize = ctypes.sizeof(info)

                found = dll.BluetoothFindNextDevice(handle, ctypes.byref(info))

                if not found:
                    break

                address_int = info.Address
                address = ":".join(
                    f"{(address_int >> (8 * i)) & 0xFF:02X}"[::-1]
                    if False else f"{(address_int >> (8 * i)) & 0xFF:02X}"
                    for i in range(5, -1, -1)
                )

                devices.append({
                    "name": info.szName or "(unnamed)",
                    "address": address,
                    "connected": bool(info.fConnected),
                    "remembered": bool(info.fRemembered),
                    "authenticated": bool(info.fAuthenticated),
                })

            dll.BluetoothFindDeviceClose(handle)

        except Exception as e:
            print("[BT] Paired scan failed:", e)

        return devices

    def list_serial_ports(self):
        ports = []

        try:
            from serial.tools import list_ports

            for port in list_ports.comports():
                if "Bluetooth" in port.description or "蓝牙" in port.description:
                    ports.append({
                        "name": port.description,
                        "address": port.device,
                        "port": port.device,
                        "connected": True,
                    })
        except Exception as e:
            print("[BT] Serial scan failed:", e)

        return ports

    def scan_ble(self, timeout=5):
        devices = []

        try:
            import asyncio
            from bleak import BleakScanner

            async def _scan():
                return await BleakScanner.discover(timeout=timeout)

            loop = asyncio.new_event_loop()

            try:
                found = loop.run_until_complete(_scan())
            finally:
                loop.close()

            for d in found:
                devices.append({
                    "name": d.name or "(unnamed)",
                    "address": d.address,
                    "connected": False,
                })
        except Exception as e:
            print("[BT] BLE scan failed:", e)

        return devices

    def list_paired_ble(self):
        devices = []

        try:
            from ctypes import wintypes
            import subprocess

            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-PnpDevice -PresentOnly -Class Bluetooth "
                    "| Select-Object FriendlyName, Status, InstanceId "
                    "| ConvertTo-Json",
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )

            if result.returncode != 0:
                print("[BT] PnP query failed:", result.stderr[:200])
                return devices

            import json as _json

            parsed = _json.loads(result.stdout or "[]")

            if isinstance(parsed, dict):
                parsed = [parsed]

            for item in parsed:
                name = item.get("FriendlyName")
                instance_id = item.get("InstanceId") or ""
                status = item.get("Status") or ""

                if not name:
                    continue

                # 过滤系统内部蓝牙服务
                skip_keywords = [
                    "设备信息", "通用属性", "通用访问",
                    "LE 枚举器", "枚举器", "RFCOMM",
                    "LE 通用属性", "GATT", "avrcp",
                    "Avrcp", "AVRCP", "Service",
                ]

                if any(k in name for k in skip_keywords):
                    continue

                # 过滤适配器
                if "Bluetooth Adapter" in name or "蓝牙适配器" in name:
                    continue

                marker = instance_id.upper()

                devices.append({
                    "name": name,
                    "address": instance_id,
                    "connected": status == "OK",
                    "remembered": True,
                    "ble": "BTHLE" in marker or "BTHLEDEVICE" in marker,
                })

        except Exception as e:
            print("[BT] Paired BLE scan failed:", e)

        return devices
