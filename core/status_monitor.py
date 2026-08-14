import threading


class StatusMonitor:

    #
    # 实时状态监视器：
    # 订阅数据流，维护输入/输出最新值快照。
    # GUI 轮询读取，实现实时显示。
    #

    def __init__(self, event_bus):
        self.event_bus = event_bus

        self.input_values = {}     # capability id -> 最新值
        self.output_values = {}    # target -> 最新值

        self._lock = threading.Lock()

        self._subscribed = False

    def start(self):
        if self._subscribed:
            return

        from core.stream import StreamData
        from core.system_event import OutputEvent

        self.event_bus.subscribe(StreamData, self._on_input)
        self.event_bus.subscribe(OutputEvent, self._on_output)

        self._subscribed = True

    def _on_input(self, stream):
        with self._lock:
            self.input_values[stream.id] = stream.value

    def _on_output(self, event):
        with self._lock:
            self.output_values[event.target] = event.value

    def get_input_value(self, capability_id):
        with self._lock:
            return self.input_values.get(capability_id)

    def get_output_value(self, target):
        with self._lock:
            return self.output_values.get(target)

    def snapshot_inputs(self):
        with self._lock:
            return dict(self.input_values)

    def snapshot_outputs(self):
        with self._lock:
            return dict(self.output_values)
