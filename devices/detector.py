import ctypes

from ctypes import wintypes


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", wintypes.DWORD),
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class DeviceDetector:

    def detect(self):
        devices = []

        devices.extend(self._detect_xinput())
        devices.extend(self._detect_serial())

        return devices

    def _detect_xinput(self):
        found = []

        try:
            xinput = ctypes.windll.xinput1_4
        except Exception as e:
            print("[Detector] No xinput1_4:", e)
            return found

        for index in range(4):
            state = XINPUT_STATE()
            result = xinput.XInputGetState(index, ctypes.byref(state))

            if result == 0:
                found.append(
                    {
                        "type": "xinput",
                        "index": index,
                        "fingerprint": {
                            "type": "xinput",
                            "index": index,
                        },
                    }
                )
                print(
                    "[Detector] XInput controller at slot",
                    index,
                )

        return found

    def _detect_serial(self):
        found = []

        try:
            from serial.tools import list_ports
        except Exception as e:
            print("[Detector] pyserial unavailable:", e)
            return found

        for port in list_ports.comports():
            vid = f"{port.vid:04X}" if port.vid else None
            pid = f"{port.pid:04X}" if port.pid else None

            fingerprint = {"type": "serial"}

            if vid and pid:
                fingerprint["vid"] = vid
                fingerprint["pid"] = pid

            if port.description:
                fingerprint["description"] = port.description

            found.append(
                {
                    "type": "serial",
                    "port": port.device,
                    "fingerprint": fingerprint,
                    "description": port.description,
                }
            )

            print(
                "[Detector] Serial port:",
                port.device,
                port.description,
                f"{vid}:{pid}" if vid else "",
            )

        return found
