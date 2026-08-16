"""XInput Windows API 共享定义（结构体、按钮掩码、DLL 加载）。

供检测器、输入设备、真实输出和 HIL 测试共用，避免重复定义 ctypes 结构。
"""

import ctypes
import ctypes.wintypes as wintypes


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", wintypes.DWORD),
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class XINPUT_VIBRATION(ctypes.Structure):
    _fields_ = [
        ("wLeftMotorSpeed", wintypes.WORD),
        ("wRightMotorSpeed", wintypes.WORD),
    ]


# XInput 按钮位掩码
XINPUT_GAMEPAD_DPAD_UP = 0x0001
XINPUT_GAMEPAD_DPAD_DOWN = 0x0002
XINPUT_GAMEPAD_DPAD_LEFT = 0x0004
XINPUT_GAMEPAD_DPAD_RIGHT = 0x0008
XINPUT_GAMEPAD_START = 0x0010
XINPUT_GAMEPAD_BACK = 0x0020
XINPUT_GAMEPAD_LEFT_THUMB = 0x0040
XINPUT_GAMEPAD_RIGHT_THUMB = 0x0080
XINPUT_GAMEPAD_LEFT_SHOULDER = 0x0100
XINPUT_GAMEPAD_RIGHT_SHOULDER = 0x0200
XINPUT_GAMEPAD_A = 0x1000
XINPUT_GAMEPAD_B = 0x2000
XINPUT_GAMEPAD_X = 0x4000
XINPUT_GAMEPAD_Y = 0x8000


def load_xinput():
    """加载 xinput1_4，失败返回 None。"""
    try:
        return ctypes.windll.xinput1_4
    except Exception as error:
        print("[XInput] No xinput1_4:", error)
        return None


def get_state(xinput, index):
    """读取指定槽位 XInput 状态，返回 XINPUT_STATE 或 None。"""
    state = XINPUT_STATE()
    result = xinput.XInputGetState(index, ctypes.byref(state))
    if result != 0:
        return None
    return state
