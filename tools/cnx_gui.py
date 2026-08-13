import os
import sys
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import config_io


class CapabilityNexusGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("CapabilityNexus")
        self.root.geometry("900x600")

        self._build_layout()
        self.refresh_devices()
        self.refresh_mappings()

    def _build_layout(self):
        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main)
        right = ttk.Frame(main)
        main.add(left, weight=1)
        main.add(right, weight=2)

        self._build_device_panel(left)
        self._build_mapping_panel(right)

    def _build_device_panel(self, parent):
        box = ttk.LabelFrame(parent, text="Devices")
        box.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.device_list = tk.Listbox(box, height=8)
        self.device_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        btns = ttk.Frame(box)
        btns.pack(fill=tk.X, padx=6, pady=4)

        ttk.Button(btns, text="Add Device", command=self.add_device_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Remove", command=self.remove_device).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Install from Library", command=self.install_from_library).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Auto-Route", command=self.auto_route).pack(side=tk.LEFT, padx=2)

        self._build_log_panel(box)

    def _build_log_panel(self, parent):
        logbox = ttk.LabelFrame(parent, text="Log")
        logbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.log_text = tk.Text(logbox, height=8, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _build_mapping_panel(self, parent):
        top = ttk.LabelFrame(parent, text="Capabilities")
        top.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.cap_list = tk.Listbox(top, height=10)
        self.cap_list.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        cap_btns = ttk.Frame(top)
        cap_btns.pack(fill=tk.X, padx=6, pady=4)
        ttk.Button(cap_btns, text="Map to Target...", command=self.map_capability_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(cap_btns, text="Unmap", command=self.unmap_capability).pack(side=tk.LEFT, padx=2)

        bottom = ttk.LabelFrame(parent, text="Current Mappings")
        bottom.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.map_text = tk.Text(bottom, height=8, state=tk.DISABLED)
        self.map_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    #
    # Devices
    #

    def refresh_devices(self):
        self.device_list.delete(0, tk.END)
        data = config_io.load_config()

        for device in data.get("devices", []):
            self.device_list.insert(
                tk.END,
                f"{device.get('name')}  [{device.get('driver')}]",
            )

    def add_device_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Device")
        dialog.geometry("420x360")

        ttk.Label(dialog, text="Name").pack(padx=8, pady=4)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var).pack(fill=tk.X, padx=8)

        ttk.Label(dialog, text="Driver (serial/xinput/hid/ftms)").pack(padx=8, pady=4)
        driver_var = tk.StringVar(value="serial")
        ttk.Entry(dialog, textvariable=driver_var).pack(fill=tk.X, padx=8)

        ttk.Label(dialog, text="Package (folder in packages/)").pack(padx=8, pady=4)
        pkg_var = tk.StringVar(value="motion_demo")
        ttk.Entry(dialog, textvariable=pkg_var).pack(fill=tk.X, padx=8)

        ttk.Label(dialog, text="Serial port (for serial)").pack(padx=8, pady=4)
        port_var = tk.StringVar(value="COM3")
        ttk.Entry(dialog, textvariable=port_var).pack(fill=tk.X, padx=8)

        def save():
            entry = {
                "name": name_var.get() or "New Device",
                "driver": driver_var.get(),
                "package": pkg_var.get(),
            }

            if driver_var.get() == "serial":
                entry["connection"] = {
                    "type": "serial",
                    "port": port_var.get(),
                    "baudrate": 115200,
                }

            data = config_io.load_config()
            data["devices"].append(entry)
            config_io.save_config(data)

            self.refresh_devices()
            dialog.destroy()

        ttk.Button(dialog, text="Save", command=save).pack(padx=8, pady=8)

    def remove_device(self):
        selection = self.device_list.curselection()
        if not selection:
            return

        index = selection[0]
        data = config_io.load_config()
        devices = data.get("devices", [])

        if index >= len(devices):
            return

        removed = devices.pop(index)
        data["devices"] = devices
        config_io.save_config(data)

        self.refresh_devices()
        self.log(f"Removed device: {removed.get('name')}")

    def install_from_library(self):
        try:
            from devices.device_library import DeviceLibrary

            library = DeviceLibrary(
                cache_path=os.path.join("config", "device_library_cache.json"),
            )
            library.refresh()
        except Exception as e:
            self.log(f"Library load failed: {e}")
            return

        devices = library.list_devices()

        if not devices:
            self.log("Device library is empty.")
            return

        names = "\n".join(
            f"  {d.get('id')} - {d.get('name')}" for d in devices
        )
        self.log(f"Available in library:\n{names}")

        dialog = tk.Toplevel(self.root)
        dialog.title("Install from Library")
        dialog.geometry("400x200")

        ttk.Label(dialog, text="Device ID:").pack(padx=8, pady=4)
        id_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=id_var).pack(fill=tk.X, padx=8)

        def do_install():
            device_id = id_var.get().strip()
            if not device_id:
                return

            downloaded = library.download_device(device_id)
            if downloaded is None:
                self.log(f"Could not download: {device_id}")
                return

            package = downloaded.get("package")
            package_dir = os.path.join(config_io.PACKAGES_PATH, package)
            os.makedirs(package_dir, exist_ok=True)

            with open(os.path.join(package_dir, "manifest.json"), "w", encoding="utf-8") as f:
                import json
                json.dump(downloaded.get("manifest", {}), f, ensure_ascii=False, indent=4)

            caps = downloaded.get("capabilities")
            if caps:
                with open(os.path.join(package_dir, "capabilities.json"), "w", encoding="utf-8") as f:
                    json.dump(caps, f, ensure_ascii=False, indent=4)

            if downloaded.get("kind") == "product":
                data = config_io.load_config()
                data["devices"].append({
                    "name": downloaded.get("name"),
                    "driver": downloaded.get("driver", "xinput"),
                    "package": package,
                })
                config_io.save_config(data)
                self.refresh_devices()

            self.log(f"Installed: {downloaded.get('name')}")
            dialog.destroy()

        ttk.Button(dialog, text="Install", command=do_install).pack(padx=8, pady=8)

    def auto_route(self):
        selection = self.device_list.curselection()
        if not selection:
            self.log("Select a device to auto-route first.")
            return

        index = selection[0]
        data = config_io.load_config()
        devices = data.get("devices", [])

        if index >= len(devices):
            return

        device = devices[index]
        package = device.get("package")

        cap_path = os.path.join(config_io.PACKAGES_PATH, package, "capabilities.json")
        if not os.path.exists(cap_path):
            self.log(f"No capabilities for package: {package}")
            return

        import json
        with open(cap_path, "r", encoding="utf-8") as f:
            caps_data = json.load(f)

        from mapping.auto_route import AutoRouter

        router = AutoRouter()
        mappings, missing = router.route(caps_data.get("capabilities", []))
        outputs = caps_data.get("outputs", [])

        profile = config_io.load_profile()
        profile["mappings"].update(mappings)
        config_io.save_profile(profile)

        self.refresh_mappings()
        self.log(f"Auto-routed {len(mappings)} capabilities.")

        if outputs:
            self.log("Outputs not covered (need manual route):")
            for out in outputs:
                self.log(f"  {out.get('id')}")

    #
    # Mappings
    #

    def refresh_mappings(self):
        self.cap_list.delete(0, tk.END)

        packages = config_io.list_package_capabilities()
        profile = config_io.load_profile()
        mapped = set(profile.get("mappings", {}).keys())

        for pkg, info in packages.items():
            for cap in info["capabilities"]:
                status = " [mapped]" if cap in mapped else ""
                self.cap_list.insert(tk.END, f"{cap}{status}  ({pkg})")

        self.map_text.config(state=tk.NORMAL)
        self.map_text.delete("1.0", tk.END)
        for source, mapping in profile.get("mappings", {}).items():
            self.map_text.insert(tk.END, f"{source} -> {config_io.mapping_desc(mapping)}\n")
        self.map_text.config(state=tk.DISABLED)

    def map_capability_dialog(self):
        selection = self.cap_list.curselection()
        if not selection:
            return

        line = self.cap_list.get(selection[0])
        source = line.split("  (")[0]
        source = source.replace(" [mapped]", "")

        dialog = tk.Toplevel(self.root)
        dialog.title("Map Capability")
        dialog.geometry("360x220")

        ttk.Label(dialog, text=f"Source: {source}").pack(padx=8, pady=4)

        ttk.Label(dialog, text="Target (e.g. right_x, button_a, xbox.motor_left):").pack(padx=8, pady=4)
        target_var = tk.StringVar(value="right_x")
        ttk.Entry(dialog, textvariable=target_var).pack(fill=tk.X, padx=8)

        ttk.Label(dialog, text="Gain (default 1.0):").pack(padx=8, pady=4)
        gain_var = tk.StringVar(value="1.0")
        ttk.Entry(dialog, textvariable=gain_var).pack(fill=tk.X, padx=8)

        return_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(dialog, text="Return to center", variable=return_var).pack(padx=8, pady=4)

        def save():
            profile = config_io.load_profile()
            try:
                gain = float(gain_var.get())
            except ValueError:
                gain = 1.0

            profile["mappings"][source] = {
                "target": target_var.get(),
                "gain": gain,
                "return_to_center": return_var.get(),
            }
            config_io.save_profile(profile)
            self.refresh_mappings()
            self.log(f"Mapped {source} -> {target_var.get()}")
            dialog.destroy()

        ttk.Button(dialog, text="Save", command=save).pack(padx=8, pady=8)

    def unmap_capability(self):
        selection = self.cap_list.curselection()
        if not selection:
            return

        line = self.cap_list.get(selection[0])
        source = line.split("  (")[0]
        source = source.replace(" [mapped]", "")

        profile = config_io.load_profile()
        mappings = profile.get("mappings", {})

        if source in mappings:
            del mappings[source]
            profile["mappings"] = mappings
            config_io.save_profile(profile)
            self.refresh_mappings()
            self.log(f"Unmapped {source}")

    #
    # Log
    #

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    CapabilityNexusGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
