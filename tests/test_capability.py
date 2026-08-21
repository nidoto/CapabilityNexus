"""Capability Runtime Layer 测试（V1.9 Phase 1）。

验证：
  1. CapabilityEvent 可正常创建（device_id / capability / value / timestamp）。
  2. 多设备隔离：dev-a / dev-b 同名能力（phone.roll）在事件中 device_id 不混乱。
  3. 旧功能回归：CapabilityEvent 经运行时桥接进入既有管线后，
     手机连接 -> Mapping -> X360 输出链路行为不变（用映射引擎做端到端回归）。
"""

import os
import time

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
# 1. 创建 CapabilityEvent
# ---------------------------------------------------------------------------

def test_create_capability_event():
    event = CapabilityEvent(
        device_id="dev-a",
        capability="phone.roll",
        value=1.0,
    )
    # 未传 timestamp 时自动填充为浮点时间戳
    assert event.device_id == "dev-a"
    assert event.capability == "phone.roll"
    assert event.value == 1.0
    assert isinstance(event.timestamp, float)
    assert event.timestamp <= time.time() + 1.0


def test_create_capability_event_explicit_timestamp():
    ts = 1700000000.123
    event = CapabilityEvent("dev-x", "trainer.power", 250.0, timestamp=ts)
    assert event.timestamp == ts


# ---------------------------------------------------------------------------
# 2. 多设备隔离（device_id 不混乱）
# ---------------------------------------------------------------------------

def test_multi_device_isolation():
    """两台手机都上报 phone.roll，事件中的 device_id 必须各自正确。"""
    a = CapabilityEvent(device_id="dev-a", capability="phone.roll", value=1)
    b = CapabilityEvent(device_id="dev-b", capability="phone.roll", value=2)

    # capability 同名，但 device_id 区分来源，互不可混淆
    assert a.capability == b.capability == "phone.roll"
    assert a.device_id == "dev-a"
    assert b.device_id == "dev-b"
    assert a.value == 1
    assert b.value == 2

    # 未来能力命名（字符串，非 enum）直接可用，系统无需改动
    future = [
        CapabilityEvent("dev-t", "trainer.power", 200.0),
        CapabilityEvent("dev-t", "trainer.cadence", 90.0),
        CapabilityEvent("dev-v", "vr.head.yaw", 0.5),
    ]
    assert {e.capability for e in future} == {
        "trainer.power", "trainer.cadence", "vr.head.yaw"
    }


# ---------------------------------------------------------------------------
# 3. 旧功能回归：CapabilityEvent -> 桥接 -> Mapping -> X360 链路
# ---------------------------------------------------------------------------

def _build_pipeline():
    """复刻 app.py 的 StreamData/Channel/ProcessedChannel 桥接 + Mapping。"""
    bus = EventBus()
    registry = CapabilityRegistry()
    # 加载内置能力定义（phone.* / xbox.* 等），与 app.py 一致
    manager = PackageManager(registry)
    manager.load(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "packages",
    ))

    adapter = StreamAdapter(registry)
    mapping = MappingEngine(bus)

    # phone.roll -> xbox.right_x（模拟手机方向控制 X360 右摇杆 X 轴）
    mapping.load_mappings({"phone.roll": "xbox.right_x"})

    outputs = []
    bus.subscribe(OutputEvent, lambda e: outputs.append(e))

    # StreamData -> Channel（既有设备路径，与 app.py 一致，用于对照兼容性）
    def stream_receive(stream):
        channel = adapter.convert(stream)
        if channel is None:
            return
        bus.publish(channel)

    bus.subscribe(StreamData, stream_receive)

    # CapabilityEvent -> CapabilityRouter -> MappingAdapter（与 app.py 一致）
    # Router 为通用能力层；MappingAdapter 把事件结构转换为 StreamData 喂给
    # 未变的 Mapping 管线。device_id / timestamp 保留在事件中。
    from app import CapabilityMappingAdapter
    router = CapabilityRouter()
    router.subscribe(CapabilityMappingAdapter(stream_receive).handle)

    # 通过路由层发布 CapabilityEvent（与 app.py 的 capability_receive 等价）
    def capability_receive(event):
        router.publish(event)

    bus.subscribe(CapabilityEvent, capability_receive)

    # Channel -> ProcessedChannel（复刻 app.py 管线；此处处理器为空操作，
    # 关注点在于 CapabilityEvent 经桥接后能否进入未变的 Mapping -> X360 链路）
    def channel_receive(channel):
        if channel.processed:
            return
        processed = ProcessedChannel(
            channel.id,
            channel.category,
            channel.value,
            capability=channel.capability,
        )
        bus.publish(processed)

    bus.subscribe(Channel, channel_receive)
    return bus, outputs


def test_capability_event_reaches_x360_via_mapping():
    """CapabilityEvent(phone.roll) 经桥接 + Mapping 产出 OutputEvent(xbox.right_x)。"""
    bus, outputs = _build_pipeline()

    # 模拟手机上报 roll
    bus.publish(CapabilityEvent(
        device_id="dev-a",
        capability="phone.roll",
        value=0.35,
    ))

    targets = [o.target for o in outputs]
    assert "xbox.right_x" in targets
    produced = [o for o in outputs if o.target == "xbox.right_x"][0]
    # Mapping gain=1.0，值透传
    assert produced.value == 0.35


def test_capability_event_bridge_is_compatible_with_streamdata():
    """桥接后，CapabilityEvent 与既有 StreamData 走同一 Mapping 链路，结果一致。"""
    bus, outputs = _build_pipeline()

    bus.publish(CapabilityEvent(device_id="dev-a", capability="phone.roll", value=0.5))
    via_event = [o for o in outputs if o.target == "xbox.right_x"]
    assert via_event and via_event[0].value == 0.5

    outputs.clear()
    # 直接发 StreamData（其它设备路径），结果应相同
    bus.publish(StreamData("phone.roll", 0.5))
    via_stream = [o for o in outputs if o.target == "xbox.right_x"]
    assert via_stream and via_stream[0].value == 0.5
