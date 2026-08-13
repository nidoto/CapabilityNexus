import ctypes
import threading
import time

from ctypes import wintypes

from core.stream import StreamData


#
# XInput 按钮位掩码
#

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


class XInputDevice:

    def __init__(self, event_bus, index=0, poll_interval=0.01):
        self.event_bus = event_bus
        self.index = index
        self.poll_interval = poll_interval

        self.running = False
        self.thread = None

        self._xinput = None
        self._connected = False
        self._last_state = None

    def connect(self):
        try:
            self._xinput = ctypes.windll.xinput1_4
        except Exception as e:
            print("[XInputDevice] Failed to load xinput1_4:", e)
            return False

        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        print(f"[XInputDevice] Polling controller {self.index}")
        return True

    def _poll_loop(self):
        while self.running:
            state = XINPUT_STATE()
            result = self._xinput.XInputGetState(self.index, ctypes.byref(state))

            if result != 0:
                if self._connected:
                    self._connected = False
                    self._last_state = None
                    print(f"[XInputDevice] Controller {self.index} disconnected")
                time.sleep(0.5)
                continue

            if not self._connected:
                self._connected = True
                self._last_state = None
                print(f"[XInputDevice] Controller {self.index} connected")

            if self._last_state is None or state.dwPacketNumber != self._last_state.dwPacketNumber:
                self._emit_state(state)
                self._last_state = state

            time.sleep(self.poll_interval)

    def _emit_state(self, state):
        def publish(capability, value):
            self.event_bus.publish(StreamData(capability, value))

        publish("xbox.left_x", float(state.sThumbLX))
        publish("xbox.left_y", float(state.sThumbLY))
        publish("xbox.right_x", float(state.sThumbRX))
        publish("xbox.right_y", float(state.sThumbRY))
        publish("xbox.left_trigger", float(state.bLeftTrigger))
        publish("xbox.right_trigger", float(state.bRightTrigger))

        buttons = [
            ("xbox.a", XINPUT_GAMEPAD_A),
            ("xbox.b", XINPUT_GAMEPAD_B),
            ("xbox.x", XINPUT_GAMEPAD_X),
            ("xbox.y", XINPUT_GAMEPAD_Y),
            ("xbox.lb", XINPUT_GAMEPAD_LEFT_SHOULDER),
            ("xbox.rb", XINPUT_GAMEPAD_RIGHT_SHOULDER),
            ("xbox.ls", XINPUT_GAMEPAD_LEFT_THUMB),
            ("xbox.rs", XINPUT_GAMEPAD_RIGHT_THUMB),
            ("xbox.start", XINPUT_GAMEPAD_START),
            ("xbox.back", XINPUT_GAMEPAD_BACK),
            ("xbox.dpad_up", XINPUT_GAMEPAD_DPAD_UP),
            ("xbox.dpad_down", XINPUT_GAMEPAD_DPAD_DOWN),
            ("xbox.dpad_left", XINPUT_GAMEPAD_DPAD_LEFT),
            ("xbox.dpad_right", XINPUT_GAMEPAD_DPAD_RIGHT),
        ]

        for capability, mask in buttons:
            publish(capability, 1.0 if state.wButtons & mask else 0.0)

    def close(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
