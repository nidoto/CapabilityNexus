from output.virtual_xinput import VirtualXInput
from output.virtual_keyboard import VirtualKeyboard
from output.virtual_mouse import VirtualMouse
from output.real_xinput import RealXInputOutput


class OutputRouter:

    #
    # target 前缀 → 输出后端
    # key_*            → 虚拟键盘
    # mouse_*          → 虚拟鼠标
    # xbox.*           → 真实 Xbox One（震动马达等）
    # 其他（摇杆/按钮） → 虚拟 x360 手柄
    #

    PREFIX_BACKENDS = {
        "key_": VirtualKeyboard,
        "mouse_": VirtualMouse,
        "xbox.": RealXInputOutput,
    }

    def __init__(self, virtual_device=None, real_devices=None, event_bus=None):
        self.event_bus = event_bus
        self.virtual = virtual_device or VirtualXInput(0, event_bus=event_bus)
        self.devices = real_devices or {}

    def send(self, target, value):
        backend = self._route(target)

        if backend is not None:
            backend.send(target, value)
            if backend is self.virtual:
                backend.update()
            return

        print("[Router] No backend for target:", target)

    def _route(self, target):
        for prefix, cls in self.PREFIX_BACKENDS.items():
            if target.startswith(prefix):
                if prefix not in self.devices:
                    self.devices[prefix] = cls()
                return self.devices[prefix]

        return self.virtual

    def close(self):
        self.virtual.close()
        for backend in self.devices.values():
            backend.close()
