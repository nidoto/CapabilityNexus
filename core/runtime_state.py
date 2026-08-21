"""Runtime State Service（V1.9 Phase 4）。

维护引擎运行时的统一状态视图，供 Runtime Dashboard UI 读取：

- Device 列表（device_id / provider / connected / capabilities）
- Capability 实时值（capability -> value + timestamp，按 device 区分）
- Consumer 状态（如 X360 是否在线）

设计约束（与 Provider/Consumer/Mapping/Router 解耦）：
- 订阅 CapabilityRouter：收到 CapabilityEvent 即更新 device / capability 实时值；
- 不直接访问 PhoneFrameParser / MappingEngine / X360 等具体实现；
- UI 只读本服务暴露的快照，不触碰底层内部对象。
"""

import threading
from typing import Dict, List


class RuntimeStateService:
    """运行时状态聚合服务（线程安全）。"""

    def __init__(self):
        self._lock = threading.Lock()
        # device_id -> {"provider", "connected", "capabilities": set, "last_seen"}
        self._devices: Dict[str, dict] = {}
        # (device_id, capability) -> {"value", "timestamp"}
        self._capabilities: Dict[tuple, dict] = {}
        # consumer name -> bool（如 "x360": True）
        self._consumer_status: Dict[str, bool] = {}
        self._router = None

    # ------------------------------------------------------------------
    # 接入路由层
    # ------------------------------------------------------------------
    def attach_router(self, router):
        """订阅 CapabilityRouter，开始接收 CapabilityEvent 更新状态。"""
        self._router = router
        router.subscribe(self.handle)

    def handle(self, event):
        """CapabilityRouter 回调：用 CapabilityEvent 更新 device / capability 状态。"""
        device_id = getattr(event, "device_id", "") or ""
        capability = getattr(event, "capability", "")
        value = getattr(event, "value", None)
        timestamp = getattr(event, "timestamp", None)
        if not capability:
            return
        with self._lock:
            dev = self._devices.setdefault(device_id, {
                "provider": "",
                "connected": True,
                "capabilities": set(),
                "last_seen": timestamp,
            })
            dev["capabilities"].add(capability)
            if timestamp is not None:
                dev["last_seen"] = timestamp
            self._capabilities[(device_id, capability)] = {
                "value": value,
                "timestamp": timestamp,
            }

    # ------------------------------------------------------------------
    # 设备 / Provider 注册（由上层从公开 API 注入，不触碰底层内部）
    # ------------------------------------------------------------------
    def register_device(self, device_id, provider=None, connected=None,
                        capabilities=None):
        with self._lock:
            dev = self._devices.setdefault(device_id, {
                "provider": "",
                "connected": False,
                "capabilities": set(),
                "last_seen": None,
            })
            if provider is not None:
                dev["provider"] = provider
            if connected is not None:
                dev["connected"] = bool(connected)
            if capabilities:
                dev["capabilities"].update(capabilities)

    def set_device_connected(self, device_id, connected):
        with self._lock:
            dev = self._devices.setdefault(device_id, {
                "provider": "",
                "connected": False,
                "capabilities": set(),
                "last_seen": None,
            })
            dev["connected"] = bool(connected)

    def set_consumer_status(self, name, connected):
        with self._lock:
            self._consumer_status[name] = bool(connected)

    # ------------------------------------------------------------------
    # 读取快照（供 UI）
    # ------------------------------------------------------------------
    def get_devices(self) -> List[dict]:
        """返回 Device 列表快照：device_id / provider / connected / capabilities。"""
        with self._lock:
            result = []
            for dev_id, dev in self._devices.items():
                result.append({
                    "device_id": dev_id,
                    "provider": dev["provider"],
                    "connected": dev["connected"],
                    "capabilities": sorted(dev["capabilities"]),
                })
            return result

    def get_capabilities(self) -> List[dict]:
        """返回 Capability 实时值快照：device_id / capability / value / timestamp。"""
        with self._lock:
            result = []
            for (dev_id, cap), info in self._capabilities.items():
                result.append({
                    "device_id": dev_id,
                    "capability": cap,
                    "value": info["value"],
                    "timestamp": info["timestamp"],
                })
            return result

    def get_output_status(self) -> Dict[str, bool]:
        """返回 Consumer 状态快照（如 X360）。"""
        with self._lock:
            return dict(self._consumer_status)
