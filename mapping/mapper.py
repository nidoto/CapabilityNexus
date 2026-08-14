from core.processed_channel import ProcessedChannel
from core.system_event import OutputEvent
import json


class MappingEngine:

    def __init__(self, event_bus):
        self.event_bus = event_bus

        # source -> [ {target, gain, return_to_center}, ... ]
        self.mapping = {}

        # target -> {source: value} 用于多对一合并
        self._target_sources = {}

        event_bus.subscribe(
            ProcessedChannel,
            self.receive,
        )

    def add_mapping(self, source, targets):
        if isinstance(targets, dict):
            targets = [targets]

        self.mapping[source] = targets

        for t in targets:
            target = t.get("target")
            if target not in self._target_sources:
                self._target_sources[target] = {}
            self._target_sources[target][source] = None

    def load_profile(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        mappings = data.get("mappings", {})

        for source, mapping in mappings.items():
            targets = self._normalize(mapping)

            self.add_mapping(source, targets)

            print("[Profile]", source, "->", [
                t["target"] for t in targets
            ])

    @staticmethod
    def _normalize(mapping):
        if isinstance(mapping, str):
            return [{"target": mapping, "gain": 1.0, "return_to_center": False}]

        if isinstance(mapping, dict):
            return [{
                "target": mapping.get("target", "?"),
                "gain": mapping.get("gain", 1.0),
                "return_to_center": mapping.get("return_to_center", False),
            }]

        if isinstance(mapping, list):
            result = []
            for item in mapping:
                if isinstance(item, str):
                    result.append({
                        "target": item,
                        "gain": 1.0,
                        "return_to_center": False,
                    })
                else:
                    result.append({
                        "target": item.get("target", "?"),
                        "gain": item.get("gain", 1.0),
                        "return_to_center": item.get("return_to_center", False),
                    })
            return result

        return []

    def receive(self, channel):
        if channel.id not in self.mapping:
            return

        configs = self.mapping[channel.id]

        for config in configs:
            target = config["target"]
            value = channel.value * config["gain"]

            # 记录该 source 对 target 的最近值
            self._target_sources[target][channel.id] = value

            sources = self._target_sources[target]

            if len(sources) == 1:
                # 一对多 / 一对一：直接发布
                self._publish(channel.id, target, value, config["gain"])
            else:
                # 多对一：最后更新的 source 生效
                self._publish(channel.id, target, value, config["gain"])

    def _publish(self, source, target, value, gain):
        event = OutputEvent(
            target,
            value,
        )

        self.event_bus.publish(event)
