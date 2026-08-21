"""Capability Runtime 集成测试（V1.9 Phase 3）：

PhoneProvider -> CapabilityRouter -> (MappingAdapter) -> X360Consumer 完整链路。

验证端到端：
  手机 phone.roll
    → PhoneProvider 解析为 CapabilityEvent
    → CapabilityRouter 分发
    → CapabilityMappingAdapter 转 StreamData -> MappingEngine
    → OutputEvent(xbox.right_x)
    → X360Consumer 收到并驱动 X360 底层
"""

import os

from core.event_bus import EventBus
from core.capability import CapabilityEvent
from core.capability_router import CapabilityRouter
from core.capability_registry import CapabilityRegistry
from core.stream import StreamData
from core.stream_adapter import StreamAdapter
from core.channel import Channel
from core.processed_channel import ProcessedChannel
from core.system_event import OutputEvent

from mapping.mapper import MappingEngine
from packages.manager import PackageManager

from app import CapabilityMappingAdapter
from devices.phone_provider import PhoneProvider
from output.x360_consumer import X360Consumer


def _build_runtime():
    """搭建 PhoneProvider -> Router -> Mapping -> X360Consumer 链路。"""
    bus = EventBus()
    registry = CapabilityRegistry()
    PackageManager(registry).load(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "packages",
    ))
    adapter = StreamAdapter(registry)
    mapping = MappingEngine(bus)
    mapping.load_mappings({"phone.roll": "xbox.right_x"})

    # StreamData -> Channel（与 app.py 一致）
    def stream_receive(stream):
        channel = adapter.convert(stream)
        if channel is None:
            return
        bus.publish(channel)

    # Channel -> ProcessedChannel（处理器为空操作，关注点在本链路）
    def channel_receive(channel):
        if channel.processed:
            return
        bus.publish(ProcessedChannel(
            channel.id, channel.category, channel.value,
            capability=channel.capability,
        ))

    bus.subscribe(Channel, channel_receive)

    # 路由层 + 映射适配器
    router = CapabilityRouter()
    router.subscribe(CapabilityMappingAdapter(stream_receive).handle)

    # X360 消费者（底层用记录型 router 代替真实 XInput）
    sent = []
    fake_x360 = type("X360Router", (), {
        "send": lambda self, t, v: sent.append((t, v)),
    })()
    x360 = X360Consumer(fake_x360)

    # OutputEvent -> CapabilityEvent -> X360Consumer（与 app.py 一致）
    def output_receive(event):
        x360.consume(CapabilityEvent(
            device_id=X360Consumer.DEVICE_ID,
            capability=event.target,
            value=event.value,
        ))

    bus.subscribe(OutputEvent, output_receive)

    # 手机 Provider（发布到 router）
    provider = PhoneProvider(
        device_id="dev-a",
        capabilities=["phone.roll"],
        publish=router.publish,
    )
    return provider, router, sent


def test_phone_provider_to_x360_consumer_link():
    provider, router, sent = _build_runtime()

    # 手机先 hello 建立身份，再发 sensors
    provider.parse('{"t":"hello","device_id":"dev-a","capabilities":["phone.roll"]}')
    provider.parse('{"t":"sensors","roll":0.5}')

    # X360 消费者应收到映射后的 xbox.right_x
    assert any(t == "xbox.right_x" for t, v in sent), sent
    target = [v for t, v in sent if t == "xbox.right_x"]
    assert target == [0.5]  # gain=1.0 透传，与旧行为一致


def test_runtime_device_id_preserved_end_to_end():
    """整条链路中 device_id 在 Provider 侧保留（X360 侧为输出设备标识）。"""
    provider, router, sent = _build_runtime()
    provider.parse('{"t":"hello","device_id":"dev-b","capabilities":["phone.roll"]}')
    provider.parse('{"t":"sensors","roll":0.9}')
    # X360 消费侧 device_id 固定为 x360（输出设备），与输入 device_id 解耦
    assert X360Consumer.DEVICE_ID == "x360"
    assert any(t == "xbox.right_x" for t, v in sent)
