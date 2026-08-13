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
        self.root.geometry("1000x650")

        self._build_menubar()
        self._build_layout()
        self.refresh_devices()

    def _build_menubar(self):
        menubar = tk.Menu(self.root)

        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Preferences...", command=self.show_preferences)
        settings_menu.add_separator()
        settings_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="System", menu=settings_menu)

        devices_menu = tk.Menu(menubar, tearoff=0)
        devices_menu.add_command(label="Add Device...", command=self.add_device_dialog)
        devices_menu.add_command(label="Install from Library...", command=self.install_from_library)
        devices_menu.add_separator()
        devices_menu.add_command(label="Refresh", command=self.refresh_devices)
        menubar.add_cascade(label="Devices", menu=devices_menu)

        mappings_menu = tk.Menu(menubar, tearoff=0)
        mappings_menu.add_command(label="Auto-Route Selected", command=self.auto_route)
        mappings_menu.add_command(label="Remove Mapping...", command=self.remove_mapping)
        mappings_menu.add_separator()
        mappings_menu.add_command(label="View Mappings", command=self.refresh_mappings)
        menubar.add_cascade(label="Mappings", menu=mappings_menu)

        output_menu = tk.Menu(menubar, tearoff=0)
        output_menu.add_command(label="Output Devices", command=self.show_output_devices)
        menubar.add_cascade(label="Output", menu=output_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Help", command=self.show_help)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _build_layout(self):
        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main)
        right = ttk.Frame(main)
        main.add(left, weight=1)
        main.add(right, weight=2)

        self._build_device_tree(left)
        self._build_mapping_panel(right)
        self._build_log_panel(self.root)

    def _build_device_tree(self, parent):
        box = ttk.LabelFrame(parent, text="Input Devices")
        box.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.device_tree = ttk.Treeview(box, columns=("func",), show="tree headings")
        self.device_tree.heading("#0", text="Device / Function")
        self.device_tree.heading("func", text="Type")
        self.device_tree.column("func", width=120)
        self.device_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.device_tree.bind("<Double-1>", self._on_tree_double_click)
        self.device_tree.bind("<Return>", self._on_tree_double_click)

        hint = ttk.Label(box, text="Double-click a function to map it to an output")
        hint.pack(pady=4)

    def _build_mapping_panel(self, parent):
        box = ttk.LabelFrame(parent, text="Current Mappings")
        box.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.map_text = tk.Text(box, state=tk.DISABLED)
        self.map_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        btns = ttk.Frame(box)
        btns.pack(fill=tk.X, padx=6, pady=4)
        ttk.Button(btns, text="Remove Selected Mapping", command=self.remove_mapping).pack(side=tk.LEFT, padx=2)

    def _build_log_panel(self, parent):
        logbox = ttk.LabelFrame(parent, text="Log")
        logbox.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.log_text = tk.Text(logbox, height=6, state=tk.DISABLED)
        self.log_text.pack(fill=tk.X, padx=6, pady=6)

    #
    # Device tree
    #

    def refresh_devices(self):
        self.device_tree.delete(*self.device_tree.get_children())

        data = config_io.load_config()
        packages = config_io.list_package_capabilities()

        for device in data.get("devices", []):
            name = device.get("name", "?")
            package = device.get("package", "")
            conn = config_io.device_conn_label(device)

            device_node = self.device_tree.insert(
                "",
                tk.END,
                text=f"{name}  [{conn}]",
                values=("device",),
                open=True,
            )

            info = packages.get(package)

            if not info:
                continue

            inputs = info.get("capabilities_full", [])
            outputs = info.get("outputs_full", [])

            if inputs:
                input_node = self.device_tree.insert(
                    device_node,
                    tk.END,
                    text="Input",
                    values=("group",),
                    open=True,
                )

                for cap in inputs:
                    self.device_tree.insert(
                        input_node,
                        tk.END,
                        text=cap.get("id", cap),
                        values=("capability",),
                    )

            if outputs:
                output_node = self.device_tree.insert(
                    device_node,
                    tk.END,
                    text="Output",
                    values=("group",),
                    open=True,
                )

                for cap in outputs:
                    self.device_tree.insert(
                        output_node,
                        tk.END,
                        text=cap.get("id", cap),
                        values=("capability",),
                    )

        self.refresh_mappings()

    def _on_tree_double_click(self, event):
        selection = self.device_tree.selection()

        if not selection:
            return

        item = self.device_tree.item(selection[0])
        values = item.get("values", [])

        if values and values[0] == "capability":
            source = item.get("text")
            self._open_map_dialog(source)

    #
    # Mapping
    #

    def refresh_mappings(self):
        profile = config_io.load_profile()

        self.map_text.config(state=tk.NORMAL)
        self.map_text.delete("1.0", tk.END)
        for source, mapping in profile.get("mappings", {}).items():
            self.map_text.insert(tk.END, f"{source} -> {config_io.mapping_desc(mapping)}\n")
        self.map_text.config(state=tk.DISABLED)

    def _open_map_dialog(self, source):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Map: {source}")
        dialog.geometry("480x460")

        ttk.Label(dialog, text=f"Map input:  {source}").pack(padx=8, pady=8)

        profile = config_io.load_profile()
        mappings = profile.get("mappings", {})

        current = mappings.get(source)

        if current:
            current_desc = config_io.mapping_desc(current)
            ttk.Label(
                dialog,
                text=f"Currently: {current_desc}",
                foreground="#4caf50",
            ).pack(padx=8)

        ttk.Label(dialog, text="Output device:").pack(padx=8, pady=(10, 2))

        from output.devices import OUTPUT_DEVICES

        device_var = tk.StringVar(value="virtual_x360")

        for device in OUTPUT_DEVICES:
            ttk.Radiobutton(
                dialog,
                text=f"{device.name}  ({device.description})",
                variable=device_var,
                value=device.id,
            ).pack(anchor=tk.W, padx=16)

        ttk.Label(dialog, text="Output function:").pack(padx=8, pady=(10, 2))

        target_var = tk.StringVar()

        target_frame = ttk.Frame(dialog)
        target_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        target_combo = ttk.Combobox(target_frame, textvariable=target_var, state="readonly")
        target_combo.pack(fill=tk.X)

        self._device_targets = {}

        def update_targets(*_args):
            device_id = device_var.get()
            device = next((d for d in OUTPUT_DEVICES if d.id == device_id), None)

            if device:
                self._device_targets = device.targets
                target_combo["values"] = list(device.targets.keys())

                if current:
                    tgt = current if isinstance(current, str) else current.get("target")
                    if tgt in device.targets:
                        target_var.set(tgt)
                        return

                if device.targets:
                    target_var.set(list(device.targets.keys())[0])

        for rb in dialog.winfo_children():
            if isinstance(rb, ttk.Radiobutton):
                rb.configure(command=update_targets)

        update_targets()

        gain_frame = ttk.Frame(dialog)
        gain_frame.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(gain_frame, text="Gain:").pack(side=tk.LEFT)
        gain_var = tk.StringVar(value="1.0")
        ttk.Entry(gain_frame, textvariable=gain_var, width=8).pack(side=tk.LEFT, padx=6)
        return_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(gain_frame, text="Return to center", variable=return_var).pack(side=tk.LEFT, padx=10)

        def apply():
            target = target_var.get()
            if not target:
                messagebox.showwarning("No target", "Select an output function")
                return

            try:
                gain = float(gain_var.get())
            except ValueError:
                gain = 1.0

            profile = config_io.load_profile()
            profile["mappings"][source] = {
                "target": target,
                "gain": gain,
                "return_to_center": return_var.get(),
            }
            config_io.save_profile(profile)

            self.refresh_mappings()
            self.log(f"Mapped {source} -> {target}")
            dialog.destroy()

        ttk.Button(dialog, text="Apply", command=apply).pack(padx=8, pady=10)

    def remove_mapping(self):
        profile = config_io.load_profile()
        mappings = profile.get("mappings", {})

        if not mappings:
            self.log("No mappings to remove.")
            return

        sources = list(mappings.keys())

        dialog = tk.Toplevel(self.root)
        dialog.title("Remove Mapping")
        dialog.geometry("360x400")

        ttk.Label(dialog, text="Select mapping to remove:").pack(padx=8, pady=8)

        self.rm_list = tk.Listbox(dialog)
        self.rm_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        for src, mapping in mappings.items():
            self.rm_list.insert(tk.END, f"{src} -> {config_io.mapping_desc(mapping)}")

        def do_remove():
            index = self.rm_list.curselection()

            if not index:
                return

            source = sources[index[0]]

            del mappings[source]
            profile["mappings"] = mappings
            config_io.save_profile(profile)

            self.refresh_mappings()
            self.log(f"Removed mapping: {source}")
            dialog.destroy()

        ttk.Button(dialog, text="Remove", command=do_remove).pack(padx=8, pady=8)

    #
    # Auto-route
    #

    def auto_route(self):
        selection = self.device_tree.selection()

        if not selection:
            self.log("Select a device to auto-route.")
            return

        item = self.device_tree.item(selection[0])
        node_id = selection[0]

        while node_id:
            node = self.device_tree.item(node_id)
            values = node.get("values", []) or []

            if values and values[0] == "device":
                device_text = node.get("text")
                break

            node_id = self.device_tree.parent(node_id)
        else:
            self.log("Select a device to auto-route.")
            return

        data = config_io.load_config()
        device = next(
            (d for d in data.get("devices", []) if device_text.startswith(d.get("name", ""))),
            None,
        )

        if device is None:
            self.log("Could not find selected device config.")
            return

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
        mappings, _missing = router.route(caps_data.get("capabilities", []))
        outputs = caps_data.get("outputs", [])

        profile = config_io.load_profile()
        profile["mappings"].update(mappings)
        config_io.save_profile(profile)

        self.refresh_devices()
        self.log(f"Auto-routed {len(mappings)} capabilities for {device.get('name')}")

        if outputs:
            self.log("Outputs not covered (need manual route):")
            for out in outputs:
                self.log(f"  {out.get('id')}")

    #
    # Menus
    #

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

        dialog = tk.Toplevel(self.root)
        dialog.title("Install from Library")
        dialog.geometry("460x300")

        ttk.Label(dialog, text="Select device to install:").pack(padx=8, pady=8)

        self.lib_list = tk.Listbox(dialog)
        self.lib_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        for d in devices:
            self.lib_list.insert(tk.END, f"{d.get('id')} - {d.get('name')}")

        def do_install():
            index = self.lib_list.curselection()

            if not index:
                return

            device_id = devices[index[0]].get("id")
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

    def show_preferences(self):
        messagebox.showinfo(
            "Preferences",
            "Settings are stored in:\n\n"
            "  config/devices.json   - connected devices\n"
            "  profiles/default.json - mappings\n"
            "  config/processors.json - processor pipelines\n\n"
            "These JSON files can be edited directly.",
        )

    def show_output_devices(self):
        from output.devices import OUTPUT_DEVICES

        dialog = tk.Toplevel(self.root)
        dialog.title("Output Devices")
        dialog.geometry("460x420")

        ttk.Label(dialog, text="Available virtual output devices:").pack(padx=8, pady=8)

        text = tk.Text(dialog, state=tk.DISABLED)
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        text.config(state=tk.NORMAL)
        for device in OUTPUT_DEVICES:
            text.insert(tk.END, f"{device.name}\n  {device.description}\n\n")
        text.config(state=tk.DISABLED)

    def show_about(self):
        messagebox.showinfo(
            "About CapabilityNexus",
            "CapabilityNexus\n\n"
            "Real-world input abstraction framework.\n"
            "Map any device capability to any virtual output.\n\n"
            "Open source - https://github.com/nidoto/CapabilityNexus",
        )

    def show_help(self):
        messagebox.showinfo(
            "Help",
            "How to use:\n\n"
            "1. Devices > Add Device - add your input device\n"
            "2. Double-click a device function in the tree\n"
            "3. Choose an output device (X360/Keyboard/Mouse)\n"
            "4. Choose the output function, click Apply\n\n"
            "Use Mappings > Auto-Route for one-click default mapping.",
        )

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
