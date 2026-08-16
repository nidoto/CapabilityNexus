"""RequestHandler 测试：游戏请求 → 映射输出或未映射提示。"""

from core.event_bus import EventBus
from core.system_event import DeviceRequestEvent
from core.system_event import OutputEvent
from output.request_handler import RequestHandler


class OutputCollector:
    def __init__(self):
        self.events = []

    def on_output(self, event):
        self.events.append(event)


def _make(mappings=None, router=None):
    bus = EventBus()
    collector = OutputCollector()
    bus.subscribe(OutputEvent, collector.on_output)
    handler = RequestHandler(bus, router=router, mappings=mappings or {})
    return bus, collector, handler


def test_mapped_request_publishes_output():
    _bus, collector, handler = _make({"xbox.motor_left": "right_trigger"})

    handler.receive(DeviceRequestEvent(source="virtual_x360", target="xbox.motor_left", value=32000))

    assert len(collector.events) == 1
    assert collector.events[0].target == "right_trigger"
    assert collector.events[0].value == 32000


def test_zero_value_unmapped_silent():
    _bus, collector, handler = _make({})

    handler.receive(DeviceRequestEvent(source="virtual_x360", target="xbox.motor_left", value=0))

    assert collector.events == []


def test_unmapped_positive_value_warns_once():
    _bus, collector, handler = _make({})

    for _ in range(3):
        handler.receive(DeviceRequestEvent(source="virtual_x360", target="xbox.motor_left", value=100))

    assert collector.events == []


def test_runtime_mapping_update():
    _bus, collector, handler = _make({"xbox.motor_left": "right_trigger"})

    handler.set_mappings({"xbox.motor_left": "left_trigger"})
    handler.receive(DeviceRequestEvent(source="virtual_x360", target="xbox.motor_left", value=1000))

    assert collector.events[0].target == "left_trigger"
