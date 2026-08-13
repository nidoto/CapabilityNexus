from core.system_event import DeviceRequestEvent
from core.system_event import OutputEvent


class RequestHandler:

    def __init__(self, event_bus, router=None, mappings=None):
        self.event_bus = event_bus
        self.router = router
        self.mappings = mappings or {}
        self.handled = set()

        self.event_bus.subscribe(
            DeviceRequestEvent,
            self.receive,
        )

    def set_router(self, router):
        self.router = router

    def set_mappings(self, mappings):
        self.mappings = mappings

    def receive(self, request):
        if not self.mappings:
            return

        if request.target not in self.mappings:
            self._warn_unmapped(request)
            return

        target = self.mappings[request.target]

        print(
            "[Request]",
            request.source,
            request.target,
            "=",
            request.value,
            "->",
            target,
        )

        self.event_bus.publish(
            OutputEvent(
                target,
                request.value,
            )
        )

    def _warn_unmapped(self, request):
        if request.value <= 0:
            return

        key = (request.target,)
        if key in self.handled:
            return

        self.handled.add(key)

        print()
        print("[IMPORTANT] Game/App requested an unmapped capability:")
        print("  Source:", request.source)
        print("  Request:", request.target, "=", request.value)
        print("  This virtual device does not support this output.")
        print("  Options:")
        print("    1. Map it to a real device:")
        print("       python tools/cnx_cli.py map-capability")
        print("       e.g.", request.target, "-> xbox.motor_left")
        print("    2. Map it to another virtual device")
        print("    3. Ignore it")
        print()
