import serial

from devices.connection import LineConnection


class SerialConnection(LineConnection):

    def __init__(self, callback, port, baudrate=115200):
        super().__init__(callback)
        self.port = port
        self.baudrate = baudrate
        self.serial = None

    def open(self):
        self.serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=1,
        )
        print("[Serial Connected]", self.port, self.baudrate)
        self.start()

    def read_lines(self):
        line = self.serial.readline()

        if not line:
            return []

        data = line.decode("utf-8", errors="replace").strip()

        if data:
            return [data]

        return []

    def close(self):
        self.running = False

        if self.serial:
            self.serial.close()
            self.serial = None
