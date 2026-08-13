import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


CONFIG_PATH = os.path.join("config", "devices.json")
PACKAGES_PATH = os.path.join("packages")
PROFILE_PATH = os.path.join("profiles", "default.json")


def ask(prompt, default=None, required=False):
    suffix = f" [{default}]" if default is not None else ""
    while True:
        answer = input(f"{prompt}{suffix}: ").strip()
        if answer:
            return answer
        if default is not None:
            return default
        if not required:
            return ""


def ask_bool(prompt, default=True):
    suffix = " (y/n)"
    hint = " [y]" if default else " [n]"
    while True:
        answer = input(f"{prompt}{suffix}{hint}: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        if not answer:
            return default


def ask_number(prompt, default=None):
    while True:
        answer = input(f"{prompt} [{default}]: ").strip()
        if not answer and default is not None:
            return default
        try:
            return float(answer)
        except ValueError:
            print("  Please enter a number.")


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"devices": []}


def save_config(data):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def ask_serial_protocol():
    print()
    print("Define the serial protocol:")
    print("  Each data line looks like: KEY=VALUE  (e.g. X=12.5)")
    has_frame = ask_bool("Does the device send a FRAME= line before data?", default=False)
    frame_prefix = "FRAME="
    if has_frame:
        frame_prefix = ask("Frame prefix", default="FRAME=")

    mapping = {}
    print()
    print("Now map each KEY to a capability id.")
    print("  A capability is like: motion.pitch, sensor.pressure, sensor.temp")
    print("  Leave KEY empty to stop.")
    while True:
        key = ask("  KEY (e.g. X, Y, P)")
        if not key:
            break
        capability = ask(f"  Capability id for '{key}' (e.g. sensor.pressure)")
        if capability:
            mapping[key] = capability

    return {
        "has_frame": has_frame,
        "frame_prefix": frame_prefix if has_frame else None,
        "mapping": mapping,
    }


def cmd_add_device():
    print("=== Add Custom Device ===")
    print()

    name = ask("Device name", required=True)
    driver = ask("Driver (serial/xinput)", default="serial")

    if driver == "xinput":
        entry = {
            "name": name,
            "driver": "xinput",
        }
    else:
        port = ask("Serial port (e.g. COM3)", required=True)
        baudrate = ask_number("Baudrate", default=115200)
        vid = ask("VID (optional, e.g. 1A86)")
        pid = ask("PID (optional, e.g. 55D3)")
        package = ask("Capability package name (folder in packages/)", required=True)

        entry = {
            "name": name,
            "driver": "serial",
            "port": port,
            "baudrate": int(baudrate),
            "package": package,
            "protocol": ask_serial_protocol(),
        }

        if vid:
            entry["vid"] = vid
        if pid:
            entry["pid"] = pid

    data = load_config()
    data["devices"].append(entry)
    save_config(data)

    print()
    print(f"[OK] Device '{name}' added to {CONFIG_PATH}")


def cmd_create_package():
    print("=== Create Capability Package ===")
    print()
    print("A package defines what capabilities a device provides.")
    print("It is stored in a folder under packages/.")

    folder = ask("Package folder name (e.g. pressure_demo)", required=True)
    name = ask("Display name (e.g. My Pressure Sensor)", required=True)
    author = ask("Author", default="user")
    version = ask("Version", default="1.0")
    description = ask("Description")

    capabilities = []
    print()
    print("Define capabilities. Categories:")
    print("  axis     - continuous value (joystick/angle/speed)")
    print("  trigger  - one-directional value (0..max)")
    print("  button   - on/off")
    print("  Leave id empty to stop.")
    while True:
        cap_id = ask("  Capability id (e.g. sensor.pressure)")
        if not cap_id:
            break

        category = ask("  Category (axis/trigger/button)", default="axis")
        value_type = "float"

        cap = {
            "id": cap_id,
            "category": category,
            "value_type": value_type,
            "continuous": category != "button",
            "return_center": category == "axis",
        }

        if category in ("axis", "trigger"):
            lo = ask_number("  Min value", default=-32768 if category == "axis" else 0)
            hi = ask_number("  Max value", default=32767)
            cap["range"] = [int(lo), int(hi)]

        capabilities.append(cap)

    package_path = os.path.join(PACKAGES_PATH, folder)
    os.makedirs(package_path, exist_ok=True)

    manifest = {
        "name": name,
        "author": author,
        "version": version,
        "description": description,
        "type": "input",
    }
    caps = {"capabilities": capabilities}

    with open(os.path.join(package_path, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=4)
    with open(os.path.join(package_path, "capabilities.json"), "w", encoding="utf-8") as f:
        json.dump(caps, f, ensure_ascii=False, indent=4)

    print()
    print(f"[OK] Package '{name}' created in packages/{folder}/")
    print("Now add a device that uses it:  python tools/cnx_cli.py add-device")


VIRTUAL_TARGETS = {
    "left_x": "Virtual X360 - Left stick X",
    "left_y": "Virtual X360 - Left stick Y",
    "right_x": "Virtual X360 - Right stick X",
    "right_y": "Virtual X360 - Right stick Y",
    "left_trigger": "Virtual X360 - Left trigger",
    "right_trigger": "Virtual X360 - Right trigger",
    "button_a": "Virtual X360 - Button A",
    "button_b": "Virtual X360 - Button B",
    "button_x": "Virtual X360 - Button X",
    "button_y": "Virtual X360 - Button Y",
    "button_lb": "Virtual X360 - LB",
    "button_rb": "Virtual X360 - RB",
    "button_start": "Virtual X360 - Start",
    "button_back": "Virtual X360 - Back",
    "button_dpad_up": "Virtual X360 - D-pad Up",
    "button_dpad_down": "Virtual X360 - D-pad Down",
    "button_dpad_left": "Virtual X360 - D-pad Left",
    "button_dpad_right": "Virtual X360 - D-pad Right",
}

REAL_TARGETS = {
    "xbox.motor_left": "Real Xbox One - Left motor (rumble)",
    "xbox.motor_right": "Real Xbox One - Right motor (rumble)",
}


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
                packages[name] = [
                    c["id"] for c in data.get("capabilities", [])
                ]

    return packages


def cmd_map_capability():
    print("=== Map Capability to Output ===")
    print()

    packages = list_package_capabilities()

    if not packages:
        print("No capability packages found under packages/.")
        print("Create one first:  python tools/cnx_cli.py create-package")
        return

    print("Available capabilities:")
    capability_ids = []
    for pkg, caps in packages.items():
        for cap in caps:
            capability_ids.append(cap)
            print(f"  {cap}   (from {pkg})")

    print()
    source = ask("Capability to map", required=True)
    if source not in capability_ids:
        print(f"[X] '{source}' is not a known capability.")
        return

    print()
    print("Available output targets:")
    print("  -- Virtual X360 --")
    for t, desc in VIRTUAL_TARGETS.items():
        print(f"  {t}  ({desc})")
    print("  -- Real devices --")
    for t, desc in REAL_TARGETS.items():
        print(f"  {t}  ({desc})")

    print()
    target = ask("Output target", required=True)

    if target not in VIRTUAL_TARGETS and target not in REAL_TARGETS:
        print(f"[X] '{target}' is not a known target. Adding anyway (custom).")

    profile = load_profile()
    profile["mappings"][source] = target
    save_profile(profile)

    print()
    print(f"[OK] {source} -> {target} added to {PROFILE_PATH}")


def cmd_list_mappings():
    profile = load_profile()
    mappings = profile.get("mappings", {})

    if not mappings:
        print("No mappings configured.")
        return

    print("=== Current Mappings ===")
    for source, target in mappings.items():
        print(f"  {source} -> {target}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tools/cnx_cli.py add-device       Add a custom device")
        print("  python tools/cnx_cli.py create-package   Create a capability package")
        print("  python tools/cnx_cli.py map-capability   Map a capability to an output target")
        print("  python tools/cnx_cli.py list-mappings    Show current mappings")
        return

    cmd = sys.argv[1]

    if cmd == "add-device":
        cmd_add_device()
    elif cmd == "create-package":
        cmd_create_package()
    elif cmd == "map-capability":
        cmd_map_capability()
    elif cmd == "list-mappings":
        cmd_list_mappings()
    else:
        print("Unknown command:", cmd)


if __name__ == "__main__":
    main()
