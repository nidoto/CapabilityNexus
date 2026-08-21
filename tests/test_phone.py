"""手机 WebSocket 设备测试：解析器 + 端到端数据流。

V1.9 Phase 1 起，PhoneFrameParser 输出统一标准格式 CapabilityEvent
（携带 device_id），而非原始 StreamData。
"""

import asyncio
import json

import pytest

from core.event_bus import EventBus
from core.capability import CapabilityEvent
from devices.websocket_connection import PhoneFrameParser


class Collector:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def _by_capability(events):
    return {e.capability: e.value for e in events}


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

    # 解析器输出 CapabilityEvent（标准格式），字段正确
    assert all(isinstance(e, CapabilityEvent) for e in collector.events)
    ids = _by_capability(collector.events)
    assert ids["phone.roll"] == 12.5
    assert ids["phone.pitch"] == -5.0
    assert ids["phone.gas"] == 0.7


def test_parser_emits_device_id():
    """传感器事件必须携带 device_id（多设备溯源所需）。"""
    collector = Collector()
    parser = PhoneFrameParser(collector)
    parser.parse(json.dumps({
        "t": "hello",
        "device_id": "dev-unit-1",
        "name": "Phone",
        "capabilities": ["gyroscope"],
    }))
    collector.events.clear()
    parser.parse(json.dumps({"t": "sensors", "roll": 1.0}))
    assert collector.events
    assert collector.events[0].device_id == "dev-unit-1"
    assert collector.events[0].capability == "phone.roll"
    assert collector.events[0].value == 1.0
    assert isinstance(collector.events[0].timestamp, float)


def test_parser_buttons_edge():
    collector = Collector()
    parser = PhoneFrameParser(collector)

    parser.parse(json.dumps({"t": "buttons", "buttons": {"a": True}}))
    a_events = [e for e in collector.events if e.capability == "phone.button_a"]
    assert a_events and a_events[-1].value == 1.0

    before = len(collector.events)
    parser.parse(json.dumps({"t": "buttons", "buttons": {"a": True}}))
    assert len(collector.events) == before

    parser.parse(json.dumps({"t": "buttons", "buttons": {"a": False}}))
    a_events = [e for e in collector.events if e.capability == "phone.button_a"]
    assert a_events[-1].value == 0.0


def test_parser_buttons_inside_sensors_frame():
    """sendAll 把 buttons 放在 sensors 帧里，应同样解析（含 back/start）。"""
    collector = Collector()
    parser = PhoneFrameParser(collector)

    parser.parse(json.dumps({
        "t": "sensors",
        "roll": 0.0,
        "buttons": {"a": True, "back": True},
    }))
    ids = _by_capability(collector.events)
    assert ids.get("phone.button_a") == 1.0
    assert ids.get("phone.button_back") == 1.0

    parser.parse(json.dumps({
        "t": "sensors",
        "buttons": {"back": False, "start": True},
    }))
    ids = _by_capability(collector.events)
    assert ids.get("phone.button_back") == 0.0
    assert ids.get("phone.button_start") == 1.0


def test_parser_invalid_json_ignored():
    collector = Collector()
    parser = PhoneFrameParser(collector)
    parser.parse("not json")
    parser.parse("")
    assert collector.events == []


def test_end_to_end_phone_ws():
    """端到端：启动服务器 → 手机客户端连接 → 发传感器 → 收到 CapabilityEvent。"""
    import time

    from devices.websocket_connection import WebSocketServerConnection
    import websockets

    bus = EventBus()
    collector = Collector()
    bus.subscribe(CapabilityEvent, collector.publish)

    # 运行时为每连接维护一个持久 parser（与 WebService 同设备共用一个 parser 一致），
    # 这样 hello 设置的 device_id 能带到后续 sensors 帧。
    parser = PhoneFrameParser(bus)
    server = WebSocketServerConnection(
        lambda msg: parser.parse(msg),
        host="127.0.0.1",
        port=8899,
    )
    server.open()
    time.sleep(0.5)

    async def client():
        async with websockets.connect("ws://127.0.0.1:8899/ws") as ws:
            await ws.send(json.dumps({
                "t": "hello",
                "device_id": "dev-e2e",
                "name": "Phone",
                "capabilities": ["gyroscope"],
            }))
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

    caps = {e.capability for e in collector.events}
    assert "phone.roll" in caps
    assert "phone.gas" in caps
    assert "phone.pitch" in caps
    # 端到端事件携带 hello 中的 device_id
    assert all(e.device_id == "dev-e2e" for e in collector.events)
