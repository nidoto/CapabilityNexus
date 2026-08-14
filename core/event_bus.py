class EventBus:

    def __init__(self, debug=False):
        self.subscribers = []
        self.debug = debug

    def subscribe(self, event_type, callback):
        self.subscribers.append((event_type, callback))

        if self.debug:
            print("[EventBus Subscribe]", event_type, callback)

    def publish(self, event):
        if self.debug:
            print("[EventBus Publish]", type(event))

        for registered_type, callback in self.subscribers:
            if isinstance(event, registered_type):
                if self.debug:
                    print("[EventBus Call]", callback)

                callback(event)
