import json
import os
import tempfile


def _project_root():
    """用户数据根目录：兼容源码运行与打包 exe。

    源码：本文件位于 <root>/tools/config_io.py → 返回 <root>。
    frozen：用户配置存 exe 同级目录（可写、持久，重打包不丢）；
    内置默认值在 _MEIPASS，读取时回退。
    """
    import sys as _sys

    if getattr(_sys, "frozen", False):
        return os.path.dirname(_sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _builtin_root():
    """内置默认数据目录（frozen 下为 _MEIPASS；源码下同用户根）。"""
    import sys as _sys

    if getattr(_sys, "frozen", False):
        return getattr(_sys, "_MEIPASS", None) or _project_root()
    return _project_root()


def _read_json(path):
    """读取 JSON，失败返回 None。"""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _read_first(preferred, fallback):
    """优先读 preferred（用户），否则回退内置 fallback。"""
    data = _read_json(preferred)
    if data is None:
        data = _read_json(fallback)
    return data


def _profile_path_user(name):
    """用户 profile 路径（exe 同级 / 源码 profiles）。"""
    return os.path.join(PROJECT_ROOT, "profiles", f"{name}.json")


def _profile_path_builtin(name):
    """内置 profile 路径（frozen 下 _MEIPASS）。"""
    return os.path.join(_builtin_root(), "profiles", f"{name}.json")


PROJECT_ROOT = _project_root()
BUILTIN_ROOT = _builtin_root()
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "devices.json")
OUTPUTS_PATH = os.path.join(PROJECT_ROOT, "config", "outputs.json")
PACKAGES_PATH = os.path.join(BUILTIN_ROOT, "packages")
PROFILE_PATH = os.path.join(PROJECT_ROOT, "profiles", "default.json")
PROFILES_DIR = os.path.join(PROJECT_ROOT, "profiles")
ACTIVE_PROFILE_PATH = os.path.join(PROJECT_ROOT, "config", "active_profile.json")
CLIENT_SETTINGS_PATH = os.path.join(PROJECT_ROOT, "config", "client.json")


def load_client_settings():
    """读取客户端设置（语言等），无则返回默认 dict。"""
    data = _read_json(CLIENT_SETTINGS_PATH)
    if data is None:
        return {}
    return data if isinstance(data, dict) else {}


def save_client_settings(data):
    """保存客户端设置（语言等）到 config/client.json。"""
    if not isinstance(data, dict):
        return
    _save_json(CLIENT_SETTINGS_PATH, data)


def load_client_language(default="zh"):
    """读取已保存的界面语言。"""
    return load_client_settings().get("language") or default


def save_client_language(lang):
    """保存界面语言。"""
    settings = load_client_settings()
    settings["language"] = lang
    save_client_settings(settings)


def load_config():
    data = _read_first(CONFIG_PATH, os.path.join(BUILTIN_ROOT, "config", "devices.json"))
    if data is None:
        return {"devices": []}
    devices = data.get("devices", [])
    data["devices"] = devices if isinstance(devices, list) else []
    return data


def load_outputs():
    data = _read_first(OUTPUTS_PATH, os.path.join(BUILTIN_ROOT, "config", "outputs.json"))
    if data is None:
        return {"outputs": []}
    outputs = data.get("outputs", [])
    data["outputs"] = outputs if isinstance(outputs, list) else []
    return data


def save_outputs(data):
    _save_json(OUTPUTS_PATH, data)


def save_config(data):
    _save_json(CONFIG_PATH, data)


def load_profile():
    return load_profile_named(get_active_profile())


def save_profile(data):
    save_profile_named(get_active_profile(), data)


#
# 多游戏配置（profiles/<game>.json）
#


def _profile_scan_dirs():
    """profiles/ 根目录 + 本地未上传目录 profiles/local/"""
    local_dir = os.path.join(PROFILES_DIR, "local")
    return [d for d in (PROFILES_DIR, local_dir) if os.path.isdir(d)]


def list_profiles():
    """返回 profiles/（含 local/）下所有 .json 配置名（不含扩展名）。"""
    names = []
    for directory in _profile_scan_dirs():
        for name in os.listdir(directory):
            if name.endswith(".json"):
                names.append(name[:-5])
    return sorted(set(names)) or ["default"]


def _profile_path(name):
    """定位配置路径：local/ 优先，其次 profiles/ 根目录（含内置回退）。"""
    local_dir = os.path.join(PROFILES_DIR, "local")
    if name:
        local_path = os.path.join(local_dir, f"{name}.json")
        if os.path.exists(local_path):
            return local_path
        root_path = os.path.join(PROFILES_DIR, f"{name}.json")
        if os.path.exists(root_path):
            return root_path
        # frozen 下回退到内置
        builtin_path = os.path.join(BUILTIN_ROOT, "profiles", f"{name}.json")
        if os.path.exists(builtin_path):
            return builtin_path
    return os.path.join(PROFILES_DIR, f"{name}.json")


def get_active_profile():
    """返回当前激活的游戏配置名，默认 'default'。"""
    try:
        if os.path.exists(ACTIVE_PROFILE_PATH):
            with open(ACTIVE_PROFILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            name = data.get("profile")
            if name and os.path.exists(_profile_path(name)):
                return name
    except (OSError, json.JSONDecodeError):
        pass
    return "default"


def set_active_profile(name):
    """激活指定游戏配置。返回是否成功。"""
    if not name or not os.path.exists(_profile_path(name)):
        return False
    _save_json(ACTIVE_PROFILE_PATH, {"profile": name})
    return True


def active_profile_path():
    return _profile_path(get_active_profile())


def load_profile_named(name):
    """加载指定游戏配置的映射。"""
    path = _profile_path(name)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {"mappings": {}}
            mappings = data.get("mappings", {})
            data["mappings"] = mappings if isinstance(mappings, dict) else {}
            return data
    except (OSError, json.JSONDecodeError) as error:
        print("[Config] Failed to load profile:", name, error)
    return {"mappings": {}}


def save_profile_named(name, data):
    """保存到指定游戏配置（本地调优保存到 profiles/local/）。"""
    if not name:
        name = "default"

    local_dir = os.path.join(PROFILES_DIR, "local")
    if name != "default" or os.path.exists(os.path.join(local_dir, f"{name}.json")):
        _save_json(os.path.join(local_dir, f"{name}.json"), data)
    else:
        _save_json(os.path.join(PROFILES_DIR, f"{name}.json"), data)


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
