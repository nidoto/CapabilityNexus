"""X360Consumer：把 X360 输出包装为 CapabilityConsumer（V1.9 Phase 3）。

- 接收 CapabilityEvent（capability 为 xbox.* 等输出目标，value 为数值）；
- consume(event) 交给底层 OutputRouter 发送。
- X360 底层（VirtualXInput / RealXInputOutput / OutputRouter 路由）不修改，
  本类仅做"能力事件 -> 底层发送"的包装，使输出侧也成为统一能力消费者。
"""

from core.consumer import CapabilityConsumer
from core.capability import CapabilityEvent


class X360Consumer(CapabilityConsumer):
    """X360 能力消费者：把 CapabilityEvent 发给底层 X360 输出路由。"""

    DEVICE_ID = "x360"

    def __init__(self, output_router):
        # OutputRouter 实例（底层不修改）
        self._router = output_router

    def consume(self, event: CapabilityEvent):
        # event.capability 即输出目标（如 xbox.right_x），value 即数值
        self._router.send(event.capability, event.value)
