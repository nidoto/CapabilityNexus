"""基础处理器测试：deadzone / sensitivity / clamp / normalizer / factory / manager。"""

from processors.clamp import ClampProcessor
from processors.deadzone import DeadzoneProcessor
from processors.factory import ProcessorFactory
from processors.manager import ProcessorManager
from processors.normalizer import NormalizerProcessor
from processors.sensitivity import SensitivityProcessor


def test_deadzone_zeroes_small_values():
    dp = DeadzoneProcessor(deadzone=5)
    assert dp.process(0) == 0
    assert dp.process(4.9) == 0
    assert dp.process(-4.9) == 0


def test_deadzone_passes_large_values():
    dp = DeadzoneProcessor(deadzone=5)
    assert dp.process(5) == 5
    assert dp.process(-5) == -5
    assert dp.process(123) == 123


def test_sensitivity_scales():
    sp = SensitivityProcessor(sensitivity=2.0)
    assert sp.process(100) == 200
    assert sp.process(-50) == -100


def test_clamp_bounds():
    cp = ClampProcessor(minimum=-100, maximum=100)
    assert cp.process(150) == 100
    assert cp.process(-150) == -100
    assert cp.process(50) == 50


def test_clamp_returns_int():
    cp = ClampProcessor()
    assert cp.process(12.7) == 12


def test_normalizer_maps_range():
    np = NormalizerProcessor(input_min=0, input_max=100, output_min=0, output_max=1000)
    assert np.process(0) == 0
    assert np.process(50) == 500
    assert np.process(100) == 1000


def test_normalizer_clamps_input():
    np = NormalizerProcessor(input_min=-10, input_max=10, output_min=-100, output_max=100)
    assert np.process(-20) == -100
    assert np.process(20) == 100


def test_factory_creates_known_types():
    factory = ProcessorFactory()
    assert factory.create({"type": "deadzone", "value": 5}) is not None
    assert factory.create({"type": "sensitivity", "value": 2}) is not None
    assert factory.create({"type": "clamp", "minimum": -1, "maximum": 1}) is not None
    assert factory.create({"type": "normalizer", "input_min": 0, "input_max": 10}) is not None


def test_factory_unknown_type_raises():
    import pytest

    factory = ProcessorFactory()
    with pytest.raises(Exception):
        factory.create({"type": "no_such_processor"})


def test_manager_runs_pipeline_in_order():
    manager = ProcessorManager()
    manager.load_dict({
        "cap.a": [
            {"type": "deadzone", "value": 10},
            {"type": "sensitivity", "value": 3},
            {"type": "clamp", "minimum": 0, "maximum": 100},
        ],
    })

    # 10 → 死区边界不清零（abs<10 才清零）→ 3*10=30
    assert manager.process("cap.a", 10) == 30
    # 5 → 死区清零 → 0
    assert manager.process("cap.a", 5) == 0
    # 100 → 3*100=300 → clamp 100
    assert manager.process("cap.a", 100) == 100


def test_manager_unknown_capability_identity():
    manager = ProcessorManager()
    manager.load_dict({})
    assert manager.process("no.such", 42) == 42
