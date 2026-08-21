"""SolutionWorkflow 测试（V1.9 Phase 12）。

覆盖工作流编排链：
  1. discover 接收 AutoRouter 结果并落到 Graph。
  2. select / deselect 用户选择连接。
  3. create_draft 基于选择创建 Solution 草稿（注册为 draft）。
  4. confirm 把草稿确认为 accepted。
  5. activate 经 Manager（+Runtime）激活并接通 MappingEngine。
  6. Graph 在 activate 后不被工作流改动（只消费/编排）。
  7. capability id 保持字符串，无 enum。

不实现 GUI（Phase 13）；仅验证编程接口与链路正确性。
"""

import enum
import tempfile

from core.capability_definition import CapabilityDefinition
from core.capability_graph import CapabilityGraph, GraphEdge
from core.capability_solution import STATUS_ACCEPTED, STATUS_DRAFT
from core.solution_manager import SolutionManager
from core.solution_store import SolutionStore
from core.solution_runtime import SolutionRuntime
from core.auto_router import AutoRouter
from core.solution_workflow import SolutionWorkflow
from core.event_bus import EventBus
from mapping.mapper import MappingEngine


def _def(cap_id, value_type="float", category="misc"):
    return CapabilityDefinition(id=cap_id, value_type=value_type, category=category)


def _build():
    graph = CapabilityGraph()
    mgr = SolutionManager(store=SolutionStore(directory=tempfile.mkdtemp(prefix="cnx_wf_")))
    engine = MappingEngine(EventBus())
    runtime = SolutionRuntime(engine, manager=mgr)
    wf = SolutionWorkflow(graph, AutoRouter(), mgr, runtime)
    sources = [
        _def("phone.roll", "float", "motion"),
        _def("phone.pitch", "float", "motion"),
        _def("mic.audio", "audio", "sensor"),  # 不兼容
    ]
    targets = [
        _def("x360.left_x", "float", "axis"),
        _def("x360.right_y", "float", "axis"),
        _def("x360.btn_a", "bool", "button"),
    ]
    return wf, graph, mgr, engine


# 1. discover 接收结果并落到 Graph
def test_discover_lands_on_graph():
    wf, graph, _, _ = _build()
    sugg = wf.discover(
        [_def("phone.roll", "float", "motion"), _def("mic.audio", "audio", "sensor")],
        [_def("x360.left_x", "float", "axis")],
    )
    # mic.audio 不兼容 -> 不应出现在建议中
    assert all(s.source != "mic.audio" for s in sugg)
    # 建议应落到 Graph（至少含 phone.roll -> x360.left_x）
    edges = {(e.source, e.target) for e in graph.list_edges()}
    assert ("phone.roll", "x360.left_x") in edges


# 2. select / deselect
def test_select_and_deselect():
    wf, _, _, _ = _build()
    wf.select("phone.roll", "x360.left_x")
    wf.select("phone.pitch", "x360.right_y")
    assert ("phone.roll", "x360.left_x") in wf.get_selection()
    assert ("phone.pitch", "x360.right_y") in wf.get_selection()
    wf.deselect("phone.roll", "x360.left_x")
    assert ("phone.roll", "x360.left_x") not in wf.get_selection()
    assert len(wf.get_selection()) == 1


# 3. create_draft 创建草稿并注册
def test_create_draft_registers_draft():
    wf, graph, mgr, _ = _build()
    wf.discover(
        [_def("phone.roll", "float", "motion"), _def("phone.pitch", "float", "motion")],
        [_def("x360.left_x", "float", "axis"), _def("x360.right_y", "float", "axis")],
    )
    wf.select("phone.roll", "x360.left_x")
    wf.select("phone.pitch", "x360.right_y")
    sid = wf.create_draft("my-solution")
    assert sid != ""

    sol = mgr.get(sid)
    assert sol is not None
    assert sol.status == STATUS_DRAFT
    # 草稿仅含所选两条边
    pairs = {(e.source, e.target) for e in sol.list_edges()}
    assert pairs == {("phone.roll", "x360.left_x"), ("phone.pitch", "x360.right_y")}


# 4. confirm 把草稿确认为 accepted
def test_confirm_moves_to_accepted():
    wf, _, mgr, _ = _build()
    wf.discover(
        [_def("phone.roll", "float", "motion")],
        [_def("x360.left_x", "float", "axis")],
    )
    wf.select("phone.roll", "x360.left_x")
    sid = wf.create_draft("draft-a")
    wf.confirm(sid)
    assert mgr.get(sid).status == STATUS_ACCEPTED


# 5. activate 经 Manager + Runtime 接通引擎
def test_activate_wires_runtime():
    wf, _, mgr, engine = _build()
    wf.discover(
        [_def("phone.roll", "float", "motion")],
        [_def("x360.left_x", "float", "axis")],
    )
    wf.select("phone.roll", "x360.left_x")
    sid = wf.create_draft("activate-a")
    wf.confirm(sid)
    wf.activate(sid)

    # 引擎最终只含该 solution 的映射
    assert "phone.roll" in engine.mapping
    assert engine.mapping["phone.roll"][0]["target"] == "x360.left_x"
    assert mgr.active_id() == sid


# 6. activate 不修改 Graph
def test_workflow_activate_does_not_modify_graph():
    wf, graph, _, _ = _build()
    wf.discover(
        [_def("phone.roll", "float", "motion"), _def("phone.pitch", "float", "motion")],
        [_def("x360.left_x", "float", "axis"), _def("x360.right_y", "float", "axis")],
    )
    before = len(graph.list_edges())
    wf.select("phone.roll", "x360.left_x")
    sid = wf.create_draft("g-a")
    wf.confirm(sid)
    wf.activate(sid)
    # 激活步骤本身不改动 Graph 边数量
    assert len(graph.list_edges()) == before


# 7. capability id 保持字符串，无 enum
def test_no_enum_ids():
    wf, _, _, _ = _build()
    wf.select("phone.roll", "x360.left_x")
    assert isinstance("phone.roll", str)
    # 工作流链路中所有 id 均为字符串
    for s, t in wf.get_selection():
        assert isinstance(s, str) and isinstance(t, str)
        assert not isinstance(s, enum.Enum)
