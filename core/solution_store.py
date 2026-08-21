"""Solution Store（V1.9 Phase 10）。

CapabilitySolution 的**持久化层**：把 Solution 存为 JSON 文件（每个 solution 一个文件，
按 id 命名），并负责 load / list / delete。

设计要点：
- Store 不依赖整张 Graph：只保存 Solution 自身（选中的边子集），不复制 Graph。
- JSON 信封保留：id / name / status / edges / metadata。
- capability id 仍为字符串，无 enum。
- 不执行 MappingEngine 内部逻辑：只序列化/反序列化，不调用 load_mappings。
- 不接 GUI。

与 SolutionManager 的关系：Manager 负责运行时注册表与 active 指针，Store 负责落盘。
两者都只新增，不修改 Phase 9 的 CapabilitySolution。
"""

import json
import os
import threading
from typing import Dict, List, Optional, Tuple

from core.capability_graph import GraphEdge
from core.capability_solution import (
    CapabilitySolution,
    STATUS_DRAFT,
    STATUS_ACTIVE,
)


def _project_root() -> str:
    # core/solution_store.py -> 上级即项目根
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SolutionStore:
    """Solution 的文件持久化（JSON，按 id 存）。"""

    def __init__(self, directory: Optional[str] = None):
        self._directory = directory or os.path.join(_project_root(), "solutions")
        self._lock = threading.Lock()
        os.makedirs(self._directory, exist_ok=True)

    # ------------------------------------------------------------------
    # 路径
    # ------------------------------------------------------------------
    def _path(self, solution_id: str) -> str:
        # id 已约定为字符串；做基本净化避免路径穿越
        safe = solution_id.replace(os.sep, "_").replace("..", "_")
        return os.path.join(self._directory, f"{safe}.json")

    # ------------------------------------------------------------------
    # 保存 / 加载
    # ------------------------------------------------------------------
    def save(
        self,
        solution: CapabilitySolution,
        solution_id: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """保存一个 Solution（带 id 与 metadata 信封）。返回 solution_id。"""
        envelope = {
            "id": solution_id,
            "name": solution.name,
            "status": solution.status,
            "edges": [e.to_dict() for e in solution.list_edges()],
            "metadata": metadata or {},
        }
        with self._lock:
            with open(self._path(solution_id), "w", encoding="utf-8") as f:
                json.dump(envelope, f, ensure_ascii=False, indent=2)
        return solution_id

    def load(self, solution_id: str) -> Optional[Tuple[CapabilitySolution, dict]]:
        """加载一个 Solution，返回 (solution, metadata)；不存在返回 None。"""
        path = self._path(solution_id)
        if not os.path.exists(path):
            return None
        with self._lock:
            with open(path, "r", encoding="utf-8") as f:
                envelope = json.load(f)

        solution = CapabilitySolution(
            envelope.get("name", solution_id),
            status=envelope.get("status", STATUS_DRAFT),
        )
        for e in envelope.get("edges", []):
            solution.add_edge(GraphEdge.from_dict(e))
        metadata = envelope.get("metadata", {}) or {}
        # source_graph 也随 metadata 还原，便于追溯
        if "source_graph" in envelope and "source_graph" not in metadata:
            metadata["source_graph"] = envelope["source_graph"]
        return solution, metadata

    def exists(self, solution_id: str) -> bool:
        return os.path.exists(self._path(solution_id))

    def delete(self, solution_id: str) -> bool:
        """删除一个 Solution 文件，返回是否实际删除。"""
        path = self._path(solution_id)
        with self._lock:
            if os.path.exists(path):
                os.remove(path)
                return True
        return False

    def list_ids(self) -> List[str]:
        """返回所有已保存的 solution id（按文件名排序）。"""
        if not os.path.isdir(self._directory):
            return []
        ids = []
        for name in os.listdir(self._directory):
            if name.endswith(".json"):
                ids.append(name[:-5])
        return sorted(ids)

    def list_all(self) -> List[Tuple[str, CapabilitySolution, dict]]:
        """返回全部 (id, solution, metadata)。"""
        result = []
        for sid in self.list_ids():
            loaded = self.load(sid)
            if loaded is not None:
                result.append((sid, loaded[0], loaded[1]))
        return result
