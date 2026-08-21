"""Solution Manager（V1.9 Phase 10）。

CapabilitySolution 的**运行时注册表**：管理内存中的 Solution 集合、active 指针，
并把变更同步到 SolutionStore（落盘）。

职责：
- register / get / remove（从运行时注册表增删）。
- activate / deactivate：维护唯一 active 指针；删除 active solution 时清理该指针
  （状态清理，req 5）。
- combined_mapping_dict()：把当前 active 的 Solution 合并为 MappingEngine 兼容的
  mapping dict（仅聚合 Solution.to_mapping_dict()，不调用 MappingEngine 内部逻辑）。
- 不复制 Graph、不接 GUI、不执行 MappingEngine 内部。

与 SolutionStore 的关系：Manager 持有 Store 引用，register/remove 时同步落盘；
也可从 Store 冷加载（load_from_store）。
"""

import threading
from typing import Any, Dict, List, Optional

from core.capability_graph import GraphEdge
from core.capability_solution import (
    CapabilitySolution,
    STATUS_ACTIVE,
    STATUS_DRAFT,
)
from core.solution_store import SolutionStore


class SolutionManager:
    """Solution 运行时注册表（内存 + 持久化同步）。"""

    def __init__(self, store: Optional[SolutionStore] = None):
        self._store = store or SolutionStore()
        self._lock = threading.RLock()
        self._solutions: Dict[str, CapabilitySolution] = {}
        self._metadata: Dict[str, dict] = {}
        self._active_id: Optional[str] = None
        self._counter = 0

    # ------------------------------------------------------------------
    # id 生成
    # ------------------------------------------------------------------
    def _next_id(self) -> str:
        with self._lock:
            self._counter += 1
            return f"sol-{self._counter}"

    # ------------------------------------------------------------------
    # 注册 / 获取 / 移除
    # ------------------------------------------------------------------
    def create(
        self,
        name: str,
        edges: Optional[List[GraphEdge]] = None,
        metadata: Optional[dict] = None,
        status: str = STATUS_DRAFT,
        solution_id: Optional[str] = None,
    ) -> str:
        """新建一个 Solution 并注册 + 落盘，返回 id。"""
        sid = solution_id or self._next_id()
        solution = CapabilitySolution(name, status=status)
        for e in (edges or []):
            solution.add_edge(e)
        self.register(solution, sid, metadata=metadata)
        return sid

    def register(
        self,
        solution: CapabilitySolution,
        solution_id: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """注册一个已有 Solution（内存 + 落盘）。返回 id。"""
        with self._lock:
            self._solutions[solution_id] = solution
            self._metadata[solution_id] = dict(metadata or {})
        self._store.save(solution, solution_id, self._metadata[solution_id])
        return solution_id

    def get(self, solution_id: str) -> Optional[CapabilitySolution]:
        with self._lock:
            return self._solutions.get(solution_id)

    def metadata(self, solution_id: str) -> dict:
        with self._lock:
            return dict(self._metadata.get(solution_id, {}))

    def remove(self, solution_id: str) -> bool:
        """从运行时注册表移除（并落盘删除）。

        若该 solution 是当前 active，则清理 active 指针（状态清理，req 5）。
        返回是否实际移除。
        """
        with self._lock:
            if solution_id not in self._solutions:
                return False
            if self._active_id == solution_id:
                self._active_id = None
            del self._solutions[solution_id]
            self._metadata.pop(solution_id, None)
        self._store.delete(solution_id)
        return True

    def list_ids(self) -> List[str]:
        with self._lock:
            return sorted(self._solutions.keys())

    def list_all(self) -> List[tuple]:
        with self._lock:
            return [
                (sid, self._solutions[sid], self._metadata[sid])
                for sid in sorted(self._solutions.keys())
            ]

    # ------------------------------------------------------------------
    # active 指针 / 状态清理
    # ------------------------------------------------------------------
    def activate(self, solution_id: str) -> None:
        """设置 active solution（同时把该 solution 标记为 active 状态）。"""
        with self._lock:
            if solution_id not in self._solutions:
                raise KeyError(f"unknown solution: {solution_id}")
            self._active_id = solution_id
            self._solutions[solution_id].activate()
        # 状态变更后落盘
        self._store.save(
            self._solutions[solution_id],
            solution_id,
            self._metadata.get(solution_id, {}),
        )

    def deactivate(self) -> None:
        """清除 active 指针（不删除 solution）。"""
        with self._lock:
            self._active_id = None

    def active_id(self) -> Optional[str]:
        with self._lock:
            return self._active_id

    def active_solution(self) -> Optional[CapabilitySolution]:
        with self._lock:
            if self._active_id is None:
                return None
            return self._solutions.get(self._active_id)

    # ------------------------------------------------------------------
    # 冷加载（从 Store 恢复注册表）
    # ------------------------------------------------------------------
    def load_from_store(self) -> int:
        """从 Store 载入全部已保存 solution 到内存。返回载入数量。"""
        count = 0
        for sid, solution, metadata in self._store.list_all():
            with self._lock:
                self._solutions[sid] = solution
                self._metadata[sid] = metadata
            count += 1
        return count

    # ------------------------------------------------------------------
    # 合并 active mapping（供上层喂 MappingEngine，不执行其内部逻辑）
    # ------------------------------------------------------------------
    def combined_mapping_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """把当前 active 的 Solution 合并为 MappingEngine 兼容的 mapping dict。

        仅聚合 Solution.to_mapping_dict()（格式已兼容），不调用 MappingEngine。
        无 active solution 时返回空 dict。
        """
        active = self.active_solution()
        if active is None:
            return {}
        return active.to_mapping_dict()
