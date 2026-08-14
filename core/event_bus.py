import threading


class EventBus:

    def __init__(self, debug=False):
        self.subscribers = []
        self.debug = debug
        self._lock = threading.RLock()

    def subscribe(self, event_type, callback):
        with self._lock:
            registration = (event_type, callback)
            if registration not in self.subscribers:
                self.subscribers.append(registration)

        if self.debug:
                print("[EventBus Subscribe]", event_type, callback)

    def unsubscribe(self, event_type, callback):
        with self._lock:
            self.subscribers = [
                item for item in self.subscribers
                if item != (event_type, callback)
            ]

    def publish(self, event):
        if self.debug:
            print("[EventBus Publish]", type(event))

        with self._lock:
            subscribers = list(self.subscribers)

        for registered_type, callback in subscribers:
            if isinstance(event, registered_type):
                if self.debug:
                    print("[EventBus Call]", callback)

                try:
                    callback(event)
                except Exception as error:
                    # One faulty subscriber must not stop the input pipeline.
                    print("[EventBus Error]", callback, error)
