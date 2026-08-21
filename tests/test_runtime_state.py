"""Runtime State Service 测试（V1.9 Phase 4）。

验证：
  1. 订阅 CapabilityRouter，收到 CapabilityEvent 更新 device / capability 状态。
  2. device 注册（provider / connected / capabilities）与读取快照。
  3. consumer 状态（X360）读取。
  4. UI 只读快照，不触碰底层内部对象。
"""

from core.capability import CapabilityEvent
from core.capability_router import CapabilityRouter
from core.runtime_state import RuntimeStateService


def _router_and_state():
    router = CapabilityRouter()
    state = RuntimeStateService()
    state.attach_router(router)
    return router, state


def test_event_updates_capability_state():
    router, state = _router_and_state()
    router.publish(CapabilityEvent("dev-a", "phone.roll", 0.3))

    caps = state.get_capabilities()
    assert len(caps) == 1
    assert caps[0]["device_id"] == "dev-a"
    assert caps[0]["capability"] == "phone.roll"
    assert caps[0]["value"] == 0.3
    assert caps[0]["timestamp"] is not None


def test_event_registers_device_and_capabilities():
    router, state = _router_and_state()
    router.publish(CapabilityEvent("dev-a", "phone.roll", 1.0))
    router.publish(CapabilityEvent("dev-a", "phone.gas", 0.5))

    devices = state.get_devices()
    assert len(devices) == 1
    dev = devices[0]
    assert dev["device_id"] == "dev-a"
    assert "phone.roll" in dev["capabilities"]
    assert "phone.gas" in dev["capabilities"]


def test_register_device_and_connected():
    router, state = _router_and_state()
    state.register_device("dev-b", provider="phone", connected=True,
                         capabilities=["phone.yaw"])
    state.set_device_connected("dev-b", False)

    devices = {d["device_id"]: d for d in state.get_devices()}
    assert devices["dev-b"]["provider"] == "phone"
    assert devices["dev-b"]["connected"] is False
    assert "phone.yaw" in devices["dev-b"]["capabilities"]


def test_consumer_status():
    router, state = _router_and_state()
    state.set_consumer_status("x360", True)
    out = state.get_output_status()
    assert out.get("x360") is True

    # 事件仅补充 capability 状态，不应清空 consumer 状态
    router.publish(CapabilityEvent("dev-a", "phone.roll", 0.1))
    assert state.get_output_status().get("x360") is True


def test_ui_reads_only_snapshots():
    """UI 通过 get_* 读取；RuntimeStateService 不暴露底层内部对象。"""
    router, state = _router_and_state()
    router.publish(CapabilityEvent("dev-a", "phone.roll", 0.2))

    # 返回的是普通 dict/list 快照，可安全序列化展示
    assert isinstance(state.get_devices(), list)
    assert isinstance(state.get_capabilities(), list)
    assert isinstance(state.get_output_status(), dict)
    # 类型与名称均符合 UI 约定
    dev = state.get_devices()[0]
    assert set(dev.keys()) == {"device_id", "provider", "connected", "capabilities"}
