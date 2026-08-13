#
# 自定义连接方式模板
#
# 用户在此定义 build_connection(callback, params) 函数，
# 返回一个 LineConnection 对象（见 devices/connection.py）。
#
# 连接类型在 config/devices.json 中声明：
#   "connection": { "type": "custom", "params": { "your_key": "value" } }
#
# 示例（自定义 UDP 连接）：
#
# from devices.connection import LineConnection
# import socket
#
# class UdpConnection(LineConnection):
#     def __init__(self, callback, ip, port):
#         super().__init__(callback)
#         self.ip = ip
#         self.port = port
#         self.sock = None
#
#     def open(self):
#         self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#         self.sock.bind((self.ip, self.port))
#         self.sock.settimeout(1)
#         self.start()
#
#     def read_lines(self):
#         try:
#             data, _ = self.sock.recvfrom(4096)
#         except socket.timeout:
#             return []
#         text = data.decode("utf-8", errors="replace")
#         return [ln.strip() for ln in text.split("\n") if ln.strip()]
#
#     def close(self):
#         self.running = False
#         if self.sock:
#             self.sock.close()
#
# def build_connection(callback, params):
#     return UdpConnection(callback, params.get("ip", "0.0.0.0"), int(params.get("port", 9999)))


def build_connection(callback, params):
    raise NotImplementedError(
        "Define build_connection(callback, params) in this file"
    )
