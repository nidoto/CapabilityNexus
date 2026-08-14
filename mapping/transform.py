import json
import time


class TransformLayer:

    #
    # Transform Layer：
    # 在 ProcessedChannel 与 MappingEngine 之间插入的能力变换。
    #
    # 变换规则（config/transforms.json）：
    #   { "source": "xbox.a", "type": "hold", "target": "xbox.b" }
    #
    # 内置变换：
    #   hold        - 按住 source，输出 target 持续为 1（松开为 0）
    #   tap         - source 按下瞬间，输出 target 一次 1 后回 0
    #   invert      - 反转值（1 <-> 0）
    #   long_press  - 长按触发：按下超过 duration 秒，松开时触发
    #   double_tap  - 连按两次（interval 秒内）触发
    #   hold_repeat - 按住时按 interval 秒间隔重复触发
    #
    # 变换输出会被标记 transformed，避免再次变换。
    #

    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.rules = []
        self._state = {}

    def load(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.rules = data.get("transforms", [])

        print("[Transform] Loaded", len(self.rules), "rules")

        for rule in self.rules:
            print("[Transform]", rule)

    def process(self, channel):
        if getattr(channel, "transformed", False):
            return [channel]

        matched = False
        results = []

        for rule in self.rules:
            if rule.get("source") != channel.id:
                continue

            matched = True

            transform_type = rule.get("type", "hold")
            target = rule.get("target", channel.id)
            params = rule.get("params", {})

            outputs = self._apply(
                transform_type,
                channel,
                target,
                params,
            )

            if outputs:
                results.extend(outputs)

        if matched:
            return results

        return [channel]

    def _apply(self, transform_type, channel, target, params):
        value = channel.value
        key = channel.id
        now = time.monotonic()

        if transform_type == "invert":
            inverted = 1.0 if value == 0 else 0.0
            return [self._transformed(target, channel.category, inverted)]

        if transform_type == "tap":
            last = self._state.get(("tap", key), 0)
            self._state[("tap", key)] = value

            if value > 0 and last == 0:
                return [
                    self._transformed(target, channel.category, 1.0),
                ]

            return []

        if transform_type == "hold":
            return [self._transformed(target, channel.category, value)]

        if transform_type == "long_press":
            # 按下记录开始时间，松开时判定时长
            duration = float(params.get("duration", 3.0))

            if value > 0:
                if ("long_press", key) not in self._state:
                    self._state[("long_press", key)] = now
                return []
            else:
                start = self._state.pop(("long_press", key), None)

                if start is not None and (now - start) >= duration:
                    return [self._transformed(target, channel.category, 1.0)]

                return []

        if transform_type == "double_tap":
            # 连按两次（间隔内）触发
            interval = float(params.get("interval", 0.4))

            if value > 0:
                last_press = self._state.get(("double_tap", key), 0)
                self._state[("double_tap", key)] = now

                if last_press and (now - last_press) <= interval:
                    self._state[("double_tap", key)] = 0
                    return [self._transformed(target, channel.category, 1.0)]

                return []

            return []

        if transform_type == "hold_repeat":
            # 按住时按间隔重复触发
            interval = float(params.get("interval", 0.2))

            if value > 0:
                last_sent = self._state.get(("hold_repeat", key), 0)

                if last_sent == 0 or (now - last_sent) >= interval:
                    self._state[("hold_repeat", key)] = now
                    return [self._transformed(target, channel.category, 1.0)]

                return []

            self._state.pop(("hold_repeat", key), None)
            return []

        return []

    def _transformed(self, target, category, value):
        from core.processed_channel import ProcessedChannel

        return ProcessedChannel(
            target,
            category,
            value,
            capability=None,
            transformed=True,
        )
