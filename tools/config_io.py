import json
import os
import tempfile


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "devices.json")
OUTPUTS_PATH = os.path.join(PROJECT_ROOT, "config", "outputs.json")
PACKAGES_PATH = os.path.join(PROJECT_ROOT, "packages")
PROFILE_PATH = os.path.join(PROJECT_ROOT, "profiles", "default.json")


def load_config():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {"devices": []}
            devices = data.get("devices", [])
            data["devices"] = devices if isinstance(devices, list) else []
            return data
    except (OSError, json.JSONDecodeError) as error:
        print("[Config] Failed to load devices:", error)
    return {"devices": []}


def load_outputs():
    try:
        if os.path.exists(OUTPUTS_PATH):
            with open(OUTPUTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {"outputs": []}
            outputs = data.get("outputs", [])
            data["outputs"] = outputs if isinstance(outputs, list) else []
            return data
    except (OSError, json.JSONDecodeError) as error:
        print("[Config] Failed to load outputs:", error)
    return {"outputs": []}


def save_outputs(data):
    _save_json(OUTPUTS_PATH, data)


def save_config(data):
    _save_json(CONFIG_PATH, data)


def load_profile():
    try:
        if os.path.exists(PROFILE_PATH):
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {"mappings": {}}
            mappings = data.get("mappings", {})
            data["mappings"] = mappings if isinstance(mappings, dict) else {}
            return data
    except (OSError, json.JSONDecodeError) as error:
        print("[Config] Failed to load profile:", error)
    return {"mappings": {}}


def save_profile(data):
    _save_json(PROFILE_PATH, data)


def _save_json(path, data):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".cnx-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def list_package_capabilities():
    packages = {}

    if os.path.exists(PACKAGES_PATH):
        for name in os.listdir(PACKAGES_PATH):
            cap_path = os.path.join(PACKAGES_PATH, name, "capabilities.json")
            if os.path.exists(cap_path):
                with open(cap_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                packages[name] = {
                    "capabilities": [
                        c["id"] for c in data.get("capabilities", [])
                    ],
                    "capabilities_full": data.get("capabilities", []),
                    "outputs": [
                        c["id"] for c in data.get("outputs", [])
                    ],
                    "outputs_full": data.get("outputs", []),
                }

    return packages


CONN_LABELS = {
    "xinput": "XInput",
    "hid": "HID",
    "serial": "USB/Serial",
    "tcp": "WiFi/TCP",
    "udp": "WiFi/UDP",
    "bluetooth": "Bluetooth",
    "ftms": "Bluetooth/BLE",
}


def device_conn_label(device):
    driver = device.get("driver")
    connection = device.get("connection", {})
    conn_type = connection.get("type")

    if conn_type and conn_type in CONN_LABELS:
        return CONN_LABELS[conn_type]

    if driver in CONN_LABELS:
        return CONN_LABELS[driver]

    return driver or "?"


def mapping_desc(mapping):
    if isinstance(mapping, str):
        return mapping

    if isinstance(mapping, list):
        return "; ".join(mapping_desc(m) for m in mapping)

    target = mapping.get("target", "?")
    parts = [target]

    if mapping.get("gain") not in (None, 1.0):
        parts.append(f"gain={mapping['gain']}")
    if mapping.get("return_to_center"):
        parts.append("return_to_center")

    return " ".join(parts)
