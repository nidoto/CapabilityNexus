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

def _web_dir():
    """手机控制页面目录（兼容源码运行与打包 exe）。"""
    import sys as _sys

    if getattr(_sys, "frozen", False):
        base = getattr(_sys, "_MEIPASS", os.path.dirname(_sys.executable))
        for candidate in (
            os.path.join(base, "web"),
            os.path.join(os.path.dirname(_sys.executable), "web"),
        ):
            if os.path.isdir(candidate):
                return candidate

    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "web",
    )


WEB_DIR = _web_dir()


class WebSocketServerConnection(LineConnection):

    def __init__(self, callback, host="0.0.0.0", port=8765):
        super().__init__(callback)
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def open(self):
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        print(f"[WebSocketServer] Listening on ws://{self.host}:{self.port}")
        print(f"[WebSocketServer] Phone page: http://<PC-IP>:{self.port}/")

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

        if path in ("/", "/index.html", "/phone.html"):
            page = os.path.join(WEB_DIR, "phone.html")
            if os.path.exists(page):
                with open(page, "r", encoding="utf-8") as f:
                    body = f.read().encode("utf-8")
                headers = Headers({
                    "Content-Type": "text/html; charset=utf-8",
                    "Content-Length": str(len(body)),
                })
                return Response(200, "OK", headers, body)

        if path == "/health":
            body = b"ok"
            headers = Headers({"Content-Type": "text/plain", "Content-Length": "2"})
            return Response(200, "OK", headers, body)

        return None

    async def _serve(self):
        async def handler(websocket):
            print(f"[WebSocketServer] Client connected: {websocket.remote_address}")
            try:
                async for message in websocket:
                    if self.callback:
                        self.callback(message)
            except websockets.exceptions.ConnectionClosed:
                print("[WebSocketServer] Client disconnected")

        self.server = await websockets.serve(
            handler,
            self.host,
            self.port,
            max_size=64 * 1024,
            process_request=self._process_request,
        )
        try:
            await self.server.wait_closed()
        except asyncio.CancelledError:
            pass

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
    """

    def __init__(self, event_bus):
        self.event_bus = event_bus
        self._last_buttons = {}

    def parse(self, message):
        try:
            if isinstance(message, bytes):
                message = message.decode("utf-8", errors="replace")
            data = json.loads(message)
        except (ValueError, json.JSONDecodeError):
            return

        frame_type = data.get("t", data.get("type", "sensors"))

        if frame_type in ("sensors", "sensor"):
            self._emit_sensors(data)
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
