import json
import os
import urllib.request


DEFAULT_LIBRARY_URL = (
    "https://raw.githubusercontent.com/nidoto/"
    "CapabilityNexus-Devices/master/index.json"
)


class DeviceLibrary:

    def __init__(self, cache_path=None, library_url=None):
        self.library_url = library_url or DEFAULT_LIBRARY_URL
        self.cache_path = cache_path
        self._devices = None

    def _load_cached(self):
        if not self.cache_path or not os.path.exists(self.cache_path):
            return None

        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("[DeviceLibrary] Cache read failed:", e)
            return None

    def _save_cache(self, data):
        if not self.cache_path:
            return

        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("[DeviceLibrary] Cache write failed:", e)

    def refresh(self):
        if os.path.exists(self.library_url):
            try:
                with open(self.library_url, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._devices = data.get("devices", [])
                self._save_cache(data)
                print("[DeviceLibrary] Loaded local file:", len(self._devices), "devices")
                return
            except Exception as e:
                print("[DeviceLibrary] Local file read failed:", e)

        try:
            req = urllib.request.Request(
                self.library_url,
                headers={"User-Agent": "CapabilityNexus"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self._devices = data.get("devices", [])
            self._save_cache(data)
            print("[DeviceLibrary] Loaded from GitHub:", len(self._devices), "devices")
        except Exception as e:
            print("[DeviceLibrary] GitHub load failed, using cache:", e)
            cached = self._load_cached()
            self._devices = cached.get("devices", []) if cached else []
            print("[DeviceLibrary] Cache has:", len(self._devices), "devices")

    def _match_fingerprint(self, device_fp, fp):
        if device_fp.get("type") != fp.get("type"):
            return False

        if fp.get("type") == "serial":
            if "vid" in fp and "vid" in device_fp:
                if fp["vid"].lower() != device_fp["vid"].lower():
                    return False
            elif "vid" in fp:
                return False

            if "pid" in fp and "pid" in device_fp:
                if fp["pid"].lower() != device_fp["pid"].lower():
                    return False
            elif "pid" in fp:
                return False

            if "description" in fp and "description" in device_fp:
                if fp["description"].lower() not in device_fp["description"].lower():
                    return False
            elif "description" in fp:
                return False

            return True

        if fp.get("type") == "xinput":
            return True

        return False

    def identify(self, detected_device):
        if self._devices is None:
            self.refresh()

        fingerprint = detected_device.get("fingerprint", {})

        for device in self._devices:
            for fp in device.get("fingerprints", []):
                if self._match_fingerprint(fp, fingerprint):
                    return device

        return None
