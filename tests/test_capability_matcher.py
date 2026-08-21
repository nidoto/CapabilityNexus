"""CapabilityMatcher 测试（V1.9 Phase 7）。

覆盖：
  1. float axis -> float axis  : compatible=True
  2. int -> float              : compatible=True
  3. motion -> axis            : 分数被提高（高于无语义亲和的弱匹配）
  4. 完全不同类型              : compatible=False
  5. suggest_targets 排序正确  : 按 score 降序
  6. 无 enum，capability id 仍字符串
"""

from core.capability_definition import CapabilityDefinition
from core.capability_matcher import compatibility, suggest_targets


def _def(cap_id, value_type="float", category="misc", unit=None):
    return CapabilityDefinition(
        id=cap_id, value_type=value_type, category=category, unit=unit,
    )


# 1. float axis -> float axis
def test_float_axis_to_float_axis_compatible():
    src = _def("phone.roll", "float", "axis", unit="deg")
    tgt = _def("x360.right_x", "float", "axis", unit="%")
    compatible, score = compatibility(src, tgt)
    assert compatible is True
    assert score >= 0.5


# 2. int -> float
def test_int_to_float_compatible():
    src = _def("phone.gas_int", "int", "axis")
    tgt = _def("x360.right_trigger", "float", "axis")
    compatible, score = compatibility(src, tgt)
    # int->float 仅类型分（0.6）即达阈值，即便分类不同也应可连
    assert compatible is True
    assert score >= 0.5


# 3. motion -> axis 提高分数
def test_motion_to_axis_boosts_score():
    src = _def("phone.roll", "float", "motion")
    tgt = _def("x360.right_x", "float", "axis")
    _, motion_score = compatibility(src, tgt)

    # 对照：同类但无 motion->axis 语义亲和的普通（sensor->axis 弱亲和）更低
    plain_src = _def("phone.temp", "float", "sensor")
    plain_tgt = _def("x360.right_x", "float", "axis")
    _, plain_score = compatibility(plain_src, plain_tgt)

    # motion->axis 拿到分类满额 0.3，应高于仅弱亲和的对照
    assert motion_score > plain_score
    assert motion_score >= 0.5  # 同时确认可连


# 4. 完全不同类型 -> 不兼容
def test_completely_different_types_incompatible():
    src = _def("mic.audio", "audio", "sensor")
    tgt = _def("screen.frame", "image", "display")
    compatible, score = compatibility(src, tgt)
    assert compatible is False
    assert score == 0.0


# 5. suggest_targets 排序正确
def test_suggest_targets_sorted_by_score():
    src = _def("phone.roll", "float", "motion")
    candidates = [
        _def("x360.right_x", "float", "axis"),       # motion->axis 最高（0.5+0.3=0.8）
        _def("x360.right_y", "float", "misc"),        # 同类型无分类亲和（0.5）
        _def("x360.btn_a", "bool", "button"),        # 完全不匹配 -> 0
    ]
    ranked = suggest_targets(src, candidates)
    scores = [s for (_, s, _) in ranked]
    # 降序
    assert scores == sorted(scores, reverse=True)
    # 最佳建议是 motion->axis（right_x）
    best = ranked[0]
    assert best[0].id == "x360.right_x"
    assert best[2] is True  # compatible
    # 兼容候选排在完全不匹配之前
    assert ranked[0][1] > ranked[2][1]


# 6. 无 enum：capability id 保持字符串
def test_no_enum_ids():
    import enum

    src = _def("trainer.power", "float", "sensor")
    tgt = _def("x360.vibration", "float", "output")
    compatible, _ = compatibility(src, tgt)
    # 类型不同(float->float 同类型得 0.5) 且分类 sensor->output 无亲和 -> 0.5 仅类型
    # 这里只验证 id 类型是 str，不引入 enum
    assert isinstance(src.id, str)
    assert isinstance(tgt.id, str)
    assert not isinstance(src.id, enum.Enum)
