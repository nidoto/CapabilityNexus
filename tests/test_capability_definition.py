"""CapabilityDefinition 测试（V1.9 Phase 5）。

验证：
  1. 字段正确保存（id / display_name / value_type / unit / min / max / category）。
  2. display_name 缺省时回落到 id。
  3. to_dict / from_dict 往返（供 UI 与序列化，不暴露内部对象）。
  4. capability 仍为字符串 id，未引入 enum。
"""

from core.capability_definition import CapabilityDefinition


def test_fields_stored():
    d = CapabilityDefinition(
        id="phone.roll",
        display_name="Roll 横滚",
        value_type="float",
        unit="deg",
        min_value=-90.0,
        max_value=90.0,
        category="axis",
    )
    assert d.id == "phone.roll"
    assert d.display_name == "Roll 横滚"
    assert d.value_type == "float"
    assert d.unit == "deg"
    assert d.min_value == -90.0
    assert d.max_value == 90.0
    assert d.category == "axis"


def test_display_name_falls_back_to_id():
    d = CapabilityDefinition(id="phone.gas")
    assert d.display_name == "phone.gas"


def test_to_dict_roundtrip():
    d = CapabilityDefinition(
        id="phone.gas",
        display_name="油门",
        value_type="float",
        unit="%",
        min_value=0.0,
        max_value=1.0,
        category="axis",
    )
    snapshot = d.to_dict()
    assert isinstance(snapshot, dict)
    assert snapshot["id"] == "phone.gas"
    assert snapshot["unit"] == "%"

    restored = CapabilityDefinition.from_dict(snapshot)
    assert restored.id == d.id
    assert restored.display_name == d.display_name
    assert restored.value_type == d.value_type
    assert restored.unit == d.unit
    assert restored.min_value == d.min_value
    assert restored.max_value == d.max_value
    assert restored.category == d.category


def test_from_dict_ignores_unknown_keys():
    d = CapabilityDefinition.from_dict({
        "id": "xbox.a",
        "display_name": "A",
        "category": "button",
        "extra_unknown": "should-be-ignored",
    })
    assert d.id == "xbox.a"
    assert d.category == "button"
    assert not hasattr(d, "extra_unknown")


def test_no_enum_used():
    import enum

    # capability id 保持普通字符串，未引入 enum 类型。
    d = CapabilityDefinition(id="trainer.power")
    assert isinstance(d.id, str)
    assert not isinstance(d.id, enum.Enum)
