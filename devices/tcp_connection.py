import socket

from devices.connection import LineConnection


class TcpConnection(LineConnection):

    #
    # WiFi / TCP 连接：
    # 设备作为 TCP 客户端连接到此服务端（或此端连接设备）。
    # 接收以 \n 结尾的行。
    #

    def __init__(self, callback, host, port):
        super().__init__(callback)
        self.host = host
        self.port = port
        self.sock = None

    def open(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.sock.settimeout(1)
        print("[TCP Connected]", self.host, self.port)
        self.start()

    def read_lines(self):
        if self.sock is None:
            return []

        try:
            if self.sock is None:
                return []
            data = self.sock.recv(4096)
        except (socket.timeout, OSError):
            return []

        if not data:
            return []

        text = data.decode("utf-8", errors="replace")
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        return lines

    def close(self):
        self.running = False

        if self.sock:
            self.sock.close()
            self.sock = None
