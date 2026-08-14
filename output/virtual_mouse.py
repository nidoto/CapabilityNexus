from output.base import OutputDevice


class VirtualMouse(OutputDevice):

    output_type = "mouse"

    #
    # 虚拟鼠标输出设备
    # 目标格式：
    #   mouse_x / mouse_y      - 移动（相对像素，有符号）
    #   mouse_scroll           - 滚轮
    #   mouse_click_left / mouse_click_right / mouse_click_middle - 点击
    #

    def __init__(self, device_id=0):
        super().__init__(device_id)

        self._mouse = None
        self._real = False
        self._pressed = set()

        self._init_mouse()

    def _init_mouse(self):
        try:
            from pynput.mouse import Controller

            self._mouse = Controller()
            self._real = True
            print("[Mouse] Virtual Mouse Ready")
        except Exception as e:
            print("[Mouse] Mouse backend unavailable, using stub:", e)

    @property
    def real(self):
        return self._real

    def send(self, target, value):
        if not target.startswith("mouse_"):
            return

        action = target[6:]

        if not self._real:
            print(f"[Mouse] {target} = {value}")
            return

        try:
            if action == "x":
                self._mouse.move(int(value), 0)
            elif action == "y":
                self._mouse.move(0, int(value))
            elif action == "scroll":
                self._mouse.scroll(0, int(value))
            elif action == "click_left":
                self._click(0, value)
            elif action == "click_right":
                self._click(1, value)
            elif action == "click_middle":
                self._click(2, value)

            print(f"[Mouse] {target} = {value}")
        except Exception as e:
            print("[Mouse] Error:", e)

    def _click(self, button_index, value):
        from pynput.mouse import Button

        buttons = [Button.left, Button.right, Button.middle]
        button = buttons[button_index]

        if bool(value):
            self._mouse.press(button)
            self._pressed.add(button)
        else:
            self._mouse.release(button)
            self._pressed.discard(button)

    def set_button(self, button, pressed):
        self.send(button, 1.0 if pressed else 0.0)

    def close(self):
        if not self._real:
            return
        for button in list(self._pressed):
            try:
                self._mouse.release(button)
            except Exception:
                pass
        self._pressed.clear()
