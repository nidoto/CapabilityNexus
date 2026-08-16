import ctypes

from devices.xinput_api import get_state
from devices.xinput_api import load_xinput


class DeviceDetector:

    def detect(self):
        devices = []

        devices.extend(self._detect_xinput())
        devices.extend(self._detect_serial())

        return devices

    def _detect_xinput(self):
        found = []

        xinput = load_xinput()
        if xinput is None:
            return found

        for index in range(4):
            if get_state(xinput, index) is None:
                continue
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
