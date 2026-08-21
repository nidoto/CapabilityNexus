"""Capability Runtime —— 设备能力标准事件。

CapabilityEvent 是所有输入设备进入引擎的**统一标准格式**。

设计目标（V1.9 Phase 1）：
  系统不关心输入设备是什么（手机 / 骑行台 / VR / 手柄 / 其它传感器），
  只关心它**提供什么能力**。每种设备把自身数据转换成 CapabilityEvent，
  下游（Mapping / X360 / 状态监视）即可统一消费，无需感知来源设备类型。

字段约定：
  - device_id : 来源设备身份（device_id 主键）。多设备并存时用于溯源，
                例如 phone.roll(dev-A) 与 phone.roll(dev-B) 通过 device_id 区分。
  - capability: 能力名（字符串，非 enum）。未来第三方设备可自由扩展
                （trainer.power / vr.head.yaw / ...）而系统无需修改。
  - value     : 数值（Any，通常为 float；按钮为 0.0/1.0）。
  - timestamp : 产生时刻（秒，浮点）。用于未来延迟补偿 / 数据同步 / 多设备融合。

本阶段不修改 Mapping / X360 / GUI / Device Identity / Reconnect：
Parser 改为输出 CapabilityEvent，运行时用一个轻量桥接把 CapabilityEvent
转回现有 StreamData 喂给未变的下游管线，保证手机二维码连接、X360 输出、
mapping 全部不受影响。
"""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CapabilityEvent:
    """单条设备能力事件（统一标准格式）。"""

    device_id: str
    capability: str
    value: Any
    # 未显式传入时取当前时间；允许调用方覆盖（重放 / 测试 / 延迟补偿）。
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        # 兼容显式传 None 的场景：回落到当前时间。
        if self.timestamp is None:
            self.timestamp = time.time()

    def __repr__(self):
        return (
            f"CapabilityEvent(device_id='{self.device_id}', "
            f"capability='{self.capability}', "
            f"value={self.value!r}, "
            f"timestamp={self.timestamp})"
        )
