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
    #   hold    - 按住 source，输出 target 持续为 1（松开为 0）
    #   tap     - source 按下瞬间，输出 target 一次 1 后回 0
    #   invert  - 反转值（1 <-> 0）
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
