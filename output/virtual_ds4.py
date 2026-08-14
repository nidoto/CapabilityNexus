from output.base import OutputDevice


class VirtualDS4(OutputDevice):

    #
    # 虚拟 PS4 (DualShock 4) 输出设备
    # 通过 vgamepad VDS4Gamepad（ViGEmBus）
    #
    # 目标：
    #   ds4.left_x / left_y / right_x / right_y - 摇杆
    #   ds4.left_trigger / right_trigger - 扳机
    #   ds4.button_cross / circle / square / triangle
    #   ds4.button_shoulder_left / right
    #   ds4.button_options / share
    #   ds4.button_thumb_left / right
    #

    AXIS_TARGETS = {
        "ds4.left_x": "left",
        "ds4.left_y": "left",
        "ds4.right_x": "right",
        "ds4.right_y": "right",
    }

    TRIGGER_TARGETS = {
        "ds4.left_trigger": "left",
        "ds4.right_trigger": "right",
    }

    BUTTON_TARGETS = {
        "ds4.button_cross": "DS4_BUTTON_CROSS",
        "ds4.button_circle": "DS4_BUTTON_CIRCLE",
        "ds4.button_square": "DS4_BUTTON_SQUARE",
        "ds4.button_triangle": "DS4_BUTTON_TRIANGLE",
        "ds4.button_shoulder_left": "DS4_BUTTON_SHOULDER_LEFT",
        "ds4.button_shoulder_right": "DS4_BUTTON_SHOULDER_RIGHT",
        "ds4.button_options": "DS4_BUTTON_OPTIONS",
        "ds4.button_share": "DS4_BUTTON_SHARE",
        "ds4.button_thumb_left": "DS4_BUTTON_THUMB_LEFT",
        "ds4.button_thumb_right": "DS4_BUTTON_THUMB_RIGHT",
        "ds4.button_trigger_left": "DS4_BUTTON_TRIGGER_LEFT",
        "ds4.button_trigger_right": "DS4_BUTTON_TRIGGER_RIGHT",
    }

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
            self._gamepad = vgamepad.VDS4Gamepad()
            self._real = True
            print("[DS4] Virtual PS4 Gamepad Created")
        except Exception as e:
            print("[DS4] Real gamepad unavailable, using simulation:", e)

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
            print("[DS4] Unknown target:", target)

    def _normalize_axis(self, value):
        if value < -32768:
            value = -32768
        elif value > 32767:
            value = 32767
        return value / 32767.0

    def _normalize_trigger(self, value):
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

        print(f"[DS4] {target} = {value} -> ({x:.3f}, {y:.3f})")

    def _update_trigger(self, target, value):
        normalized = self._normalize_trigger(value)
        side = self.TRIGGER_TARGETS[target]

        self._trigger[side] = normalized

        if self._real:
            getattr(self._gamepad, f"{side}_trigger_float")(normalized)

        print(f"[DS4] {target} = {value} -> {normalized:.3f}")

    def _update_button(self, target, value):
        pressed = bool(value)

        if self._real:
            vg_button = getattr(
                self._vgamepad.DS4_BUTTONS,
                self.BUTTON_TARGETS[target],
            )

            if pressed:
                self._gamepad.press_button(vg_button)
            else:
                self._gamepad.release_button(vg_button)

        print(f"[DS4] {target} = {pressed}")

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
