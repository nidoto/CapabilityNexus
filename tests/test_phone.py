"""手机 WebSocket 设备测试：解析器 + 端到端数据流。"""

import asyncio
import json

import pytest

from core.event_bus import EventBus
from core.stream import StreamData
from devices.websocket_connection import PhoneFrameParser


class Collector:
    def __init__(self):
        self.streams = []

    def publish(self, stream):
        self.streams.append(stream)


def test_parser_sensors():
    collector = Collector()
    parser = PhoneFrameParser(collector)

    parser.parse(json.dumps({
        "t": "sensors",
        "roll": 12.5,
        "pitch": -5.0,
        "yaw": 0.0,
        "gas": 0.7,
        "brake": 0.0,
    }))

    ids = {s.id: s.value for s in collector.streams}
    assert ids["phone.roll"] == 12.5
    assert ids["phone.pitch"] == -5.0
    assert ids["phone.gas"] == 0.7


def test_parser_buttons_edge():
    collector = Collector()
    parser = PhoneFrameParser(collector)

    parser.parse(json.dumps({"t": "buttons", "buttons": {"a": True}}))
    a_streams = [s for s in collector.streams if s.id == "phone.button_a"]
    assert a_streams and a_streams[-1].value == 1.0

    before = len(collector.streams)
    parser.parse(json.dumps({"t": "buttons", "buttons": {"a": True}}))
    assert len(collector.streams) == before

    parser.parse(json.dumps({"t": "buttons", "buttons": {"a": False}}))
    a_streams = [s for s in collector.streams if s.id == "phone.button_a"]
    assert a_streams[-1].value == 0.0


def test_parser_buttons_inside_sensors_frame():
    """sendAll 把 buttons 放在 sensors 帧里，应同样解析（含 back/start）。"""
    collector = Collector()
    parser = PhoneFrameParser(collector)

    parser.parse(json.dumps({
        "t": "sensors",
        "roll": 0.0,
        "buttons": {"a": True, "back": True},
    }))
    ids = {s.id: s.value for s in collector.streams}
    assert ids.get("phone.button_a") == 1.0
    assert ids.get("phone.button_back") == 1.0

    parser.parse(json.dumps({
        "t": "sensors",
        "buttons": {"back": False, "start": True},
    }))
    ids = {s.id: s.value for s in collector.streams}
    assert ids.get("phone.button_back") == 0.0
    assert ids.get("phone.button_start") == 1.0


def test_parser_invalid_json_ignored():
    collector = Collector()
    parser = PhoneFrameParser(collector)
    parser.parse("not json")
    parser.parse("")
    assert collector.streams == []


def test_end_to_end_phone_ws():
    """端到端：启动服务器 → 手机客户端连接 → 发传感器 → 收到数据。"""
    import time

    from devices.websocket_connection import WebSocketServerConnection
    import websockets

    bus = EventBus()
    collector = Collector()
    bus.subscribe(StreamData, collector.publish)

    server = WebSocketServerConnection(
        lambda msg: PhoneFrameParser(bus).parse(msg),
        host="127.0.0.1",
        port=8899,
    )
    server.open()
    time.sleep(0.5)

    async def client():
        async with websockets.connect("ws://127.0.0.1:8899/ws") as ws:
            await ws.send(json.dumps({
                "t": "sensors",
                "roll": 30.0,
                "pitch": 10.0,
                "gas": 1.0,
            }))
            await asyncio.sleep(0.2)

    try:
        asyncio.run(client())
        time.sleep(0.3)
    finally:
        server.close()

    ids = {s.id for s in collector.streams}
    assert "phone.roll" in ids
    assert "phone.gas" in ids
    assert "phone.pitch" in ids
