"""AutoRouteEngine 测试（V1.9 Phase 8）。

覆盖：
  3. 不兼容能力不会生成 suggestion（discover 只返回兼容对）。
  4. apply_suggestions 正确创建 GraphEdge，origin="auto"，confidence 保留 score。
  5. 已有 edge 不会重复添加（幂等）。
  6. capability id 仍为字符串，无 enum。
"""

from core.capability_definition import CapabilityDefinition
from core.capability_graph import CapabilityGraph, GraphEdge
from core.auto_router import AutoRouter, Suggestion


def _def(cap_id, value_type="float", category="misc"):
    return CapabilityDefinition(id=cap_id, value_type=value_type, category=category)


def _sources_and_targets():
    sources = [
        _def("phone.roll", "float", "motion"),     # 兼容 -> x360.right_x (axis)
        _def("mic.audio", "audio", "sensor"),       # 不兼容 -> 任何目标
    ]
    targets = [
        _def("x360.right_x", "float", "axis"),
        _def("x360.btn_a", "bool", "button"),
    ]
    return sources, targets


# 3. 不兼容能力不产生 suggestion
def test_incompatible_not_suggested():
    sources, targets = _sources_and_targets()
    router = AutoRouter()
    sugg = router.discover(sources, targets)

    # mic.audio 完全不兼容，不应出现在任何 suggestion 的 source 中
    assert all(s.source != "mic.audio" for s in sugg)
    # phone.roll -> x360.right_x（motion->axis）应当存在
    assert any(s.source == "phone.roll" and s.target == "x360.right_x" for s in sugg)
    # phone.roll -> x360.btn_a（motion->button，类型 float vs bool 不兼容）不应存在
    assert not any(s.source == "phone.roll" and s.target == "x360.btn_a" for s in sugg)


# 4. apply_suggestions 正确创建 GraphEdge（origin=auto, confidence 保留）
def test_apply_creates_auto_edge_with_confidence():
    sources, targets = _sources_and_targets()
    router = AutoRouter()
    sugg = router.discover(sources, targets)

    graph = CapabilityGraph()
    added = router.apply_suggestions(graph, sugg)
    assert added == 1

    edges = graph.get_edges_for_source("phone.roll")
    assert len(edges) == 1
    edge = edges[0]
    assert edge.target == "x360.right_x"
    assert edge.origin == "auto"
    # confidence 应等于 discover 给出的 score
    sugg_score = next(
        s.score for s in sugg if s.source == "phone.roll" and s.target == "x360.right_x"
    )
    assert edge.confidence == sugg_score


# 5. 已有 edge 不会重复添加
def test_existing_edge_not_duplicated():
    sources, targets = _sources_and_targets()
    router = AutoRouter()
    sugg = router.discover(sources, targets)

    graph = CapabilityGraph()
    # 预先已存在一条（例如用户手动）相同连接
    graph.add_edge(GraphEdge(
        source="phone.roll", target="x360.right_x",
        origin="manual", confidence=1.0,
    ))
    added = router.apply_suggestions(graph, sugg)
    # 不应再新增
    assert added == 0
    edges = graph.get_edges_for_source("phone.roll")
    assert len(edges) == 1
    # 且保留原 manual 边（不被覆盖）
    assert edges[0].origin == "manual"


# 5b. 重复 apply 同批 suggestion 幂等
def test_repeated_apply_idempotent():
    sources, targets = _sources_and_targets()
    router = AutoRouter()
    sugg = router.discover(sources, targets)

    graph = CapabilityGraph()
    first = router.apply_suggestions(graph, sugg)
    second = router.apply_suggestions(graph, sugg)
    assert first == 1
    assert second == 0
    assert len(graph.get_edges_for_source("phone.roll")) == 1


# 6. capability id 仍为字符串，无 enum
def test_no_enum_ids():
    import enum

    sources, targets = _sources_and_targets()
    router = AutoRouter()
    sugg = router.discover(sources, targets)
    for s in sugg:
        assert isinstance(s.source, str)
        assert isinstance(s.target, str)
        assert not isinstance(s.source, enum.Enum)
    # Suggestion 也可序列化（to_dict）
    assert all(isinstance(s.to_dict(), dict) for s in sugg)
