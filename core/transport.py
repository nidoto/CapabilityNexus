import time


class TransportController:

    #
    # 统一传输控制：
    # 按能力声明的传输模式决定是否广播数据。
    #
    # 模式：
    #   stream - 持续流，按 rate(Hz) 节流发送
    #   state  - 最新值，值变化才发送
    #   edge   - 边沿触发，按下/释放瞬间才发送
    #
    # 缺省按 category 推断：
    #   button -> edge
    #   axis / trigger / motor -> stream
    #

    DEFAULT_RATES = {
        "slow": 30,
        "medium": 125,
        "fast": 1000,
    }

    def __init__(self):
        self._last_value = {}
        self._last_send = {}

    def should_send(self, channel):
        capability = channel.capability or {}
        transport = capability.get("transport") or {}
        mode = transport.get("mode")

        if mode is None:
            mode = self._infer_mode(capability)

        if mode == "edge":
            return self._check_edge(channel.id, channel.value)

        if mode == "state":
            return self._check_state(channel.id, channel.value)

        return self._check_stream(channel.id, transport)

    def _infer_mode(self, capability):
        category = capability.get("category")
        if category == "button":
            return "edge"
        return "stream"

    def _check_edge(self, capability_id, value):
        key = ("edge", capability_id)
        last = self._last_value.get(key)

        self._last_value[key] = value

        if last is None:
            return True

        return (last == 0) != (value == 0)

    def _check_state(self, capability_id, value):
        key = ("state", capability_id)
        last = self._last_value.get(key)

        self._last_value[key] = value

        if last is None:
            return True

        return last != value

    def _check_stream(self, capability_id, transport):
        key = ("stream", capability_id)

        rate = transport.get("rate")
        if rate is None:
            speed = transport.get("speed", "medium")
            rate = self.DEFAULT_RATES.get(speed, 125)

        if rate <= 0:
            return True

        interval = 1.0 / rate
        now = time.monotonic()
        last = self._last_send.get(key)

        if last is None or (now - last) >= interval:
            self._last_send[key] = now
            return True

        return False
