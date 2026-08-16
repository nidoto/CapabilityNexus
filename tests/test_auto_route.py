"""AutoRouter 测试：按命名约定自动路由能力到 x360 目标。"""

from mapping.auto_route import AutoRouter


def _cap(cap_id, category):
    return {"id": cap_id, "category": category}


def test_routes_axis():
    router = AutoRouter()
    mappings, missing = router.route([
        _cap("phone.left_x", "axis"),
        _cap("phone.right_y", "axis"),
    ])
    assert missing == []
    assert mappings["phone.left_x"]["target"] == "left_x"
    assert mappings["phone.right_y"]["target"] == "right_y"


def test_routes_trigger():
    router = AutoRouter()
    mappings, _missing = router.route([
        _cap("phone.left_trigger", "trigger"),
    ])
    assert mappings["phone.left_trigger"]["target"] == "left_trigger"


def test_routes_buttons():
    router = AutoRouter()
    mappings, missing = router.route([
        _cap("phone.a", "button"),
        _cap("phone.b", "button"),
        _cap("phone.dpad_up", "button"),
    ])
    assert missing == []
    assert mappings["phone.a"]["target"] == "button_a"
    assert mappings["phone.b"]["target"] == "button_b"
    assert mappings["phone.dpad_up"]["target"] == "button_dpad_up"


def test_unknown_capability_reported_missing():
    router = AutoRouter()
    mappings, missing = router.route([
        _cap("phone.motor_left", "motor"),
        _cap("phone.unknown_thing", "axis"),
    ])
    assert mappings == {}
    assert missing == ["phone.motor_left", "phone.unknown_thing"]


def test_axis_sets_return_to_center():
    router = AutoRouter()
    mappings, _missing = router.route([
        _cap("phone.left_x", "axis"),
        _cap("phone.a", "button"),
    ])
    assert mappings["phone.left_x"]["return_to_center"] is True
    assert mappings["phone.a"]["return_to_center"] is False
