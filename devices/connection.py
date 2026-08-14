import threading
import time


class LineConnection:

    #
    # 统一连接抽象：
    # 任何传输方式（串口/蓝牙/WiFi/自定义）都按行回调。
    # 连接负责：打开、逐行读取、关闭。
    #

    def __init__(self, callback):
        self.callback = callback
        self.running = False
        self.thread = None
        self._consecutive_errors = 0

    def open(self):
        raise NotImplementedError("LineConnection.open()")

    def read_lines(self):
        raise NotImplementedError("LineConnection.read_lines()")

    def close(self):
        raise NotImplementedError("LineConnection.close()")

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            try:
                for line in self.read_lines():
                    if not self.running:
                        return
                    if line:
                        self.callback(line)
                self._consecutive_errors = 0
            except Exception as e:
                print("[Connection Error]", e)
                self._consecutive_errors += 1
                if self._consecutive_errors >= 3:
                    print("[Connection] Stopping after repeated read errors")
                    self.running = False
                    return
                time.sleep(0.2)

    def join(self, timeout=2):
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=timeout)
