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
        import re

        try:
            import asyncio
            from winsdk.windows.devices.enumeration import (
                DeviceInformation as DI,
            )

            async def _enum():
                return await DI.find_all_async()

            loop = asyncio.new_event_loop()

            try:
                items = loop.run_until_complete(_enum())
            finally:
                loop.close()

            for item in items:
                name = item.name
                device_id = item.id

                if not name:
                    continue

                marker = device_id.upper()

                is_bluetooth = any(
                    m in marker
                    for m in ("BTHLE", "BTHENUM", "BTHHFENUM", "BTH#", "\\?\\BTH")
                )

                if not is_bluetooth:
                    continue

                connected = False

                try:
                    connected = bool(
                        item.properties.get(
                            "System.Devices.Aep.IsConnected",
                            False,
                        )
                    )
                except Exception:
                    connected = False

                devices.append({
                    "name": name,
                    "address": device_id,
                    "connected": connected,
                    "remembered": True,
                    "ble": "BTHLE" in marker,
                })

            seen = {}
            for d in devices:
                mac = ""
                m = re.search(r"Dev_([0-9A-Fa-f]{12})", d["address"])
                if m:
                    mac = m.group(1).lower()
                else:
                    m2 = re.search(r"([0-9A-Fa-f]{12})", d["address"])
                    if m2:
                        mac = m2.group(1).lower()

                key = (d["name"], mac)

                if key not in seen:
                    seen[key] = d

            return list(seen.values())

        except Exception as e:
            print("[BT] Paired BLE scan failed:", e)

        return devices
