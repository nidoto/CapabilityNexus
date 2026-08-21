"""SolutionRuntime 测试（V1.9 Phase 11）。

覆盖：
  1. activate(A) 再 activate(B) -> MappingEngine 最终只含 B（A 被替换）。
  2. Runtime 不修改 Graph：激活前后 Graph 边数量不变（Runtime 只消费 Solution）。
  3. capability id 保持字符串，无 enum。
"""

import enum
import tempfile

from core.capability_graph import CapabilityGraph, GraphEdge
from core.capability_solution import CapabilitySolution
from core.solution_manager import SolutionManager
from core.solution_store import SolutionStore
from core.solution_runtime import SolutionRuntime
from core.event_bus import EventBus
from mapping.mapper import MappingEngine


def _tmp_manager():
    d = tempfile.mkdtemp(prefix="cnx_rt_")
    return SolutionManager(store=SolutionStore(directory=d))


def _engine():
    return MappingEngine(EventBus())


# 1. activate(A) 再 activate(B) -> 引擎最终只含 B
def test_activate_a_then_b_leaves_only_b():
    mgr = _tmp_manager()
    engine = _engine()
    runtime = SolutionRuntime(engine, manager=mgr)

    sol_a = CapabilitySolution("A")
    sol_a.add_edge(GraphEdge("phone.roll", "x360.left_x"))
    mgr.register(sol_a, "A")

    sol_b = CapabilitySolution("B")
    sol_b.add_edge(GraphEdge("phone.pitch", "x360.right_y"))
    mgr.register(sol_b, "B")

    runtime.activate("A")
    assert "phone.roll" in engine.mapping
    assert "phone.pitch" not in engine.mapping

    runtime.activate("B")
    # A 被整体替换，仅剩 B
    assert "phone.pitch" in engine.mapping
    assert "phone.roll" not in engine.mapping
    assert engine.mapping["phone.pitch"][0]["target"] == "x360.right_y"


# 2. Runtime 不修改 Graph：激活前后边数量不变
def test_runtime_does_not_modify_graph():
    graph = CapabilityGraph()
    graph.add_edge(GraphEdge("phone.roll", "x360.left_x"))
    graph.add_edge(GraphEdge("phone.pitch", "x360.right_y"))
    n_before = len(graph.list_edges())
    assert n_before == 2

    mgr = _tmp_manager()
    engine = _engine()
    runtime = SolutionRuntime(engine, manager=mgr)

    sol_a = CapabilitySolution.from_graph(graph, [("phone.roll", "x360.left_x")], name="A")
    mgr.register(sol_a, "A")
    sol_b = CapabilitySolution.from_graph(graph, [("phone.pitch", "x360.right_y")], name="B")
    mgr.register(sol_b, "B")

    runtime.activate("A")
    runtime.activate("B")

    # Graph 边数量应保持不变（Runtime 只消费 Solution，不碰 Graph）
    assert len(graph.list_edges()) == n_before
    # 且 Graph 的边内容未被改动
    targets = {e.target for e in graph.list_edges()}
    assert "x360.left_x" in targets
    assert "x360.right_y" in targets


# 3. capability id 保持字符串，无 enum
def test_capability_ids_are_strings():
    mgr = _tmp_manager()
    engine = _engine()
    runtime = SolutionRuntime(engine, manager=mgr)

    sol_a = CapabilitySolution("A")
    sol_a.add_edge(GraphEdge("phone.roll", "x360.left_x"))
    mgr.register(sol_a, "A")
    runtime.activate("A")

    # MappingEngine 中的 source / target 均为字符串
    for source, items in engine.mapping.items():
        assert isinstance(source, str)
        assert not isinstance(source, enum.Enum)
        for item in items:
            assert isinstance(item["target"], str)
            assert not isinstance(item["target"], enum.Enum)
