import json
import os

from devices.detector import DeviceDetector
from devices.device_library import DeviceLibrary


class DeviceManager:

    def __init__(self, event_bus, config_path=None):
        self.event_bus = event_bus
        self.config_path = config_path or os.path.join("config", "devices.json")

        self.detector = DeviceDetector()
        self.library = DeviceLibrary(
            cache_path=os.path.join("config", "device_library_cache.json")
        )

        self.devices = []
        self._config = []
        self._connected = []

    def load_config(self):
        if not os.path.exists(self.config_path):
            print("[DeviceManager] No config file, auto-detect only:", self.config_path)
            self._config = []
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._config = data.get("devices", [])
        print("[DeviceManager] Loaded config devices:", len(self._config))

    def add_custom_device(self, device_config):
        if not self._config:
            self.load_config()

        self._config.append(device_config)
        self.save_config()
        print("[DeviceManager] Added custom device:", device_config.get("name"))

    def save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"devices": self._config}, f, ensure_ascii=False, indent=4)

    def discover(self):
        self.load_config()
        self.library.refresh()

        detected = self.detector.detect()
        print("[DeviceManager] Detected devices:", len(detected))

        resolved = []

        for d in detected:
            entry = self.library.identify(d)

            if entry:
                kind = entry.get("kind", "product")

                config_entry = self._match_config(d)

                if config_entry:
                    resolved.append((d, config_entry, "config"))
                    print("[DeviceManager] Matched config:", config_entry.get("name"))
                elif kind == "product":
                    resolved.append((d, entry, "auto"))
                    print("[DeviceManager] Identified product:", entry.get("name"))
                else:
                    print(
                        "[DeviceManager] Template device:",
                        entry.get("name"),
                    )
                    print(
                        "[DeviceManager]   Define its capabilities in",
                        self.config_path,
                        "(it's a custom board - you choose what each channel is)",
                    )
            else:
                config_entry = self._match_config(d)

                if config_entry:
                    resolved.append((d, config_entry, "config"))
                    print("[DeviceManager] Matched config:", config_entry.get("name"))
                else:
                    print(
                        "[DeviceManager] Unknown device:",
                        d.get("description", d.get("type")),
                    )
                    print(
                        "[DeviceManager]   Add it manually in",
                        self.config_path,
                        "e.g. custom development boards (ESP32/Raspberry Pi)",
                    )

        return resolved

    def _match_config(self, detected):
        for entry in self._config:
            fp = detected.get("fingerprint", {})

            if fp.get("type") == "serial":
                if fp.get("vid") == entry.get("vid") and fp.get("pid") == entry.get("pid"):
                    return entry

            if fp.get("type") == "xinput":
                if entry.get("driver") == "xinput":
                    return entry

        return None

    def connect_all(self, parsed_resolved):
        for detected, entry, source in parsed_resolved:
            instance = self._build_device(detected, entry)
            if instance:
                self._connected.append(instance)

    def _build_device(self, detected, entry):
        driver = entry.get("driver")

        if driver == "xinput":
            from devices.xinput_device import XInputDevice

            index = detected.get("index", 0)
            device = XInputDevice(self.event_bus, index=index)
            device.connect()
            return device

        if driver == "hid":
            from devices.hid_device import HIDDevice

            index = entry.get("index", 0)
            device = HIDDevice(self.event_bus, index=index)
            device.connect()
            return device

        if driver == "serial":
            from devices.connection_factory import ConnectionFactory
            from protocols.serial_protocol import SerialParser

            connection_params = entry.get("connection", {})

            if "type" not in connection_params:
                connection_params = {
                    "type": "serial",
                    "port": entry.get("port"),
                    "baudrate": entry.get("baudrate", 115200),
                }

            protocol = entry.get("protocol", {})
            parser = SerialParser(
                self.event_bus,
                mapping=protocol.get("mapping"),
                has_frame=protocol.get("has_frame", False),
            )

            def callback(line):
                parser.parse(line)

            connection = ConnectionFactory.create(
                callback,
                connection_params,
            )
            connection.open()
            return connection

        print("[DeviceManager] Unknown driver:", driver)
        return None

    def close_all(self):
        for device in self._connected:
            device.close()
        self._connected = []
