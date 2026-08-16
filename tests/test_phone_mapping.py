"""手机 → X360 映射端到端测试：phone.* 能力经处理器+映射到达 X360 输出目标。"""

from core.event_bus import EventBus
from core.processed_channel import ProcessedChannel
from core.system_event import OutputEvent
from mapping.mapper import MappingEngine
from processors.manager import ProcessorManager


def _pipeline(mappings_path, processors_path):
    bus = EventBus()
    outputs = []
    bus.subscribe(OutputEvent, lambda e: outputs.append((e.target, e.value)))
    pm = ProcessorManager()
    pm.load(processors_path)
    eng = MappingEngine(bus)
    eng.load_profile(mappings_path)
    return pm, eng, outputs


def _send(pm, eng, outputs, cap_id, category, value):
    processed = pm.process(cap_id, value)
    eng.receive(ProcessedChannel(cap_id, category, processed, capability=cap_id))
    return processed


def _by_target(outputs):
    return {t: v for t, v in outputs}


def test_phone_roll_maps_to_right_x():
    pm, eng, outputs = _pipeline("profiles/default.json", "config/processors.json")
    _send(pm, eng, outputs, "phone.roll", "axis", 0.5)
    targets = _by_target(outputs)
    assert abs(targets["right_x"] - 16383) < 2


def test_phone_gas_maps_to_right_trigger():
    pm, eng, outputs = _pipeline("profiles/default.json", "config/processors.json")
    _send(pm, eng, outputs, "phone.gas", "trigger", 1.0)
    targets = _by_target(outputs)
    assert abs(targets["right_trigger"] - 255) < 1


def test_phone_brake_maps_to_left_trigger():
    pm, eng, outputs = _pipeline("profiles/default.json", "config/processors.json")
    _send(pm, eng, outputs, "phone.brake", "trigger", 0.3)
    targets = _by_target(outputs)
    assert abs(targets["left_trigger"] - 76) < 2


def test_phone_buttons_map_to_x360_buttons():
    pm, eng, outputs = _pipeline("profiles/default.json", "config/processors.json")
    _send(pm, eng, outputs, "phone.button_a", "button", 1.0)
    _send(pm, eng, outputs, "phone.dpad_up", "button", 1.0)
    targets = _by_target(outputs)
    assert targets["button_a"] == 1.0
    assert targets["button_dpad_up"] == 1.0


def test_phone_gas_half_is_127():
    pm, eng, outputs = _pipeline("profiles/default.json", "config/processors.json")
    _send(pm, eng, outputs, "phone.gas", "trigger", 0.5)
    targets = _by_target(outputs)
    assert abs(targets["right_trigger"] - 127) < 2
