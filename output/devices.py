class OutputDeviceInfo:

    def __init__(self, device_id, name, description, targets):
        self.id = device_id
        self.name = name
        self.description = description
        self.targets = targets


OUTPUT_DEVICES = [
    OutputDeviceInfo(
        "virtual_x360",
        "XInput-compatible Virtual Controller",
        "Standard game controller protocol (XInput compatible)",
        {
            "left_x": "Left Stick X",
            "left_y": "Left Stick Y",
            "right_x": "Right Stick X",
            "right_y": "Right Stick Y",
            "left_trigger": "Left Trigger",
            "right_trigger": "Right Trigger",
            "button_a": "A Button",
            "button_b": "B Button",
            "button_x": "X Button",
            "button_y": "Y Button",
            "button_lb": "Left Bumper",
            "button_rb": "Right Bumper",
            "button_ls": "Left Stick Press",
            "button_rs": "Right Stick Press",
            "button_start": "Start",
            "button_back": "Back",
            "button_dpad_up": "D-Pad Up",
            "button_dpad_down": "D-Pad Down",
            "button_dpad_left": "D-Pad Left",
            "button_dpad_right": "D-Pad Right",
        },
    ),
    OutputDeviceInfo(
        "virtual_keyboard",
        "Virtual Keyboard",
        "Emulate keyboard key presses",
        {
            "key_w": "W Key",
            "key_a": "A Key",
            "key_s": "S Key",
            "key_d": "D Key",
            "key_space": "Space",
            "key_enter": "Enter",
            "key_shift": "Shift",
            "key_ctrl": "Ctrl",
            "key_alt": "Alt",
            "key_1": "1 Key",
            "key_2": "2 Key",
            "key_3": "3 Key",
            "key_f1": "F1",
            "key_f2": "F2",
            "key_f3": "F3",
            "key_f4": "F4",
            "key_f5": "F5",
            "key_f6": "F6",
            "key_f7": "F7",
            "key_f8": "F8",
            "key_f9": "F9",
            "key_f10": "F10",
            "key_f11": "F11",
            "key_f12": "F12",
        },
    ),
    OutputDeviceInfo(
        "virtual_mouse",
        "Virtual Mouse",
        "Emulate mouse movement and clicks",
        {
            "mouse_x": "Move X",
            "mouse_y": "Move Y",
            "mouse_scroll": "Scroll",
            "mouse_click_left": "Left Click",
            "mouse_click_right": "Right Click",
            "mouse_click_middle": "Middle Click",
        },
    ),
    OutputDeviceInfo(
        "virtual_ds4",
        "DualShock Protocol Virtual Controller",
        "Standard game controller protocol (DualShock 4 compatible)",
        {
            "ds4.left_x": "Left Stick X",
            "ds4.left_y": "Left Stick Y",
            "ds4.right_x": "Right Stick X",
            "ds4.right_y": "Right Stick Y",
            "ds4.left_trigger": "Left Trigger",
            "ds4.right_trigger": "Right Trigger",
            "ds4.button_cross": "Cross",
            "ds4.button_circle": "Circle",
            "ds4.button_square": "Square",
            "ds4.button_triangle": "Triangle",
            "ds4.button_shoulder_left": "L1",
            "ds4.button_shoulder_right": "R1",
            "ds4.button_trigger_left": "L2",
            "ds4.button_trigger_right": "R2",
            "ds4.button_options": "Options",
            "ds4.button_share": "Share",
            "ds4.button_thumb_left": "Left Stick Press",
            "ds4.button_thumb_right": "Right Stick Press",
        },
    ),
]


def get_output_device(device_id):
    for device in OUTPUT_DEVICES:
        if device.id == device_id:
            return device
    return None
