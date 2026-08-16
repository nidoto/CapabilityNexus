import ctypes
import threading
import time

from core.stream import StreamData
from devices.xinput_api import XINPUT_GAMEPAD_A
from devices.xinput_api import XINPUT_GAMEPAD_B
from devices.xinput_api import XINPUT_GAMEPAD_BACK
from devices.xinput_api import XINPUT_GAMEPAD_DPAD_DOWN
from devices.xinput_api import XINPUT_GAMEPAD_DPAD_LEFT
from devices.xinput_api import XINPUT_GAMEPAD_DPAD_RIGHT
from devices.xinput_api import XINPUT_GAMEPAD_DPAD_UP
from devices.xinput_api import XINPUT_GAMEPAD_LEFT_SHOULDER
from devices.xinput_api import XINPUT_GAMEPAD_LEFT_THUMB
from devices.xinput_api import XINPUT_GAMEPAD_RIGHT_SHOULDER
from devices.xinput_api import XINPUT_GAMEPAD_RIGHT_THUMB
from devices.xinput_api import XINPUT_GAMEPAD_START
from devices.xinput_api import XINPUT_GAMEPAD_X
from devices.xinput_api import XINPUT_GAMEPAD_Y
from devices.xinput_api import XINPUT_STATE
from devices.xinput_api import get_state
from devices.xinput_api import load_xinput


class XInputDevice:

    @staticmethod
    def detect_connected():
        """返回已连接 XInput 设备的槽位列表 [0, 1, ...]"""
        connected = []

        xinput = load_xinput()
        if xinput is None:
            return connected

        for index in range(4):
            if get_state(xinput, index) is not None:
                connected.append(index)

        return connected

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
        self._xinput = load_xinput()
        if self._xinput is None:
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

            # 始终发布当前状态，保证实时监控显示最新值
            self._emit_state(state)
            if self._last_state is None or state.dwPacketNumber != self._last_state.dwPacketNumber:
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
