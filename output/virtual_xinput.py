from output.base import OutputDevice


class VirtualXInput(OutputDevice):

    output_type = "xinput"


    #
    # XInput 目标名（与 profiles 中的映射目标一致）
    #

    AXIS_TARGETS = {

        "left_x": "left",

        "left_y": "left",

        "right_x": "right",

        "right_y": "right"

    }


    TRIGGER_TARGETS = {

        "left_trigger": "left",

        "right_trigger": "right"

    }


    BUTTON_TARGETS = {

        "button_a": "A",

        "button_b": "B",

        "button_x": "X",

        "button_y": "Y",

        "button_lb": "LEFT_SHOULDER",

        "button_rb": "RIGHT_SHOULDER",

        "button_ls": "LEFT_THUMB",

        "button_rs": "RIGHT_THUMB",

        "button_start": "START",

        "button_back": "BACK",

        "button_dpad_up": "DPAD_UP",

        "button_dpad_down": "DPAD_DOWN",

        "button_dpad_left": "DPAD_LEFT",

        "button_dpad_right": "DPAD_RIGHT"

    }


    def __init__(
        self,
        device_id=0,
        event_bus=None
    ):

        super().__init__(
            device_id
        )


        self.event_bus = event_bus


        self._axis = {

            "left": [0.0, 0.0],

            "right": [0.0, 0.0]

        }


        self._trigger = {

            "left": 0.0,

            "right": 0.0

        }


        self._button = {}

        self._gamepad = None

        self._vgamepad = None

        self._real = False


        self._init_gamepad()


    def _init_gamepad(
        self
    ):

        try:

            import vgamepad

            self._vgamepad = vgamepad

            self._gamepad = vgamepad.VX360Gamepad()

            self._real = True

            print(
                "[XInput] Virtual XInput-compatible Gamepad Created"
            )

            self._register_request_notification()

        except Exception as e:

            print(
                "[XInput] Real gamepad unavailable, using simulation:",
                e
            )


    def _register_request_notification(
        self
    ):

        #
        # 游戏对虚拟手柄发送请求（震动反馈）时，
        # vgamepad 会调用此回调。
        # 我们把它转换为 DeviceRequestEvent 发布到 EventBus，
        # 让客户端决定：映射到真实设备 / 其他虚拟设备 / 提示用户。
        #

        if not self.event_bus:
            return

        try:

            from core.system_event import DeviceRequestEvent

            def on_request(client, target, large_motor, small_motor, led_number, user_data):
                self.event_bus.publish(
                    DeviceRequestEvent(
                        source="virtual_x360",
                        target="xbox.motor_left",
                        value=float(large_motor),
                    )
                )
                self.event_bus.publish(
                    DeviceRequestEvent(
                        source="virtual_x360",
                        target="xbox.motor_right",
                        value=float(small_motor),
                    )
                )

            self._gamepad.register_notification(on_request)

        except Exception as e:

            print(
                "[XInput] Request notification failed:",
                e
            )


    @property
    def real(
        self
    ):

        return self._real


    def send(
        self,
        target,
        value
    ):

        if target in self.AXIS_TARGETS:

            self._update_axis(
                target,
                value
            )

        elif target in self.TRIGGER_TARGETS:

            self._update_trigger(
                target,
                value
            )

        elif target in self.BUTTON_TARGETS:

            self._update_button(
                target,
                value
            )

        else:

            print(
                "[XInput] Unknown target:",
                target
            )


    #
    # -32768 ~ 32767 归一化为 -1.0 ~ 1.0
    #

    @staticmethod
    def _normalize_axis(
        value
    ):

        if value < -32768:

            value = -32768

        elif value > 32767:

            value = 32767


        return value / 32767.0


    #
    # 0 ~ 255 归一化为 0.0 ~ 1.0
    #

    @staticmethod
    def _normalize_trigger(
        value
    ):

        if value < 0:

            value = 0

        elif value > 255:

            value = 255


        return value / 255.0


    def _update_axis(
        self,
        target,
        value
    ):

        normalized = self._normalize_axis(
            value
        )


        side = self.AXIS_TARGETS[target]


        x, y = self._axis[side]


        if target.endswith(
            "_x"
        ):

            x = normalized

        else:

            y = normalized


        self._axis[side] = [x, y]


        if self._real:

            getattr(
                self._gamepad,
                f"{side}_joystick_float"
            )(
                x,
                y
            )


    def _update_trigger(
        self,
        target,
        value
    ):

        normalized = self._normalize_trigger(
            value
        )


        side = self.TRIGGER_TARGETS[target]


        self._trigger[side] = normalized


        if self._real:

            getattr(
                self._gamepad,
                f"{side}_trigger_float"
            )(
                normalized
            )


    def _update_button(
        self,
        target,
        value
    ):

        pressed = bool(
            value
        )


        self._button[target] = pressed


        if self._real:

            vg_button = getattr(
                self._vgamepad.XUSB_BUTTON,
                f"XUSB_GAMEPAD_{self.BUTTON_TARGETS[target]}"
            )


            if pressed:

                self._gamepad.press_button(
                    vg_button
                )

            else:

                self._gamepad.release_button(
                    vg_button
                )


    def update(
        self
    ):

        if self._real:

            self._gamepad.update()


    def set_axis(
        self,
        axis,
        value
    ):

        self.send(
            axis,
            value
        )


    def set_button(
        self,
        button,
        pressed
    ):

        self.send(
            button,
            1.0 if pressed else 0.0
        )


    def set_trigger(
        self,
        trigger,
        value
    ):

        self.send(
            trigger,
            value
        )


    def close(
        self
    ):

        if self._real:

            self._gamepad.reset()
