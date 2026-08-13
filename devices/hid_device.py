import threading
import time

from core.stream import StreamData


class HIDDevice:

    #
    # USB HID 设备输入源（pygame joystick）
    # 支持任意 HID 手柄/方向盘/飞行摇杆/杂牌手柄
    #
    # 能力命名：
    #   hid.axis0   - 轴（-1.0 ~ 1.0）
    #   hid.button0 - 按钮（0/1）
    #   hid.hat0_x  - 帽子 X（-1/0/1）
    #   hid.hat0_y  - 帽子 Y（-1/0/1）
    #

    def __init__(self, event_bus, index=0, poll_interval=0.01):
        self.event_bus = event_bus
        self.index = index
        self.poll_interval = poll_interval

        self.running = False
        self.thread = None
        self.joystick = None
        self._pygame = None

    def connect(self):
        try:
            import pygame

            self._pygame = pygame
            pygame.init()
            pygame.joystick.init()

            count = pygame.joystick.get_count()

            if self.index >= count:
                print(f"[HID] No joystick at index {self.index} ({count} found)")
                return False

            self.joystick = pygame.joystick.Joystick(self.index)
            self.joystick.init()

            self.name = self.joystick.get_name()
            self.axes = self.joystick.get_numaxes()
            self.buttons = self.joystick.get_numbuttons()
            self.hats = self.joystick.get_numhats()

            print(
                f"[HID] Connected: {self.name} "
                f"axes={self.axes} buttons={self.buttons} hats={self.hats}"
            )

            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            return True

        except Exception as e:
            print("[HID] Init failed:", e)
            return False

    def _loop(self):
        while self.running:
            self._pygame.event.pump()

            for axis in range(self.axes):
                value = self.joystick.get_axis(axis)
                self.event_bus.publish(
                    StreamData(f"hid.axis{axis}", float(value))
                )

            for button in range(self.buttons):
                value = self.joystick.get_button(button)
                self.event_bus.publish(
                    StreamData(f"hid.button{button}", float(value))
                )

            for hat in range(self.hats):
                hx, hy = self.joystick.get_hat(hat)
                self.event_bus.publish(
                    StreamData(f"hid.hat{hat}_x", float(hx))
                )
                self.event_bus.publish(
                    StreamData(f"hid.hat{hat}_y", float(hy))
                )

            time.sleep(self.poll_interval)

    def close(self):
        self.running = False

        if self.thread:
            self.thread.join(timeout=1)
