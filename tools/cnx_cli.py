import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


CONFIG_PATH = os.path.join("config", "devices.json")
PACKAGES_PATH = os.path.join("packages")


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


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tools/cnx_cli.py add-device      Add a custom device")
        print("  python tools/cnx_cli.py create-package  Create a capability package")
        return

    cmd = sys.argv[1]

    if cmd == "add-device":
        cmd_add_device()
    elif cmd == "create-package":
        cmd_create_package()
    else:
        print("Unknown command:", cmd)


if __name__ == "__main__":
    main()
