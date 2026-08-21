"""Capability Solution System（V1.9 Phase 9）。

从 CapabilityGraph（Phase 6）中挑选**一部分**连接，组成一个"解决方案"，
最终可导出为标准 Mapping Rule 喂给 MappingEngine。

设计要点：
- Solution **不复制整个 Graph**：只持有被选中的边（GraphEdge 子集），
  例如 Graph 中 phone.roll 同时连 left_x / right_x，Solution 可只选其中一条。
- Solution 是连接方案的"候选/确认"载体，带生命周期：draft -> accepted -> active。
- to_mapping_dict() 输出与 MappingEngine.load_mappings 完全兼容的形状
  { source: [ {target, gain, return_to_center}, ... ] }。
- auto/manual 元数据（GraphEdge.origin / confidence）随边保留，JSON 往返不丢。
- capability id 仍为字符串，无 enum。

职责边界（不修改已有分层）：
- 不执行任何映射：Solution 只描述"选了哪些连接"，由上层（app / GUI）在
  active 时调用 graph.to_mapping_dict() / solution.to_mapping_dict() 喂给 MappingEngine；
- 不持有运行时值（归 RuntimeStateService）；不感知事件广播（CapabilityRouter 不变）。
"""

import json
from typing import Any, Dict, List, Optional

from core.capability_graph import CapabilityGraph, GraphEdge

# 生命周期状态（有序）。draft -> accepted -> active。
STATUS_DRAFT = "draft"
STATUS_ACCEPTED = "accepted"
STATUS_ACTIVE = "active"
_STATUS_ORDER = {STATUS_DRAFT: 0, STATUS_ACCEPTED: 1, STATUS_ACTIVE: 2}


class CapabilitySolution:
    """一组被选中的能力连接（Graph 的边子集）+ 生命周期状态。

    不持有整张 Graph；只保存被选中的 GraphEdge 列表。
    """

    def __init__(self, name: str, status: str = STATUS_DRAFT):
        self.name = name
        self._status = STATUS_DRAFT
        self._edges: List[GraphEdge] = []
        # 可选：记录来源 Graph 标识（不保存 Graph 对象本身，避免整图复制）
        self.source_graph: Optional[str] = None
        self.set_status(status)

    # ------------------------------------------------------------------
    # 状态生命周期
    # ------------------------------------------------------------------
    @property
    def status(self) -> str:
        return self._status

    def set_status(self, status: str) -> None:
        """设置生命周期状态，仅允许合法状态与向前推进（不允许回退）。"""
        if status not in _STATUS_ORDER:
            raise ValueError(f"invalid solution status: {status!r}")
        if _STATUS_ORDER[status] < _STATUS_ORDER[self._status]:
            raise ValueError(
                f"cannot move status backward: {self._status} -> {status}"
            )
        self._status = status

    def accept(self) -> None:
        """draft -> accepted。"""
        self.set_status(STATUS_ACCEPTED)

    def activate(self) -> None:
        """accepted -> active（draft 可直接激活）。"""
        self.set_status(STATUS_ACTIVE)

    # ------------------------------------------------------------------
    # 边子集管理
    # ------------------------------------------------------------------
    def add_edge(self, edge: GraphEdge) -> GraphEdge:
        """添加一条被选中的连接；同源同目标已存在则覆盖（保留最新元数据）。"""
        for i, existing in enumerate(self._edges):
            if existing.source == edge.source and existing.target == edge.target:
                self._edges[i] = edge
                return edge
        self._edges.append(edge)
        return edge

    def remove_edge(self, source: str, target: str) -> bool:
        """移除一条被选中的连接，返回是否实际移除。"""
        before = len(self._edges)
        self._edges = [
            e for e in self._edges
            if not (e.source == source and e.target == target)
        ]
        return len(self._edges) != before

    def list_edges(self) -> List[GraphEdge]:
        return list(self._edges)

    def get_edges_for_source(self, source: str) -> List[GraphEdge]:
        return [e for e in self._edges if e.source == source]

    # ------------------------------------------------------------------
    # 从 Graph 中选边创建 Solution（不复制整图）
    # ------------------------------------------------------------------
    @classmethod
    def from_graph(
        cls,
        graph: CapabilityGraph,
        selections: List[tuple],
        name: str = "solution",
        status: str = STATUS_DRAFT,
    ) -> "CapabilitySolution":
        """从 graph 中挑选指定连接组成 Solution。

        selections: [(source, target), ...]，只引用 Graph 中已存在的边；
        不存在的边被忽略（不静默创建）。Solution 仅持有被选中的边，
        不复制 Graph 的其余节点/边。
        """
        solution = cls(name, status=status)
        solution.source_graph = getattr(graph, "name", None)
        by_key = {
            (e.source, e.target): e for e in graph.list_edges()
        }
        for src, tgt in selections:
            edge = by_key.get((src, tgt))
            if edge is not None:
                # 复制一份边引用加入 Solution（与 Graph 解耦，互不干扰）
                solution.add_edge(GraphEdge(
                    source=edge.source,
                    target=edge.target,
                    gain=edge.gain,
                    return_to_center=edge.return_to_center,
                    origin=edge.origin,
                    confidence=edge.confidence,
                    transform=edge.transform,
                ))
        return solution

    # ------------------------------------------------------------------
    # 导出 Mapping Rule（与 MappingEngine 完全兼容）
    # ------------------------------------------------------------------
    def to_mapping_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """导出为 MappingEngine 期望的标准 mapping 形状。

        返回：{ source: [ {target, gain, return_to_center}, ... ] }
        直接喂 MappingEngine.load_mappings(...)。
        """
        result: Dict[str, List[Dict[str, Any]]] = {}
        for edge in self._edges:
            result.setdefault(edge.source, []).append({
                "target": edge.target,
                "gain": edge.gain,
                "return_to_center": edge.return_to_center,
            })
        return result

    # ------------------------------------------------------------------
    # JSON 序列化（status + 选中边 + auto/manual 元数据）
    # ------------------------------------------------------------------
    def to_json(self) -> str:
        payload = {
            "name": self.name,
            "status": self._status,
            "source_graph": self.source_graph,
            "edges": [e.to_dict() for e in self._edges],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "CapabilitySolution":
        data = json.loads(text)
        solution = cls(data["name"], status=data.get("status", STATUS_DRAFT))
        solution.source_graph = data.get("source_graph")
        for e in data.get("edges", []):
            solution._edges.append(GraphEdge.from_dict(e))
        return solution
