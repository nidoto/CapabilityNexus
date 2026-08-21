"""Solution Workflow Layer（V1.9 Phase 12）。

把既有分层串成一条**工作流**（不实现 GUI，GUI 留给 Phase 13）：

    AutoRouter          (Phase 8: 发现兼容连接建议)
        ↓
    SolutionWorkflow    (本层: 接收发现结果 / 用户选择 / 草稿 / 确认 / 注册 / 激活)
        ↓
    CapabilitySolution  (Phase 9: 选边 + 生命周期)
        ↓
    SolutionManager     (Phase 10: 运行时注册 + 持久化 + active 指针)
        ↓
    SolutionRuntime     (Phase 11: 激活并喂 MappingEngine)

本层职责（全部为"编排"，不新增底层逻辑）：
- 接收 AutoRouter 发现结果（discover），并可落到 Graph（apply_suggestions）；
- 提供用户选择连接的能力（select / deselect / set_selection）；
- 基于所选连接创建 Solution 草稿（create_draft，落到 Manager 为 draft）；
- 确认 Solution（confirm：draft -> accepted）；
- 注册 Solution（register，若尚未注册）；
- 激活 Solution（activate：经 Manager + 可选 Runtime 接通 MappingEngine）。

边界（不修改已有分层）：
- 不实现 GUI；只暴露编程接口，由 Phase 13 GUI 驱动；
- 不复制 Graph（Solution 仍只持有选中边子集）；
- capability id 保持字符串，无 enum；
- 不直接调用 MappingEngine 内部逻辑（仅经 SolutionRuntime 公开接口）。
"""

from typing import Dict, List, Optional, Tuple

from core.auto_router import AutoRouter, Suggestion
from core.capability_graph import CapabilityGraph
from core.capability_solution import CapabilitySolution, STATUS_ACCEPTED, STATUS_DRAFT
from core.solution_manager import SolutionManager
from core.solution_runtime import SolutionRuntime
from core.capability_definition import CapabilityDefinition


class SolutionWorkflow:
    """Solution 工作流编排层（AutoRouter -> Solution -> Manager -> Runtime）。"""

    def __init__(
        self,
        graph: CapabilityGraph,
        auto_router: AutoRouter,
        manager: SolutionManager,
        runtime: Optional[SolutionRuntime] = None,
    ):
        self._graph = graph
        self._auto_router = auto_router
        self._manager = manager
        self._runtime = runtime
        self._suggestions: List[Suggestion] = []
        self._selection: List[Tuple[str, str]] = []

    # ------------------------------------------------------------------
    # 1. 接收 AutoRouter 发现结果
    # ------------------------------------------------------------------
    def discover(
        self,
        sources: List[CapabilityDefinition],
        targets: List[CapabilityDefinition],
    ) -> List[Suggestion]:
        """运行 AutoRouter 发现兼容连接，并记录结果（同时落到 Graph 作为候选边）。

        返回兼容建议列表（供用户选择）。Graph 因此获得 origin="auto" 的候选边。
        """
        suggestions = self._auto_router.discover(sources, targets)
        self._suggestions = suggestions
        # 把建议落到 Graph（描述层），便于后续按 (source,target) 选边建 Solution。
        self._auto_router.apply_suggestions(self._graph, suggestions)
        return suggestions

    def get_suggestions(self) -> List[Suggestion]:
        return list(self._suggestions)

    # ------------------------------------------------------------------
    # 2. 用户选择连接的能力
    # ------------------------------------------------------------------
    def select(self, source: str, target: str) -> None:
        """选择一条连接（加入当前选择集）。"""
        if (source, target) not in self._selection:
            self._selection.append((source, target))

    def deselect(self, source: str, target: str) -> None:
        """取消选择一条连接。"""
        self._selection = [
            (s, t) for (s, t) in self._selection if not (s == source and t == target)
        ]

    def set_selection(self, pairs: List[Tuple[str, str]]) -> None:
        """整体设置当前选择集（替换）。"""
        self._selection = [(s, t) for (s, t) in pairs]

    def get_selection(self) -> List[Tuple[str, str]]:
        return list(self._selection)

    # ------------------------------------------------------------------
    # 3. 创建 Solution 草稿（基于所选连接，注册为 draft）
    # ------------------------------------------------------------------
    def create_draft(self, name: Optional[str] = None) -> str:
        """基于当前选择集，从 Graph 中选边构建 Solution 草稿并注册（draft）。

        返回 solution id。选择集为空时返回空字符串（不创建）。
        """
        if not self._selection:
            return ""
        solution = CapabilitySolution.from_graph(
            self._graph,
            self._selection,
            name=name or "workflow-draft",
            status=STATUS_DRAFT,
        )
        solution_id = self._manager.create(
            solution.name,
            edges=solution.list_edges(),
            metadata={"origin": "workflow", "source_graph": getattr(self._graph, "name", None)},
            status=STATUS_DRAFT,
        )
        return solution_id

    # ------------------------------------------------------------------
    # 4. 确认 Solution（draft -> accepted）
    # ------------------------------------------------------------------
    def confirm(self, solution_id: str) -> None:
        """把草稿确认为 accepted 状态（并落盘）。"""
        solution = self._manager.get(solution_id)
        if solution is None:
            raise KeyError(f"unknown solution: {solution_id}")
        solution.accept()
        self._manager.register(solution, solution_id, self._manager.metadata(solution_id))

    # ------------------------------------------------------------------
    # 5. 注册 Solution（若尚未在 Manager 中）
    # ------------------------------------------------------------------
    def register(self, solution: CapabilitySolution, solution_id: Optional[str] = None) -> str:
        """注册一个 Solution 到 Manager（内存 + 落盘）。返回 id。"""
        return self._manager.register(solution, solution_id or solution.name)

    # ------------------------------------------------------------------
    # 6. 激活 Solution（经 Manager（+ 可选 Runtime）接通 MappingEngine）
    # ------------------------------------------------------------------
    def activate(self, solution_id: str) -> None:
        """激活 Solution：经 Manager 设 active，并由 Runtime 接通 MappingEngine。

        若本工作流未绑定 Runtime，则仅经 Manager 设定 active（不接线引擎）。
        """
        if self._runtime is not None:
            self._runtime.activate(solution_id)
        else:
            self._manager.activate(solution_id)
