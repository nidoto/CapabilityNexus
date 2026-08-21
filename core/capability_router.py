"""Capability Routing Layer（V1.9 Phase 2）。

CapabilityRouter 是通用能力事件分发器：

- 不知道任何具体设备（Phone / VR / 骑行台 / 手柄 ...）；
- 不知道任何具体能力（phone.roll / vr.head.yaw / trainer.power ...）；
- 不持有 Device，不依赖 Mapping / X360 / GUI。

它只负责把 CapabilityEvent 广播给所有订阅的 handler。未来的 Client Adapter、
Recorder、多设备融合消费者等都作为 handler 接入，无需修改 Router 或已有 handler。
"""

from core.capability import CapabilityEvent


class CapabilityRouter:
    """把 CapabilityEvent 分发给所有 handler（通用能力层，无设备/能力知识）。"""

    def __init__(self):
        self._handlers = []

    def subscribe(self, handler):
        """注册一个 handler(event: CapabilityEvent)。重复注册忽略。"""
        if handler not in self._handlers:
            self._handlers.append(handler)

    def unsubscribe(self, handler):
        """注销 handler。"""
        if handler in self._handlers:
            self._handlers.remove(handler)

    def publish(self, event):
        """广播事件给所有 handler。

        单 handler 异常不影响其余 handler（与 EventBus 的容错一致）：
        一个消费者故障不能中断输入管线。
        """
        for handler in list(self._handlers):
            try:
                handler(event)
            except Exception as error:
                print("[CapabilityRouter] handler failed:", error)
