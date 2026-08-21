"""Capability Graph Foundation（V1.9 Phase 6）。

能力连接**描述层**：用图结构表达"哪种能力连到哪种能力"，
与已有分层解耦：

- 不执行任何转换，不持有运行时值（运行时值归 RuntimeStateService）；
- 不感知具体设备（Provider/Consumer 不变）；
- 不知道事件如何广播（CapabilityRouter 不变）；
- 不修改 MappingEngine：Graph 只在其**之上**生成标准 mapping dict，
  由调用方喂给 MappingEngine.load_mappings(...)。

设计约束：
- capability 使用字符串 id（与 CapabilityEvent / CapabilityDefinition 一致），
  不引入 enum。
- GraphNode 不内嵌 CapabilityDefinition 全量字段，仅存 definition_ref，
  显示信息由 UI 组合 Registry + RuntimeState 获取（延续定义/运行分离原则）。
- GraphEdge 的 gain / return_to_center 字段**刻意与 MappingEngine 的 mapping
  项同构**，使 Graph -> Mapping Rule 成为纯字段映射，零转换损失。
- GraphNode 预留 provider_type / device_selector 扩展字段：只保存，不实现匹配逻辑。
"""

import json
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GraphNode:
    """图中的一个能力节点（连接关系描述，非运行时值）。"""

    id: str
    kind: str = "both"          # "source" | "target" | "both"
    definition_ref: Optional[str] = None  # 指向 CapabilityRegistry 的 id（只读引用）
    role: str = "input"         # 逻辑角色："input" | "output"（用于布局）
    # --- 未来扩展字段：只保存，不实现匹配逻辑 ---
    provider_type: Optional[str] = None
    device_selector: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "definition_ref": self.definition_ref,
            "role": self.role,
            "provider_type": self.provider_type,
            "device_selector": self.device_selector,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GraphNode":
        return cls(
            id=data["id"],
            kind=data.get("kind", "both"),
            definition_ref=data.get("definition_ref"),
            role=data.get("role", "input"),
            provider_type=data.get("provider_type"),
            device_selector=data.get("device_selector"),
        )


@dataclass
class GraphEdge:
    """有向连接：source_cap -> target_cap。"""

    source: str
    target: str
    gain: float = 1.0
    return_to_center: bool = False
    origin: str = "manual"      # "auto" | "manual"
    confidence: float = 1.0      # 自动推断置信度（0~1）
    transform: Optional[str] = None  # 预留：未来转换层标识

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "gain": self.gain,
            "return_to_center": self.return_to_center,
            "origin": self.origin,
            "confidence": self.confidence,
            "transform": self.transform,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GraphEdge":
        return cls(
            source=data["source"],
            target=data["target"],
            gain=data.get("gain", 1.0),
            return_to_center=data.get("return_to_center", False),
            origin=data.get("origin", "manual"),
            confidence=data.get("confidence", 1.0),
            transform=data.get("transform"),
        )


class CapabilityGraph:
    """能力连接图（线程安全，纯描述层）。

    只描述"谁连到谁"，不执行、不持有运行时值、不碰 MappingEngine 内部。
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._nodes: Dict[str, GraphNode] = {}
        # 用 list 保存边，支持同源多目标与去重检查
        self._edges: List[GraphEdge] = []

    # ------------------------------------------------------------------
    # 节点
    # ------------------------------------------------------------------
    def add_node(self, node: GraphNode) -> GraphNode:
        with self._lock:
            self._nodes[node.id] = node
            return node

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        with self._lock:
            return self._nodes.get(node_id)

    def remove_node(self, node_id: str):
        """移除节点及其所有关联边。"""
        with self._lock:
            self._nodes.pop(node_id, None)
            self._edges = [
                e for e in self._edges
                if e.source != node_id and e.target != node_id
            ]

    def list_nodes(self) -> List[GraphNode]:
        with self._lock:
            return list(self._nodes.values())

    # ------------------------------------------------------------------
    # 边
    # ------------------------------------------------------------------
    def add_edge(self, edge: GraphEdge) -> GraphEdge:
        """添加一条连接；同源同目标已存在则覆盖（保留最新 gain/origin 等）。"""
        with self._lock:
            # 确保两端节点存在（自动补为 both 角色，便于反序列化）
            if edge.source not in self._nodes:
                self._nodes[edge.source] = GraphNode(edge.source, kind="source", role="input")
            if edge.target not in self._nodes:
                self._nodes[edge.target] = GraphNode(edge.target, kind="target", role="output")

            for i, existing in enumerate(self._edges):
                if existing.source == edge.source and existing.target == edge.target:
                    self._edges[i] = edge
                    return edge
            self._edges.append(edge)
            return edge

    def remove_edge(self, source: str, target: str) -> bool:
        """移除指定连接，返回是否实际移除。"""
        with self._lock:
            before = len(self._edges)
            self._edges = [
                e for e in self._edges
                if not (e.source == source and e.target == target)
            ]
            return len(self._edges) != before

    def get_edges_for_source(self, source: str) -> List[GraphEdge]:
        """返回从指定源能力出发的所有连接（供生成 mapping / UI 展示）。"""
        with self._lock:
            return [e for e in self._edges if e.source == source]

    def list_edges(self) -> List[GraphEdge]:
        with self._lock:
            return list(self._edges)

    # ------------------------------------------------------------------
    # 生成 Mapping Rule（喂给 MappingEngine.load_mappings）
    # ------------------------------------------------------------------
    def to_mapping_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """导出为 MappingEngine 期望的标准 mapping 形状。

        返回：{ source: [ {target, gain, return_to_center}, ... ] }
        与 mapping/mapper.py 的 _normalize / add_mapping 完全兼容。
        """
        with self._lock:
            result: Dict[str, List[Dict[str, Any]]] = {}
            for edge in self._edges:
                result.setdefault(edge.source, []).append({
                    "target": edge.target,
                    "gain": edge.gain,
                    "return_to_center": edge.return_to_center,
                })
            return result

    @classmethod
    def from_mapping_dict(cls, mapping: Dict[str, Any]) -> "CapabilityGraph":
        """从存量 mapping dict 重建图（保证可逆，用于可视化/编辑存量配置）。

        mapping 形状：{ source: [ {target, gain, return_to_center}, ... ] }
        或由 mapper._normalize 接受的字符串/字典/列表形式（此处仅接受标准形式）。
        """
        graph = cls()
        for source, targets in (mapping or {}).items():
            if isinstance(targets, dict):
                targets = [targets]
            if isinstance(targets, str):
                targets = [{"target": targets, "gain": 1.0, "return_to_center": False}]
            for t in (targets or []):
                if isinstance(t, str):
                    t = {"target": t, "gain": 1.0, "return_to_center": False}
                graph.add_edge(GraphEdge(
                    source=source,
                    target=t.get("target", "?"),
                    gain=t.get("gain", 1.0),
                    return_to_center=t.get("return_to_center", False),
                    origin="manual",
                    confidence=1.0,
                ))
        return graph

    # ------------------------------------------------------------------
    # JSON 序列化（供未来 UI / 持久化；不暴露内部对象）
    # ------------------------------------------------------------------
    def to_json(self) -> str:
        with self._lock:
            payload = {
                "nodes": [n.to_dict() for n in self._nodes.values()],
                "edges": [e.to_dict() for e in self._edges],
            }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "CapabilityGraph":
        data = json.loads(text)
        graph = cls()
        with graph._lock:
            for n in data.get("nodes", []):
                graph._nodes[n["id"]] = GraphNode.from_dict(n)
            for e in data.get("edges", []):
                graph._edges.append(GraphEdge.from_dict(e))
        return graph
