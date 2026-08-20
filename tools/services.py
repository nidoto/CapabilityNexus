"""服务管理：Web 手机服务（独立启停）+ 驱动状态。

WebService 独立于引擎运行，方便用户按需开启/关闭手机连接服务。
启动后手机通过 http://<IP>:<port>/ 打开控制页面，ws://<IP>:<port>/ws
发送传感器数据。
"""

import socket
import threading
import time
import uuid
from collections import deque


def _is_local(ip):
    """判断是否为局域网私有 IP（RFC 1918 + CGNAT + link-local）。"""
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
        or (a == 192 and b == 168)
        or (a == 100 and 64 <= b <= 127)
        or (a == 169 and b == 254)  # link-local 169.254.x.x
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


class DeviceSession:
    """单个手机设备的连接生命周期状态（按 device_id 主键）。

    状态机：
      OFFLINE      - 服务未运行，或设备从未连接 / 已主动停止
      CONNECTED    - WebSocket 已连且正在收发数据
      RECONNECTING - WebSocket 已断开，但设备对象保留（profile / 已有
                     解析状态不删除），等待手机按退避策略自动重连

    重连成功后（device_id 校验通过）恢复同一 session，不创建新设备。
    """

    STATUS_OFFLINE = "OFFLINE"
    STATUS_CONNECTED = "CONNECTED"
    STATUS_RECONNECTING = "RECONNECTING"

    def __init__(self, device_id, name="Phone", capabilities=None):
        self.device_id = device_id
        self.name = name
        self.capabilities = list(capabilities or [])
        self.status = self.STATUS_OFFLINE
        self.last_seen = None
        self.reconnect_attempts = 0

    def to_dict(self):
        return {
            "device_id": self.device_id,
            "status": self.status,
            "last_seen": self.last_seen,
            "reconnect_attempts": self.reconnect_attempts,
            "name": self.name,
            "capabilities": list(self.capabilities),
        }


class WebService:
    """Web 手机服务：独立于引擎的 WebSocket 服务器。

    use_https=True 时启用 HTTPS（自签证书）：手机访问 https://IP:port 需要
    在浏览器点"继续访问"，但可获得完整能力（陀螺仪等 secure context API）。
    use_https=False 时仅 HTTP：手机直接访问，但陀螺仪不可用（触屏模式）。

    连接生命周期见 DeviceSession：CONNECTED / RECONNECTING / OFFLINE。
    WebSocket 断开时保留设备对象（device_id / profile / parser 状态），
    重连时按 device_id 恢复同一 session，不创建新设备。
    """

    def __init__(self, port=8765, callback=None, use_https=True, on_client_change=None):
        self.port = port
        self.callback = callback
        self.use_https = use_https
        self._on_client_change = on_client_change  # 手机连接/断开回调(计数)，给 GUI
        self._server = None
        self._lock = threading.Lock()
        self._parser = None  # PhoneFrameParser，用于记录连接的手机设备
        self._session = None  # DeviceSession，按 device_id 保留设备对象
        self._client_count = 0
        self._ssl = None
        self._last_data_ts = None  # 最近一次收到手机真实数据的时间戳
        self._last_frame_ts = None  # 上一帧真实数据到达的时间戳（算帧间隔）
        self._data_intervals = deque(maxlen=50)  # 最近 50 帧到达间隔采样（取平均延时）

    @property
    def scheme(self):
        return "https" if self.use_https and self._ssl else "http"

    @property
    def ws_scheme(self):
        return "wss" if self.scheme == "https" else "ws"

    def _on_client_count_changed(self, count):
        """WebSocket 客户端数量变化（连接或断开）。

        断开（count 归 0）且当前为 CONNECTED 时，进入 RECONNECTING：
        保留设备对象（device_id / profile / parser），等待手机重连。
        """
        with self._lock:
            self._client_count = count
            if (count == 0 and self._session is not None
                    and self._session.status == DeviceSession.STATUS_CONNECTED):
                self._session.status = DeviceSession.STATUS_RECONNECTING
                self._session.reconnect_attempts += 1
                # 注意：不清除 self._parser / session，设备对象保留
        # 通知 GUI 刷新
        cb = self._on_client_change
        if cb is not None:
            try:
                cb(count)
            except Exception as error:
                print("[WebService] on_client_change callback failed:", error)

    @property
    def phone_status(self):
        """返回当前手机连接状态：CONNECTED / RECONNECTING / OFFLINE。"""
        with self._lock:
            if self._server is None or self._session is None:
                return DeviceSession.STATUS_OFFLINE
            return self._session.status

    @property
    def phone_session(self):
        """返回当前设备 session 快照 dict（含 device_id/status/last_seen/reconnect_attempts）。"""
        with self._lock:
            if self._session is None:
                return None
            return self._session.to_dict()

    def _make_server(self):
        from devices.websocket_connection import WebSocketServerConnection
        from devices.websocket_connection import PhoneFrameParser
        from devices.websocket_connection import PhoneProfileStore

        self._parser = PhoneFrameParser(event_bus=None)
        self._profile_store = PhoneProfileStore()

        # HTTPS：生成自签证书
        self._ssl = None
        if self.use_https:
            try:
                from tools.certs import ssl_context
                self._ssl = ssl_context()
            except Exception as error:
                print(f"[WebService] HTTPS setup failed, falling back to HTTP: {error}")
                self._ssl = None

        def wrapped_callback(message, websocket=None):
            # 解析 hello 记录设备身份；sensors/buttons 帧只更新设备存在，
            # 实际能力数据由外部 callback 转发（带 event_bus 的 parser）
            try:
                import json as _json

                if isinstance(message, bytes):
                    message = message.decode("utf-8", errors="replace")
                data = _json.loads(message)
                frame_type = data.get("t", data.get("type", "sensors"))
                if frame_type == "hello":
                    self._parser.parse(message)
                    # 身份主键：device_id（手机端生成并持久化）。
                    # 手机未带 device_id 时由服务端生成并回传，让其持久化。
                    dev_id = self._parser.device_id or str(uuid.uuid4())
                    if self._parser.device:
                        self._parser.device["device_id"] = dev_id
                    # 恢复已有 session（device_id 校验通过则不创建新设备）
                    with self._lock:
                        if self._session is None or self._session.device_id != dev_id:
                            self._session = DeviceSession(
                                dev_id,
                                self._parser.device_name,
                                self._parser.device_capabilities,
                            )
                        self._session.status = DeviceSession.STATUS_CONNECTED
                        self._session.last_seen = time.time()
                        self._session.reconnect_attempts = 0
                        self._session.name = self._parser.device_name
                        self._session.capabilities = self._parser.device_capabilities
                    # 兼容旧格式：按手机名迁移 <用户>-<手机名>.json
                    self._profile_store.migrate_legacy(dev_id, self._parser.device_name)
                    saved = self._profile_store.load(dev_id)
                    if websocket is not None:
                        try:
                            if not data.get("device_id"):
                                # 让手机记住它被分配的 device_id（localStorage）
                                server.send_json(websocket, {
                                    "t": "device_id",
                                    "device_id": dev_id,
                                })
                            if saved:
                                server.send_json(websocket, {
                                    "t": "config",
                                    "config": saved,
                                })
                        except Exception as error:
                            print("[WebService] Config reply failed:", error)
                elif frame_type == "config":
                    # 手机保存配置：反转/方向盘最大角度/油门增益
                    self._parser.device = self._parser.device or {"name": "Phone"}
                    dev_id = self._parser.device_id or data.get("device_id")
                    if not dev_id:
                        dev_id = str(uuid.uuid4())
                        if self._parser.device:
                            self._parser.device["device_id"] = dev_id
                    cfg = data.get("config") or {}
                    self._profile_store.save(dev_id, cfg)

                # 手机真实数据（hello/传感器/按钮）算"活跃连接"；
                # 同时用服务端到达时间戳测平均帧间隔（近似平均延时，不增加任何传输数据）
                if frame_type in ("hello", "sensors", "sensor", "buttons", "config"):
                    now = time.time()
                    with self._lock:
                        if self._session is not None:
                            self._session.last_seen = now
                    if self._last_frame_ts is not None:
                        interval_ms = (now - self._last_frame_ts) * 1000
                        # 过滤异常间隔（<1ms 或 >2s），避免重连/暂停污染平均值
                        if 1 <= interval_ms <= 2000:
                            self._data_intervals.append(interval_ms)
                    self._last_frame_ts = now
                    self._last_data_ts = now
            except (ValueError, _json.JSONDecodeError):
                pass
            if self.callback:
                self.callback(message)

        server = WebSocketServerConnection(
            wrapped_callback,
            host="0.0.0.0",
            port=self.port,
            ssl_context=self._ssl,
            on_client_change=self._on_client_count_changed,
        )
        self._server = server
        return server

    @property
    def is_phone_connected(self):
        """是否至少有一台手机连接。"""
        with self._lock:
            server = self._server
            if server is None:
                return False
            return server.client_count > 0

    @property
    def device_name(self):
        with self._lock:
            if self._parser is not None:
                return self._parser.device_name
        return ""

    @property
    def device_id(self):
        with self._lock:
            if self._parser is not None:
                return self._parser.device_id
        return ""

    @property
    def device_capabilities(self):
        with self._lock:
            if self._parser is not None:
                return self._parser.device_capabilities
        return []

    def is_running(self):
        with self._lock:
            return self._server is not None and self._server.thread is not None

    def start(self):
        """启动服务。返回 (ok, message)。"""
        with self._lock:
            if self._server is not None:
                return False, "already running"

            server = self._make_server()
            try:
                server.open()
            except Exception as error:
                return False, f"start failed: {error}"

            # 确认服务器真正监听成功（open 可能因端口被占静默失败）
            ready = getattr(server, "_ready", None)
            if ready is None or not ready.is_set():
                print("[WebService] start: bind failed or not ready "
                      f"(port {self.port} may be in use)")
                return False, f"端口 {self.port} 被占用或绑定失败"

            self._server = server
            return True, ""

    @property
    def last_data_ts(self):
        """最近一次收到手机真实数据的时间戳，没有则为 None。"""
        with self._lock:
            return self._last_data_ts

    @property
    def data_interval_ms(self):
        """最近 50 帧真实数据的平均到达间隔（毫秒），未测得为 None。

        服务端纯计时得出，不向手机发送任何额外数据。
        反映真实数据流速度：100Hz 发送约为 10ms，50Hz 约为 20ms。
        """
        with self._lock:
            if not self._data_intervals:
                return None
            return round(sum(self._data_intervals) / len(self._data_intervals), 1)

    def stop(self):
        """停止服务。返回 (ok, message)。"""
        with self._lock:
            if self._server is None:
                return False, "not running"

            server = self._server
            self._server = None
            self._parser = None
            self._session = None  # 主动停止：设备对象移除，状态转 OFFLINE
            self._data_intervals.clear()
            try:
                server.close()
            except Exception as error:
                return False, f"stop failed: {error}"
            return True, ""

    def info(self):
        """返回服务信息 dict。"""
        running = self.is_running()
        ips = get_local_ips()
        scheme = self.scheme
        ws_scheme = self.ws_scheme
        session = self.phone_session
        return {
            "running": running,
            "port": self.port,
            "ips": ips,
            "best_ip": best_local_ip(),
            "scheme": scheme,
            "page_urls": [f"{scheme}://{ip}:{self.port}/" for ip in ips],
            "ws_urls": [f"{ws_scheme}://{ip}:{self.port}/ws" for ip in ips],
            "phone_status": self.phone_status,
            "phone_session": session,
        }

    def send_to_phones(self, message):
        """向所有已连接的手机广播 JSON 消息（如震动请求）。"""
        import json as _json

        server = self._server
        if server is None:
            return
        try:
            if isinstance(message, dict):
                payload = message
            else:
                payload = _json.loads(message)
            server.broadcast_json(payload)
        except Exception as error:
            print("[WebService] Phone broadcast failed:", error)

    def forward_request_event(self, request):
        """把游戏请求事件（如震动）转发给手机：xbox.motor_* → 手机振动。

        注意：vgamepad 的 register_notification 回调给的是 0~255 的电机强度，
        不是 0~65535。这里按 0~255 归一化，并用平方根曲线让低强度也可感知。
        值为 0 表示停止振动，不转发（避免游戏空闲时的连续 0 值刷屏）。
        """
        target = getattr(request, "target", "")
        value = getattr(request, "value", 0.0)
        if target not in ("xbox.motor_left", "xbox.motor_right"):
            return
        if value <= 0:
            return  # 停止振动 / 空闲，不转发
        # 0~255 → 0.0~1.0，平方根提升低强度感知
        ratio = min(max(value / 255.0, 0.0), 1.0)
        ratio = ratio ** 0.6
        # 最小振动 30ms，保证手机可感知
        duration_ms = int(30 + ratio * 270)
        self.send_to_phones({"t": "vibrate", "duration_ms": duration_ms})

    def close(self):
        with self._lock:
            if self._server is not None:
                try:
                    self._server.close()
                except Exception:
                    pass
                self._server = None
                self._parser = None
                self._session = None
