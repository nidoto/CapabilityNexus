"""角度响应处理器。

把陀螺仪角度（固件已换算为 -32768..32767 轴值）映射到摇杆值：

  - 先由轴值还原为角度（轴值 / 32767 * 180）
  - 死区内的角度归零
  - 按 points 映射到输出百分比
  - 输出 = 百分比 / 100 * 32767

mode:
  linear - 分段线性插值（平滑过渡）
  step   - 阶梯区间：落在哪个角度区间就用该区间的固定百分比
           区间的上边界取 points[i][0]，即角度达到该值进入下一档。

配置示例（游戏专属）：
  {
    "type": "curve",
    "mode": "step",
    "max_degrees": 30,
    "deadzone": 2.5,
    "points": [
      [-30, -100], [-25, -80], [-20, -60], [-15, -30],
      [-10, -20], [-5, -10], [0, 0],
      [5, 10], [10, 20], [15, 30], [20, 60], [25, 80], [30, 100]
    ]
  }

step 模式语义（正侧）：
  0°~5°    -> 10%
  5°~10°   -> 20%
  10°~15°  -> 30%
  15°~20°  -> 60%
  20°~25°  -> 80%
  25°~30°  -> 100%
  30°+     -> 100%
  死区内   -> 0%
"""


class CurveProcessor:

    def __init__(self, max_degrees=30, deadzone=2.5, points=None, mode="step"):
        self.max_degrees = float(max_degrees)
        self.deadzone = float(deadzone)
        self.mode = mode if mode in ("linear", "step") else "step"
        self.points = self._normalize_points(points)

    @staticmethod
    def _normalize_points(points):
        if not points:
            points = [
                [-30, -100], [-25, -80], [-20, -60], [-15, -30],
                [-10, -20], [-5, -10], [0, 0],
                [5, 10], [10, 20], [15, 30], [20, 60], [25, 80],
                [30, 100],
            ]
        return sorted(
            (float(angle), float(pct))
            for angle, pct in points
        )

    @staticmethod
    def _axis_to_angle(value):
        return value / 32767.0 * 180.0

    def process(self, value):
        angle = self._axis_to_angle(value)

        if abs(angle) < self.deadzone:
            return 0

        if angle > self.max_degrees:
            angle = self.max_degrees
        elif angle < -self.max_degrees:
            angle = -self.max_degrees

        pct = self._map(angle)
        return int((pct / 100.0) * 32767.0)

    def _map(self, angle):
        if self.mode == "linear":
            return self._interpolate(angle)
        return self._step(angle)

    def _interpolate(self, angle):
        points = self.points

        if angle <= points[0][0]:
            return points[0][1]
        if angle >= points[-1][0]:
            return points[-1][1]

        for i in range(len(points) - 1):
            a0, p0 = points[i]
            a1, p1 = points[i + 1]

            if a0 <= angle <= a1:
                if a1 == a0:
                    return p1
                ratio = (angle - a0) / (a1 - a0)
                return p0 + ratio * (p1 - p0)

        return angle

    def _step(self, angle):
        """阶梯区间映射。

        points 按角度升序。每个档位 points[i]=(a_i, p_i) 表示：
          角度达到 a_i 后进入该档，输出 p_i，直到达到下一档边界。
        即档位区间为 [a_i, a_{i+1})。
        """
        points = self.points
        sign = 1.0 if angle >= 0 else -1.0
        a = abs(angle)

        # 轴值->角度往返存在 ±0.003° 舍入误差，加微小容差避免档位边界误判
        eps = 0.05

        # 低于最低档边界（含 0）→ 最低档输出
        if a + eps < points[0][0]:
            return points[0][1] * sign

        # 超过最高档直接取最高档
        if a + eps >= points[-1][0]:
            return points[-1][1] * sign

        # 找角度所在的档位：a >= a_i 且 a < a_{i+1}
        for i in range(len(points) - 1):
            a_i, p_i = points[i]
            a_next, _ = points[i + 1]

            if a_i - eps <= a < a_next - eps:
                return p_i * sign

        return points[-1][1] * sign
