from output.virtual_xinput import VirtualXInput
from output.real_xinput import RealXInputOutput


class OutputRouter:

    #
    # target 前缀 → 输出后端
    # xbox.*      → 真实 Xbox One 手柄（震动马达等真实输出能力）
    # 其他        → 虚拟 x360 手柄
    #

    REAL_PREFIXES = {
        "xbox": RealXInputOutput,
    }

    def __init__(self, virtual_device=None, real_devices=None):
        self.virtual = virtual_device or VirtualXInput(0)
        self.real = real_devices or {}

    def send(self, target, value):
        backend = self._route(target)

        if backend is not None:
            backend.send(target, value)
            if backend is self.virtual:
                backend.update()
            return

        print("[Router] No backend for target:", target)

    def _route(self, target):
        for prefix, cls in self.REAL_PREFIXES.items():
            if target.startswith(prefix + "."):
                if prefix not in self.real:
                    self.real[prefix] = cls()
                return self.real[prefix]

        return self.virtual

    def close(self):
        self.virtual.close()
        for backend in self.real.values():
            backend.close()
