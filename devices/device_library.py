import json
import os
import urllib.request

from devices.remote_library import RemoteJsonLibrary


DEFAULT_LIBRARY_URL = (
    "https://raw.githubusercontent.com/nidoto/"
    "CapabilityNexus-Devices/master/index.json"
)


class DeviceLibrary(RemoteJsonLibrary):

    DATA_KEY = "devices"
    LOG_PREFIX = "[DeviceLibrary]"

    def __init__(self, cache_path=None, library_url=None):
        super().__init__(
            cache_path=cache_path,
            library_url=library_url or DEFAULT_LIBRARY_URL,
        )

    def refresh(self):
        # 本地索引文件优先
        if os.path.exists(self.library_url):
            try:
                with open(self.library_url, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._entries = data.get("devices", [])
                self._save_cache(data)
                print("[DeviceLibrary] Loaded local file:", len(self._entries), "devices")
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
            self._entries = data.get("devices", [])
            self._save_cache(data)
            print("[DeviceLibrary] Loaded from GitHub:", len(self._entries), "devices")
        except Exception as e:
            print("[DeviceLibrary] GitHub load failed, using cache:", e)
            cached = self._load_cached()
            self._entries = cached.get("devices", []) if cached else []
            print("[DeviceLibrary] Cache has:", len(self._entries), "devices")

    def _match_fingerprint(self, device_fp, fp):
        if device_fp.get("type") != fp.get("type"):
            return False

        if fp.get("type") == "serial":
            if "vid" in device_fp:
                if "vid" not in fp or device_fp["vid"].lower() != fp["vid"].lower():
                    return False

            if "pid" in device_fp:
                if "pid" not in fp or device_fp["pid"].lower() != fp["pid"].lower():
                    return False

            if "description" in device_fp:
                if "description" not in fp:
                    return False
                if device_fp["description"].lower() not in fp["description"].lower():
                    return False

            return True

        if fp.get("type") == "xinput":
            return True

        return False

    def identify(self, detected_device):
        if self._entries is None:
            self.refresh()

        fingerprint = detected_device.get("fingerprint", {})

        for device in self._entries:
            for fp in device.get("fingerprints", []):
                if self._match_fingerprint(fp, fingerprint):
                    return device

        return None

    def get_device(self, device_id):
        if self._entries is None:
            self.refresh()

        for device in self._entries:
            if device.get("id") == device_id:
                return device

        return None

    def list_devices(self):
        if self._entries is None:
            self.refresh()
        return self._entries or []

    def search(self, query):
        if self._entries is None:
            self.refresh()

        query = (query or "").lower()
        results = []

        for device in self._entries:
            name = (device.get("name") or "").lower()
            device_id = (device.get("id") or "").lower()

            if query in name or query in device_id:
                results.append(device)

        return results

    def install(self, device_id, packages_path="packages", config_path="config/devices.json"):
        downloaded = self.download_device(device_id)

        if downloaded is None:
            return None

        package = downloaded.get("package")
        package_dir = os.path.join(packages_path, package)
        os.makedirs(package_dir, exist_ok=True)

        with open(os.path.join(package_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(downloaded.get("manifest", {}), f, ensure_ascii=False, indent=2)

        capabilities = downloaded.get("capabilities")
        if capabilities:
            with open(os.path.join(package_dir, "capabilities.json"), "w", encoding="utf-8") as f:
                json.dump(capabilities, f, ensure_ascii=False, indent=2)

        return downloaded

    def _file_url(self, device_id, filename):
        return super()._file_url(device_id, filename, subdir="devices")

    def download_device(self, device_id):
        device = self.get_device(device_id)

        if device is None:
            print("[DeviceLibrary] Device not in library:", device_id)
            return None

        result = dict(device)

        try:
            result["manifest"] = self._fetch_file(
                self._file_url(device_id, "manifest.json")
            )
        except Exception as e:
            print("[DeviceLibrary] Manifest download failed:", e)
            return None

        try:
            result["capabilities"] = self._fetch_file(
                self._file_url(device_id, "capabilities.json")
            )
        except Exception as e:
            print("[DeviceLibrary] No capabilities file (template):", e)
            result["capabilities"] = None

        return result
