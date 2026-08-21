"""Solution UI Layer 测试（V1.9 Phase 13）。

覆盖（均不依赖 Tk；GUI 面板逻辑由 SolutionController + 模型层承载，可被 pytest 直测）：
  1. Suggestion 可转换为 GUI model（SolutionCandidateView）。
  2. GUI 选择调用 workflow.select（经 controller.toggle）。
  3. Create draft 后：manager.get(id) 存在且 status == "draft"。
  4. Confirm 后：status == "accepted"。
  5. Activate 后：MappingEngine mapping 正确。
  6. GUI 层不修改 Graph：激活前后 graph edge count 不变。
  7. capability id 为 string（type(source)==str, type(target)==str），无 enum。

不修改任何核心文件；不引入 GUI 依赖到测试中（不 import tkinter）。
"""

import enum
import tempfile

from core.capability_definition import CapabilityDefinition
from core.capability_graph import CapabilityGraph
from core.solution_manager import SolutionManager
from core.solution_store import SolutionStore
from core.solution_runtime import SolutionRuntime
from core.auto_router import AutoRouter, Suggestion
from core.solution_workflow import SolutionWorkflow
from core.solution_ui_model import (
    SolutionController,
    candidate_from_suggestion,
    candidates_from_suggestions,
    SolutionCandidateView,
    STATUS_DRAFT_STR,
)
from core.event_bus import EventBus
from mapping.mapper import MappingEngine


def _def(cap_id, value_type="float", category="misc"):
    return CapabilityDefinition(id=cap_id, value_type=value_type, category=category)


def _build():
    graph = CapabilityGraph()
    mgr = SolutionManager(store=SolutionStore(directory=tempfile.mkdtemp(prefix="cnx_ui_")))
    engine = MappingEngine(EventBus())
    runtime = SolutionRuntime(engine, manager=mgr)
    wf = SolutionWorkflow(graph, AutoRouter(), mgr, runtime)
    ctrl = SolutionController(wf)
    return wf, ctrl, graph, mgr, engine


# 1. Suggestion -> GUI model
def test_suggestion_to_candidate_view():
    sug = Suggestion("phone.roll", "x360.left_x", 0.92)
    view = candidate_from_suggestion(sug, selected=True)
    assert isinstance(view, SolutionCandidateView)
    assert view.source == "phone.roll"
    assert view.target == "x360.left_x"
    assert view.score == 0.92
    assert view.selected is True

    # 批量转换 + selected 标记
    views = candidates_from_suggestions(
        [sug, Suggestion("phone.pitch", "x360.right_y", 0.88)],
        selected_pairs=[("phone.roll", "x360.left_x")],
    )
    assert views[0].selected is True
    assert views[1].selected is False


# 2. GUI 选择调用 workflow.select（经 controller.toggle）
def test_gui_selection_calls_workflow_select():
    wf, ctrl, _, _, _ = _build()
    # controller 包装 workflow.select/deselect
    ctrl.toggle("phone.roll", "x360.left_x")
    assert ("phone.roll", "x360.left_x") in wf.get_selection()
    # 再次 toggle 取消
    ctrl.toggle("phone.roll", "x360.left_x")
    assert ("phone.roll", "x360.left_x") not in wf.get_selection()


# 3. Create draft -> manager 中存在且 status == draft
def test_create_draft_status_draft():
    wf, ctrl, graph, mgr, _ = _build()
    wf.discover(
        [_def("phone.roll", "float", "motion")],
        [_def("x360.left_x", "float", "axis")],
    )
    ctrl.set_selected([("phone.roll", "x360.left_x")])
    sid = ctrl.create_draft("ui-sol")
    assert sid != ""
    sol = mgr.get(sid)
    assert sol is not None
    assert sol.status == STATUS_DRAFT_STR


# 4. Confirm -> accepted
def test_confirm_status_accepted():
    wf, ctrl, graph, mgr, _ = _build()
    wf.discover(
        [_def("phone.roll", "float", "motion")],
        [_def("x360.left_x", "float", "axis")],
    )
    ctrl.set_selected([("phone.roll", "x360.left_x")])
    sid = ctrl.create_draft("ui-sol")
    ctrl.confirm(sid)
    assert mgr.get(sid).status == "accepted"


# 5. Activate -> MappingEngine mapping 正确
def test_activate_engine_mapping():
    wf, ctrl, graph, mgr, engine = _build()
    wf.discover(
        [_def("phone.roll", "float", "motion")],
        [_def("x360.left_x", "float", "axis")],
    )
    ctrl.set_selected([("phone.roll", "x360.left_x")])
    sid = ctrl.create_draft("ui-sol")
    ctrl.confirm(sid)
    ctrl.activate(sid)

    assert "phone.roll" in engine.mapping
    assert engine.mapping["phone.roll"][0]["target"] == "x360.left_x"
    assert mgr.active_id() == sid


# 6. GUI 层不修改 Graph：激活前后 edge count 不变
def test_gui_activate_does_not_modify_graph():
    wf, ctrl, graph, mgr, engine = _build()
    wf.discover(
        [_def("phone.roll", "float", "motion"), _def("phone.pitch", "float", "motion")],
        [_def("x360.left_x", "float", "axis"), _def("x360.right_y", "float", "axis")],
    )
    # 发现后 Graph 已有候选边；记录此时数量
    n_after_discover = len(graph.list_edges())
    ctrl.set_selected([("phone.roll", "x360.left_x")])
    sid = ctrl.create_draft("ui-sol")
    ctrl.confirm(sid)
    ctrl.activate(sid)
    # 激活步骤（GUI 层）不改动 Graph 边数量
    assert len(graph.list_edges()) == n_after_discover


# 7. capability id 是 string，无 enum
def test_capability_ids_are_strings():
    wf, ctrl, _, _, _ = _build()
    ctrl.toggle("phone.roll", "x360.left_x")
    for s, t in wf.get_selection():
        assert isinstance(s, str) and isinstance(t, str)
        assert not isinstance(s, enum.Enum)
    # candidate view 字段也是字符串
    view = candidate_from_suggestion(Suggestion("phone.roll", "x360.left_x", 0.9))
    assert isinstance(view.source, str)
    assert isinstance(view.target, str)
