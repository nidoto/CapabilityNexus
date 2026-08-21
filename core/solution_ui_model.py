"""Solution UI Model Layer（V1.9 Phase 13）。

把底层能力链（Suggestion / CapabilitySolution / SolutionManager）转换为
**GUI 可显示结构**，并提供不含 Tk 的纯逻辑控制器，供 GUI 面板调用。

设计边界（不修改已有分层、不触碰核心能力链）：
- 本模块**不依赖 Tk / Qt**：只做数据结构转换 + 对 SolutionWorkflow 的薄封装，
  因此可被 pytest 直接测试，无需 GUI 环境。
- GUI 面板（tools/solution_gui.py）只读取这里的 View 结构、调用 Controller 的方法；
  不直接访问 Graph 内部、不直接调用 MappingEngine。
- capability id 保持字符串，无 enum。
- 控制器仅调用 SolutionWorkflow 的公开接口（select/deselect/create_draft/
  confirm/activate），不自行改动 Graph 或 Solution。

View 结构（与 GUI 解耦的纯数据）：
  SolutionCandidateView: {source, target, score, selected}
  SolutionStatusView:    {id, name, status, edges:[...]}
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from core.auto_router import Suggestion
from core.capability_graph import CapabilityGraph
from core.capability_solution import (
    CapabilitySolution,
    STATUS_ACTIVE,
    STATUS_ACCEPTED,
    STATUS_DRAFT,
)
from core.solution_manager import SolutionManager
from core.solution_workflow import SolutionWorkflow

# 暴露给 GUI/测试的状态字符串（与 CapabilitySolution 保持一致，避免魔法串散落）。
STATUS_DRAFT_STR = STATUS_DRAFT
STATUS_ACCEPTED_STR = STATUS_ACCEPTED
STATUS_ACTIVE_STR = STATUS_ACTIVE


# ----------------------------------------------------------------------
# View 结构（GUI 只读）
# ----------------------------------------------------------------------
@dataclass
class SolutionCandidateView:
    """一条发现结果在 GUI 中的展示结构。"""

    source: str
    target: str
    score: float
    selected: bool = False

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "score": self.score,
            "selected": self.selected,
        }


@dataclass
class SolutionStatusView:
    """一个 Solution 在 GUI 中的展示结构。"""

    id: str
    name: str
    status: str
    edges: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "edges": self.edges,
        }


# ----------------------------------------------------------------------
# 转换函数
# ----------------------------------------------------------------------
def candidate_from_suggestion(sug: Suggestion, selected: bool = False) -> SolutionCandidateView:
    """Suggestion -> SolutionCandidateView。"""
    return SolutionCandidateView(
        source=sug.source,
        target=sug.target,
        score=sug.score,
        selected=selected,
    )


def candidates_from_suggestions(
    suggestions: List[Suggestion],
    selected_pairs: List[Tuple[str, str]] = None,
) -> List[SolutionCandidateView]:
    """一组 Suggestion -> GUI 候选列表（按 selected_pairs 标记勾选）。"""
    selected_pairs = selected_pairs or []
    sel = set(selected_pairs)
    return [
        candidate_from_suggestion(s, (s.source, s.target) in sel)
        for s in suggestions
    ]


def status_views_from_manager(manager: SolutionManager) -> List[SolutionStatusView]:
    """SolutionManager 中的全部 Solution -> GUI 状态列表。"""
    views: List[SolutionStatusView] = []
    for sid, solution, _meta in manager.list_all():
        views.append(_status_view(sid, solution))
    return views


def _status_view(sid: str, solution: CapabilitySolution) -> SolutionStatusView:
    edges = [
        {
            "source": e.source,
            "target": e.target,
            "gain": e.gain,
            "origin": e.origin,
            "confidence": e.confidence,
        }
        for e in solution.list_edges()
    ]
    return SolutionStatusView(
        id=sid,
        name=solution.name,
        status=solution.status,
        edges=edges,
    )


# ----------------------------------------------------------------------
# 控制器（不含 Tk）：GUI 面板调用它，由它驱动 SolutionWorkflow
# ----------------------------------------------------------------------
class SolutionController:
    """GUI 与 SolutionWorkflow 之间的薄封装（无 GUI 依赖，可单测）。

    职责：把 GUI 的"发现 / 勾选 / 建草稿 / 确认 / 激活"动作翻译成对
    SolutionWorkflow 的调用。自身不持有 Graph 状态、不修改核心能力链。
    """

    def __init__(self, workflow: SolutionWorkflow):
        self._workflow = workflow

    # 1. 发现
    def run_discovery(
        self,
        sources: List[Any],
        targets: List[Any],
    ) -> List[SolutionCandidateView]:
        """调用 workflow.discover，返回可显示的候选列表。"""
        suggestions = self._workflow.discover(sources, targets)
        return candidates_from_suggestions(suggestions, self._workflow.get_selection())

    # 2. 选择（勾选 / 取消）
    def toggle(self, source: str, target: str) -> bool:
        """勾选切换：已选则取消（deselect），未选则选择（select）。

        返回切换后是否处于"已选"状态。
        """
        if (source, target) in self._workflow.get_selection():
            self._workflow.deselect(source, target)
            return False
        self._workflow.select(source, target)
        return True

    def set_selected(self, pairs: List[Tuple[str, str]]) -> None:
        self._workflow.set_selection(pairs)

    # 3. 创建草稿
    def create_draft(self, name: str = None) -> str:
        return self._workflow.create_draft(name)

    # 4. 确认
    def confirm(self, solution_id: str) -> None:
        self._workflow.confirm(solution_id)

    # 5. 激活
    def activate(self, solution_id: str) -> None:
        self._workflow.activate(solution_id)

    # 读取状态（供 GUI 刷新）
    def candidates(self) -> List[SolutionCandidateView]:
        return candidates_from_suggestions(
            self._workflow.get_suggestions(), self._workflow.get_selection()
        )

    def statuses(self) -> List[SolutionStatusView]:
        return status_views_from_manager(self._workflow._manager)

    def get_solution_status(self, solution_id: str) -> str:
        sol = self._workflow._manager.get(solution_id)
        return sol.status if sol is not None else ""
