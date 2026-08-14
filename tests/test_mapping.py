"""MappingEngine 测试：映射、增益、多对一、运行时重载。"""

from core.event_bus import EventBus
from core.processed_channel import ProcessedChannel
from core.system_event import OutputEvent
from mapping.mapper import MappingEngine


def _processed(cap_id, value):
    return ProcessedChannel(id=cap_id, category="axis", value=value)


class OutputCollector:
    def __init__(self):
        self.events = []

    def on_output(self, event):
        self.events.append(event)


def _make_engine(mappings):
    bus = EventBus()
    engine = MappingEngine(bus)
    engine.load_mappings(mappings)
    collector = OutputCollector()
    bus.subscribe(OutputEvent, collector.on_output)
    return engine, collector


def test_simple_mapping():
    _engine, collector = _make_engine({"motion.pitch": "right_x"})

    _engine.receive(_processed("motion.pitch", 1000))

    assert len(collector.events) == 1
    assert collector.events[0].target == "right_x"
    assert collector.events[0].value == 1000


def test_gain_applied():
    _engine, collector = _make_engine({
        "control.right_x": [{"target": "right_x", "gain": -1.0, "return_to_center": False}],
    })

    _engine.receive(_processed("control.right_x", 1000))

    assert collector.events[0].value == -1000


def test_one_to_many():
    _engine, collector = _make_engine({
        "motion.pitch": [
            {"target": "right_x", "gain": 1.0, "return_to_center": False},
            {"target": "right_y", "gain": 0.5, "return_to_center": False},
        ],
    })

    _engine.receive(_processed("motion.pitch", 1000))

    targets = sorted(e.target for e in collector.events)
    assert targets == ["right_x", "right_y"]
    assert {e.value for e in collector.events} == {1000, 500}


def test_unmapped_ignored():
    _engine, collector = _make_engine({})

    _engine.receive(_processed("unmapped.cap", 500))

    assert collector.events == []


def test_many_to_one_last_wins():
    """多个源映射到同一 target，最后到达者覆盖（在发布时体现）。"""
    _engine, collector = _make_engine({
        "src.a": "right_x",
        "src.b": "right_x",
    })

    _engine.receive(_processed("src.a", 100))
    _engine.receive(_processed("src.b", 200))

    assert len(collector.events) == 2
    assert collector.events[-1].value == 200


def test_runtime_reload():
    _engine, collector = _make_engine({"src.a": "right_x"})

    _engine.receive(_processed("src.a", 1.0))
    assert len(collector.events) == 1

    # 运行时替换映射
    _engine.load_mappings({"src.a": "left_x"})
    _engine.receive(_processed("src.a", 2.0))

    assert collector.events[-1].target == "left_x"
    assert collector.events[-1].value == 2.0
