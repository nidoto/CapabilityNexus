"""CapabilityGraph 测试（V1.9 Phase 6）。

验证：
  1. node / edge 增删（含 remove_node 级联删边、重复边覆盖）。
  2. mapping roundtrip：to_mapping_dict / from_mapping_dict 可逆。
  3. graph -> mapping 与 MappingEngine 输入格式一致（target/gain/return_to_center）。
  4. JSON 序列化往返（节点/边元数据不丢）。
  5. origin / confidence 元数据在序列化与 mapping 生成中保留。
  6. 不引入 enum：capability id 保持字符串。
"""

from core.capability_graph import CapabilityGraph, GraphNode, GraphEdge


def _edge(src, tgt, **kw):
    return GraphEdge(source=src, target=tgt, **kw)


# ----------------------------------------------------------------------
# 1. node / edge 增删
# ----------------------------------------------------------------------
def test_add_and_remove_node_cascades_edges():
    g = CapabilityGraph()
    g.add_node(GraphNode("phone.roll", kind="source", role="input"))
    g.add_node(GraphNode("x360.right_x", kind="target", role="output"))
    g.add_edge(_edge("phone.roll", "x360.right_x"))

    assert len(g.list_nodes()) == 2
    assert len(g.get_edges_for_source("phone.roll")) == 1

    g.remove_node("phone.roll")
    assert g.get_node("phone.roll") is None
    # 关联边应被级联移除
    assert g.get_edges_for_source("phone.roll") == []
    assert len(g.list_edges()) == 0


def test_add_duplicate_edge_overwrites():
    g = CapabilityGraph()
    g.add_edge(_edge("a", "b", gain=1.0, origin="auto"))
    g.add_edge(_edge("a", "b", gain=2.0, origin="manual"))

    edges = g.get_edges_for_source("a")
    assert len(edges) == 1
    assert edges[0].gain == 2.0
    assert edges[0].origin == "manual"


def test_remove_edge_returns_whether_removed():
    g = CapabilityGraph()
    g.add_edge(_edge("a", "b"))
    assert g.remove_edge("a", "b") is True
    # 重复移除返回 False
    assert g.remove_edge("a", "b") is False


# ----------------------------------------------------------------------
# 2. mapping roundtrip
# ----------------------------------------------------------------------
def test_mapping_roundtrip():
    g = CapabilityGraph()
    g.add_edge(_edge("phone.roll", "x360.right_x", gain=0.5, return_to_center=True))
    g.add_edge(_edge("phone.gas", "x360.right_trigger", gain=1.0))

    mapping = g.to_mapping_dict()
    g2 = CapabilityGraph.from_mapping_dict(mapping)

    mapping2 = g2.to_mapping_dict()
    assert mapping2 == mapping
    # 边数一致
    assert len(g2.list_edges()) == 2


# ----------------------------------------------------------------------
# 3. graph -> mapping 与 MappingEngine 输入格式一致
# ----------------------------------------------------------------------
def test_graph_to_mapping_matches_mapping_engine_shape():
    g = CapabilityGraph()
    g.add_edge(_edge("phone.roll", "x360.right_x", gain=0.8, return_to_center=False))

    mapping = g.to_mapping_dict()
    # MappingEngine.load_mappings 接受的 key/字段形状：
    # { source: [ {target, gain, return_to_center}, ... ] }
    assert "phone.roll" in mapping
    items = mapping["phone.roll"]
    assert isinstance(items, list) and len(items) == 1
    item = items[0]
    assert item["target"] == "x360.right_x"
    assert item["gain"] == 0.8
    assert item["return_to_center"] is False
    # 不携带 Graph 专属元数据（MappingEngine 不识别 origin/confidence）
    assert "origin" not in item
    assert "confidence" not in item


# ----------------------------------------------------------------------
# 4. JSON 序列化
# ----------------------------------------------------------------------
def test_json_roundtrip_preserves_nodes_and_edges():
    g = CapabilityGraph()
    node = GraphNode(
        "phone.roll",
        kind="source",
        role="input",
        provider_type="phone",
        device_selector="dev-A",
    )
    g.add_node(node)
    g.add_node(GraphNode("x360.right_x", kind="target", role="output"))
    g.add_edge(_edge("phone.roll", "x360.right_x", gain=0.5))

    text = g.to_json()
    g2 = CapabilityGraph.from_json(text)

    n = g2.get_node("phone.roll")
    assert n is not None
    assert n.kind == "source"
    assert n.provider_type == "phone"
    assert n.device_selector == "dev-A"
    assert len(g2.get_edges_for_source("phone.roll")) == 1


# ----------------------------------------------------------------------
# 5. origin / confidence 保留
# ----------------------------------------------------------------------
def test_origin_and_confidence_preserved_in_json():
    g = CapabilityGraph()
    g.add_edge(_edge("a", "b", origin="auto", confidence=0.73))

    g2 = CapabilityGraph.from_json(g.to_json())
    edge = g2.get_edges_for_source("a")[0]
    assert edge.origin == "auto"
    assert edge.confidence == 0.73


def test_origin_and_confidence_excluded_from_mapping_dict():
    g = CapabilityGraph()
    g.add_edge(_edge("a", "b", origin="auto", confidence=0.9))

    item = g.to_mapping_dict()["a"][0]
    # mapping dict 只含 MappingEngine 需要的字段
    assert set(item.keys()) == {"target", "gain", "return_to_center"}


# ----------------------------------------------------------------------
# 6. 不引入 enum：capability id 保持字符串
# ----------------------------------------------------------------------
def test_no_enum_ids():
    import enum

    g = CapabilityGraph()
    g.add_edge(_edge("trainer.power", "x360.vibration"))
    for e in g.list_edges():
        assert isinstance(e.source, str)
        assert isinstance(e.target, str)
        assert not isinstance(e.source, enum.Enum)
