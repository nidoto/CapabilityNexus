"""Capability Routing Layer 测试（V1.9 Phase 2）。

验证 CapabilityRouter / CapabilityMappingAdapter：
  1. 基础分发：handler 收到同一个 CapabilityEvent。
  2. 多订阅：两个 handler 同时收到。
  3. device_id 保留：路由前后 device_id 不丢失。
  4. Mapping 回归：phone.roll -> Router -> MappingAdapter -> MappingEngine
     -> xbox.right_x，结果与 V1.8 / V1.9 Phase 1 一致。
"""

import os

from core.capability import CapabilityEvent
from core.capability_registry import CapabilityRegistry
from core.capability_router import CapabilityRouter
from core.stream import StreamData
from core.stream_adapter import StreamAdapter
from core.channel import Channel
from core.processed_channel import ProcessedChannel
from core.system_event import OutputEvent
from core.event_bus import EventBus

from mapping.mapper import MappingEngine
from packages.manager import PackageManager


# ---------------------------------------------------------------------------
# 1. 基础分发
# ---------------------------------------------------------------------------

def test_basic_dispatch_same_event():
    """handler 收到的是发布出去的同一个事件对象。"""
    router = CapabilityRouter()
    received = []
    router.subscribe(received.append)

    event = CapabilityEvent(device_id="dev-a", capability="phone.roll", value=1.0)
    router.publish(event)

    assert len(received) == 1
    assert received[0] is event  # 同一对象，未复制/改写


# ---------------------------------------------------------------------------
# 2. 多订阅
# ---------------------------------------------------------------------------

def test_multiple_subscribers():
    """两个 handler 同时收到同一事件。"""
    router = CapabilityRouter()
    a, b = [], []
    router.subscribe(a.append)
    router.subscribe(b.append)

    event = CapabilityEvent(device_id="dev-b", capability="phone.gas", value=0.8)
    router.publish(event)

    assert [e for e in a] == [event]
    assert [e for e in b] == [event]


def test_unsubscribe_stops_receiving():
    router = CapabilityRouter()
    got = []
    router.subscribe(got.append)
    router.publish(CapabilityEvent("dev-x", "phone.brake", 0.0))
    assert len(got) == 1

    router.unsubscribe(got.append)
    router.publish(CapabilityEvent("dev-x", "phone.brake", 1.0))
    assert len(got) == 1  # 注销后不再收到


# ---------------------------------------------------------------------------
# 3. device_id 保留
# ---------------------------------------------------------------------------

def test_device_id_preserved_through_router():
    """Router 前后 device_id 完全保留，不丢失/不串改。"""
    router = CapabilityRouter()
    seen = []
    router.subscribe(seen.append)

    event = CapabilityEvent(
        device_id="dev-a",
        capability="phone.roll",
        value=1.0,
    )
    router.publish(event)

    assert seen[0].device_id == "dev-a"
    assert seen[0].capability == "phone.roll"
    assert seen[0].value == 1.0


# ---------------------------------------------------------------------------
# 4. Mapping 回归（Router + MappingAdapter -> MappingEngine -> X360）
# ---------------------------------------------------------------------------

def _build_routed_pipeline():
    """复刻 app.py：CapabilityRouter + CapabilityMappingAdapter + Mapping。"""
    bus = EventBus()
    registry = CapabilityRegistry()
    PackageManager(registry).load(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "packages",
    ))

    adapter = StreamAdapter(registry)
    mapping = MappingEngine(bus)
    mapping.load_mappings({"phone.roll": "xbox.right_x"})

    outputs = []
    bus.subscribe(OutputEvent, lambda e: outputs.append(e))

    def stream_receive(stream):
        channel = adapter.convert(stream)
        if channel is None:
            return
        bus.publish(channel)

    bus.subscribe(StreamData, stream_receive)

    # 路由层 + 映射适配器（与 app.py 一致）
    from app import CapabilityMappingAdapter
    router = CapabilityRouter()
    router.subscribe(CapabilityMappingAdapter(stream_receive).handle)

    # Channel -> ProcessedChannel（app.py 管线；此处处理器为空操作）
    def channel_receive(channel):
        if channel.processed:
            return
        bus.publish(ProcessedChannel(
            channel.id, channel.category, channel.value,
            capability=channel.capability,
        ))

    bus.subscribe(Channel, channel_receive)
    return bus, router, outputs


def test_routing_layer_reaches_x360_via_mapping():
    """phone.roll 经 Router + MappingAdapter + Mapping 产出 xbox.right_x。"""
    bus, router, outputs = _build_routed_pipeline()

    router.publish(CapabilityEvent(
        device_id="dev-a",
        capability="phone.roll",
        value=0.35,
    ))

    produced = [o for o in outputs if o.target == "xbox.right_x"]
    assert produced, "Mapping 未产出 xbox.right_x"
    assert produced[0].value == 0.35  # gain=1.0 透传，与旧行为一致


def test_routing_layer_compatible_with_streamdata_path():
    """经 Router 的 CapabilityEvent 与直接 StreamData 走同一 Mapping，结果一致。"""
    bus, router, outputs = _build_routed_pipeline()

    router.publish(CapabilityEvent("dev-a", "phone.roll", 0.5))
    via_event = [o for o in outputs if o.target == "xbox.right_x"]
    assert via_event and via_event[0].value == 0.5

    outputs.clear()
    # 直接走 StreamData（其它设备路径），结果应相同
    bus.publish(StreamData("phone.roll", 0.5))
    via_stream = [o for o in outputs if o.target == "xbox.right_x"]
    assert via_stream and via_stream[0].value == 0.5


def test_router_is_capability_agnostic():
    """Router 不含任何具体能力/设备的字面判断：未来能力直接透传。"""
    router = CapabilityRouter()
    seen = []
    router.subscribe(seen.append)

    future = [
        CapabilityEvent("dev-t", "trainer.power", 200.0),
        CapabilityEvent("dev-v", "vr.head.yaw", 0.5),
        CapabilityEvent("dev-w", "wheel.angle", -1.2),
    ]
    for e in future:
        router.publish(e)

    assert [e.capability for e in seen] == [
        "trainer.power", "vr.head.yaw", "wheel.angle"
    ]
