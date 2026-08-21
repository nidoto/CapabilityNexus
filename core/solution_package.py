"""Solution Package（V1.9 Phase 15）。

把 CapabilitySolution 包装成**可交换配置单元**（用户可导出/导入/分享）。

设计边界（不修改已有分层、不污染 Runtime）：
- SolutionPackage 只是**包装层**：持有一个 CapabilitySolution + 包级元数据
  （id / name / description / metadata），不复制也不重实现 Solution 逻辑。
- to_dict() / from_dict() 复用 CapabilitySolution 自身的 JSON 序列化，
  内部 solution 字段不丢失（含 edge 的 origin/confidence 等元数据）。
- capability id 保持字符串，无 enum。
- 不替代 SolutionStore（运行时注册保存）；本类面向"用户文件交换"，
  文件落盘由 SolutionSerializer 负责。
"""

import json
from typing import Any, Dict, Optional

from core.capability_solution import CapabilitySolution


class SolutionPackage:
    """可交换的 Solution 配置包（CapabilitySolution 的包装）。"""

    def __init__(
        self,
        solution: CapabilitySolution,
        id: str = "",
        name: str = "",
        description: str = "",
        metadata: Optional[dict] = None,
    ):
        # 包装而非复制：直接持有传入的 Solution 实例
        self.solution = solution
        # 包级 id/name：缺省时回落到内部 solution 的 name
        self.id = id or solution.name
        self.name = name or solution.name
        self.description = description
        self.metadata = dict(metadata or {})

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """导出为可分享的包结构（solution 字段复用其自身 JSON 结构）。"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
            "solution": json.loads(self.solution.to_json()),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SolutionPackage":
        """从包结构重建（内部 solution 经 CapabilitySolution.from_json 还原）。"""
        inner = data.get("solution", {})
        solution = CapabilitySolution.from_json(json.dumps(inner))
        return cls(
            solution=solution,
            id=data.get("id", solution.name),
            name=data.get("name", solution.name),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )

    # ------------------------------------------------------------------
    # 文件交换（委托 SolutionSerializer，保持文件层独立）
    # ------------------------------------------------------------------
    def save(self, path: str) -> None:
        """导出包到文件（便捷方法，委托 SolutionSerializer）。"""
        from core.solution_serializer import SolutionSerializer

        SolutionSerializer().save(self, path)

    @classmethod
    def load(cls, path: str) -> "SolutionPackage":
        """从文件载入包（便捷方法，委托 SolutionSerializer）。"""
        from core.solution_serializer import SolutionSerializer

        return SolutionSerializer().load(path)
