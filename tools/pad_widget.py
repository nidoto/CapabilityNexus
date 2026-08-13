import tkinter as tk


class VirtualPadWidget:

    #
    # 虚拟 Xbox 360 手柄图形控件
    #
    # 每个通道是可点击的热区：
    #   left_x / left_y / right_x / right_y / left_trigger / right_trigger
    #   button_a / button_b / button_x / button_y
    #   button_lb / button_rb / button_start / button_back
    #   button_dpad_up / button_dpad_down / button_dpad_left / button_dpad_right
    #
    # 点击通道触发 on_channel_click(channel_id)
    #

    CHANNELS = [
        ("button_a", "A"),
        ("button_b", "B"),
        ("button_x", "X"),
        ("button_y", "Y"),
        ("button_lb", "LB"),
        ("button_rb", "RB"),
        ("button_start", "START"),
        ("button_back", "BACK"),
        ("button_dpad_up", "DPAD"),
        ("button_dpad_down", "DPAD"),
        ("button_dpad_left", "DPAD"),
        ("button_dpad_right", "DPAD"),
        ("left_trigger", "LT"),
        ("right_trigger", "RT"),
        ("left_x", "L-STICK"),
        ("right_x", "R-STICK"),
    ]

    def __init__(self, parent, on_channel_click=None, width=520, height=320):
        self.on_channel_click = on_channel_click
        self.hotspots = {}

        self.canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            bg="#1e1e1e",
            highlightthickness=0,
        )
        self.canvas.pack()

        self.canvas.bind("<Button-1>", self._on_click)
        self._draw()

    def _on_click(self, event):
        for channel_id, region in self.hotspots.items():
            x1, y1, x2, y2 = region
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                if self.on_channel_click:
                    self.on_channel_click(channel_id)
                return

    def _oval_btn(self, cx, cy, r, channel_id, label):
        self.hotspots[channel_id] = (cx - r, cy - r, cx + r, cy + r)
        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill="#3a3a3a",
            outline="#555",
        )
        self.canvas.create_text(
            cx, cy, text=label, fill="#ccc", font=("Arial", 10, "bold"),
        )

    def _stick(self, cx, cy, channel_id, label):
        self.hotspots[channel_id] = (cx - 38, cy - 38, cx + 38, cy + 38)
        self.canvas.create_oval(
            cx - 35, cy - 35, cx + 35, cy + 35,
            fill="#2a2a2a",
            outline="#666",
        )
        self.canvas.create_oval(
            cx - 15, cy - 15, cx + 15, cy + 15,
            fill="#444",
            outline="#666",
        )
        self.canvas.create_text(
            cx, cy + 48, text=label, fill="#888", font=("Arial", 8),
        )

    def _trigger(self, x, y, channel_id, label):
        self.hotspots[channel_id] = (x - 40, y - 18, x + 40, y + 18)
        self.canvas.create_rectangle(
            x - 40, y - 18, x + 40, y + 18,
            fill="#3a3a3a",
            outline="#555",
        )
        self.canvas.create_text(
            x, y, text=label, fill="#ccc", font=("Arial", 9, "bold"),
        )

    def _dpad(self, cx, cy, ids):
        size = 12
        positions = [
            ("button_dpad_up", cx, cy - 26),
            ("button_dpad_down", cx, cy + 26),
            ("button_dpad_left", cx - 26, cy),
            ("button_dpad_right", cx + 26, cy),
        ]

        for channel_id, px, py in positions:
            self.hotspots[channel_id] = (px - size, py - size, px + size, py + size)
            self.canvas.create_rectangle(
                px - size, py - size, px + size, py + size,
                fill="#3a3a3a",
                outline="#555",
            )

        self.canvas.create_text(
            cx, cy + 40, text="DPAD", fill="#888", font=("Arial", 8),
        )

    def _draw(self):
        canvas = self.canvas

        # 手柄主体
        canvas.create_oval(
            60, 60, 260, 290,
            fill="#2a2a2a",
            outline="#444",
            width=2,
        )
        canvas.create_oval(
            260, 60, 460, 290,
            fill="#2a2a2a",
            outline="#444",
            width=2,
        )
        canvas.create_rectangle(
            150, 60, 370, 290,
            fill="#2a2a2a",
            outline="#444",
        )

        # 左摇杆
        self._stick(140, 165, "left_x", "L-STICK (click to map)")

        # 右摇杆
        self._stick(380, 165, "right_x", "R-STICK (click to map)")

        # D-pad
        self._dpad(140, 250, [
            "button_dpad_up",
            "button_dpad_down",
            "button_dpad_left",
            "button_dpad_right",
        ])

        # ABXY 按钮
        self._oval_btn(300, 110, 16, "button_y", "Y")
        self._oval_btn(330, 140, 16, "button_b", "B")
        self._oval_btn(270, 140, 16, "button_a", "A")
        self._oval_btn(300, 170, 16, "button_x", "X")

        # LB / RB
        self._trigger(175, 80, "button_lb", "LB")
        self._trigger(345, 80, "button_rb", "RB")

        # Start / Back
        self._oval_btn(250, 240, 10, "button_back", "·")
        self._oval_btn(270, 240, 10, "button_start", "··")

        # 扳机
        self._trigger(175, 45, "left_trigger", "LT")
        self._trigger(345, 45, "right_trigger", "RT")
