import socket

from devices.connection import LineConnection


class UdpConnection(LineConnection):

    #
    # UDP 网络连接：
    # 绑定本地端口接收设备通过 UDP 发送的行数据（\n 分隔）。
    # 适合低延迟网络设备（骑行台/模拟设备/自组硬件）。
    #

    def __init__(self, callback, host="0.0.0.0", port=8888):
        super().__init__(callback)
        self.host = host
        self.port = port
        self.sock = None

    def open(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.sock.settimeout(1)
        print("[UDP Listening]", self.host, self.port)
        self.start()

    def read_lines(self):
        if self.sock is None:
            return []

        try:
            data, _addr = self.sock.recvfrom(4096)
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
