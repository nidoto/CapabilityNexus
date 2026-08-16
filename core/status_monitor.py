import threading
import time


class StatusMonitor:

    #
    # 实时状态监视器：
    # 订阅数据流，维护输入/输出最新值快照。
    # 只显示"真实输入"通道，过滤硬件漂移 / 静止噪声。
    #
    # 显示模型（输入/输出窗口共用）：
    #   - 基线：通道首次收到的值 = 设备静止时的位置（含漂移）
    #   - 激活：当前值偏离基线超过阈值 → 判定为真实输入
    #   因此：
    #     漂移值（静止非零，等于基线）→ 不显示
    #     按住按钮 / 推住摇杆（偏离基线）→ 一直显示最新值
    #     松开 / 回中（回到基线）→ 自动消失
    #     设备断开（停止发布数据）→ 通道过期，自动消失
    #

    # 偏离基线阈值（过滤微小噪声 / 漂移抖动）
    CHANGE_EPSILON = 0.5

    # 数据新鲜窗口：通道在此时间内仍在接收数据才视为已连接
    FRESH_WINDOW = 2.0

    def __init__(self, event_bus):
        self.event_bus = event_bus

        self.input_values = {}       # capability id -> 最新值
        self.output_values = {}      # target -> 最新值
        self.request_values = {}     # 请求能力名 -> 最新值（反向请求）
        self.request_sources = {}    # 请求能力名 -> 来源（虚拟设备/程序）
        self.request_history = []    # 最近收到的反向请求事件
        self._active_requests = set()

        self._input_baseline = {}      # capability id -> 基线（首次值）
        self._output_baseline = {}     # target -> 基线（首次值）
        self._input_last_update = {}   # capability id -> 最近数据到达时间
        self._output_last_update = {}  # target -> 最近数据到达时间

        self._lock = threading.Lock()

        self._subscribed = False

    def start(self):
        if self._subscribed:
            return

        from core.stream import StreamData
        from core.system_event import OutputEvent
        from core.system_event import DeviceRequestEvent

        self.event_bus.subscribe(StreamData, self._on_input)
        self.event_bus.subscribe(OutputEvent, self._on_output)
        self.event_bus.subscribe(DeviceRequestEvent, self._on_request)

        self._subscribed = True

    def stop(self):
        if not self._subscribed:
            return

        from core.stream import StreamData
        from core.system_event import OutputEvent
        from core.system_event import DeviceRequestEvent

        self.event_bus.unsubscribe(StreamData, self._on_input)
        self.event_bus.unsubscribe(OutputEvent, self._on_output)
        self.event_bus.unsubscribe(DeviceRequestEvent, self._on_request)
        self._subscribed = False

    def _on_request(self, event):
        with self._lock:
            value = float(event.value)
            # ViGEm emits idle zero-rumble notifications when a virtual pad
            # is attached. Ignore those unless they end a real vibration.
            if value <= 0 and event.target not in self._active_requests:
                return

            timestamp = time.strftime("%H:%M:%S")
            self.request_values[event.target] = value
            self.request_sources[event.target] = event.source
            self.request_history.append((timestamp, event.source, event.target, value))
            if value > 0:
                self._active_requests.add(event.target)
            else:
                self._active_requests.discard(event.target)
            if len(self.request_history) > 100:
                del self.request_history[:-100]

    def _on_input(self, stream):
        with self._lock:
            self._input_last_update[stream.id] = time.monotonic()

            # 首次值作为基线（设备静止位置，含漂移）
            if stream.id not in self._input_baseline:
                self._input_baseline[stream.id] = stream.value

            self.input_values[stream.id] = stream.value

    def _on_output(self, event):
        with self._lock:
            self._output_last_update[event.target] = time.monotonic()

            if event.target not in self._output_baseline:
                self._output_baseline[event.target] = event.value

            self.output_values[event.target] = event.value

    def get_input_value(self, capability_id):
        with self._lock:
            return self.input_values.get(capability_id)

    def snapshot_outputs(self):
        with self._lock:
            return dict(self.output_values)

    def active_inputs(self, fresh_window=None):
        """返回已连接且有真实输入的通道 {id: 最新值}"""
        return self._active_snapshot(
            self.input_values,
            self._input_baseline,
            self._input_last_update,
            fresh_window,
        )

    def all_requests(self):
        """返回记录到的所有反向请求 {能力名: (来源, 最新值)}

        反向请求（如游戏/程序要求的震动）是持久累积的：
        收到左震动记录左震动，收到右震动再新增右震动，
        不会自动过期，直到用户手动清空或重启引擎。
        """
        with self._lock:
            return {
                target: (self.request_sources.get(target, "?"), value)
                for target, value in self.request_values.items()
            }

    def recent_requests(self, limit=30):
        with self._lock:
            return list(self.request_history[-limit:])

    def clear_requests(self):
        with self._lock:
            self.request_values.clear()
            self.request_sources.clear()
            self.request_history.clear()
            self._active_requests.clear()

    def _active_snapshot(self, values, baseline, last_update, fresh_window):
        if fresh_window is None:
            fresh_window = self.FRESH_WINDOW

        cutoff = time.monotonic() - fresh_window

        with self._lock:
            active = {}

            for key, value in list(values.items()):
                # 未连接（数据过期）→ 不显示
                if last_update.get(key, 0) < cutoff:
                    values.pop(key, None)
                    baseline.pop(key, None)
                    last_update.pop(key, None)
                    continue

                base = baseline.get(key)

                # 未偏离基线（静止 / 漂移 / 回中）→ 不显示
                if base is None or abs(value - base) <= self.CHANGE_EPSILON:
                    continue

                active[key] = value

            return active
