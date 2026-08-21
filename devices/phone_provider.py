"""PhoneProvider：把手机输入包装为 CapabilityProvider 业务入口（V1.9 Phase 3）。

- PhoneFrameParser 不再是直接业务入口；由 PhoneProvider 包装它。
- parse(message) 委托内部 PhoneFrameParser 解析，解析出的 CapabilityEvent
  经注入的 event_bus（或 publish sink）流出，进入 CapabilityRouter。
- capabilities() 返回该手机提供的能力名（字符串）。
- 不修改 PhoneFrameParser 的解析逻辑、不修改 Mapping / X360 / DeviceContext。
"""

from core.provider import CapabilityProvider
from devices.websocket_connection import PhoneFrameParser


class _EventBusShim:
    """把 CapabilityEvent 转发给 provider 的发布 sink（event_bus / publish）。"""

    __slots__ = ("_forward",)

    def __init__(self, forward):
        self._forward = forward

    def publish(self, event):
        self._forward(event)


class PhoneProvider(CapabilityProvider):
    """手机能力提供方：包装 PhoneFrameParser，统一产出 CapabilityEvent。"""

    def __init__(self, device_id="", capabilities=None, event_bus=None,
                 publish=None):
        # 优先用显式 publish；否则用 event_bus.publish（与 WebService 注入一致）
        if publish is None and event_bus is not None:
            publish = event_bus.publish
        super().__init__(capabilities=capabilities, publish=publish)
        self.device_id = device_id
        self._event_bus = event_bus
        # 内部 parser：解析出的 CapabilityEvent 经 shim 交给注入的发布 sink
        self._parser = PhoneFrameParser(event_bus=_EventBusShim(self._forward))
        # 注：不把 self._publish 指向 self._forward（否则 _forward 内 self._publish
        # 调用会自递归）。_forward 已按"publish 优先、否则 event_bus"处理。

    def _forward(self, event):
        # 优先用显式 publish sink；否则经注入的 event_bus 流出。
        # 兼容 set_event_bus 把 event_bus 置为 None 的情况：未注入则不发布。
        if self._publish is not None:
            self._publish(event)
        elif self._event_bus is not None:
            self._event_bus.publish(event)

    # event_bus 兼容属性（WebService.set_event_bus 通过它注入 / 同步）
    @property
    def event_bus(self):
        return self._event_bus

    @event_bus.setter
    def event_bus(self, value):
        self._event_bus = value
        # 重新绑定内部 parser 的 event_bus（shim 仍指向 self._forward，动态读取
        # 最新 self._event_bus，因此引擎重连/重启后转发目标自动更新）
        self._parser.event_bus = _EventBusShim(self._forward)

    def parse(self, message):
        """委托内部 PhoneFrameParser 解析（业务入口统一走 Provider）。"""
        self._parser.parse(message)

    @property
    def resolved_device_id(self):
        """hello 之后由解析器回填的真实 device_id；否则用构造时传入的。"""
        return self._parser.device_id or self.device_id

    def capabilities(self):
        # 显式配置优先；否则从解析器已解析的身份取
        if self._capabilities:
            return list(self._capabilities)
        return list(self._parser.device_capabilities)
