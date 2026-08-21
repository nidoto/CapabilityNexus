"""Solution Serializer（V1.9 Phase 15）。

负责 SolutionPackage 与 JSON 文件之间的转换（用户导入/导出/分享）。

与 SolutionStore 的关系（两者不替代）：
- SolutionStore：运行时注册保存（Manager 内部使用，按 id 落盘）。
- SolutionSerializer：用户级文件交换（导入/导出 .solution 文件）。

数据流：
    User File  ->  SolutionSerializer.load  ->  SolutionPackage
               ->  CapabilitySolution  ->  SolutionManager

设计边界：
- 不修改 CapabilitySolution / SolutionStore / MappingEngine 等既有模块；
- capability id 保持字符串，无 enum；
- 仅做文件读写与包结构转换，不执行任何映射逻辑。
"""

import json
import os
from typing import Any, Dict


class SolutionSerializer:
    """SolutionPackage <-> JSON 文件的转换层。"""

    def save(self, package: "Any", path: str) -> None:
        """把 SolutionPackage 写入 JSON 文件。"""
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(package.to_dict(), f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> "Any":
        """从 JSON 文件载入 SolutionPackage；文件不存在抛 FileNotFoundError。"""
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)
        # 延迟导入避免循环依赖（package 也引用 serializer）
        from core.solution_package import SolutionPackage

        return SolutionPackage.from_dict(data)
