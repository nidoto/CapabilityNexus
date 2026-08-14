import os
import sys
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import config_io
from tools.i18n import I18n


class CapabilityNexusGUI:

    def __init__(self, root):
        self.root = root
        self.i18n = I18n("zh")

        self.root.title(self.t("app_title"))
        self.root.geometry("1000x650")

        self._build_menubar()
        self._build_layout()

        self.refresh_devices()

    def t(self, key):
        return self.i18n.t(key)

    def _rebuild(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self._build_menubar()
        self._build_layout()
        self.refresh_devices()

    #
    # Menu bar
    #

    def _build_menubar(self):
        menubar = tk.Menu(self.root)

        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label=self.t("menu_preferences"), command=self.show_preferences)
        settings_menu.add_separator()
        settings_menu.add_command(label=self.t("menu_exit"), command=self.root.quit)
        menubar.add_cascade(label=self.t("menu_system"), menu=settings_menu)

        devices_menu = tk.Menu(menubar, tearoff=0)
        devices_menu.add_command(label=self.t("menu_add_device"), command=self.add_device_dialog)
        devices_menu.add_command(label=self.t("menu_install_library"), command=self.install_from_library)
        devices_menu.add_separator()
        devices_menu.add_command(label=self.t("menu_refresh"), command=self.refresh_devices)
        menubar.add_cascade(label=self.t("menu_devices"), menu=devices_menu)

        mappings_menu = tk.Menu(menubar, tearoff=0)
        mappings_menu.add_command(label=self.t("menu_auto_route"), command=self.auto_route)
        mappings_menu.add_command(label=self.t("menu_remove_mapping"), command=self.remove_mapping)
        mappings_menu.add_separator()
        mappings_menu.add_command(label=self.t("menu_view_mappings"), command=self.refresh_mappings)
        menubar.add_cascade(label=self.t("menu_mappings"), menu=mappings_menu)

        output_menu = tk.Menu(menubar, tearoff=0)
        output_menu.add_command(label=self.t("menu_output_devices"), command=self.show_output_devices)
        menubar.add_cascade(label=self.t("menu_output"), menu=output_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=self.t("menu_about"), command=self.show_about)
        help_menu.add_command(label=self.t("menu_help_item"), command=self.show_help)
        menubar.add_cascade(label=self.t("menu_help"), menu=help_menu)

        lang_menu = tk.Menu(menubar, tearoff=0)
        lang_menu.add_command(label="中文", command=lambda: self._switch_lang("zh"))
        lang_menu.add_command(label="English", command=lambda: self._switch_lang("en"))
        menubar.add_cascade(label=self.t("menu_language"), menu=lang_menu)

        self.root.config(menu=menubar)

    def _switch_lang(self, lang):
        self.i18n.set_language(lang)
        self.root.title(self.t("app_title"))
        self._rebuild()

    #
    # Layout
    #

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
        box = ttk.LabelFrame(parent, text=self.t("tree_devices"))
        box.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.device_tree = ttk.Treeview(box, columns=("func",), show="tree headings")
        self.device_tree.heading("#0", text=self.t("tree_device_function"))
        self.device_tree.heading("func", text=self.t("tree_type"))
        self.device_tree.column("func", width=120)
        self.device_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.device_tree.bind("<Double-1>", self._on_tree_double_click)
        self.device_tree.bind("<Return>", self._on_tree_double_click)

        hint = ttk.Label(box, text=self.t("tree_hint"))
        hint.pack(pady=4)

    def _build_mapping_panel(self, parent):
        box = ttk.LabelFrame(parent, text=self.t("panel_mappings"))
        box.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.map_text = tk.Text(box, state=tk.DISABLED)
        self.map_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        btns = ttk.Frame(box)
        btns.pack(fill=tk.X, padx=6, pady=4)
        ttk.Button(btns, text=self.t("panel_remove_mapping"), command=self.remove_mapping).pack(side=tk.LEFT, padx=2)

    def _build_log_panel(self, parent):
        logbox = ttk.LabelFrame(parent, text=self.t("panel_log"))
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
                    text=self.t("tree_input"),
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
                    text=self.t("tree_output"),
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
        dialog.title(f"{self.t('dlg_map_title')}: {source}")
        dialog.geometry("480x460")

        ttk.Label(dialog, text=f"{self.t('dlg_map_prompt')}:  {source}").pack(padx=8, pady=8)

        profile = config_io.load_profile()
        mappings = profile.get("mappings", {})

        current = mappings.get(source)

        if current:
            current_desc = config_io.mapping_desc(current)
            ttk.Label(
                dialog,
                text=f"{self.t('dlg_map_current')}: {current_desc}",
                foreground="#4caf50",
            ).pack(padx=8)

        ttk.Label(dialog, text=self.t("dlg_output_device")).pack(padx=8, pady=(10, 2))

        from output.devices import OUTPUT_DEVICES

        device_var = tk.StringVar(value="virtual_x360")

        for device in OUTPUT_DEVICES:
            ttk.Radiobutton(
                dialog,
                text=f"{device.name}  ({device.description})",
                variable=device_var,
                value=device.id,
            ).pack(anchor=tk.W, padx=16)

        ttk.Label(dialog, text=self.t("dlg_output_function")).pack(padx=8, pady=(10, 2))

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
                    if isinstance(current, list):
                        tgt = current[0].get("target") if current else None
                    elif isinstance(current, str):
                        tgt = current
                    else:
                        tgt = current.get("target")

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
        ttk.Label(gain_frame, text=self.t("dlg_gain")).pack(side=tk.LEFT)
        gain_var = tk.StringVar(value="1.0")
        ttk.Entry(gain_frame, textvariable=gain_var, width=8).pack(side=tk.LEFT, padx=6)
        return_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(gain_frame, text=self.t("dlg_return_center"), variable=return_var).pack(side=tk.LEFT, padx=10)

        def apply():
            target = target_var.get()
            if not target:
                messagebox.showwarning(self.t("dlg_no_target"), self.t("dlg_no_target_msg"))
                return

            try:
                gain = float(gain_var.get())
            except ValueError:
                gain = 1.0

            new_mapping = {
                "target": target,
                "gain": gain,
                "return_to_center": return_var.get(),
            }

            profile = config_io.load_profile()
            existing = profile["mappings"].get(source)

            if append_var.get():
                if isinstance(existing, list):
                    profile["mappings"][source] = existing + [new_mapping]
                elif isinstance(existing, dict):
                    profile["mappings"][source] = [existing, new_mapping]
                else:
                    profile["mappings"][source] = [new_mapping]
            else:
                profile["mappings"][source] = [new_mapping]

            config_io.save_profile(profile)

            self.refresh_mappings()
            self.log(f"{self.t('log_mapped')} {source} -> {target}")
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=8, pady=4)
        append_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            btn_frame,
            text="Add as extra output (one-to-many)",
            variable=append_var,
        ).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text=self.t("dlg_apply"), command=apply).pack(side=tk.RIGHT)

    def remove_mapping(self):
        profile = config_io.load_profile()
        mappings = profile.get("mappings", {})

        if not mappings:
            self.log("No mappings to remove.")
            return

        sources = list(mappings.keys())

        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("menu_remove_mapping"))
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
            self.log(f"{self.t('log_removed_mapping')}: {source}")
            dialog.destroy()

        ttk.Button(dialog, text=self.t("dlg_apply"), command=do_remove).pack(padx=8, pady=8)

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
        self.log(f"{self.t('log_auto_routed')} {len(mappings)}: {device.get('name')}")

        if outputs:
            self.log("Outputs not covered (need manual route):")
            for out in outputs:
                self.log(f"  {out.get('id')}")

    #
    # Add device
    #

    def add_device_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("dlg_add_title"))
        dialog.geometry("520x520")

        # 连接方式
        ttk.Label(dialog, text=self.t("dlg_conn_type")).pack(padx=8, pady=(10, 2))
        conn_var = tk.StringVar(value="serial")

        conn_options = [
            ("serial", "USB / Serial"),
            ("hid", "USB HID (gamepad/wheel)"),
            ("xinput", "XInput compatible (gamepad)"),
            ("tcp", "Network / WiFi (TCP)"),
            ("udp", "Network / WiFi (UDP)"),
            ("bluetooth", "Bluetooth (RFCOMM)"),
            ("ftms", "Bluetooth (BLE Trainer)"),
            ("custom", "Custom connection"),
        ]

        conn_combo = ttk.Combobox(
            dialog,
            textvariable=conn_var,
            values=[label for _key, label in conn_options],
            state="readonly",
        )
        conn_combo.pack(fill=tk.X, padx=8)

        conn_map = {label: key for key, label in conn_options}

        # 字段区
        fields_frame = ttk.LabelFrame(dialog, text="")
        fields_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        field_vars = {}
        bluetooth_selected = {}

        # 底部区（名称/硬件库检索/能力包/保存）——连接成功后显示
        bottom_frame = ttk.Frame(dialog)
        bottom_frame.pack(fill=tk.X, padx=8, pady=6)

        def add_field(parent, label, default):
            frame = ttk.Frame(parent)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=label, width=24).pack(side=tk.LEFT)
            var = tk.StringVar(value=default)
            ttk.Entry(frame, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
            return var

        def build_fields(conn_key):
            for widget in fields_frame.winfo_children():
                widget.destroy()

            field_vars.clear()
            bluetooth_selected.clear()

            if conn_key == "serial":
                field_vars["port"] = add_field(fields_frame, self.t("dlg_serial_port"), "COM3")
                field_vars["baudrate"] = add_field(fields_frame, self.t("dlg_baudrate"), "115200")
                show_bottom()
            elif conn_key == "tcp":
                field_vars["host"] = add_field(fields_frame, self.t("dlg_host"), "192.168.1.100")
                field_vars["port"] = add_field(fields_frame, self.t("dlg_port"), "8888")
                show_bottom()
            elif conn_key == "udp":
                field_vars["host"] = add_field(fields_frame, self.t("dlg_host"), "0.0.0.0")
                field_vars["port"] = add_field(fields_frame, self.t("dlg_port"), "8888")
                show_bottom()
            elif conn_key == "hid":
                field_vars["index"] = add_field(fields_frame, "Joystick index", "0")
                show_bottom()
            elif conn_key in ("bluetooth", "ftms"):
                # 蓝牙：搜索配对窗口
                ttk.Button(
                    fields_frame,
                    text="Search Bluetooth Devices...",
                    command=lambda: self._bluetooth_scan_dialog(bluetooth_selected, on_bluetooth_picked, conn_key),
                ).pack(pady=12)

                status_var = tk.StringVar(value="No device selected")
                ttk.Label(fields_frame, textvariable=status_var).pack(pady=4)
                field_vars["_status"] = status_var

                hide_bottom()
            else:
                show_bottom()

        def on_bluetooth_picked(device_info):
            bluetooth_selected.update(device_info)

            status = field_vars.get("_status")
            if status:
                status.set(f"Selected: {device_info.get('label', '?')}")

            show_bottom()

        def hide_bottom():
            for widget in bottom_frame.winfo_children():
                widget.destroy()

        def show_bottom():
            for widget in bottom_frame.winfo_children():
                widget.destroy()

            # 自定义名称
            ttk.Label(bottom_frame, text=self.t("dlg_custom_name")).pack(padx=4, pady=(6, 2))
            name_var = tk.StringVar()
            ttk.Entry(bottom_frame, textvariable=name_var).pack(fill=tk.X, padx=4)

            # 硬件库检索勾选
            use_library_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                bottom_frame,
                text=self.t("dlg_use_library"),
                variable=use_library_var,
            ).pack(anchor=tk.W, padx=4, pady=2)

            # 能力包
            ttk.Label(bottom_frame, text=self.t("dlg_package")).pack(padx=4, pady=(6, 2))
            pkg_var = tk.StringVar(value="motion_demo")
            ttk.Entry(bottom_frame, textvariable=pkg_var).pack(fill=tk.X, padx=4)

            ttk.Button(
                bottom_frame,
                text=self.t("dlg_save"),
                command=lambda: save(conn_map[conn_var.get()], name_var, use_library_var, pkg_var),
            ).pack(padx=4, pady=8)

        def save(conn_key, name_var, use_library_var, pkg_var):
            driver = conn_key

            if conn_key in ("tcp", "udp", "bluetooth", "custom"):
                driver = "serial"

            entry = {
                "name": name_var.get() or "New Device",
                "driver": driver,
                "package": pkg_var.get(),
                "use_library": use_library_var.get(),
            }

            if conn_key == "serial":
                entry["connection"] = {
                    "type": "serial",
                    "port": field_vars["port"].get(),
                    "baudrate": int(field_vars["baudrate"].get() or 115200),
                }
            elif conn_key == "tcp":
                entry["connection"] = {
                    "type": "tcp",
                    "host": field_vars["host"].get(),
                    "port": int(field_vars["port"].get() or 8888),
                }
            elif conn_key == "udp":
                entry["connection"] = {
                    "type": "udp",
                    "host": field_vars["host"].get(),
                    "port": int(field_vars["port"].get() or 8888),
                }
            elif conn_key == "bluetooth":
                if not bluetooth_selected:
                    messagebox.showwarning(self.t("dlg_no_target"), "Select a Bluetooth device first")
                    return
                entry["connection"] = {
                    "type": "bluetooth",
                    "device": bluetooth_selected.get("port") or bluetooth_selected.get("address"),
                    "channel": int(bluetooth_selected.get("channel", 1)),
                }
            elif conn_key == "ftms":
                if not bluetooth_selected:
                    messagebox.showwarning(self.t("dlg_no_target"), "Select a BLE device first")
                    return
                entry["driver"] = "ftms"
                entry["address"] = bluetooth_selected.get("address")
            elif conn_key == "hid":
                entry["driver"] = "hid"
                entry["index"] = int(field_vars["index"].get() or 0)

            data = config_io.load_config()

            if use_library_var.get():
                try:
                    from devices.device_library import DeviceLibrary

                    library = DeviceLibrary(
                        cache_path=os.path.join("config", "device_library_cache.json"),
                    )
                    library.refresh()

                    fingerprint = None
                    if conn_key == "serial":
                        fingerprint = {
                            "type": "serial",
                            "vid": field_vars["port"].get(),
                        }
                    elif conn_key == "xinput":
                        fingerprint = {"type": "xinput"}

                    detected = {"fingerprint": fingerprint or {}}
                    matched = library.identify(detected) if fingerprint else None

                    if matched:
                        library.install(
                            matched.get("id"),
                            packages_path=config_io.PACKAGES_PATH,
                        )
                        entry["package"] = matched.get("package", entry.get("package"))
                        entry["library_id"] = matched.get("id")
                        self.log(f"Library match: {matched.get('name')}")
                except Exception as e:
                    self.log(f"Library lookup failed: {e}")

            data["devices"].append(entry)
            config_io.save_config(data)

            self.refresh_devices()
            self.log(f"{self.t('log_added_device')}: {entry.get('name')}")
            dialog.destroy()

        def on_conn_change(*_args):
            build_fields(conn_map[conn_var.get()])

        conn_combo.bind("<<ComboboxSelected>>", on_conn_change)
        build_fields("serial")

    def _bluetooth_scan_dialog(self, bluetooth_selected, on_picked, conn_key):
        import queue

        from devices.bluetooth_scanner import BluetoothScanner

        dialog = tk.Toplevel(self.root)
        dialog.title("Bluetooth Devices")
        dialog.geometry("560x460")

        ttk.Label(dialog, text="Paired devices:", font=("Arial", 10, "bold")).pack(
            anchor=tk.W, padx=8, pady=(8, 2),
        )

        self.bt_list = tk.Listbox(dialog, height=12)
        self.bt_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        devices = []
        scanner = BluetoothScanner()
        result_queue = queue.Queue()

        def worker_paired():
            paired = scanner.list_paired_ble()
            result_queue.put(("paired", paired))

        def worker_scan():
            found = scanner.scan_ble(timeout=5)
            result_queue.put(("scan", found))

        def poll_queue():
            try:
                while True:
                    kind, payload = result_queue.get_nowait()

                    if kind == "paired":
                        self.bt_list.delete(0, tk.END)

                        if not payload:
                            self.bt_list.insert(tk.END, "(no paired Bluetooth devices found)")
                            continue

                        for d in payload:
                            state = "connected" if d.get("connected") else ""
                            label = f"{d['name']}  [{state}]" if state else d["name"]

                            devices.append({
                                "label": label,
                                "address": d["address"],
                                "port": d["address"],
                                "channel": 1,
                                "is_ble": d.get("ble", False),
                                "is_paired": True,
                            })
                            self.bt_list.insert(tk.END, label)

                    elif kind == "scan":
                        self.bt_list.delete(0, tk.END)

                        if not payload:
                            self.bt_list.insert(tk.END, "(no new devices found)")
                            continue

                        for d in payload:
                            devices.append({
                                "label": d["name"],
                                "address": d["address"],
                                "port": d["address"],
                                "channel": 1,
                                "is_ble": True,
                                "is_paired": False,
                            })
                            self.bt_list.insert(tk.END, f"NEW  {d['name']} - {d['address']}")

            except queue.Empty:
                pass

            self.root.after(100, poll_queue)

        def search_new():
            self.bt_list.delete(0, tk.END)
            devices.clear()
            self.bt_list.insert(tk.END, "(scanning for new BLE devices...)")

            import threading
            threading.Thread(target=worker_scan, daemon=True).start()

        def select():
            index = self.bt_list.curselection()

            if not index:
                return

            device_info = devices[index[0]]

            if conn_key == "bluetooth" and not device_info.get("is_ble"):
                on_picked(device_info)
                dialog.destroy()
            elif conn_key == "ftms" and device_info.get("is_ble"):
                on_picked(device_info)
                dialog.destroy()
            else:
                messagebox.showwarning(
                    self.t("dlg_no_target"),
                    "Pick a matching device type",
                )

        btns = ttk.Frame(dialog)
        btns.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(btns, text="Search New Devices...", command=search_new).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text=self.t("dlg_apply"), command=select).pack(side=tk.LEFT, padx=2)

        import threading
        threading.Thread(target=worker_paired, daemon=True).start()
        self.root.after(100, poll_queue)

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
        dialog.title(self.t("menu_install_library"))
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

        ttk.Button(dialog, text=self.t("dlg_apply"), command=do_install).pack(padx=8, pady=8)

    def show_output_devices(self):
        from output.devices import OUTPUT_DEVICES

        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("menu_output_devices"))
        dialog.geometry("460x420")

        ttk.Label(dialog, text="Available virtual output devices:").pack(padx=8, pady=8)

        text = tk.Text(dialog, state=tk.DISABLED)
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        text.config(state=tk.NORMAL)
        for device in OUTPUT_DEVICES:
            text.insert(tk.END, f"{device.name}\n  {device.description}\n\n")
        text.config(state=tk.DISABLED)

    def show_preferences(self):
        messagebox.showinfo(self.t("prefs_title"), self.t("prefs_body"))

    def show_about(self):
        messagebox.showinfo(self.t("about_title"), self.t("about_body"))

    def show_help(self):
        messagebox.showinfo(self.t("help_title"), self.t("help_body"))

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
