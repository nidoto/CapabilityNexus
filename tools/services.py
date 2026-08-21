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

from devices.websocket_connection import PhoneFrameParser


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


class DeviceContext:
    """单台手机设备的运行时上下文（按 device_id 聚合）。

    每台手机拥有独立的：
      - session：连接生命周期状态（DeviceSession）
      - parser ：PhoneFrameParser（解析该设备的传感器/按钮帧）
      - websocket：当前活跃 WebSocket 连接（断开时为 None）

    多手机并存时，WebService 用 dict[device_id -> DeviceContext] 管理，
    消息按 device_id 路由到对应 parser，断开只影响对应设备，互不覆盖。
    """

    def __init__(self, device_id, name="Phone", capabilities=None, websocket=None,
                 event_bus=None):
        self.device_id = device_id
        self.session = DeviceSession(device_id, name, capabilities)
        # 每台设备一个独立 parser，绑定到引擎 event_bus：消息按 device_id
        # 路由到对应 parser，禁止跨设备共享全局 parser。
        self.parser = PhoneFrameParser(event_bus=event_bus)
        self.websocket = websocket

    @property
    def status(self):
        return self.session.status

    def to_dict(self):
        d = self.session.to_dict()
        d["websocket_open"] = self.websocket is not None
        return d


class WebService:
    """Web 手机服务：独立于引擎的 WebSocket 服务器。

    use_https=True 时启用 HTTPS（自签证书）：手机访问 https://IP:port 需要
    在浏览器点"继续访问"，但可获得完整能力（陀螺仪等 secure context API）。
    use_https=False 时仅 HTTP：手机直接访问，但陀螺仪不可用（触屏模式）。

    连接生命周期见 DeviceSession：CONNECTED / RECONNECTING / OFFLINE。
    WebSocket 断开时保留设备对象（device_id / profile / parser 状态），
    重连时按 device_id 恢复同一 session，不创建新设备。
    """

    def __init__(self, port=8765, callback=None, use_https=True, on_client_change=None,
                 event_bus=None):
        self.port = port
        self.callback = callback
        self.use_https = use_https
        self._on_client_change = on_client_change  # 手机连接/断开回调(计数)，给 GUI
        # 引擎 event_bus：消息由对应设备的独立 parser 发布到这里。
        # 引擎可能晚于 Web 服务启动，故允许后续通过 set_event_bus 注入。
        self.event_bus = event_bus
        self._server = None
        self._lock = threading.Lock()
        # 每台手机一台设备：device_id -> DeviceContext（session + parser + websocket）
        self._devices = {}
        self._client_count = 0
        self._ssl = None
        self._last_data_ts = None  # 最近一次收到手机真实数据的时间戳
        self._last_frame_ts = None  # 上一帧真实数据到达的时间戳（算帧间隔）
        self._data_intervals = deque(maxlen=50)  # 最近 50 帧到达间隔采样（取平均延时）

    def set_event_bus(self, event_bus):
        """引擎启动后注入 event_bus，使各设备 parser 能发布到引擎。

        已存在的 DeviceContext 同步更新 parser 的 event_bus（保持按钮边沿状态）。
        """
        with self._lock:
            self.event_bus = event_bus
            if event_bus is not None:
                for ctx in self._devices.values():
                    ctx.parser.event_bus = event_bus

    @property
    def scheme(self):
        return "https" if self.use_https and self._ssl else "http"

    @property
    def ws_scheme(self):
        return "wss" if self.scheme == "https" else "ws"

    def _on_client_count_changed(self, count):
        """WebSocket 客户端数量变化（连接或断开）→ 仅用于通知 GUI 刷新。"""
        with self._lock:
            self._client_count = count
        cb = self._on_client_change
        if cb is not None:
            try:
                cb(count)
            except Exception as error:
                print("[WebService] on_client_change callback failed:", error)

    def _on_client_disconnected(self, websocket):
        """单个 WebSocket 连接断开：只影响对应 device_id 的设备上下文。

        定位到持有该 websocket 的 DeviceContext，将其 session 置为 RECONNECTING
        （保留 device_id / profile / parser / 历史配置），等待手机按 device_id 重连。
        不影响其他仍在连接的设备。
        """
        with self._lock:
            target_id = None
            for dev_id, ctx in self._devices.items():
                if ctx.websocket is websocket:
                    target_id = dev_id
                    break
            if target_id is None:
                return
            ctx = self._devices[target_id]
            ctx.websocket = None
            if ctx.session.status == DeviceSession.STATUS_CONNECTED:
                ctx.session.status = DeviceSession.STATUS_RECONNECTING
                ctx.session.reconnect_attempts += 1
                # 注意：不删除 DeviceContext，设备对象（含 parser / profile）保留

    @property
    def phone_status(self):
        """返回当前（或最近活跃）手机连接状态：CONNECTED / RECONNECTING / OFFLINE。

        多设备下取"最优"状态用于整体指示：任一 CONNECTED 即 CONNECTED；
        否则任一 RECONNECTING 即 RECONNECTING；都为空则 OFFLINE。
        """
        with self._lock:
            if self._server is None or not self._devices:
                return DeviceSession.STATUS_OFFLINE
            has_reconnecting = False
            for ctx in self._devices.values():
                if ctx.session.status == DeviceSession.STATUS_CONNECTED:
                    return DeviceSession.STATUS_CONNECTED
                if ctx.session.status == DeviceSession.STATUS_RECONNECTING:
                    has_reconnecting = True
            return DeviceSession.STATUS_RECONNECTING if has_reconnecting else DeviceSession.STATUS_OFFLINE

    @property
    def phone_session(self):
        """返回当前活跃设备的 session 快照（多设备取第一个有状态的）。"""
        with self._lock:
            if not self._devices:
                return None
            for ctx in self._devices.values():
                if ctx.session.status != DeviceSession.STATUS_OFFLINE:
                    return ctx.to_dict()
            # 全部 OFFLINE：返回最后一个设备的快照
            last = next(reversed(self._devices.values()))
            return last.to_dict()

    def device_contexts(self):
        """返回所有 DeviceContext 的快照列表（dict）。"""
        with self._lock:
            return {dev_id: ctx.to_dict() for dev_id, ctx in self._devices.items()}

    def _resolve_device_id(self, data, websocket):
        """从帧或当前 websocket 反查 device_id（用于非 hello 帧路由）。"""
        dev_id = data.get("device_id")
        if dev_id:
            return dev_id
        with self._lock:
            for cid, ctx in self._devices.items():
                if ctx.websocket is websocket:
                    return cid
        return None

    def _get_or_create_context(self, dev_id, name, capabilities, websocket):
        """按 device_id 获取或创建 DeviceContext，绝不覆盖其他设备。

        - 不存在：新建并登记。
        - 已存在：恢复同一设备（更新 websocket 与展示信息、重置连接状态），
          不重建、不覆盖其他设备。
        """
        with self._lock:
            ctx = self._devices.get(dev_id)
            if ctx is None:
                ctx = DeviceContext(
                    dev_id, name or "Phone", capabilities, websocket,
                    event_bus=self.event_bus,
                )
                self._devices[dev_id] = ctx
            else:
                # 已存在：恢复同一设备，更新 websocket 与展示信息，不重建
                ctx.websocket = websocket
                ctx.session.status = DeviceSession.STATUS_CONNECTED
                ctx.session.last_seen = time.time()
                ctx.session.reconnect_attempts = 0
                if name:
                    ctx.session.name = name
                if capabilities:
                    ctx.session.capabilities = list(capabilities)
            return ctx

    def _make_server(self):
        from devices.websocket_connection import WebSocketServerConnection
        from devices.websocket_connection import PhoneProfileStore

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
            # 多设备运行时：每条消息必须按 device_id 找到对应 DeviceContext，
            # 并由该设备独立的 parser 解析（禁止全局共享 parser）。
            # 真实数据（hello/sensors/buttons）直接发布到引擎 event_bus；
            # self.callback 仅用于 GUI 通知（日志/刷新），不再承担解析。
            try:
                import json as _json

                if isinstance(message, bytes):
                    message = message.decode("utf-8", errors="replace")
                data = _json.loads(message)
                frame_type = data.get("t", data.get("type", "sensors"))

                # 解析 device_id（hello 帧从解析器取；其余帧从帧或 websocket 反查）
                temp_parser = PhoneFrameParser(event_bus=None)
                temp_parser.parse(message)
                dev_id = temp_parser.device_id or data.get("device_id")

                if frame_type == "hello":
                    # 身份主键：device_id（手机端生成并持久化）。
                    # 手机未带 device_id 时由服务端生成并回传，让其持久化。
                    if not dev_id:
                        dev_id = str(uuid.uuid4())
                    name = temp_parser.device_name
                    caps = temp_parser.device_capabilities
                    # hello 流程：存在则恢复同一设备（不覆盖其他设备）；
                    # 不存在则创建。设备身份/配置以 device_id 为准。
                    ctx = self._get_or_create_context(dev_id, name, caps, websocket)
                    # 兼容旧格式：按手机名迁移 <用户>-<手机名>.json
                    self._profile_store.migrate_legacy(dev_id, name)
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
                    # 由该设备独立 parser 发布 hello 身份（保持按钮边沿状态隔离）
                    if self.event_bus is not None:
                        ctx.parser.parse(message)
                else:
                    # 非 hello 帧：必须按 device_id 找到对应 context，否则丢弃
                    dev_id = self._resolve_device_id(data, websocket)
                    if not dev_id:
                        return
                    with self._lock:
                        ctx = self._devices.get(dev_id)
                    if ctx is None:
                        return
                    if frame_type == "config":
                        # 手机保存配置：反转/方向盘最大角度/油门增益
                        cfg = data.get("config") or {}
                        self._profile_store.save(dev_id, cfg)
                        return
                    # sensors / buttons 等真实数据：只路由到对应设备的独立 parser
                    if self.event_bus is not None:
                        ctx.parser.parse(message)

                # 手机真实数据（hello/传感器/按钮）算"活跃连接"；
                # 同时用服务端到达时间戳测平均帧间隔（近似平均延时，不增加任何传输数据）
                if frame_type in ("hello", "sensors", "sensor", "buttons", "config"):
                    now = time.time()
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
            on_client_disconnect=self._on_client_disconnected,
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
        """返回当前活跃设备的显示名（多设备取第一个非 OFFLINE 的）。"""
        with self._lock:
            for ctx in self._devices.values():
                if ctx.session.status != DeviceSession.STATUS_OFFLINE:
                    return ctx.session.name
            for ctx in self._devices.values():
                return ctx.session.name
        return ""

    @property
    def device_id(self):
        """返回当前活跃设备的 device_id（多设备取第一个非 OFFLINE 的）。"""
        with self._lock:
            for dev_id, ctx in self._devices.items():
                if ctx.session.status != DeviceSession.STATUS_OFFLINE:
                    return dev_id
            for dev_id in self._devices:
                return dev_id
        return ""

    @property
    def device_capabilities(self):
        """返回当前活跃设备的能力列表。"""
        with self._lock:
            for ctx in self._devices.values():
                if ctx.session.status != DeviceSession.STATUS_OFFLINE:
                    return list(ctx.session.capabilities)
            for ctx in self._devices.values():
                return list(ctx.session.capabilities)
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
            self._devices = {}  # 主动停止：所有设备对象移除，状态转 OFFLINE
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
            "phone_devices": self.device_contexts(),
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
                self._devices = {}
