import asyncio
import threading

from bleak import BleakScanner
from bleak import BleakClient

from core.stream import StreamData


FTMS_SERVICE = "00001826-0000-1000-8000-00805f9b34fb"
INDOOR_BIKE_DATA = "00002ad2-0000-1000-8000-00805f9b34fb"


class FTMSDevice:

    #
    # BLE FTMS 骑行台输入源（Indoor Bike / Fitness Machine）
    # 支持：功率、踏频、速度、阻力
    #
    # 能力：
    #   cycling.power    - 瞬时功率 (W)
    #   cycling.cadence  - 踏频 (rpm)
    #   cycling.speed    - 速度 (km/h)
    #   cycling.resistance - 阻力等级
    #

    def __init__(self, event_bus, address=None, name=None, scan_timeout=8):
        self.event_bus = event_bus
        self.address = address
        self.name = name
        self.scan_timeout = scan_timeout

        self.running = False
        self.thread = None
        self.client = None

    def connect(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return True

    def _run(self):
        try:
            asyncio.run(self._async_run())
        except Exception as e:
            print("[FTMS] Error:", e)
            self.running = False

    async def _async_run(self):
        device = await self._find_device()

        if device is None:
            print("[FTMS] No fitness machine found (scan", self.scan_timeout, "s)")
            self.running = False
            return

        print("[FTMS] Connecting to:", device)

        self.client = BleakClient(device)

        try:
            await self.client.connect()
        except Exception as e:
            print("[FTMS] Connect failed:", e)
            self.running = False
            return

        print("[FTMS] Connected, subscribing Indoor Bike Data...")

        def handle_measurement(_client, data: bytearray):
            self._parse_indoor_bike(data)

        try:
            await self.client.start_notify(INDOOR_BIKE_DATA, handle_measurement)
        except Exception as e:
            print("[FTMS] Subscribe failed:", e)

        while self.running:
            await asyncio.sleep(0.5)

        try:
            await self.client.disconnect()
        except Exception:
            pass

    async def _find_device(self):
        if self.address:
            return self.address

        devices = await BleakScanner.discover(timeout=self.scan_timeout)

        for d in devices:
            if self.name and self.name.lower() in (d.name or "").lower():
                return d

            if d.service_uuids and FTMS_SERVICE in [
                u.lower() for u in d.service_uuids
            ]:
                return d

        return None

    def _parse_indoor_bike(self, data):
        if len(data) < 2:
            return

        flags = data[0] | (data[1] << 8)
        offset = 2

        #
        # Flag bits (Indoor Bike Data):
        #   bit0: Instantaneous Speed present
        #   bit1: Instantaneous Cadence present
        #   bit2: Instantaneous Power present
        #   bit3: Resistance Level present
        #   bit4: Target Power present
        #

        def read_u16():
            nonlocal offset
            if offset + 2 > len(data):
                return None
            value = data[offset] | (data[offset + 1] << 8)
            offset += 2
            return value

        def read_s16():
            value = read_u16()
            if value is None:
                return None
            if value >= 0x8000:
                value -= 0x10000
            return value

        if flags & 0x01:
            speed_raw = read_u16()
            if speed_raw is not None:
                self._emit("cycling.speed", speed_raw * 0.01)

        if flags & 0x02:
            cadence = read_u16()
            if cadence is not None:
                self._emit("cycling.cadence", float(cadence))

        if flags & 0x04:
            power = read_s16()
            if power is not None:
                self._emit("cycling.power", float(power))

        if flags & 0x08:
            resistance = read_s16()
            if resistance is not None:
                self._emit("cycling.resistance", float(resistance))

    def _emit(self, capability, value):
        self.event_bus.publish(
            StreamData(capability, value)
        )

    def close(self):
        self.running = False

        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
