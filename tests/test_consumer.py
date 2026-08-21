"""Capability Consumer 测试（V1.9 Phase 3）。

验证：
  1. CapabilityConsumer 基类 consume() 未实现则抛 NotImplementedError。
  2. X360Consumer.consume(CapabilityEvent) 把事件交给底层 X360 路由（底层不变）。
  3. 自定义 Consumer 收到同一个 CapabilityEvent（多消费者隔离）。
"""

from core.capability import CapabilityEvent
from core.consumer import CapabilityConsumer
from output.x360_consumer import X360Consumer


def test_base_consumer_not_implemented():
    c = CapabilityConsumer()
    try:
        c.consume(CapabilityEvent("dev", "phone.roll", 1.0))
        assert False, "应抛 NotImplementedError"
    except NotImplementedError:
        pass


def test_x360_consumer_sends_to_backend():
    """X360Consumer 把 CapabilityEvent(xbox.right_x) 发给底层 router.send。"""
    sent = []
    fake_router = type("R", (), {"send": lambda self, t, v: sent.append((t, v))})()

    consumer = X360Consumer(fake_router)
    consumer.consume(CapabilityEvent(
        device_id=X360Consumer.DEVICE_ID,
        capability="xbox.right_x",
        value=0.42,
    ))

    assert sent == [("xbox.right_x", 0.42)]
    # 设备标识为 X360 输出侧
    assert consumer.DEVICE_ID == "x360"


def test_custom_consumer_receives_event():
    """自定义消费者收到的是发布出去的同一 CapabilityEvent。"""
    received = []
    consumer = type("Rec", (CapabilityConsumer,), {
        "consume": lambda self, e: received.append(e),
    })()
    ev = CapabilityEvent("dev-a", "phone.roll", 1.0)
    consumer.consume(ev)
    assert received == [ev]
