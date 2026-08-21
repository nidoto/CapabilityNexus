"""Solution Runtime Integration（V1.9 Phase 11）。

把 Solution 体系与 MappingEngine 接通：**只消费 Solution，不改 Graph、不碰 GUI**。

职责：
- SolutionRuntime 持有 MappingEngine 引用（与 Phase 4 一致，mapping 仍由
  MappingEngine 执行），并可持有 SolutionManager（active 指针来源）。
- activate(solution_id)：经 Manager 设定 active，再把 active Solution 的
  to_mapping_dict() 喂给 MappingEngine.load_mappings(...)。
- 因为 MappingEngine.load_mappings 是"整体替换"，连续 activate(A) 再 activate(B)
  后，引擎中只保留 B（A 被替换）——满足"最终 mapping 仅含 B"。
- Runtime **不修改 Graph**：它只读 Solution / Manager，绝不增删 Graph 的边或节点。
- capability id 保持字符串，无 enum。

边界（不修改已有分层）：
- 不接 GUI；
- 不重新设计架构；
- 不执行任何未在 MappingEngine 中定义的内部逻辑（只调用公开的 load_mappings）。
"""

from typing import Optional

from core.capability_solution import CapabilitySolution
from core.solution_manager import SolutionManager
from mapping.mapper import MappingEngine


class SolutionRuntime:
    """Solution -> MappingEngine 的接线层（仅消费 Solution）。"""

    def __init__(
        self,
        mapping_engine: MappingEngine,
        manager: Optional[SolutionManager] = None,
    ):
        self._engine = mapping_engine
        self._manager = manager

    # ------------------------------------------------------------------
    # 应用单个 Solution（不改 Graph）
    # ------------------------------------------------------------------
    def apply_solution(self, solution: CapabilitySolution) -> None:
        """把指定 Solution 的 mapping dict 喂给 MappingEngine。

        只调用公开的 load_mappings；不触碰 Graph。
        """
        self._engine.load_mappings(solution.to_mapping_dict())

    # ------------------------------------------------------------------
    # 经 Manager 激活并接线
    # ------------------------------------------------------------------
    def activate(self, solution_id: str) -> None:
        """设定 active（经 Manager）并把 active Solution 应用到引擎。

        activate(A) 再 activate(B) -> 引擎最终只含 B（load_mappings 整体替换）。
        """
        if self._manager is None:
            raise RuntimeError("SolutionRuntime 未绑定 SolutionManager")
        self._manager.activate(solution_id)
        active = self._manager.active_solution()
        if active is not None:
            self.apply_solution(active)

    def apply_active(self) -> None:
        """把当前 Manager 的 active Solution 应用到引擎（不切换 active）。"""
        if self._manager is None:
            return
        active = self._manager.active_solution()
        if active is not None:
            self.apply_solution(active)

    def deactivate(self) -> None:
        """清除 active 并清空引擎 mapping。"""
        if self._manager is not None:
            self._manager.deactivate()
        self._engine.load_mappings({})
