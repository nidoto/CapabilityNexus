"""Transport 测试：stream 节流 / state 变化才发 / edge 边沿触发。"""

import time

from core.channel import Channel
from core.transport import TransportController


def _channel(cap_id, value, capability=None):
    return Channel(id=cap_id, category="axis", value=value, capability=capability)


def test_stream_throttled_by_rate():
    transport = TransportController()
    capability = {"transport": {"mode": "stream", "rate": 100}}

    # 首次立即发送
    assert transport.should_send(_channel("a", 1.0, capability)) is True
    # 立即再发一次应被节流
    assert transport.should_send(_channel("a", 1.5, capability)) is False


def test_stream_resumes_after_interval():
    transport = TransportController()
    # rate=30Hz 约 33ms 间隔，sleep 60ms 确保下一帧可发
    capability = {"transport": {"mode": "stream", "rate": 30}}

    assert transport.should_send(_channel("a", 1.0, capability)) is True
    assert transport.should_send(_channel("a", 1.0, capability)) is False
    time.sleep(0.06)
    assert transport.should_send(_channel("a", 1.0, capability)) is True


def test_state_only_on_change():
    transport = TransportController()
    capability = {"transport": {"mode": "state"}}

    assert transport.should_send(_channel("a", 1.0, capability)) is True
    assert transport.should_send(_channel("a", 1.0, capability)) is False
    assert transport.should_send(_channel("a", 2.0, capability)) is True


def test_edge_on_press_release():
    transport = TransportController()
    capability = {"transport": {"mode": "edge"}}

    # 按下（0->1）触发
    assert transport.should_send(_channel("btn", 0.0, capability)) is True
    assert transport.should_send(_channel("btn", 1.0, capability)) is True
    # 保持按住不触发
    assert transport.should_send(_channel("btn", 1.0, capability)) is False
    # 释放（1->0）触发
    assert transport.should_send(_channel("btn", 0.0, capability)) is True


def test_infer_stream_for_axis():
    transport = TransportController()
    # 无 transport 配置的 axis 推断为 stream
    capability = {"category": "axis"}
    assert transport.should_send(_channel("a", 1.0, capability)) is True


def test_infer_edge_for_button():
    transport = TransportController()
    capability = {"category": "button"}
    # button 推断为 edge：首帧 0 触发
    assert transport.should_send(_channel("btn", 0.0, capability)) is True
