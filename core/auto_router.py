"""Auto Route Engine Layer（V1.9 Phase 8）。

在已有分层之上，**发现可能的连接关系**（不执行、不接线、不碰 MappingEngine）：

- 输入：一组源能力定义 + 一组目标能力定义（通常来自 CapabilityRegistry）。
- 借助 Phase 7 Matcher 计算每对 (source, target) 的兼容性；
- 只输出**兼容**的建议（不兼容能力不产生 suggestion，req 3）；
- apply_suggestions() 把建议落成 GraphEdge（origin="auto"，confidence 保留分数，
  且**不重复**已有边，req 4/5）；
- 全部基于字符串 capability id，无 enum（req 6）。

职责边界（与已有分层解耦）：
- 只读 CapabilityDefinition / CapabilityRegistry 元数据，不持有运行时值
  （实时值归 RuntimeStateService）；
- 不修改 CapabilityRouter / MappingEngine / Provider / Consumer；
- 不自动执行任何映射：只是"发现"，真正的建连确认留给 Phase 9（Solution System / GUI）；
- 不重复添加已有 GraphEdge（无论 manual 还是 auto），保证幂等。
"""

from dataclasses import dataclass
from typing import List, Optional

from core.capability_definition import CapabilityDefinition
from core.capability_graph import CapabilityGraph, GraphEdge
from core.capability_matcher import compatibility


@dataclass
class Suggestion:
    """一条自动发现的连接建议（尚未落成 GraphEdge）。"""

    source: str
    target: str
    score: float

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target, "score": self.score}


class AutoRouter:
    """自动发现能力连接建议，并把建议落成 GraphEdge（幂等、不执行）。"""

    def __init__(self, threshold: Optional[float] = None):
        # 阈值可覆盖（默认沿用 matcher 的兼容性判定，即 compatible=True）。
        self._threshold = threshold

    # ------------------------------------------------------------------
    # 发现
    # ------------------------------------------------------------------
    def discover(
        self,
        sources: List[CapabilityDefinition],
        targets: List[CapabilityDefinition],
    ) -> List[Suggestion]:
        """对 sources × targets 做兼容性推断，返回兼容建议（按分数降序）。

        不兼容的能力对**不会产生** suggestion（req 3）。
        """
        suggestions: List[Suggestion] = []
        for src in sources:
            for tgt in targets:
                compatible, score = compatibility(src, tgt)
                # 只保留兼容对；threshold 覆盖时按自定义阈值再过滤。
                if not compatible:
                    continue
                if self._threshold is not None and score < self._threshold:
                    continue
                suggestions.append(Suggestion(src.id, tgt.id, score))
        # 按分数降序、同分按 (source, target) 稳定排序
        suggestions.sort(key=lambda s: (-s.score, s.source, s.target))
        return suggestions

    # ------------------------------------------------------------------
    # 落成 GraphEdge（幂等）
    # ------------------------------------------------------------------
    def apply_suggestions(
        self,
        graph: CapabilityGraph,
        suggestions: List[Suggestion],
    ) -> int:
        """把建议落成 GraphEdge（origin="auto"，confidence=score）。

        - 已存在相同 source->target 边时**跳过**（不重复添加，也不覆盖 manual 边）；
        - 返回实际新增的边数。

        注意：本方法只修改 Graph（描述层），不触发任何映射执行。
        """
        added = 0
        for sug in suggestions:
            # 已有边（无论 auto 还是 manual）直接跳过，保证幂等。
            existing = graph.get_edges_for_source(sug.source)
            if any(e.target == sug.target for e in existing):
                continue
            graph.add_edge(GraphEdge(
                source=sug.source,
                target=sug.target,
                gain=1.0,
                return_to_center=False,
                origin="auto",
                confidence=sug.score,
            ))
            added += 1
        return added
