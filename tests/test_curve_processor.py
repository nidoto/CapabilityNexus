"""CurveProcessor 测试：step / linear 模式、死区、档位边界、饱和。"""

from processors.curve import CurveProcessor


def _axis_from_degrees(deg):
    """固件角度→轴值：angle/180*32767。"""
    return round(deg / 180 * 32767)


def _pct(value):
    return value / 32767.0 * 100.0


def _assert_pct(actual, expected_pct, tolerance=1.0):
    assert abs(_pct(actual) - expected_pct) <= tolerance, (
        f"expected ~{expected_pct}%, got {_pct(actual):.2f}%"
    )


STEP_POINTS = [
    [-12, -80], [-10, -80], [-7, -50], [-4, -30], [-1.5, -10], [0, 0],
    [1.5, 10], [4, 30], [7, 50], [10, 80], [12, 80],
]


def test_step_deadzone_zero():
    cp = CurveProcessor(max_degrees=12, deadzone=1.5, points=STEP_POINTS, mode="step")
    assert cp.process(_axis_from_degrees(1.4)) == 0
    assert cp.process(_axis_from_degrees(-1.4)) == 0


def test_step_bands():
    cp = CurveProcessor(max_degrees=12, deadzone=1.5, points=STEP_POINTS, mode="step")

    _assert_pct(cp.process(_axis_from_degrees(2)), 10)
    _assert_pct(cp.process(_axis_from_degrees(5)), 30)
    _assert_pct(cp.process(_axis_from_degrees(8)), 50)
    _assert_pct(cp.process(_axis_from_degrees(11)), 80)


def test_step_saturation_at_max():
    cp = CurveProcessor(max_degrees=12, deadzone=1.5, points=STEP_POINTS, mode="step")
    # 超过最大角度仍封顶
    _assert_pct(cp.process(_axis_from_degrees(12)), 80)
    _assert_pct(cp.process(_axis_from_degrees(20)), 80)


def test_step_negative_symmetric():
    cp = CurveProcessor(max_degrees=12, deadzone=1.5, points=STEP_POINTS, mode="step")
    _assert_pct(abs(cp.process(_axis_from_degrees(-2))), 10)
    _assert_pct(abs(cp.process(_axis_from_degrees(-11))), 80)


def test_linear_interpolation():
    points = [[-30, -100], [-15, -30], [0, 0], [15, 30], [30, 100]]
    cp = CurveProcessor(max_degrees=30, deadzone=0, points=points, mode="linear")

    _assert_pct(cp.process(_axis_from_degrees(15)), 30)
    _assert_pct(cp.process(_axis_from_degrees(7.5)), 15)


def test_linear_deadzone():
    points = [[-30, -100], [0, 0], [30, 100]]
    cp = CurveProcessor(max_degrees=30, deadzone=2.5, points=points, mode="linear")

    assert cp.process(_axis_from_degrees(2.4)) == 0


def test_default_points_valid():
    cp = CurveProcessor()
    # 默认配置不应报错，死区内为 0
    assert cp.process(0) == 0
    assert cp.process(_axis_from_degrees(20)) > 0
