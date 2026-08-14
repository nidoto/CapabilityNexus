from output.base import OutputDevice


class VGamepadDevice(OutputDevice):

    #
    # vgamepad (ViGEmBus) 输出设备公共基类
    # XInput / DualShock 共用：摇杆/扳机/按钮的归一化与更新逻辑
    #
    # 子类需要定义：
    #   GAMEPAD_CLASS   - vgamepad 手柄类（如 VX360Gamepad / VDS4Gamepad）
    #   BUTTONS_ENUM    - vgamepad 按钮枚举（如 XUSB_BUTTON / DS4_BUTTONS）
    #   AXIS_TARGETS    - {目标: 左/右摇杆}
    #   TRIGGER_TARGETS - {目标: 左/右扳机}
    #   BUTTON_TARGETS  - {目标: 按钮枚举成员名}
    #

    GAMEPAD_CLASS = None
    BUTTONS_ENUM = None
    AXIS_TARGETS = {}
    TRIGGER_TARGETS = {}
    BUTTON_TARGETS = {}

    def __init__(self, device_id=0):
        super().__init__(device_id)

        self._axis = {
            "left": [0.0, 0.0],
            "right": [0.0, 0.0],
        }
        self._trigger = {
            "left": 0.0,
            "right": 0.0,
        }

        self._gamepad = None
        self._vgamepad = None
        self._real = False

        self._init_gamepad()

    def _init_gamepad(self):
        try:
            import vgamepad

            self._vgamepad = vgamepad
            self._gamepad = self.GAMEPAD_CLASS()
            self._real = True
            print(f"[{type(self).__name__}] Virtual gamepad Created")
        except Exception as e:
            print(f"[{type(self).__name__}] Real gamepad unavailable, using simulation:", e)

    @property
    def real(self):
        return self._real

    def send(self, target, value):
        if target in self.AXIS_TARGETS:
            self._update_axis(target, value)
        elif target in self.TRIGGER_TARGETS:
            self._update_trigger(target, value)
        elif target in self.BUTTON_TARGETS:
            self._update_button(target, value)
        else:
            print(f"[{type(self).__name__}] Unknown target:", target)

    @staticmethod
    def _normalize_axis(value):
        if value < -32768:
            value = -32768
        elif value > 32767:
            value = 32767
        return value / 32767.0

    @staticmethod
    def _normalize_trigger(value):
        if value < 0:
            value = 0
        elif value > 255:
            value = 255
        return value / 255.0

    def _update_axis(self, target, value):
        normalized = self._normalize_axis(value)
        side = self.AXIS_TARGETS[target]

        x, y = self._axis[side]

        if target.endswith("_x"):
            x = normalized
        else:
            y = normalized

        self._axis[side] = [x, y]

        if self._real:
            getattr(self._gamepad, f"{side}_joystick_float")(x, y)

    def _update_trigger(self, target, value):
        normalized = self._normalize_trigger(value)
        side = self.TRIGGER_TARGETS[target]

        self._trigger[side] = normalized

        if self._real:
            getattr(self._gamepad, f"{side}_trigger_float")(normalized)

    def _update_button(self, target, value):
        pressed = bool(value)

        if self._real:
            vg_button = getattr(
                self.BUTTONS_ENUM,
                self.BUTTON_TARGETS[target],
            )

            if pressed:
                self._gamepad.press_button(vg_button)
            else:
                self._gamepad.release_button(vg_button)

    def update(self):
        if self._real:
            self._gamepad.update()

    def set_axis(self, axis, value):
        self.send(axis, value)

    def set_button(self, button, pressed):
        self.send(button, 1.0 if pressed else 0.0)

    def set_trigger(self, trigger, value):
        self.send(trigger, value)

    def close(self):
        if self._real:
            self._gamepad.reset()
