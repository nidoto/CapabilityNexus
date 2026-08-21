"""WebSocket 连接（手机浏览器传感器设备）。

手机网页通过 WebSocket 连到 PC，发送 JSON 帧：
  {"t": "sensors", "roll": 12.3, "pitch": -5.1, "yaw": 0.2,
   "accelX": 0.1, "accelY": 0.3, "accelZ": 9.8,
   "gas": 0.5, "brake": 0.0,
   "buttons": {"a": true, "b": false, ...},
   "dpad": {"up": false, ...}}

同一个端口同时提供：
  - HTTP  GET /         返回手机控制页面（phone.html）
  - WebSocket /ws       接收手机传感器数据

服务端把每个 JSON 帧解析为一行回调（与 LineConnection 兼容）。
"""

import asyncio
import json
import os
import threading

import websockets

from devices.connection import LineConnection


class PhoneProfileStore:
    """按手机身份保存/读取手机配置（反转、方向盘最大角度、油门增益）。

    身份主键是 device_id（手机端生成并持久化的稳定 UUID），与用户名/手机名
    无关。文件名直接为 <device_id>.json，存放在 config/phone_profiles/ 下。
    name 仅作为显示名称，不再参与文件命名。

    兼容旧格式：旧文件名为 <计算机用户名>-<手机名>.json。旧文件不会被删除，
    发现时通过 migrate_legacy() 复制为新格式（device_id.json）后继续可用。
    """

    def __init__(self, directory=None):
        if directory is None:
            base = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config",
                "phone_profiles",
            )
            directory = base
        self.directory = directory

    def _sanitize(self, value):
        import re

        return re.sub(r"[^\w\-]+", "_", value or "").strip("_") or "phone"

    def _path(self, device_id):
        safe = self._sanitize(device_id)
        filename = f"{safe}.json"
        return os.path.join(self.directory, filename)

    def _find_legacy_by_name(self, name):
        """按手机名查找旧格式文件：目录中任何以 -<sanitized_name>.json 结尾的文件。

        不依赖用户名环境变量，纯按设备显示名匹配（只读兼容，不引入用户维度）。
        返回找到的第一个旧文件路径，没有返回 None。
        """
        if not name or not os.path.isdir(self.directory):
            return None
        suffix = f"-{self._sanitize(name)}.json"
        try:
            for fn in os.listdir(self.directory):
                if fn.endswith(suffix) and fn != suffix:
                    return os.path.join(self.directory, fn)
        except OSError:
            return None
        return None

    def load(self, device_id):
        """读取手机配置，没有则返回空 dict。"""
        try:
            path = self._path(device_id)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except (OSError, json.JSONDecodeError) as error:
            print("[PhoneProfile] Load failed:", error)
        return {}

    def save(self, device_id, config):
        """保存手机配置（原子写入）。"""
        if not device_id:
            return False
        try:
            os.makedirs(self.directory, exist_ok=True)
            path = self._path(device_id)
            fd, temp_path = __import__("tempfile").mkstemp(
                prefix=".cnx-", suffix=".tmp", dir=self.directory
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, path)
            print(f"[PhoneProfile] Saved {path}")
            return True
        except OSError as error:
            print("[PhoneProfile] Save failed:", error)
            return False

    def migrate_legacy(self, device_id, name):
        """将旧格式 <*>-<手机名>.json 复制为新格式 <device_id>.json。

        按手机显示名（非用户名）查找旧文件，旧文件不会被删除（仅复制）。
        返回是否执行了复制。若新格式文件已存在则跳过（不覆盖已有身份配置）。
        """
        if not device_id or not name:
            return False
        new_path = self._path(device_id)
        if os.path.exists(new_path):
            return False
        legacy = self._find_legacy_by_name(name)
        if legacy is None:
            return False
        try:
            import shutil

            os.makedirs(self.directory, exist_ok=True)
            shutil.copyfile(legacy, new_path)
            print(f"[PhoneProfile] Migrated legacy {legacy} -> {new_path}")
            return True
        except OSError as error:
            print("[PhoneProfile] Migration failed:", error)
            return False

    def list_profiles(self):
        """返回所有已保存的手机配置文件名。"""
        if not os.path.isdir(self.directory):
            return []
        return sorted(n for n in os.listdir(self.directory) if n.endswith(".json"))


def _web_dir():
    """手机控制页面目录（兼容源码运行与打包 exe）。

    打包 exe 下优先使用 exe 同级目录的 web/（发布者可覆盖更新页面，
    无需重新打包），其次回退到 PyInstaller 内嵌的 _MEIPASS/web。
    """
    import sys as _sys

    if getattr(_sys, "frozen", False):
        base = getattr(_sys, "_MEIPASS", os.path.dirname(_sys.executable))
        for candidate in (
            os.path.join(os.path.dirname(_sys.executable), "web"),
            os.path.join(base, "web"),
        ):
            if os.path.isdir(candidate):
                return candidate

    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "web",
    )


WEB_DIR = _web_dir()


class WebSocketServerConnection(LineConnection):

    def __init__(self, callback, host="0.0.0.0", port=8765, ssl_context=None,
                 on_client_change=None, on_client_disconnect=None):
        super().__init__(callback)
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.on_client_change = on_client_change  # 客户端连接/断开回调(计数)
        self.on_client_disconnect = on_client_disconnect  # 单个连接断开回调(websocket)
        self.server = None
        self.thread = None
        self._ready = None
        self._clients = set()
        self._loop = None

    @property
    def client_count(self):
        """当前已连接的手机客户端数量。"""
        return len(self._clients)

    def _notify_client_change(self):
        """客户端集合变化时通知上层（用于 GUI 刷新连接状态）。"""
        callback = self.on_client_change
        if callback is None:
            return
        try:
            callback(self.client_count)
        except Exception as error:
            print("[WebSocketServer] on_client_change callback failed:", error)

    def _notify_client_disconnect(self, websocket):
        """单个连接断开时通知上层（传入具体 websocket，便于按设备定位）。"""
        callback = self.on_client_disconnect
        if callback is None:
            return
        try:
            callback(websocket)
        except Exception as error:
            print("[WebSocketServer] on_client_disconnect callback failed:", error)

    def open(self):
        self._ready = threading.Event()
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        # 等待服务器真正开始监听（避免 open 返回但端口未就绪）
        self._ready.wait(timeout=5)
        if not self._ready.is_set():
            print(f"[WebSocketServer] Warning: server may not be ready on {self.host}:{self.port}")
        scheme = "wss" if self.ssl_context else "ws"
        http_scheme = "https" if self.ssl_context else "http"
        print(f"[WebSocketServer] Listening on {scheme}://{self.host}:{self.port}")
        print(f"[WebSocketServer] Phone page: {http_scheme}://<PC-IP>:{self.port}/")

    def _run_server(self):
        asyncio.run(self._serve())

    async def _process_request(self, connection, request):
        """websockets 17.x process_request 钩子：返回 HTTP 响应或 None（升级为 WS）。

        - /ws 路径 → 返回 None，允许升级为 WebSocket
        - 其他路径（/、/phone.html）→ 返回手机控制页面
        """
        from websockets.http11 import Response
        from websockets.datastructures import Headers

        path = request.path

        # WebSocket 端点：手机页面连接 ws://IP:port/ws
        if path in ("/ws", "/phone"):
            return None

        # 页面分发：入口页检测平台后跳转
        page_map = {
            "/": "index.html",
            "/index.html": "index.html",
            "/phone.html": "index.html",
            "/phone-android.html": "phone-android.html",
            "/phone-ios.html": "phone-ios.html",
        }

        if path in page_map:
            page = os.path.join(WEB_DIR, page_map[path])
            if os.path.exists(page):
                with open(page, "r", encoding="utf-8") as f:
                    body = f.read().encode("utf-8")
                headers = Headers({
                    "Content-Type": "text/html; charset=utf-8",
                    "Content-Length": str(len(body)),
                    "Cache-Control": "no-store, no-cache, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                })
                return Response(200, "OK", headers, body)

        if path == "/health":
            body = b"ok"
            headers = Headers({"Content-Type": "text/plain", "Content-Length": "2"})
            return Response(200, "OK", headers, body)

        return None

    async def _serve(self):
        self._loop = asyncio.get_event_loop()
        callback = self.callback
        # 检测回调是否接受第二个参数（websocket），兼容单/双参数回调
        try:
            import inspect as _inspect
            _sig = _inspect.signature(callback)
            _takes_ws = len(_sig.parameters) >= 2
        except (TypeError, ValueError):
            _takes_ws = False

        def dispatch(message, websocket=None):
            if callback is None:
                return
            if _takes_ws:
                callback(message, websocket)
            else:
                callback(message)

        async def handler(websocket):
            print(f"[WebSocketServer] Client connected: {websocket.remote_address}")
            self._clients.add(websocket)
            self._notify_client_change()
            try:
                async for message in websocket:
                    dispatch(message, websocket)
            except websockets.exceptions.ConnectionClosed:
                print("[WebSocketServer] Client disconnected")
            finally:
                self._clients.discard(websocket)
                self._notify_client_disconnect(websocket)
                self._notify_client_change()

        self.server = await websockets.serve(
            handler,
            self.host,
            self.port,
            max_size=64 * 1024,
            process_request=self._process_request,
            ssl=self.ssl_context,
        )
        self._ready.set()
        try:
            await self.server.wait_closed()
        except asyncio.CancelledError:
            pass

    def send_json(self, websocket, data):
        """向指定客户端发送 JSON 消息。

        使用服务端自身的事件循环（self._loop），避免用主线程的
        get_event_loop() 提交到错误/未运行的循环导致消息发不出去。
        """
        loop = self._loop
        if loop is None:
            print("[WebSocketServer] Send skipped: no event loop")
            return

        try:
            asyncio.run_coroutine_threadsafe(
                self._send_impl(websocket, data),
                loop,
            )
        except Exception as error:
            print("[WebSocketServer] Send failed:", error)

    def broadcast_json(self, data):
        """向所有已连接客户端广播 JSON 消息。"""
        for websocket in list(self._clients):
            self.send_json(websocket, data)

    async def _send_impl(self, websocket, data):
        try:
            await websocket.send(json.dumps(data, ensure_ascii=False))
        except Exception as error:
            print("[WebSocketServer] Send failed:", error)

    def close(self):
        self.running = False

        if self.server is not None:
            self.server.close()

        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=2)


class PhoneFrameParser:

    """把手机 WebSocket JSON 帧解析成多个 StreamData。

    传感器轴（roll/pitch/yaw/accel）→ phone.* 能力
    触屏按钮 / 油门 / 刹车 → phone.* 能力

    设备身份：hello 帧携带 {device_id, name, capabilities}。
    device_id 是主键（手机端生成并持久化），name 仅作显示。
    识别优先级：device_id > name。
    """

    def __init__(self, event_bus):
        self.event_bus = event_bus
        self._last_buttons = {}
        self.device = None  # {"device_id", "name", "capabilities"}

    @property
    def device_id(self):
        return (self.device or {}).get("device_id") or ""

    @property
    def device_name(self):
        return (self.device or {}).get("name", "Phone")

    @property
    def device_capabilities(self):
        return (self.device or {}).get("capabilities", [])

    def parse(self, message):
        try:
            if isinstance(message, bytes):
                message = message.decode("utf-8", errors="replace")
            data = json.loads(message)
        except (ValueError, json.JSONDecodeError):
            return

        frame_type = data.get("t", data.get("type", "sensors"))

        if frame_type == "hello":
            self.device = {
                "device_id": data.get("device_id") or "",
                "name": data.get("name") or "Phone",
                "capabilities": data.get("capabilities") or [],
            }
        elif frame_type in ("sensors", "sensor"):
            self._emit_sensors(data)
            # sendAll 把 buttons/dpad 一起放在 sensors 帧里
            if data.get("buttons") or data.get("dpad"):
                self._emit_buttons(data)
        elif frame_type == "buttons":
            self._emit_buttons(data)

    def _emit_sensors(self, data):
        from core.stream import StreamData

        mapping = {
            "roll": "phone.roll",
            "pitch": "phone.pitch",
            "yaw": "phone.yaw",
            "accelX": "phone.accel_x",
            "accelY": "phone.accel_y",
            "accelZ": "phone.accel_z",
            "gas": "phone.gas",
            "brake": "phone.brake",
        }

        for key, capability in mapping.items():
            if key in data:
                try:
                    value = float(data[key])
                except (TypeError, ValueError):
                    continue
                self.event_bus.publish(StreamData(capability, value))

    def _emit_buttons(self, data):
        from core.stream import StreamData

        buttons = data.get("buttons") or {}
        dpad = data.get("dpad") or {}

        button_map = {
            "a": "phone.button_a",
            "b": "phone.button_b",
            "x": "phone.button_x",
            "y": "phone.button_y",
            "back": "phone.button_back",
            "start": "phone.button_start",
        }
        dpad_map = {
            "up": "phone.dpad_up",
            "down": "phone.dpad_down",
            "left": "phone.dpad_left",
            "right": "phone.dpad_right",
        }

        all_buttons = {}
        for key, capability in button_map.items():
            all_buttons[capability] = bool(buttons.get(key, False))
        for key, capability in dpad_map.items():
            all_buttons[capability] = bool(dpad.get(key, False))

        for capability, pressed in all_buttons.items():
            if self._last_buttons.get(capability) == pressed:
                continue
            self._last_buttons[capability] = pressed
            self.event_bus.publish(StreamData(capability, 1.0 if pressed else 0.0))
