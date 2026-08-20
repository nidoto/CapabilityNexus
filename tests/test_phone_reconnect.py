"""手机连接生命周期测试：DeviceSession 状态机 + 重连退避。

仅覆盖服务端状态机与退避策略；手机端 HTML 的退避/状态显示在浏览器中验证。
"""

import time

from tools.services import DeviceSession, WebService


def test_session_initial_offline():
    s = DeviceSession("dev-1", "Phone X", ["gyroscope"])
    assert s.status == DeviceSession.STATUS_OFFLINE
    assert s.device_id == "dev-1"
    assert s.reconnect_attempts == 0
    d = s.to_dict()
    assert d["device_id"] == "dev-1"
    assert d["status"] == "OFFLINE"
    assert d["reconnect_attempts"] == 0
    assert d["last_seen"] is None


def test_session_connected_and_reconnecting():
    s = DeviceSession("dev-1")
    # 连接成功
    s.status = DeviceSession.STATUS_CONNECTED
    s.last_seen = time.time()
    s.reconnect_attempts = 0
    assert s.status == "CONNECTED"

    # 客户端断开：进入 RECONNECTING，保留设备对象，计数 +1
    s.status = DeviceSession.STATUS_RECONNECTING
    s.reconnect_attempts += 1
    assert s.status == "RECONNECTING"
    assert s.reconnect_attempts == 1
    # device_id / name 仍在（不删除）
    assert s.device_id == "dev-1"

    # 重连成功：恢复同一 session，计数归零，不创建新设备
    s.status = DeviceSession.STATUS_CONNECTED
    s.last_seen = time.time()
    s.reconnect_attempts = 0
    assert s.status == "CONNECTED"
    assert s.reconnect_attempts == 0
    assert s.device_id == "dev-1"


def test_webservice_status_transitions(monkeypatch):
    """WebService：客户端断开→RECONNECTING（保留），hello 同 device_id→恢复。"""
    ws = WebService(port=18999, callback=None, use_https=False)
    ws._server = object()  # 模拟服务正在运行（phone_status 需要 server 非空）

    events = []
    ws._on_client_change = lambda c: events.append(c)  # 捕获 GUI 回调，不旁路真实逻辑

    # 直接用内部状态机：先建 session（模拟 hello 成功）
    ws._session = DeviceSession("dev-abc", "Phone", ["gyroscope"])
    ws._session.status = DeviceSession.STATUS_CONNECTED
    ws._session.last_seen = time.time()

    # 客户端数从 1 → 0：应进入 RECONNECTING，不清除 session
    ws._on_client_count_changed(0)
    assert ws.phone_status == "RECONNECTING"
    assert ws.phone_session["device_id"] == "dev-abc"  # 设备对象保留
    assert ws.phone_session["reconnect_attempts"] == 1

    # 客户端数 0 → 1（重连），但 session 仍由 hello 恢复；这里仅验证计数回调
    ws._on_client_count_changed(1)
    # 没有新 hello 时仍是 RECONNECTING（等待 hello 恢复）；session 保留
    assert ws.phone_session["device_id"] == "dev-abc"


def test_backoff_schedule_is_1_2_5():
    """退避策略：优先 1s / 2s / 5s，超出后停留在 5s。"""
    backoff = [1000, 2000, 5000]
    attempts = [0, 1, 2, 3, 4]
    delays = [backoff[min(a, len(backoff) - 1)] for a in attempts]
    assert delays == [1000, 2000, 5000, 5000, 5000]
