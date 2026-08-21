"""Capability Provider 测试（V1.9 Phase 3）。

验证：
  1. PhoneProvider 把手机帧解析为 CapabilityEvent 并发布（业务入口统一）。
  2. capabilities() 返回能力名（字符串）。
  3. 生命周期 start/stop/is_running。
"""

import json

from core.capability import CapabilityEvent
from core.provider import CapabilityProvider
from devices.phone_provider import PhoneProvider


def _fake_bus():
    collected = []
    return collected, lambda e: collected.append(e)


def test_phone_provider_produces_capability_event():
    """PhoneProvider.parse(sensors) 产出带 device_id 的 CapabilityEvent。"""
    collected, publish = _fake_bus()
    provider = PhoneProvider(
        device_id="dev-a",
        capabilities=["phone.roll", "phone.gas"],
        publish=publish,
    )
    # hello 建立身份（phone 端会先发 hello）
    provider.parse(json.dumps({
        "t": "hello",
        "device_id": "dev-a",
        "name": "Phone A",
        "capabilities": ["phone.roll", "phone.gas"],
    }))
    collected.clear()
    provider.parse(json.dumps({"t": "sensors", "roll": 0.35, "gas": 0.8}))

    events = [e for e in collected if isinstance(e, CapabilityEvent)]
    assert events, "未产出 CapabilityEvent"
    by_cap = {e.capability: e.value for e in events}
    assert by_cap["phone.roll"] == 0.35
    assert by_cap["phone.gas"] == 0.8
    # 设备身份保留在事件中
    assert all(e.device_id == "dev-a" for e in events)


def test_phone_provider_uses_event_bus_sink():
    """未给 publish 但给 event_bus 时，经 event_bus.publish 流出。"""
    collected, _ = _fake_bus()
    bus = type("Bus", (), {"publish": lambda self, e: collected.append(e)})()
    provider = PhoneProvider(device_id="dev-b", event_bus=bus)
    provider.parse(json.dumps({"t": "sensors", "pitch": -1.0}))
    assert any(
        isinstance(e, CapabilityEvent) and e.capability == "phone.pitch"
        for e in collected
    )


def test_phone_provider_capabilities():
    # 显式配置优先
    p = PhoneProvider(device_id="dev-c", capabilities=["phone.roll"])
    assert p.capabilities() == ["phone.roll"]

    # 未配置时从解析器身份取
    p2 = PhoneProvider(device_id="dev-d", publish=lambda e: None)
    p2.parse(json.dumps({
        "t": "hello",
        "device_id": "dev-d",
        "capabilities": ["phone.yaw", "phone.brake"],
    }))
    assert p2.capabilities() == ["phone.yaw", "phone.brake"]


def test_provider_lifecycle():
    """基类生命周期 start/stop/is_running。"""
    p = CapabilityProvider(capabilities=["x"])
    assert not p.is_running()
    p.start()
    assert p.is_running()
    p.stop()
    assert not p.is_running()


def test_provider_publish_forwards():
    seen = []
    p = CapabilityProvider(publish=seen.append)
    ev = CapabilityEvent("dev-x", "wheel.angle", 1.0)
    p.publish(ev)
    assert seen == [ev]
