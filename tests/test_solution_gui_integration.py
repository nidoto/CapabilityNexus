"""Solution GUI Integration 测试（V1.9 Phase 14）。

验证 Phase 14 的"最小接线"：app.py 装配 Solution 栈并注入 GUI，GUI 的
SolutionPanel 使用注入的 controller，且用户操作经由 controller 驱动
SolutionWorkflow -> Manager -> Runtime -> MappingEngine。

测试策略（不实例化完整 CapabilityNexusApp，避免重型副作用/挂起）：
  - 通过 app._build_solution_stack(fake_app) 验证 app 层装配与注入；
  - 用真实（隐藏）Tk 根实例化 SolutionPanel，验证面板构建与注入 controller；
  - 经 controller（面板持有的同一实例）驱动 discover/select/draft/confirm/
    activate 全流程，验证引擎与 Manager 状态正确、Graph 不被改动、id 为字符串。

不修改任何核心文件。
"""

import types
import tempfile

import pytest

from core.capability_definition import CapabilityDefinition
from core.capability_graph import CapabilityGraph
from core.solution_manager import SolutionManager
from core.solution_store import SolutionStore
from core.solution_runtime import SolutionRuntime
from core.auto_router import AutoRouter
from core.solution_workflow import SolutionWorkflow
from core.solution_ui_model import SolutionController
from core.event_bus import EventBus
from mapping.mapper import MappingEngine

import app as app_module

# 仅在测试函数内导入 tkinter（避免无显示环境下模块加载问题）
tk = None
ttk = None


def _tk_root_or_skip():
    """尝试创建隐藏 Tk 根；无显示环境（headless CI）则 skip。"""
    import tkinter as _tk
    try:
        root = _tk.Tk()
        root.withdraw()
    except Exception as exc:  # 无显示 / tk 未正确安装
        pytest.skip(f"no display for tkinter: {exc}")
    return _tk, root


def _def(cap_id, value_type="float", category="misc"):
    return CapabilityDefinition(id=cap_id, value_type=value_type, category=category)


def _make_stack():
    """构建一套真实 Solution 栈（与 app._build_solution_stack 同构，用于面板驱动）。"""
    graph = CapabilityGraph()
    mgr = SolutionManager(store=SolutionStore(directory=tempfile.mkdtemp(prefix="cnx_int_")))
    engine = MappingEngine(EventBus())
    runtime = SolutionRuntime(engine, manager=mgr)
    wf = SolutionWorkflow(graph, AutoRouter(), mgr, runtime)
    ctrl = SolutionController(wf)
    return graph, mgr, engine, wf, ctrl


# ----------------------------------------------------------------------
# 1. GUI 可以创建 SolutionPanel（真实 Tk 根，隐藏）
# ----------------------------------------------------------------------
def test_gui_can_create_solution_panel():
    _tk, root = _tk_root_or_skip()
    try:
        parent = _tk.Frame(root)
        from tools.solution_gui import SolutionPanel

        _, _, _, _, ctrl = _make_stack()
        panel = SolutionPanel(
            parent, ctrl,
            source_provider=lambda: [], target_provider=lambda: [],
        )
        assert isinstance(panel, SolutionPanel)
    finally:
        root.destroy()


# ----------------------------------------------------------------------
# 2. Panel 使用注入的 workflow/controller
# ----------------------------------------------------------------------
def test_panel_uses_injected_controller():
    _tk, root = _tk_root_or_skip()
    try:
        parent = _tk.Frame(root)
        from tools.solution_gui import SolutionPanel

        _, _, _, _, ctrl = _make_stack()
        panel = SolutionPanel(parent, ctrl, lambda: [], lambda: [])
        # 面板持有被注入的同一个 controller（其内即 workflow）
        assert panel.controller is ctrl
        assert panel.controller._workflow is ctrl._workflow
    finally:
        root.destroy()


# ----------------------------------------------------------------------
# 3. 用户选择调用 workflow.select()
# ----------------------------------------------------------------------
def test_user_selection_calls_workflow_select():
    _, _, _, wf, ctrl = _make_stack()
    ctrl.toggle("phone.roll", "x360.left_x")
    assert ("phone.roll", "x360.left_x") in wf.get_selection()
    # 再次 toggle 取消
    ctrl.toggle("phone.roll", "x360.left_x")
    assert ("phone.roll", "x360.left_x") not in wf.get_selection()


# ----------------------------------------------------------------------
# 4. Create Draft -> manager 中出现 draft
# ----------------------------------------------------------------------
def test_create_draft_in_manager():
    graph, mgr, _, wf, ctrl = _make_stack()
    wf.discover(
        [_def("phone.roll", "float", "motion")],
        [_def("x360.left_x", "float", "axis")],
    )
    ctrl.set_selected([("phone.roll", "x360.left_x")])
    sid = ctrl.create_draft("gui-sol")
    assert sid != ""
    assert mgr.get(sid) is not None
    assert mgr.get(sid).status == "draft"


# ----------------------------------------------------------------------
# 5. Confirm -> draft -> accepted
# ----------------------------------------------------------------------
def test_confirm_to_accepted():
    graph, mgr, _, wf, ctrl = _make_stack()
    wf.discover(
        [_def("phone.roll", "float", "motion")],
        [_def("x360.left_x", "float", "axis")],
    )
    ctrl.set_selected([("phone.roll", "x360.left_x")])
    sid = ctrl.create_draft("gui-sol")
    ctrl.confirm(sid)
    assert mgr.get(sid).status == "accepted"


# ----------------------------------------------------------------------
# 6. Activate -> MappingEngine 获得正确 mapping
# ----------------------------------------------------------------------
def test_activate_engine_mapping():
    graph, mgr, engine, wf, ctrl = _make_stack()
    wf.discover(
        [_def("phone.roll", "float", "motion")],
        [_def("x360.left_x", "float", "axis")],
    )
    ctrl.set_selected([("phone.roll", "x360.left_x")])
    sid = ctrl.create_draft("gui-sol")
    ctrl.confirm(sid)
    ctrl.activate(sid)

    assert "phone.roll" in engine.mapping
    assert engine.mapping["phone.roll"][0]["target"] == "x360.left_x"
    assert mgr.active_id() == sid


# ----------------------------------------------------------------------
# 7. Activate 前后 Graph edge count 不变
# ----------------------------------------------------------------------
def test_activate_does_not_modify_graph():
    graph, mgr, engine, wf, ctrl = _make_stack()
    wf.discover(
        [_def("phone.roll", "float", "motion"), _def("phone.pitch", "float", "motion")],
        [_def("x360.left_x", "float", "axis"), _def("x360.right_y", "float", "axis")],
    )
    n = len(graph.list_edges())
    ctrl.set_selected([("phone.roll", "x360.left_x")])
    sid = ctrl.create_draft("gui-sol")
    ctrl.confirm(sid)
    ctrl.activate(sid)
    # 激活步骤（GUI 层）不改动 Graph 边数量
    assert len(graph.list_edges()) == n


# ----------------------------------------------------------------------
# 8. capability id 保持 str，禁止 enum
# ----------------------------------------------------------------------
def test_capability_ids_are_strings():
    import enum

    _, _, _, wf, ctrl = _make_stack()
    ctrl.toggle("phone.roll", "x360.left_x")
    for s, t in wf.get_selection():
        assert isinstance(s, str) and isinstance(t, str)
        assert not isinstance(s, enum.Enum)


# ----------------------------------------------------------------------
# app.py 装配与注入验证（不构造完整 CapabilityNexusApp）
# ----------------------------------------------------------------------
def test_app_builds_solution_stack():
    """app._build_solution_stack 装配并暴露 workflow/controller（复用传入引擎）。"""
    fake = types.SimpleNamespace(
        mapping_engine=MappingEngine(EventBus()),
        event_bus=EventBus(),
    )
    wf, ctrl = app_module.CapabilityNexusApp._build_solution_stack(fake)
    assert isinstance(wf, SolutionWorkflow)
    assert isinstance(ctrl, SolutionController)
    # controller 内部 workflow 与返回的一致
    assert ctrl._workflow is wf
    # runtime 已被绑定到传入的 mapping_engine（不复建）
    assert wf._runtime._engine is fake.mapping_engine
