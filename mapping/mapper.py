from core.processed_channel import ProcessedChannel
from core.system_event import OutputEvent
import json
import threading


class MappingEngine:

    def __init__(self, event_bus):
        self.event_bus = event_bus

        # source -> [ {target, gain, return_to_center}, ... ]
        self.mapping = {}

        # target -> {source: value} 用于多对一合并
        self._target_sources = {}
        self._lock = threading.RLock()

        event_bus.subscribe(
            ProcessedChannel,
            self.receive,
        )

    def add_mapping(self, source, targets):
        if isinstance(targets, dict):
            targets = [targets]

        with self._lock:
            self.mapping[source] = targets

            for t in targets:
                target = t.get("target")
                if target not in self._target_sources:
                    self._target_sources[target] = {}
                self._target_sources[target][source] = None

    def load_profile(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.load_mappings(data.get("mappings", {}))

    def load_mappings(self, mappings):
        """Replace mappings at runtime and rebuild target fan-in state."""
        with self._lock:
            self.mapping.clear()
            self._target_sources.clear()

            for source, mapping in (mappings or {}).items():
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
        with self._lock:
            configs = list(self.mapping.get(channel.id, []))
            events = []
            for config in configs:
                target = config["target"]
                value = channel.value * config["gain"]
                self._target_sources[target][channel.id] = value
                events.append((target, value, config["gain"]))

        for target, value, gain in events:
            self._publish(channel.id, target, value, gain)

    def _publish(self, source, target, value, gain):
        event = OutputEvent(
            target,
            value,
        )

        self.event_bus.publish(event)
