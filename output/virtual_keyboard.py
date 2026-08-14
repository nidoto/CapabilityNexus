from output.base import OutputDevice


class VirtualKeyboard(OutputDevice):

    output_type = "keyboard"

    #
    # 虚拟键盘输出设备
    # 目标格式：key_<键名>（如 key_w, key_a, key_space, key_enter）
    # 值：1 按下 / 0 释放
    #

    def __init__(self, device_id=0):
        super().__init__(device_id)

        self._keyboard = None
        self._real = False

        self._init_keyboard()

    def _init_keyboard(self):
        try:
            from pynput.keyboard import Controller

            self._keyboard = Controller()
            self._real = True
            print("[Keyboard] Virtual Keyboard Ready")
        except Exception as e:
            print("[Keyboard] Keyboard unavailable, using simulation:", e)

    @property
    def real(self):
        return self._real

    def send(self, target, value):
        if not target.startswith("key_"):
            return

        key_name = target[4:]
        pressed = bool(value)

        if not self._real:
            print(f"[Keyboard] {target} = {pressed}")
            return

        try:
            from pynput.keyboard import Key

            key = self._resolve_key(key_name)

            if pressed:
                self._keyboard.press(key)
            else:
                self._keyboard.release(key)

            print(f"[Keyboard] {target} = {pressed}")
        except Exception as e:
            print("[Keyboard] Error:", e)

    def _resolve_key(self, key_name):
        from pynput.keyboard import Key

        special = {
            "enter": Key.enter,
            "space": Key.space,
            "tab": Key.tab,
            "esc": Key.esc,
            "backspace": Key.backspace,
            "shift": Key.shift,
            "ctrl": Key.ctrl,
            "alt": Key.alt,
            "up": Key.up,
            "down": Key.down,
            "left": Key.left,
            "right": Key.right,
            "f1": Key.f1,
            "f2": Key.f2,
            "f3": Key.f3,
            "f4": Key.f4,
            "f5": Key.f5,
            "f6": Key.f6,
            "f7": Key.f7,
            "f8": Key.f8,
            "f9": Key.f9,
            "f10": Key.f10,
            "f11": Key.f11,
            "f12": Key.f12,
        }

        if key_name in special:
            return special[key_name]

        if len(key_name) == 1:
            return key_name.lower()

        raise ValueError(f"Unknown key: {key_name}")

    def set_button(self, button, pressed):
        self.send(button, 1.0 if pressed else 0.0)

    def close(self):
        pass
