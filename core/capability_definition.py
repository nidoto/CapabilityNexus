"""Capability Definition（V1.9 Phase 5）。

Capability Registry Layer 的"声明侧"：描述一种能力**应当是什么样**，
与运行时数据（CapabilityEvent / RuntimeStateService 中的实时值）解耦。

- CapabilityDefinition 只是静态元数据（名称 / 类型 / 单位 / 范围 / 分类），
  不参与事件路由，也不保存实时值。
- CapabilityRegistry（core/capability_registry.py）以它为存储单元，
  提供 register / unregister / get / list_all。
- RuntimeStateService 只保存运行数据；UI 通过 RuntimeState（实时值）
  + Registry（定义/显示信息）组合出完整展示，互不直接依赖。

设计约束：
- capability 仍使用字符串 id（非 enum），与 Phase 1 的 CapabilityEvent 一致；
- 不引入 enum，保持轻量与第三方自由扩展。
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CapabilityDefinition:
    """单种能力的静态定义（声明元数据，非运行时值）。

    字段：
      - id          : 能力标识（字符串，如 "phone.roll"），与 CapabilityEvent.capability 对应。
      - display_name: 展示名（UI 用，如 "Roll 横滚"）。
      - value_type  : 取值类型（字符串描述，如 "float" / "bool" / "int"），不强制校验运行时值。
      - unit        : 单位（可选，如 "deg" / "%" / None）。
      - min_value   : 取值下界（可选）。
      - max_value   : 取值上界（可选）。
      - category    : 分类（字符串，如 "axis" / "button" / "sensor"），便于 UI 分组。
    """

    id: str
    display_name: str = ""
    value_type: str = "float"
    unit: Optional[str] = None
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    category: str = "misc"

    def __post_init__(self):
        # display_name 缺省时回落到 id，保证 UI 总有可读文本。
        if not self.display_name:
            self.display_name = self.id

    def to_dict(self) -> dict:
        """导出为普通 dict（供 UI / 序列化，不暴露 dataclass 内部对象）。"""
        return {
            "id": self.id,
            "display_name": self.display_name,
            "value_type": self.value_type,
            "unit": self.unit,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CapabilityDefinition":
        """从普通 dict 构造（容忍额外字段，忽略未知键）。"""
        return cls(
            id=data["id"],
            display_name=data.get("display_name", ""),
            value_type=data.get("value_type", "float"),
            unit=data.get("unit"),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            category=data.get("category", "misc"),
        )
