from devices.connection import LineConnection


class BluetoothConnection(LineConnection):

    #
    # 蓝牙 RFCOMM 连接（Windows 通过 pyserial / bluetooth）
    # device: 蓝牙地址或名称（如 "COM4" 或 "AA:BB:CC:DD:EE:FF"）
    # 依赖：pybluez 或 pyserial bluetooth
    #

    def __init__(self, callback, device, channel=1, baudrate=115200):
        super().__init__(callback)
        self.device = device
        self.channel = channel
        self.baudrate = baudrate
        self.stream = None
        self.port = None

    def open(self):
        if self.device and self.device.upper().startswith("COM"):
            import serial

            self.port = serial.Serial(
                self.device,
                self.baudrate,
                timeout=1,
            )
            self.stream = self.port
            print("[Bluetooth Connected]", self.device)
        else:
            import bluetooth

            self.port = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.port.connect((self.device, self.channel))
            self.port.settimeout(1)
            self.stream = self.port
            print("[Bluetooth Connected]", self.device, "ch", self.channel)

        self.start()

    def read_lines(self):
        if self.stream is None:
            return []

        try:
            data = self.stream.recv(4096)
        except Exception as e:
            if "timeout" in str(e).lower():
                return []
            raise

        if not data:
            return []

        text = data.decode("utf-8", errors="replace")
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        return lines

    def close(self):
        self.running = False

        if self.stream:
            try:
                self.stream.close()
            except Exception:
                pass
            self.stream = None
