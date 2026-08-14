"""服务管理：Web 手机服务（独立启停）+ 驱动状态。

WebService 独立于引擎运行，方便用户按需开启/关闭手机连接服务。
启动后手机通过 http://<IP>:<port>/ 打开控制页面，ws://<IP>:<port>/ws
发送传感器数据。
"""

import socket
import threading


def _is_local(ip):
    """判断是否为局域网私有 IP。"""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError:
        return False
    return (
        a == 10
        or (a == 172 and 16 <= b <= 31)
        or a == 192 and b == 168
        or a == 100 and 64 <= b <= 127
        or a == 169 and b == 254  # link-local，不太可能
    )


def get_local_ips():
    """返回本机局域网 IPv4 地址列表。"""
    ips = set()

    # 方法1：连接 UDP 获取本机出口 IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass

    # 方法2：枚举所有网卡
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                ips.add(ip)
    except OSError:
        pass

    return sorted(ips)


def best_local_ip():
    """返回最适合局域网访问的 IP（优先局域网私有地址）。"""
    ips = get_local_ips()
    if not ips:
        return ""

    # 优先局域网私有地址
    for ip in ips:
        if _is_local(ip):
            return ip

    # 兜底：第一个
    return ips[0]


class WebService:
    """Web 手机服务：独立于引擎的 WebSocket 服务器。"""

    def __init__(self, port=8765, callback=None):
        self.port = port
        self.callback = callback
        self._server = None
        self._lock = threading.Lock()

    def is_running(self):
        with self._lock:
            return self._server is not None and self._server.thread is not None

    def start(self):
        """启动服务。返回 (ok, message)。"""
        with self._lock:
            if self._server is not None:
                return False, "already running"

            from devices.websocket_connection import WebSocketServerConnection

            server = WebSocketServerConnection(
                self.callback,
                host="0.0.0.0",
                port=self.port,
            )
            try:
                server.open()
            except Exception as error:
                return False, f"start failed: {error}"

            self._server = server
            return True, ""

    def stop(self):
        """停止服务。返回 (ok, message)。"""
        with self._lock:
            if self._server is None:
                return False, "not running"

            server = self._server
            self._server = None
            try:
                server.close()
            except Exception as error:
                return False, f"stop failed: {error}"
            return True, ""

    def info(self):
        """返回服务信息 dict。"""
        running = self.is_running()
        ips = get_local_ips()
        return {
            "running": running,
            "port": self.port,
            "ips": ips,
            "best_ip": best_local_ip(),
            "page_urls": [f"http://{ip}:{self.port}/" for ip in ips],
            "ws_urls": [f"ws://{ip}:{self.port}/ws" for ip in ips],
        }

    def close(self):
        with self._lock:
            if self._server is not None:
                try:
                    self._server.close()
                except Exception:
                    pass
                self._server = None
