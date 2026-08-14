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
            cache_path=os.path.join(
                os.path.dirname(os.path.abspath(self.config_path)),
                "device_library_cache.json",
            )
        )

        self.devices = []
        self._config = []
        self._connected = []
        self._connected_entries = []
        self._detected_xinput_indices = []
        self._library_refresh_started = False

    def load_config(self):
        if not os.path.exists(self.config_path):
            print("[DeviceManager] No config file, auto-detect only:", self.config_path)
            self._config = []
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        devices = data.get("devices", [])
        self._config = devices if isinstance(devices, list) else []
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

        # 设备库网络刷新放后台，避免阻塞引擎启动（网络不通时可能超时）
        if hasattr(self, "_library_refresh_started") and not self._library_refresh_started:
            self._library_refresh_started = True
            import threading
            threading.Thread(target=self.library.refresh, daemon=True).start()

        detected = self.detector.detect()
        self._detected_xinput_indices = [
            d["index"] for d in detected if d.get("type") == "xinput"
        ]
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
                    # 自动识别的成品设备：登记到 config，供设备树显示和映射
                    auto_entry = {
                        "name": entry.get("name", entry.get("id")),
                        "driver": entry.get("driver", d.get("type")),
                        "package": entry.get("package", ""),
                        "auto_connected": True,
                    }

                    if d.get("type") == "xinput":
                        auto_entry["index"] = d.get("index", 0)

                    # 去重：同 driver + index 已存在则不重复添加
                    duplicate = any(
                        c.get("driver") == auto_entry["driver"]
                        and c.get("index") == auto_entry.get("index")
                        for c in self._config
                    )

                    if not duplicate:
                        self._config.append(auto_entry)
                        self.save_config()
                        print("[DeviceManager] Auto-connected product:", entry.get("name"))

                    resolved.append((d, auto_entry, "config"))
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

        # 始终监听型设备（phone WebSocket 服务器）：来自 config，始终连接
        for entry in self._config:
            if entry.get("driver") == "phone":
                detected = {"type": "phone"}
                resolved.append((detected, entry, "config"))
                print("[DeviceManager] Phone device from config:", entry.get("name"))

        return resolved

    def detected_xinput_indices(self):
        """Return XInput slots found before virtual outputs were created."""
        return list(self._detected_xinput_indices)

    def _match_config(self, detected):
        for entry in self._config:
            fp = detected.get("fingerprint", {})

            if fp.get("type") == "serial":
                # 串口匹配：检测到的 vid/pid 必须存在且与 config 一致
                detected_port = detected.get("port")
                configured_connection = entry.get("connection", {})
                configured_port = configured_connection.get("port", entry.get("port"))

                if detected_port and configured_port:
                    if detected_port.upper() == str(configured_port).upper():
                        return entry

                vid = fp.get("vid")
                pid = fp.get("pid")

                if not vid or not pid:
                    continue

                if vid == entry.get("vid") and pid == entry.get("pid"):
                    return entry

            if fp.get("type") == "xinput":
                if (
                    entry.get("driver") == "xinput"
                    and entry.get("index", 0) == fp.get("index", 0)
                ):
                    return entry

        return None

    def connect_all(self, parsed_resolved):
        for detected, entry, source in parsed_resolved:
            self.connect_device(detected, entry)

    def connect_device(self, detected, entry):
        """Connect one detected device while the client is already running."""
        for connected_entry in self._connected_entries:
            if self._same_device(connected_entry, entry):
                return self._connected[
                    self._connected_entries.index(connected_entry)
                ]

        try:
            instance = self._build_device(detected, entry)
        except Exception as error:
            print("[DeviceManager] Connect failed:", error)
            return None
        if instance:
            self._connected.append(instance)
            self._connected_entries.append(entry)
        return instance

    def disconnect_device(self, entry):
        """Close and forget one device while the engine is running."""
        for index, connected_entry in enumerate(self._connected_entries):
            if not self._same_device(connected_entry, entry):
                continue

            instance = self._connected.pop(index)
            self._connected_entries.pop(index)
            try:
                instance.close()
            except Exception as e:
                print("[DeviceManager] Device close failed:", e)
            return True

        return False

    @staticmethod
    def _same_device(left, right):
        if left.get("driver") != right.get("driver"):
            return False

        driver = left.get("driver")
        if driver == "xinput":
            return left.get("index", 0) == right.get("index", 0)
        if driver == "serial":
            left_connection = left.get("connection", {})
            right_connection = right.get("connection", {})
            return (
                left_connection.get("port", left.get("port"))
                == right_connection.get("port", right.get("port"))
            )
        if driver == "ftms":
            return left.get("address") == right.get("address")

        return left.get("name") == right.get("name")

    def connected_devices(self):
        """返回当前已连接设备的 config 条目列表（供 GUI 显示）"""
        return list(self._connected_entries)

    def online_devices(self):
        """返回当前真正在线的设备 config 条目列表

        区分于 connected_devices（已尝试连接的实例）：
        online 只统计实例当前确实在线/打开的。
        """
        online = []

        for instance, entry in zip(self._connected, self._connected_entries):
            if self._is_online(instance):
                online.append(entry)

        return online

    @staticmethod
    def _is_online(instance):
        """判断设备实例当前是否在线（各驱动属性不同，做兼容判断）"""
        # 显式 real 属性（XInput/HID 等）
        real = getattr(instance, "real", None)
        if real is not None:
            return bool(real)

        # XInput 轮询线程的连接标志
        connected = getattr(instance, "_connected", None)
        if connected is not None:
            return bool(connected)

        # 串口：serial 句柄存在即在线
        serial = getattr(instance, "serial", None)
        if serial is not None:
            return serial.is_open

        # HID：joystick 存在即在线
        joystick = getattr(instance, "joystick", None)
        if joystick is not None:
            return True

        # FTMS：client 存在即在线
        client = getattr(instance, "client", None)
        if client is not None:
            return True

        # 无法判断时视为在线（保守）
        return True

    def _build_device(self, detected, entry):
        driver = entry.get("driver")

        if driver == "xinput":
            from devices.xinput_device import XInputDevice

            index = entry.get("index", detected.get("index", 0))
            device = XInputDevice(self.event_bus, index=index)
            if not device.connect():
                return None
            return device

        if driver == "hid":
            from devices.hid_device import HIDDevice

            index = entry.get("index", 0)
            device = HIDDevice(self.event_bus, index=index)
            if not device.connect():
                return None
            return device

        if driver == "ftms":
            from devices.ftms_device import FTMSDevice

            device = FTMSDevice(
                self.event_bus,
                address=entry.get("address"),
                name=entry.get("name"),
            )
            device.connect()
            return device

        if driver == "ant":
            from devices.ant_device import ANTDevice

            device = ANTDevice(
                self.event_bus,
                device_type=entry.get("device_type", "all"),
            )
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

        if driver == "phone":
            from devices.connection_factory import ConnectionFactory
            from devices.websocket_connection import PhoneFrameParser

            connection_params = entry.get("connection", {})
            if "type" not in connection_params:
                connection_params = {
                    "type": "websocket",
                    "port": entry.get("port", 8765),
                }

            parser = PhoneFrameParser(self.event_bus)

            def phone_callback(message):
                parser.parse(message)

            connection = ConnectionFactory.create(
                phone_callback,
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
        self._connected_entries = []
