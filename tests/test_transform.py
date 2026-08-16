"""TransformLayer 测试：hold / tap / invert / long_press / double_tap / hold_repeat。"""

import time

from core.event_bus import EventBus
from core.processed_channel import ProcessedChannel
from mapping.transform import TransformLayer


def _processed(cap_id, value):
    return ProcessedChannel(id=cap_id, category="button", value=value)


def _layer_with_rules(rules):
    bus = EventBus()
    layer = TransformLayer(bus)
    layer.rules = rules
    return layer


def test_pass_through_when_no_rule():
    layer = _layer_with_rules([])
    ch = _processed("xbox.a", 1.0)
    assert layer.process(ch) == [ch]


def test_pass_through_when_transformed():
    layer = _layer_with_rules([])
    ch = ProcessedChannel(
        id="xbox.a",
        category="button",
        value=1.0,
        transformed=True,
    )
    assert layer.process(ch) == [ch]


def test_hold_forwards_value():
    layer = _layer_with_rules([
        {"source": "xbox.a", "type": "hold", "target": "xbox.b"},
    ])
    out = layer.process(_processed("xbox.a", 1.0))
    assert len(out) == 1
    assert out[0].id == "xbox.b"
    assert out[0].value == 1.0
    assert out[0].transformed is True


def test_tap_fires_only_on_rising_edge():
    layer = _layer_with_rules([
        {"source": "xbox.a", "type": "tap", "target": "xbox.b"},
    ])

    out_rise = layer.process(_processed("xbox.a", 1.0))
    assert len(out_rise) == 1
    assert out_rise[0].value == 1.0

    # 保持按住：不再触发
    assert layer.process(_processed("xbox.a", 1.0)) == []

    # 松开：不触发
    assert layer.process(_processed("xbox.a", 0.0)) == []


def test_invert_flips_button():
    layer = _layer_with_rules([
        {"source": "xbox.a", "type": "invert", "target": "xbox.b"},
    ])
    assert layer.process(_processed("xbox.a", 1.0))[0].value == 0.0
    assert layer.process(_processed("xbox.a", 0.0))[0].value == 1.0


def test_long_press_requires_duration():
    layer = _layer_with_rules([
        {"source": "xbox.a", "type": "long_press", "target": "xbox.b",
         "params": {"duration": 0.05}},
    ])

    layer.process(_processed("xbox.a", 1.0))
    # 立即松开：时长不足，不触发
    assert layer.process(_processed("xbox.a", 0.0)) == []

    layer.process(_processed("xbox.a", 1.0))
    time.sleep(0.08)
    out = layer.process(_processed("xbox.a", 0.0))
    assert len(out) == 1
    assert out[0].value == 1.0


def test_double_tap_within_interval():
    layer = _layer_with_rules([
        {"source": "xbox.a", "type": "double_tap", "target": "xbox.b",
         "params": {"interval": 0.2}},
    ])

    layer.process(_processed("xbox.a", 1.0))
    layer.process(_processed("xbox.a", 0.0))
    out = layer.process(_processed("xbox.a", 1.0))
    assert len(out) == 1
    assert out[0].value == 1.0


def test_double_tap_single_press_no_fire():
    layer = _layer_with_rules([
        {"source": "xbox.a", "type": "double_tap", "target": "xbox.b",
         "params": {"interval": 0.2}},
    ])
    assert layer.process(_processed("xbox.a", 1.0)) == []


def test_hold_repeat_respects_interval():
    layer = _layer_with_rules([
        {"source": "xbox.a", "type": "hold_repeat", "target": "xbox.b",
         "params": {"interval": 0.03}},
    ])

    # 第一次按下立即触发
    assert len(layer.process(_processed("xbox.a", 1.0))) == 1
    # 间隔未到：不触发
    assert layer.process(_processed("xbox.a", 1.0)) == []

    time.sleep(0.05)
    assert len(layer.process(_processed("xbox.a", 1.0))) == 1

    # 松开后清空状态，再次按下可立即触发
    layer.process(_processed("xbox.a", 0.0))
    assert len(layer.process(_processed("xbox.a", 1.0))) == 1
