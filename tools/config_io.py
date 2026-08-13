import json
import os


CONFIG_PATH = os.path.join("config", "devices.json")
PACKAGES_PATH = os.path.join("packages")
PROFILE_PATH = os.path.join("profiles", "default.json")


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"devices": []}


def save_config(data):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_profile():
    if os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"mappings": {}}


def save_profile(data):
    os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


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
                    "outputs": [
                        c["id"] for c in data.get("outputs", [])
                    ],
                }

    return packages


def mapping_desc(mapping):
    if isinstance(mapping, str):
        return mapping

    target = mapping.get("target", "?")
    parts = [target]

    if mapping.get("gain") not in (None, 1.0):
        parts.append(f"gain={mapping['gain']}")
    if mapping.get("return_to_center"):
        parts.append("return_to_center")

    return " ".join(parts)
