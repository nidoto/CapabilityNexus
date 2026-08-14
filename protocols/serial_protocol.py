from core.stream import StreamData


class SerialParser:

    DEFAULT_ALIASES = {
        # ESP32 sends final XInput-compatible values. The client forwards
        # these values without applying an angle processor.
        "x": "control.right_x",
        "y": "control.right_y",
        "z": "control.right_z",
    }

    def __init__(self, event_bus, mapping=None, has_frame=False, frame_prefix="FRAME="):
        self.event_bus = event_bus
        self.mapping = mapping or {}
        self.has_frame = has_frame
        self.frame_prefix = frame_prefix

        self.frame = None
        self.last_frame = -1

    def parse(self, line):
        line = line.strip()

        if not line:
            return

        # Frame counters are transport metadata, not input capabilities.
        if line.startswith(self.frame_prefix):
            if self.has_frame:
                self._on_frame(line)
            return

        if self.has_frame:
            if line.startswith(self.frame_prefix):
                self._on_frame(line)
                return

            if self.frame is None:
                return

        if "=" not in line:
            return

        key, value = line.split("=", 1)

        normalized_key = key.strip().lower()
        if self.mapping and key not in self.mapping and normalized_key not in self.mapping:
            return

        try:
            value = float(value)
        except ValueError:
            return

        capability = self.mapping.get(
            key,
            self.mapping.get(
                normalized_key,
                self.DEFAULT_ALIASES.get(normalized_key, normalized_key),
            ),
        )
        stream = StreamData(
            id=capability,
            value=value
        )

        self.event_bus.publish(stream)

    def _on_frame(self, line):
        try:
            frame = int(line.split("=")[1])
        except (ValueError, IndexError):
            return

        if frame < self.last_frame:
            print(
                "[SerialParser] Frame counter reset, resync",
                frame
            )
            self.last_frame = frame - 1

        self.last_frame = frame
        self.frame = frame
