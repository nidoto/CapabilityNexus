"""端到端管线测试（无硬件）：StreamData → Channel → Processed → OutputEvent。"""

from core.event_bus import EventBus
from core.capability_registry import CapabilityRegistry
from core.stream_adapter import StreamAdapter
from core.channel import Channel
from core.processed_channel import ProcessedChannel
from core.system_event import OutputEvent
from core.stream import StreamData
from packages.manager import PackageManager
from processors.manager import ProcessorManager
from mapping.mapper import MappingEngine


def test_full_pipeline_axis():
    """陀螺仪轴：StreamData → Channel → 处理器 → 映射 → OutputEvent。"""
    bus = EventBus()

    registry = CapabilityRegistry()
    package_manager = PackageManager(registry)
    package_manager.load("packages")

    adapter = StreamAdapter(registry)
    processors = ProcessorManager()
    processors.load("config/processors.json")

    # 用 curve 处理器覆盖 control.right_x（模拟游戏专属调优）
    processors.load_dict({
        "control.right_x": [{
            "type": "curve",
            "mode": "step",
            "max_degrees": 12,
            "deadzone": 1.5,
            "points": [
                [-12, -80], [-7, -50], [-4, -30], [-1.5, -10], [0, 0],
                [1.5, 10], [4, 30], [7, 50], [10, 80], [12, 80],
            ],
        }],
    })

    engine = MappingEngine(bus)
    engine.load_mappings({"control.right_x": "right_x"})

    outputs = []
    bus.subscribe(OutputEvent, outputs.append)

    # 模拟 ESP32 固件发送 8°（轴值 = 8/180*32767 ≈ 1456）
    axis_value = round(8 / 180 * 32767)

    # StreamData -> Channel
    channel = adapter.convert(StreamData("control.right_x", float(axis_value)))
    assert channel is not None

    # Channel -> 处理器
    processed_value = processors.process("control.right_x", channel.value)
    assert processed_value > 0

    # ProcessedChannel -> 映射 -> OutputEvent
    processed = ProcessedChannel("control.right_x", "axis", processed_value)
    engine.receive(processed)

    assert len(outputs) == 1
    assert outputs[0].target == "right_x"
    # 8° 落在 7°~10° 档 → 50%
    expected = round(0.50 * 32767)
    assert abs(outputs[0].value - expected) <= 2


def test_full_pipeline_button():
    """按钮：StreamData → Channel → 映射 → OutputEvent。"""
    bus = EventBus()

    registry = CapabilityRegistry()
    package_manager = PackageManager(registry)
    package_manager.load("packages")

    adapter = StreamAdapter(registry)
    engine = MappingEngine(bus)
    engine.load_mappings({"xbox.a": "button_a"})

    outputs = []
    bus.subscribe(OutputEvent, outputs.append)

    channel = adapter.convert(StreamData("xbox.a", 1.0))
    assert channel is not None
    assert channel.category == "button"

    engine.receive(ProcessedChannel("xbox.a", "button", 1.0))

    assert len(outputs) == 1
    assert outputs[0].target == "button_a"
    assert outputs[0].value == 1.0
