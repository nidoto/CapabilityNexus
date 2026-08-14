from output.vgamepad_base import VGamepadDevice


class VirtualDS4(VGamepadDevice):

    output_type = "ds4"

    GAMEPAD_CLASS = None
    BUTTONS_ENUM = None

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

    def _init_gamepad(self):
        import vgamepad

        self.GAMEPAD_CLASS = vgamepad.VDS4Gamepad
        self.BUTTONS_ENUM = vgamepad.DS4_BUTTONS
        super()._init_gamepad()
