"""Capability Consumer 抽象（V1.9 Phase 3）。

CapabilityConsumer 是输出侧业务入口的基类：

- consume(event: CapabilityEvent)：消费一个能力事件。

基类不感知任何具体输入设备，也不感知具体输出后端（X360 / 键盘 / 鼠标 ...）。
具体消费者（如 X360Consumer）子类化并实现 consume，把事件交给底层后端。
"""

from core.capability import CapabilityEvent


class CapabilityConsumer:
    """能力消费方基类（与具体输入设备 / 输出后端解耦）。"""

    def consume(self, event: CapabilityEvent):
        raise NotImplementedError("CapabilityConsumer.consume must be implemented")
