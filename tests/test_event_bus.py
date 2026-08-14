"""EventBus 测试：订阅 / 发布 / 退订 / 异常隔离 / 类型过滤。"""

from core.event_bus import EventBus


class EventA:
    pass


class EventB:
    pass


def test_subscribe_and_publish():
    bus = EventBus()
    received = []

    bus.subscribe(EventA, received.append)
    bus.publish(EventA())

    assert len(received) == 1
    assert isinstance(received[0], EventA)


def test_type_filtering():
    bus = EventBus()
    a_received = []
    b_received = []

    bus.subscribe(EventA, a_received.append)
    bus.subscribe(EventB, b_received.append)

    bus.publish(EventA())
    bus.publish(EventB())

    assert len(a_received) == 1
    assert len(b_received) == 1


def test_unsubscribe():
    bus = EventBus()
    received = []
    callback = received.append

    bus.subscribe(EventA, callback)
    bus.unsubscribe(EventA, callback)
    bus.publish(EventA())

    assert received == []


def test_subscriber_isolation():
    """一个订阅者抛异常不中断其他订阅者。"""
    bus = EventBus()
    received = []

    def faulty(_event):
        raise RuntimeError("boom")

    bus.subscribe(EventA, faulty)
    bus.subscribe(EventA, received.append)

    bus.publish(EventA())

    assert len(received) == 1


def test_dedup_subscribe():
    """同一 (类型, 回调) 不重复订阅。"""
    bus = EventBus()
    received = []
    callback = received.append

    bus.subscribe(EventA, callback)
    bus.subscribe(EventA, callback)
    bus.publish(EventA())

    assert len(received) == 1
