"""CapabilitySolution 测试（V1.9 Phase 9）。

覆盖：
  1. 创建 Solution（含从 Graph 选边，不复制整图）。
  2. add_edge / remove_edge。
  3. to_mapping_dict 与 MappingEngine 格式一致。
  4. JSON roundtrip（status + 选中边 + 元数据不丢）。
  5. status 生命周期：draft -> accepted -> active（不可回退）。
  6. auto/manual 元数据（origin / confidence）保留。
  7. capability id 是 string，无 enum。
"""

from core.capability_graph import CapabilityGraph, GraphEdge
from core.capability_solution import (
    CapabilitySolution,
    STATUS_DRAFT,
    STATUS_ACCEPTED,
    STATUS_ACTIVE,
)


def _build_graph():
    g = CapabilityGraph()
    g.add_edge(GraphEdge("phone.roll", "x360.left_x", gain=1.0, origin="auto", confidence=0.8))
    g.add_edge(GraphEdge("phone.roll", "x360.right_x", gain=0.5, origin="manual", confidence=1.0))
    return g


# 1. 创建 Solution（从 Graph 选边，不复制整图）
def test_create_solution_from_graph_subset():
    g = _build_graph()
    # 只选 phone.roll -> x360.left_x，不复制 right_x
    sol = CapabilitySolution.from_graph(
        g, [("phone.roll", "x360.left_x")], name="sol-a",
    )
    edges = sol.list_edges()
    assert len(edges) == 1
    assert edges[0].target == "x360.left_x"
    # 证明未复制整图：Graph 有 2 条边，Solution 仅 1 条
    assert len(g.list_edges()) == 2
    # 修改 Solution 不影响原 Graph
    sol.add_edge(GraphEdge("phone.roll", "x360.right_x"))
    assert len(g.list_edges()) == 2
    assert len(sol.list_edges()) == 2


# 2. add_edge / remove_edge
def test_add_and_remove_edge():
    sol = CapabilitySolution("sol-b")
    sol.add_edge(GraphEdge("phone.roll", "x360.left_x", gain=1.0))
    assert len(sol.list_edges()) == 1
    # 重复 add 同边覆盖，不增加数量
    sol.add_edge(GraphEdge("phone.roll", "x360.left_x", gain=0.6))
    assert len(sol.list_edges()) == 1
    assert sol.list_edges()[0].gain == 0.6

    assert sol.remove_edge("phone.roll", "x360.left_x") is True
    assert len(sol.list_edges()) == 0
    assert sol.remove_edge("phone.roll", "x360.left_x") is False


# 3. to_mapping_dict 与 MappingEngine 格式一致
def test_to_mapping_dict_matches_mapping_engine():
    g = _build_graph()
    sol = CapabilitySolution.from_graph(
        g, [("phone.roll", "x360.left_x")], name="sol-c",
    )
    mapping = sol.to_mapping_dict()
    assert "phone.roll" in mapping
    items = mapping["phone.roll"]
    assert isinstance(items, list) and len(items) == 1
    item = items[0]
    assert item["target"] == "x360.left_x"
    assert item["gain"] == 1.0
    # 仅含 MappingEngine 需要的字段
    assert set(item.keys()) == {"target", "gain", "return_to_center"}


# 4. JSON roundtrip
def test_json_roundtrip_preserves_state():
    g = _build_graph()
    sol = CapabilitySolution.from_graph(
        g, [("phone.roll", "x360.left_x")], name="sol-d", status=STATUS_ACCEPTED,
    )
    sol.source_graph = "main-graph"
    text = sol.to_json()
    sol2 = CapabilitySolution.from_json(text)

    assert sol2.name == "sol-d"
    assert sol2.status == STATUS_ACCEPTED
    assert sol2.source_graph == "main-graph"
    assert len(sol2.list_edges()) == 1
    assert sol2.list_edges()[0].target == "x360.left_x"


# 5. status 生命周期：draft -> accepted -> active
def test_status_lifecycle():
    sol = CapabilitySolution("sol-e", status=STATUS_DRAFT)
    assert sol.status == STATUS_DRAFT

    sol.accept()
    assert sol.status == STATUS_ACCEPTED

    sol.activate()
    assert sol.status == STATUS_ACTIVE

    # 不可回退
    import pytest
    with pytest.raises(ValueError):
        sol.set_status(STATUS_DRAFT)
    with pytest.raises(ValueError):
        sol.set_status("bogus")


# 6. auto/manual 元数据保留
def test_auto_manual_metadata_preserved():
    g = _build_graph()
    sol = CapabilitySolution.from_graph(
        g,
        [("phone.roll", "x360.left_x"), ("phone.roll", "x360.right_x")],
        name="sol-f",
    )
    by_target = {e.target: e for e in sol.list_edges()}
    # auto 边保留 origin/confidence
    assert by_target["x360.left_x"].origin == "auto"
    assert by_target["x360.left_x"].confidence == 0.8
    # manual 边保留 origin/confidence
    assert by_target["x360.right_x"].origin == "manual"
    assert by_target["x360.right_x"].confidence == 1.0

    # JSON 往返后仍保留
    sol2 = CapabilitySolution.from_json(sol.to_json())
    by_target2 = {e.target: e for e in sol2.list_edges()}
    assert by_target2["x360.left_x"].origin == "auto"
    assert by_target2["x360.left_x"].confidence == 0.8
    assert by_target2["x360.right_x"].origin == "manual"


# 7. capability id 是 string，无 enum
def test_no_enum_ids():
    import enum

    g = _build_graph()
    sol = CapabilitySolution.from_graph(g, [("phone.roll", "x360.left_x")], name="sol-g")
    for e in sol.list_edges():
        assert isinstance(e.source, str)
        assert isinstance(e.target, str)
        assert not isinstance(e.source, enum.Enum)
