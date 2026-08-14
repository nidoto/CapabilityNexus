from output.vgamepad_base import VGamepadDevice


class VirtualXInput(VGamepadDevice):

    output_type = "xinput"

    GAMEPAD_CLASS = None
    BUTTONS_ENUM = None

    AXIS_TARGETS = {
        "left_x": "left",
        "left_y": "left",
        "right_x": "right",
        "right_y": "right",
    }

    TRIGGER_TARGETS = {
        "left_trigger": "left",
        "right_trigger": "right",
    }

    BUTTON_TARGETS = {
        "button_a": "XUSB_GAMEPAD_A",
        "button_b": "XUSB_GAMEPAD_B",
        "button_x": "XUSB_GAMEPAD_X",
        "button_y": "XUSB_GAMEPAD_Y",
        "button_lb": "XUSB_GAMEPAD_LEFT_SHOULDER",
        "button_rb": "XUSB_GAMEPAD_RIGHT_SHOULDER",
        "button_ls": "XUSB_GAMEPAD_LEFT_THUMB",
        "button_rs": "XUSB_GAMEPAD_RIGHT_THUMB",
        "button_start": "XUSB_GAMEPAD_START",
        "button_back": "XUSB_GAMEPAD_BACK",
        "button_dpad_up": "XUSB_GAMEPAD_DPAD_UP",
        "button_dpad_down": "XUSB_GAMEPAD_DPAD_DOWN",
        "button_dpad_left": "XUSB_GAMEPAD_DPAD_LEFT",
        "button_dpad_right": "XUSB_GAMEPAD_DPAD_RIGHT",
    }

    def __init__(self, device_id=0, event_bus=None):
        self.event_bus = event_bus
        super().__init__(device_id)

    def _init_gamepad(self):
        try:
            import vgamepad
        except Exception as error:
            print("[VirtualXInput] vgamepad unavailable:", error)
            return

        self.GAMEPAD_CLASS = vgamepad.VX360Gamepad
        self.BUTTONS_ENUM = vgamepad.XUSB_BUTTON
        super()._init_gamepad()

        if self._real and self.event_bus:
            self._register_request_notification()

    def _register_request_notification(self):
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
            print("[XInput] Request notification failed:", e)
