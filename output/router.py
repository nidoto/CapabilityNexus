from output.virtual_xinput import VirtualXInput
from output.virtual_keyboard import VirtualKeyboard
from output.virtual_mouse import VirtualMouse
from output.virtual_ds4 import VirtualDS4
from output.real_xinput import RealXInputOutput


class OutputRouter:

    #
    # target 前缀 → 输出后端类型
    # key_*            → 键盘
    # mouse_*          → 鼠标
    # ds4.*            → DualShock 兼容
    # xbox.*           → 真实 XInput 设备（震动等）
    # 其他（摇杆/按钮） → XInput 兼容控制器
    #

    PREFIX_TYPES = {
        "key_": "keyboard",
        "mouse_": "mouse",
        "ds4.": "ds4",
        "xbox.": "real",
    }

    DEFAULT_BACKENDS = {
        "keyboard": VirtualKeyboard,
        "mouse": VirtualMouse,
        "ds4": VirtualDS4,
        "real": RealXInputOutput,
    }

    def __init__(self, virtual_device=None, real_devices=None, event_bus=None,
                 managed_instances=None):
        self.event_bus = event_bus
        self.virtual = virtual_device

        # managed_instances: callable(id) -> instance（用户启用的输出设备）
        self.managed_instances = managed_instances or (lambda _id: None)

        self.devices = real_devices or {}

    def send(self, target, value):
        backend = self._route(target)

        if backend is not None:
            backend.send(target, value)

            if isinstance(backend, VirtualXInput):
                backend.update()

            return

        print("[Router] No backend for target:", target)

    def _route(self, target):
        backend_type = None

        for prefix, btype in self.PREFIX_TYPES.items():
            if target.startswith(prefix):
                backend_type = btype
                break

        if backend_type == "real":
            # 真实设备输出（震动等），按需创建
            if "real" not in self.devices:
                self.devices["real"] = RealXInputOutput()
            return self.devices["real"]

        if backend_type in ("keyboard", "mouse", "ds4"):
            # 优先使用用户启用的实例，否则按类型查找或自动创建
            instance = self._find_managed(backend_type)

            if instance is not None:
                return instance

            if backend_type not in self.devices:
                cls = self.DEFAULT_BACKENDS[backend_type]
                self.devices[backend_type] = cls()

            return self.devices[backend_type]

        # 默认：XInput 兼容控制器
        managed = self._find_managed("xinput")
        if managed is not None:
            return managed

        if self.virtual is None:
            self.virtual = VirtualXInput(0, event_bus=self.event_bus)
        return self.virtual

    def _find_managed(self, backend_type):
        if not self.managed_instances:
            return None

        # managed_instances 是所有输出设备的实例字典
        instances = self.managed_instances()

        if not isinstance(instances, dict):
            return None

        for instance in instances.values():
            inst_type = getattr(instance, "output_type", None)

            if inst_type is None:
                inst_type = type(instance).__name__.lower()

            if backend_type in inst_type or inst_type in backend_type:
                return instance

        return None

    def close(self):
        if self.virtual is not None:
            self.virtual.close()

        for backend in self.devices.values():
            backend.close()
