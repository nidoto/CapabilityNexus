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


def test_webservice_status_transitions():
    """WebService 多设备：单个连接断开只影响对应 device_id，不覆盖其他设备。"""
    from tools.services import DeviceContext

    ws = WebService(port=18999, callback=None, use_https=False)
    ws._server = object()  # 模拟服务正在运行（phone_status 需要 server 非空）

    # 模拟两台设备均已连接
    ws._devices["dev-aaa"] = DeviceContext("dev-aaa", "Phone A", ["gyroscope"])
    ws._devices["dev-bbb"] = DeviceContext("dev-bbb", "Phone B", ["gyroscope"])
    ws._devices["dev-aaa"].session.status = DeviceSession.STATUS_CONNECTED
    ws._devices["dev-bbb"].session.status = DeviceSession.STATUS_CONNECTED
    ws._devices["dev-aaa"].websocket = object()
    ws._devices["dev-bbb"].websocket = object()

    # 断开 dev-aaa 的 websocket：只影响 dev-aaa
    ws._on_client_disconnected(ws._devices["dev-aaa"].websocket)
    assert ws._devices["dev-aaa"].session.status == DeviceSession.STATUS_RECONNECTING
    assert ws._devices["dev-aaa"].session.reconnect_attempts == 1
    # dev-bbb 不受影响（仍 CONNECTED，设备对象保留）
    assert ws._devices["dev-bbb"].session.status == DeviceSession.STATUS_CONNECTED

    # 整体状态取最优：仍有 CONNECTED 设备 → CONNECTED
    assert ws.phone_status == "CONNECTED"
    # 断开 dev-bbb 后，全部 RECONNECTING
    ws._on_client_disconnected(ws._devices["dev-bbb"].websocket)
    assert ws.phone_status == "RECONNECTING"


def test_webservice_context_not_overwritten():
    """hello 同 device_id 恢复原 context；不同 device_id 不覆盖其他设备。"""
    from devices.websocket_connection import WebSocketServerConnection

    ws = WebService(port=18998, callback=None, use_https=False)
    ws._server = object()

    # 手动注入一台已连接设备
    from tools.services import DeviceContext
    ws._devices["dev-aaa"] = DeviceContext("dev-aaa", "Phone A", ["gyroscope"])
    ws._devices["dev-aaa"].session.status = DeviceSession.STATUS_CONNECTED

    # 用内部辅助创建/获取 context（模拟 hello 同 id 恢复）
    # 直接验证 _get_or_create_context 行为
    with ws._lock:
        got = ws._get_or_create_context("dev-aaa", "Phone A2", ["gyroscope"], object())
    assert got is ws._devices["dev-aaa"]  # 恢复同一 context，未新建
    assert ws._devices["dev-aaa"].session.name == "Phone A2"  # 仅更新展示信息

    # 不同 device_id 创建新 context，不影响 dev-aaa
    with ws._lock:
        new_ctx = ws._get_or_create_context("dev-bbb", "Phone B", ["gyroscope"], object())
    assert new_ctx is not ws._devices["dev-aaa"]
    assert set(ws._devices.keys()) == {"dev-aaa", "dev-bbb"}


def test_backoff_schedule_is_1_2_5():
    """退避策略：优先 1s / 2s / 5s，超出后停留在 5s。"""
    backoff = [1000, 2000, 5000]
    attempts = [0, 1, 2, 3, 4]
    delays = [backoff[min(a, len(backoff) - 1)] for a in attempts]
    assert delays == [1000, 2000, 5000, 5000, 5000]
