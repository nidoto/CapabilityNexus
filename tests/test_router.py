"""OutputRouter 测试：target 前缀路由到正确后端（使用假后端，不依赖硬件）。"""

from output.router import OutputRouter


class FakeBackend:
    output_type = ""

    def __init__(self, name):
        self.name = name
        self.sent = []
        self.closed = False

    def send(self, target, value):
        self.sent.append((target, value))

    def update(self):
        pass

    def close(self):
        self.closed = True


class FakeKeyboard(FakeBackend):
    output_type = "keyboard"


class FakeMouse(FakeBackend):
    output_type = "mouse"


class FakeDS4(FakeBackend):
    output_type = "ds4"


def _router(managed=None, virtual=None):
    return OutputRouter(
        virtual_device=virtual,
        managed_instances=(lambda: managed) if managed is not None else None,
    )


def test_default_target_routes_to_virtual_xinput():
    virtual = FakeBackend("virtual")
    router = _router(virtual=virtual)

    router.send("right_x", 1000)

    assert virtual.sent == [("right_x", 1000)]


def test_keyboard_prefix_uses_managed_instance():
    kb = FakeKeyboard("kb")
    router = _router(managed={"kb": kb})

    router.send("key_w", 1.0)

    assert kb.sent == [("key_w", 1.0)]


def test_mouse_prefix_uses_managed_instance():
    mouse = FakeMouse("m")
    router = _router(managed={"m": mouse})

    router.send("mouse_x", 50)

    assert mouse.sent == [("mouse_x", 50)]


def test_ds4_prefix_uses_managed_instance():
    ds4 = FakeDS4("d")
    router = _router(managed={"d": ds4})

    router.send("ds4.button_cross", 1.0)

    assert ds4.sent == [("ds4.button_cross", 1.0)]


def test_find_managed_matches_output_type():
    xi = FakeBackend("xi")
    xi.output_type = "xinput"
    router = _router(managed={"a": xi}, virtual=FakeBackend("fallback"))

    router.send("button_a", 1.0)

    assert xi.sent == [("button_a", 1.0)]


def test_xbox_prefix_creates_real_backend():
    router = _router()
    router.send("xbox.motor_left", 1000)

    # 真实后端会尝试加载 xinput1_4；没有硬件时仅不应崩溃
    assert "real" in router.devices
