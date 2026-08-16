import ctypes

from devices.xinput_api import XINPUT_VIBRATION
from devices.xinput_api import load_xinput
from output.base import OutputDevice


class RealXInputOutput(OutputDevice):

    #
    # 真实 Xbox One 手柄的输出能力（震动马达）
    # 通过 XInputSetState 直接驱动真实硬件
    #

    MOTOR_TARGETS = {
        "xbox.motor_left": "left",
        "xbox.motor_right": "right",
    }

    def __init__(self, device_id=0, index=0):
        super().__init__(device_id)
        self.index = index

        self._vibration = XINPUT_VIBRATION(0, 0)
        self._xinput = None
        self._real = False

        self._init_xinput()

    def _init_xinput(self):
        self._xinput = load_xinput()
        if self._xinput is not None:
            self._real = True
            print("[RealXInput] Real Xbox output ready (slot", self.index, ")")

    @property
    def real(self):
        return self._real

    def send(self, target, value):
        if target in self.MOTOR_TARGETS:
            self._set_motor(self.MOTOR_TARGETS[target], value)
        else:
            print("[RealXInput] Unknown target:", target)

    def _set_motor(self, side, value):
        if value < 0:
            value = 0
        elif value > 65535:
            value = 65535

        value = int(value)

        if side == "left":
            self._vibration.wLeftMotorSpeed = value
        else:
            self._vibration.wRightMotorSpeed = value

        if self._real:
            self._xinput.XInputSetState(
                self.index,
                ctypes.byref(self._vibration),
            )

        print(f"[RealXInput] motor_{side} = {value}")

    def set_axis(self, axis, value):
        self.send(axis, value)

    def set_button(self, button, pressed):
        pass

    def set_trigger(self, trigger, value):
        self.send(trigger, value)

    def close(self):
        if self._real:
            self._vibration.wLeftMotorSpeed = 0
            self._vibration.wRightMotorSpeed = 0
            self._xinput.XInputSetState(
                self.index,
                ctypes.byref(self._vibration),
            )
