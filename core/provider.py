"""Capability Provider 抽象（V1.9 Phase 3）。

CapabilityProvider 是输入侧业务入口的基类：

- 生命周期：start() / stop() / is_running()
- 能力声明：capabilities() -> List[str]（字符串命名，未来第三方设备无需改系统）
- 发布：publish(event) 把 CapabilityEvent 交给注入的 sink（router / event_bus）

基类不感知任何具体设备（Phone / VR / 骑行台 / 手柄 ...），只负责"产生能力事件"。
具体设备由子类（如 PhoneProvider）包装对应 Parser 实现。
"""

from typing import Callable, List, Optional


class CapabilityProvider:
    """输入设备的能力提供方基类（与具体设备解耦）。"""

    def __init__(
        self,
        capabilities: Optional[List[str]] = None,
        publish: Optional[Callable] = None,
    ):
        self._capabilities = list(capabilities or [])
        self._publish = publish
        self._running = False

    # ---- 生命周期 ----
    def start(self):
        self._running = True

    def stop(self):
        self._running = False

    def is_running(self):
        return self._running

    # ---- 能力声明 ----
    def capabilities(self) -> List[str]:
        return list(self._capabilities)

    def set_capabilities(self, capabilities):
        self._capabilities = list(capabilities or [])

    # ---- 发布 ----
    def set_publish(self, publish: Callable):
        self._publish = publish

    def publish(self, event):
        if self._publish is not None:
            self._publish(event)
