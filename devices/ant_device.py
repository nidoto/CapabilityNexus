import threading

from core.stream import StreamData


class ANTDevice:

    #
    # ANT+ 骑行设备输入源
    # 需要 USB ANT+ 适配器（如 Garmin USB ANT Stick）
    #
    # 支持：
    #   FitnessEquipment (FE-C) - 功率/速度/踏频/阻力
    #   PowerMeter - 功率计
    #   BikeSpeedCadence - 速度/踏频
    #
    # 能力（与 BLE FTMS 统一）：
    #   cycling.power / cycling.cadence / cycling.speed / cycling.resistance
    #

    def __init__(self, event_bus, device_type="all"):
        self.event_bus = event_bus
        self.device_type = device_type

        self.running = False
        self.thread = None
        self._node = None

    def connect(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return True

    def _run(self):
        try:
            self._check_ant_stick()

            if not self._has_ant():
                print("[ANT] No USB ANT+ adapter found")
                self.running = False
                return

            self._start_openant()
        except Exception as e:
            print("[ANT] Error:", e)
            self.running = False

    def _has_ant(self):
        try:
            import serial.tools.list_ports

            for port in serial.tools.list_ports.comports():
                name = (port.description or "").lower()
                if "ant" in name:
                    return True

            return False
        except Exception:
            return False

    def _check_ant_stick(self):
        try:
            import serial.tools.list_ports

            for port in serial.tools.list_ports.comports():
                print("[ANT] Port:", port.device, port.description)
        except Exception as e:
            print("[ANT] Port scan:", e)

    def _start_openant(self):
        try:
            from openant.easy.node import Node
            from openant.base.driver import USBDriver

            driver = USBDriver()
            node = Node(driver)
            self._node = node

            self._attach_devices(node)

            print("[ANT] ANT+ scanning (Ctrl+C to stop)...")
            node.start()
        except Exception as e:
            print("[ANT] openant start failed:", e)
        finally:
            self._node = None

    def _attach_devices(self, node):
        if self.device_type in ("all", "fe_c"):
            try:
                from openant.devices.fitness_equipment import FitnessEquipment

                fec = FitnessEquipment(node)
                fec.on_device_data = self._on_fec
                print("[ANT] FE-C trainer armed")
            except Exception as e:
                print("[ANT] FE-C:", e)

        if self.device_type in ("all", "power"):
            try:
                from openant.devices.power_meter import PowerMeter

                power = PowerMeter(node)
                power.on_device_data = self._on_power
                print("[ANT] Power meter armed")
            except Exception as e:
                print("[ANT] Power:", e)

        if self.device_type in ("all", "speed"):
            try:
                from openant.devices.bike_speed_cadence import BikeSpeedCadence

                sc = BikeSpeedCadence(node)
                sc.on_device_data = self._on_sc
                print("[ANT] Speed/Cadence sensor armed")
            except Exception as e:
                print("[ANT] Speed/Cadence:", e)

    def _on_fec(self, data):
        try:
            # FE-C 数据含功率/速度/踏频/阻力
            for page in data:
                d = page._data

                if "inst_power" in d:
                    self._emit("cycling.power", float(d["inst_power"]))
                if "inst_cadence" in d:
                    self._emit("cycling.cadence", float(d["inst_cadence"]))
                if "inst_speed" in d:
                    self._emit("cycling.speed", float(d["inst_speed"]))
        except Exception:
            pass

    def _on_power(self, data):
        try:
            for page in data:
                d = page._data
                if "power" in d:
                    self._emit("cycling.power", float(d["power"]))
        except Exception:
            pass

    def _on_sc(self, data):
        try:
            for page in data:
                d = page._data
                if "instantaneous_cadence" in d:
                    self._emit("cycling.cadence", float(d["instantaneous_cadence"]))
                if "instantaneous_speed" in d:
                    self._emit("cycling.speed", float(d["instantaneous_speed"]))
        except Exception:
            pass

    def _emit(self, capability, value):
        self.event_bus.publish(
            StreamData(capability, value)
        )

    def close(self):
        self.running = False
        node = self._node
        if node is not None:
            stop = getattr(node, "stop", None)
            if callable(stop):
                try:
                    stop()
                except Exception as e:
                    print("[ANT] Stop failed:", e)
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=2)
        self.thread = None
