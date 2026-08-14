"""CapabilityRegistry 测试：注册、通配匹配、exists、list。"""

from core.capability_registry import CapabilityRegistry


def _cap(cap_id, category="axis"):
    return {"id": cap_id, "category": category}


def test_register_and_get():
    registry = CapabilityRegistry()
    registry.register("testpkg", _cap("motion.pitch"))

    result = registry.get("motion.pitch")
    assert result is not None
    assert result["package"] == "testpkg"
    assert result["definition"]["category"] == "axis"


def test_wildcard_pattern():
    registry = CapabilityRegistry()
    registry.register("hidpkg", _cap("hid.axis*"))

    result = registry.get("hid.axis0")
    assert result is not None
    assert result["definition"]["id"] == "hid.axis0"
    assert result["package"] == "hidpkg"

    assert registry.get("hid.axis15") is not None
    assert registry.get("hid.button0") is None


def test_get_unknown_returns_none():
    registry = CapabilityRegistry()
    assert registry.get("nope.missing") is None


def test_exists():
    registry = CapabilityRegistry()
    registry.register("testpkg", _cap("xbox.a", "button"))
    assert registry.exists("xbox.a")
    assert not registry.exists("xbox.b")


def test_list_and_list_all():
    registry = CapabilityRegistry()
    registry.register("p", _cap("motion.pitch"))
    registry.register("p", _cap("hid.axis*"))

    all_keys = registry.list_all()
    assert "hid.axis*" in all_keys
    assert "motion.pitch" in all_keys
    # list() 只含精确注册（不含通配模式）
    assert "motion.pitch" in registry.list()
