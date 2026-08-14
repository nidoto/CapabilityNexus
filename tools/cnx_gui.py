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
        self.app = None

        self.root.title(self.t("app_title"))
        self.root.geometry("1600x1000")
        self.root.minsize(1280, 820)
        self._configure_style()

        self._build_menubar()
        self._build_layout()

        self.refresh_devices()
        self._start_monitor_loop()
        self.root.after(300, self._auto_start_engine)

    def _configure_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.root.configure(bg="#111827")
        style.configure("TFrame", background="#111827")
        style.configure("TLabelframe", background="#1b2535", bordercolor="#334155")
        style.configure("TLabelframe.Label", background="#1b2535", foreground="#cbd5e1", font=("Segoe UI", 10, "bold"))
        style.configure("TLabel", background="#111827", foreground="#cbd5e1")
        style.configure("Title.TLabel", background="#111827", foreground="#f8fafc", font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", background="#111827", foreground="#94a3b8", font=("Segoe UI", 9))
        style.configure("TButton", padding=(10, 6), background="#263449", foreground="#e2e8f0")
        style.map("TButton", background=[("active", "#334155")])
        style.configure("Accent.TButton", padding=(12, 7), background="#2563eb", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#1d4ed8")])
        style.configure("Treeview", background="#172033", fieldbackground="#172033", foreground="#dbeafe", rowheight=27, borderwidth=0)
        style.configure("Treeview.Heading", background="#263449", foreground="#cbd5e1", padding=7, relief="flat")
        style.map("Treeview", background=[("selected", "#1d4ed8")], foreground=[("selected", "#ffffff")])

    def _set_engine_badge(self, running):
        if not hasattr(self, "engine_badge"):
            return
        if running:
            self.engine_badge.configure(text=self.t("ui_engine_online"), bg="#123b34", fg="#86efac")
        else:
            self.engine_badge.configure(text=self.t("ui_engine_offline"), bg="#3f1d2e", fg="#fda4af")

    def _auto_start_engine(self):
        self._check_runtime_dependencies()
        if self.app is None:
            self.start_engine()

    def _check_runtime_dependencies(self):
        from tools.dependency_check import check_dependencies, missing_dependencies

        status = check_dependencies()
        missing = missing_dependencies(status)
        if not missing:
            return

        details = "\n".join(f"- {item}" for item in missing)

        # 区分：驱动缺失（可在客户端内装）vs Python 包缺失（需 pip）
        driver_missing = []
        python_missing = []
        for item in missing:
            if "ViGEmBus" in item or "HidHide" in item:
                driver_missing.append(item)
            else:
                python_missing.append(item)

        lines = ["CapabilityNexus 依赖检查发现以下组件未安装：", "", details, ""]

        can_fix_in_app = bool(driver_missing)
        if can_fix_in_app:
            lines.append("驱动可以通过 系统 > 驱动管理 一键安装。")

        if python_missing:
            lines.append("Python 包需要通过 pip 安装：")
            lines.append("  py -3 -m pip install -r requirements.txt")

        message = "\n".join(lines)
        self.log("Missing runtime dependencies: " + ", ".join(missing))

        if can_fix_in_app:
            answer = messagebox.askyesno(
                self.t("menu_drivers"),
                message + "\n\n" + self.t("drivers_open_manager_ask"),
            )
            if answer:
                self.show_drivers()
        else:
            messagebox.showwarning(self.t("menu_drivers"), message)

    def _start_monitor_loop(self):
        self._monitor_job = self.root.after(200, self._monitor_tick)

    def _monitor_tick(self):
        self._refresh_live_values()
        self._render_request_tree()
        self._render_request_monitor()

        # 服务面板低频刷新（驱动 sc query 较重，约每 2 秒）
        self._services_tick_counter = getattr(self, "_services_tick_counter", 0) + 1
        if self._services_tick_counter % 10 == 0:
            self._services_tick_refresh()

        self._monitor_job = self.root.after(200, self._monitor_tick)

    def _services_tick_refresh(self):
        """定时刷新服务面板状态（不频繁）。"""
        if hasattr(self, "_refresh_web"):
            self._refresh_web()
        if hasattr(self, "_refresh_drivers"):
            self._refresh_drivers()

    def t(self, key):
        return self.i18n.t(key)

    def _rebuild(self):
        if getattr(self, "_monitor_job", None) is not None:
            self.root.after_cancel(self._monitor_job)
            self._monitor_job = None

        for widget in self.root.winfo_children():
            widget.destroy()

        self._build_menubar()
        self._build_layout()
        self.refresh_devices()
        self._start_monitor_loop()

    #
    # Menu bar
    #

    def _build_menubar(self):
        menubar = tk.Menu(self.root)

        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label=self.t("menu_preferences"), command=self.show_preferences)
        settings_menu.add_command(label=self.t("menu_services"), command=self.show_services)
        settings_menu.add_command(label=self.t("menu_drivers"), command=self.show_drivers)
        settings_menu.add_command(label=self.t("menu_hidhide"), command=self.show_hidhide)
        settings_menu.add_separator()
        settings_menu.add_command(label=self.t("menu_start_engine"), command=self.start_engine)
        settings_menu.add_command(label=self.t("menu_stop_engine"), command=self.stop_engine)
        settings_menu.add_separator()
        settings_menu.add_command(label=self.t("menu_exit"), command=self.root.quit)
        menubar.add_cascade(label=self.t("menu_system"), menu=settings_menu)

        devices_menu = tk.Menu(menubar, tearoff=0)
        devices_menu.add_command(label=self.t("menu_add_device"), command=self.add_device_dialog)
        devices_menu.add_command(label=self.t("menu_history_devices"), command=self.show_history_devices)
        devices_menu.add_separator()
        devices_menu.add_command(label=self.t("menu_refresh"), command=self.refresh_devices)
        menubar.add_cascade(label=self.t("menu_devices"), menu=devices_menu)

        mappings_menu = tk.Menu(menubar, tearoff=0)
        mappings_menu.add_command(label=self.t("menu_game_profiles"), command=self.show_game_profiles)
        mappings_menu.add_command(label=self.t("menu_tuning_workspace"), command=lambda: self.show_tuning_workspace())
        mappings_menu.add_separator()
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
        header = tk.Frame(self.root, bg="#111827", height=78)
        header.pack(fill=tk.X, padx=18, pady=(14, 10))
        header.pack_propagate(False)

        identity = ttk.Frame(header)
        identity.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(identity, text="CapabilityNexus", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(identity, text=self.t("ui_subtitle"), style="Subtitle.TLabel").pack(anchor=tk.W, pady=(2, 0))

        actions = ttk.Frame(header)
        actions.pack(side=tk.RIGHT, fill=tk.Y)
        self.engine_badge = tk.Label(actions, text=self.t("ui_engine_offline"), bg="#3f1d2e", fg="#fda4af", font=("Segoe UI", 9, "bold"), padx=8, pady=5)
        self.engine_badge.pack(side=tk.LEFT, padx=(0, 10), pady=17)
        ttk.Button(actions, text=self.t("ui_start_engine"), style="Accent.TButton", command=self.start_engine).pack(side=tk.LEFT, padx=3, pady=15)
        ttk.Button(actions, text=self.t("ui_stop_engine"), command=self.stop_engine).pack(side=tk.LEFT, padx=3, pady=15)
        ttk.Button(actions, text=self.t("ui_refresh"), command=self.refresh_devices).pack(side=tk.LEFT, padx=(3, 0), pady=15)
        self._set_engine_badge(self.app is not None)

        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        col_input = ttk.Frame(main)
        col_output = ttk.Frame(main)
        col_request = ttk.Frame(main)
        main.add(col_input, weight=1)
        main.add(col_output, weight=1)
        main.add(col_request, weight=1)

        self._build_device_tree(col_input)
        self._build_output_panel(col_output)
        self._build_request_panel(col_request)

        self._build_log_panel(self.root)

    def _build_device_tree(self, parent):
        box = ttk.LabelFrame(parent, text=self.t("tree_devices"))
        box.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.device_tree = ttk.Treeview(box, columns=("func",), show="tree headings")
        self.device_tree.heading("#0", text=self.t("tree_device_function"))
        self.device_tree.heading("func", text=self.t("tree_mapping"))
        self.device_tree.column("func", width=120)
        self.device_tree.configure(height=14)
        self.device_tree.pack(fill=tk.BOTH, expand=False, padx=6, pady=6)

        self.device_tree.bind("<Double-1>", self._on_tree_double_click)
        self.device_tree.bind("<Return>", self._on_tree_double_click)
        self.device_tree.bind("<Button-3>", self._on_tree_right_click)

        self.tree_menu = tk.Menu(self.root, tearoff=0)
        self.tree_menu.add_command(label=self.t("btn_add_device"), command=self.add_device_dialog)
        self.tree_menu.add_command(label=self.t("btn_remove_device"), command=self.remove_selected_device)
        self.tree_menu.add_command(label=self.t("btn_auto_route"), command=self.auto_route)
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label=self.t("menu_refresh"), command=self.refresh_devices)

        hint = ttk.Label(box, text=self.t("tree_hint"))
        hint.pack(pady=4)

        self._build_input_monitor(box)

    def _build_input_monitor(self, parent):
        mon = ttk.LabelFrame(parent, text=self.t("mon_input"))
        mon.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self.input_monitor = tk.Text(mon, height=10, state=tk.DISABLED, bg="#0f172a", fg="#67e8f9", relief=tk.FLAT, padx=8, pady=6, font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(mon, command=self.input_monitor.yview)
        self.input_monitor.configure(yscrollcommand=scrollbar.set)
        mon.columnconfigure(0, weight=1)
        mon.rowconfigure(0, weight=1)
        self.input_monitor.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 4), pady=4)

    def _build_output_monitor(self, parent):
        mon = ttk.LabelFrame(parent, text=self.t("mon_output"))
        mon.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self.output_monitor = tk.Text(mon, height=10, state=tk.DISABLED, bg="#0f172a", fg="#86efac", relief=tk.FLAT, padx=8, pady=6, font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(mon, command=self.output_monitor.yview)
        self.output_monitor.configure(yscrollcommand=scrollbar.set)
        mon.columnconfigure(0, weight=1)
        mon.rowconfigure(0, weight=1)
        self.output_monitor.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 4), pady=4)

    def _append_monitor(self, widget, text):
        widget.config(state=tk.NORMAL)
        widget.insert(tk.END, text + "\n")
        widget.see(tk.END)

        # 限制行数
        lines = int(widget.index("end-1c").split(".")[0])
        if lines > 50:
            widget.delete("1.0", f"{lines - 40}.0")

        widget.config(state=tk.DISABLED)

    def _on_tree_right_click(self, event):
        item = self.device_tree.identify_row(event.y)

        if item:
            self.device_tree.selection_set(item)

        self.tree_menu.tk_popup(event.x_root, event.y_root)

    def _reload_runtime_mapping(self, profile):
        if self.app is None or not hasattr(self.app, "mapping_engine"):
            return
        self.app.mapping_engine.load_mappings(profile.get("mappings", {}))

    def _find_device_node(self, item_id):
        while item_id:
            node = self.device_tree.item(item_id)
            tags = node.get("tags", [])

            if "device" in tags:
                return node.get("text")

            item_id = self.device_tree.parent(item_id)

        return None

    def remove_selected_device(self):
        selection = self.device_tree.selection()

        if not selection:
            self.log("Select a device to remove.")
            return

        device_text = self._find_device_node(selection[0])

        if device_text is None:
            self.log("Select a device node to remove.")
            return

        if not messagebox.askyesno("Remove Device", f"Remove '{device_text}'?"):
            return

        data = config_io.load_config()
        devices = data.get("devices", [])

        device = next(
            (d for d in devices if device_text.startswith(d.get("name", ""))),
            None,
        )

        if device is None:
            self.log("Device not found in config.")
            return

        if self.app is not None and hasattr(self.app, "device_manager"):
            self.app.device_manager.disconnect_device(device)

        devices.remove(device)
        data["devices"] = devices
        config_io.save_config(data)

        self.refresh_devices()
        self.log(f"Removed device: {device.get('name')}")

    def show_history_devices(self):
        """显示历史设备列表（用户曾连接过，可能当前不在线）"""
        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("menu_history_devices"))
        dialog.geometry("480x360")

        ttk.Label(
            dialog,
            text=self.t("dlg_history_hint"),
            wraplength=440,
        ).pack(padx=8, pady=8, fill=tk.X)

        self.history_list = tk.Listbox(dialog)
        self.history_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        data = config_io.load_config()
        devices = data.get("devices", [])

        online_names = set()

        if self.app is not None and hasattr(self.app, "device_manager"):
            for entry in self.app.device_manager.online_devices():
                online_names.add(entry.get("name"))

        for device in devices:
            name = device.get("name", "?")
            conn = config_io.device_conn_label(device)
            status = "在线" if name in online_names else "离线"
            self.history_list.insert(tk.END, f"[{status}] {name}  ({conn})")

        if not devices:
            self.history_list.insert(tk.END, "(无历史设备记录)")

        def remove_selected():
            sel = self.history_list.curselection()

            if not sel:
                self.log("Select a history device to remove.")
                return

            # 列表条目按 devices 顺序插入，索引对应
            idx = sel[0]

            if idx >= len(devices):
                return

            device = devices[idx]

            if not messagebox.askyesno(
                self.t("menu_history_devices"),
                f"Remove '{device.get('name')}' from history?",
            ):
                return

            devices.remove(device)
            data["devices"] = devices
            config_io.save_config(data)
            self.history_list.delete(idx)
            self.log(f"Removed history device: {device.get('name')}")

        btn = ttk.Button(dialog, text=self.t("btn_remove_device"), command=remove_selected)
        btn.pack(padx=8, pady=8)

    def _build_output_panel(self, parent):
        box = ttk.LabelFrame(parent, text=self.t("tree_outputs"))
        box.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.output_tree = ttk.Treeview(box, columns=("func",), show="tree headings")
        self.output_tree.heading("#0", text=self.t("tree_output_device"))
        self.output_tree.heading("func", text=self.t("tree_mapping"))
        self.output_tree.column("func", width=120)
        self.output_tree.configure(height=14)
        self.output_tree.pack(fill=tk.BOTH, expand=False, padx=6, pady=6)

        self.output_tree.bind("<Double-1>", self._on_output_tree_double_click)
        self.output_tree.bind("<Return>", self._on_output_tree_double_click)
        self.output_tree.bind("<Button-3>", self._on_output_tree_right_click)

        self.output_tree_menu = tk.Menu(self.root, tearoff=0)
        self.output_tree_menu.add_command(
            label=self.t("btn_add_output"),
            command=self.add_output_dialog,
        )
        self.output_tree_menu.add_command(
            label=self.t("btn_remove_output"),
            command=self.remove_selected_output,
        )

        hint = ttk.Label(box, text=self.t("tree_output_hint"))
        hint.pack(pady=4)

        self._build_output_monitor(box)

        self.refresh_outputs()

    def _build_request_panel(self, parent):
        box = ttk.LabelFrame(parent, text=self.t("panel_requests"))
        box.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 当前程序：识别用户运行的程序，匹配反向需求库
        prog = ttk.LabelFrame(box, text=self.t("prog_current"))
        prog.pack(fill=tk.X, padx=6, pady=(4, 2))

        row = ttk.Frame(prog)
        row.pack(fill=tk.X, padx=4, pady=4)

        # 可输入过滤：输入关键字（如 gta）即过滤进程列表
        self.proc_combo = ttk.Combobox(row)
        self.proc_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.proc_combo.bind("<KeyRelease>", self._on_proc_filter)
        self.proc_combo.bind("<<ComboboxSelected>>", self._on_proc_selected)
        self.proc_combo.bind("<Return>", self._on_proc_filter)
        self.proc_combo.bind("<Double-Button-1>", self._on_proc_double_click)

        self.proc_refresh_btn = ttk.Button(
            row,
            text=self.t("btn_refresh_proc"),
            command=self._refresh_process_list,
        )
        self.proc_refresh_btn.pack(side=tk.LEFT, padx=2)

        self.prog_status = ttk.Label(
            prog,
            text=self.t("prog_status_none"),
            foreground="#666",
            wraplength=260,
        )
        self.prog_status.pack(fill=tk.X, padx=4, pady=(0, 4))

        self._refresh_process_list()

        self._build_request_monitor(box)

    def _refresh_process_list(self):
        """枚举进程并回填下拉框（ctypes 极快，同步执行）"""
        from devices.process_list import list_processes

        try:
            self._process_entries = list_processes()
        except Exception as e:
            print("[ProcessList] enumerate failed:", e)
            self._process_entries = []

        self._apply_proc_filter()

    def _apply_proc_filter(self):
        """仅内存过滤，不重新枚举进程"""
        if not hasattr(self, "_process_entries"):
            self._process_entries = []

        query = self._current_proc_filter()

        labels = []
        self._process_keys = []

        for entry in self._process_entries:
            name = entry.get("name", "")
            pid = entry.get("pid")
            title = entry.get("title", "")

            if title:
                label = f"{name} (PID {pid}) - {title[:40]}"
            else:
                label = f"{name} (PID {pid})"

            # 关键字匹配进程名或窗口标题
            if query:
                haystack = f"{name} {title}".lower()
                if query not in haystack:
                    continue

            labels.append(label)
            self._process_keys.append(entry)

        self.proc_combo["values"] = labels

    def _current_proc_filter(self):
        try:
            return (self.proc_combo.get() or "").strip().lower()
        except Exception:
            return ""

    def _on_proc_filter(self, event):
        """输入关键字：内存过滤进程列表，不重新枚举"""
        self._apply_proc_filter()

        # 若输入已精确命中某个进程名，自动识别
        query = self._current_proc_filter()

        if query:
            for entry in self._process_entries:
                if (entry.get("name") or "").lower() == query:
                    self.proc_combo.selection_clear()
                    self._identify_process(entry)
                    return

    def _on_proc_selected(self, event):
        """从下拉列表选择后自动识别"""
        index = self.proc_combo.current()

        if index < 0 or index >= len(self._process_keys):
            return

        self._identify_process(self._process_keys[index])

    def _on_proc_double_click(self, event):
        """双击进程：若该进程有对应游戏配置，打开该配置的调优页面。"""
        index = self.proc_combo.current()

        if index < 0 or index >= len(self._process_keys):
            return

        entry = self._process_keys[index]

        from devices.process_list import process_exe_name

        try:
            exe_name = process_exe_name(entry) or ""
        except Exception as error:
            self.log(f"Process exe lookup failed: {error}")
            return

        profile_name = self._profile_for_process(exe_name)

        if profile_name is None:
            self.log(f"No tuning profile for process: {exe_name or entry.get('name')}")
            return

        # 自动切换到该游戏的配置并打开调优页面
        from tools import config_io

        if config_io.get_active_profile() != profile_name:
            if not config_io.set_active_profile(profile_name):
                return
            self.log(f"Active game profile: {profile_name}")
            self._reload_profile_config()

        self.show_tuning_workspace(profile_name)

    @staticmethod
    def _profile_for_process(exe_name):
        """进程 exe 名 → 游戏配置名（无匹配返回 None）。"""
        if not exe_name:
            return None

        exe_lower = exe_name.lower().replace(".exe", "").replace("_", " ").strip()

        from tools import config_io

        profiles = config_io.list_profiles()
        if "default" in profiles:
            profiles.remove("default")

        # 精确匹配：配置名与 exe 名相近
        for name in profiles:
            if exe_lower in name or name in exe_lower:
                return name

        return None

    def _identify_process(self, entry):
        """识别进程：匹配反向需求库并导入"""
        from devices.process_list import process_exe_name
        exe_name = process_exe_name(entry)
        self._selected_process_label = f"{entry.get('name')} (PID {entry.get('pid')})"

        self.log(f"{self.t('log_selected_proc')}: {entry.get('name')} (PID {entry.get('pid')})")
        self.prog_status.config(text="正在检索程序需求库...", foreground="#2563eb")

        import threading

        def worker():
            try:
                from devices.request_library import RequestLibrary

                library = RequestLibrary()
                library.ensure_loaded()
                matched = library.identify(exe_name)
                if matched is None:
                    result = ("unmatched", exe_name, None)
                else:
                    program_id = matched.get("id")
                    downloaded = library.download(program_id)
                    result = (
                        "matched" if downloaded is not None else "download_failed",
                        matched.get("name", program_id),
                        downloaded,
                    )
            except Exception as error:
                result = ("error", str(error), None)

            self.root.after(0, lambda: apply_result(result))

        def apply_result(result):
            status, value, downloaded = result
            if status == "unmatched":
                self.prog_status.config(
                    text=self.t("prog_status_unmatched").format(value),
                    foreground="#c0392b",
                )
                self.log(self.t("log_unmatched_proc"))
            elif status == "download_failed":
                self.prog_status.config(
                    text=self.t("prog_status_download_fail").format(value),
                    foreground="#c0392b",
                )
            elif status == "error":
                self.prog_status.config(text=f"需求库检索失败：{value}", foreground="#c0392b")
                self.log(f"Request library failed: {value}")
            else:
                self._current_program = downloaded
                self._import_request_config(downloaded)
                self.prog_status.config(
                    text=self.t("prog_status_matched").format(value),
                    foreground="#2e7d32",
                )

        threading.Thread(target=worker, daemon=True).start()

    def _import_request_config(self, config):
        """导入反向需求配置：把已知请求写入 StatusMonitor 持久列表"""
        if self.app is None or not hasattr(self.app, "status_monitor"):
            return

        requests = (config.get("requests_data") or {}).get("requests", {})

        if not isinstance(requests, dict):
            requests = {}

        source = config.get("source", config.get("id", "library"))

        with self.app.status_monitor._lock:
            for target, info in requests.items():
                value = self._request_default_value(info)

                if target not in self.app.status_monitor.request_values:
                    self.app.status_monitor.request_values[target] = value
                    self.app.status_monitor.request_sources[target] = source

        self.log(self.t("log_imported_req").format(len(requests)))

        mapping = config.get("mapping") or (config.get("requests_data") or {}).get("mapping", {})

        if mapping:
            self._apply_request_mapping(mapping)

        self._render_request_tree()
        self._render_request_monitor()

    def _request_default_value(self, info):
        if isinstance(info, dict):
            if info.get("default") is not None:
                return float(info["default"])

            rng = info.get("range")
            if isinstance(rng, list) and len(rng) >= 2:
                return float(rng[1])

            return 0.0

        if info is not None:
            return float(info)

        return 0.0

    def _apply_request_mapping(self, mapping):
        profile = config_io.load_profile()
        existing = profile.get("mappings", {})

        added = 0

        for source, target in mapping.items():
            if source in existing:
                continue
            existing[source] = [{
                "target": target,
                "gain": 1.0,
                "return_to_center": False,
            }]
            added += 1

        profile["mappings"] = existing
        config_io.save_profile(profile)

        if added and self.app is not None:
            self.app.request_handler.set_mappings(existing)

        self.refresh_mappings()
        self.log(self.t("log_applied_mapping").format(added))

    def _build_request_monitor(self, parent):
        mon = ttk.LabelFrame(parent, text=self.t("mon_request"))
        mon.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self.request_monitor = tk.Text(
            mon,
            height=8,
            state=tk.DISABLED,
            bg="#0f172a",
            fg="#fbbf24",
            relief=tk.FLAT,
            padx=8,
            pady=6,
            font=("Consolas", 9),
        )
        scrollbar = ttk.Scrollbar(mon, command=self.request_monitor.yview)
        self.request_monitor.configure(yscrollcommand=scrollbar.set)
        self.request_monitor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0), pady=4)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=4)

    def _on_request_double_click(self, event):
        self.map_selected_request()

    def _clear_requests(self):
        if self.app is None or not hasattr(self.app, "status_monitor"):
            return

        self.app.status_monitor.clear_requests()

        self._render_request_tree()
        self._render_request_monitor()

    def map_selected_request(self):
        selection = self.request_tree.selection()

        if not selection:
            self.log(self.t("log_no_request"))
            return

        item = self.request_tree.item(selection[0])
        text = item.get("text", "")
        target = text.split(" -> ")[-1].strip()

        if not target or "=" in target:
            self.log(self.t("log_no_request"))
            return

        self._map_request_to_real(target)

    def _map_request_to_real(self, target):
        profile = config_io.load_profile()
        mappings = profile.get("mappings", {})

        existing = mappings.get(target)
        if existing:
            self.log(f"{target} already mapped: {config_io.mapping_desc(existing)}")
            return

        mappings[target] = [{
            "target": target,
            "gain": 1.0,
            "return_to_center": False,
        }]
        config_io.save_profile(profile)

        self.refresh_mappings()
        self.log(f"{self.t('log_mapped_request')}: {target} -> {target}")
        self._render_request_tree()

        if self.app is not None:
            self.app.request_handler.set_mappings(mappings)

    def _render_request_tree(self):
        if not hasattr(self, "request_tree"):
            return

        self.request_tree.delete(*self.request_tree.get_children())

        if self.app is None or not hasattr(self.app, "status_monitor"):
            return

        requests = self.app.status_monitor.all_requests()
        if not requests:
            return

        profile = config_io.load_profile()
        mappings = profile.get("mappings", {})

        for target, (source, value) in requests.items():
            mapped = target in mappings

            self.request_tree.insert(
                "",
                tk.END,
                text=f"{source} -> {target}",
                values=(f"{value:.0f}", "mapped" if mapped else "unmapped"),
                tags=("request", "mapped") if mapped else ("request", "unmapped"),
            )

        self.request_tree.tag_configure("mapped", foreground="#2e7d32")
        self.request_tree.tag_configure("unmapped", foreground="#c0392b")

    def _render_request_monitor(self):
        if not hasattr(self, "request_monitor"):
            return

        self.request_monitor.config(state=tk.NORMAL)
        self.request_monitor.delete("1.0", tk.END)

        if self.app is not None and hasattr(self.app, "status_monitor"):
            requests = self.app.status_monitor.all_requests()
            history = self.app.status_monitor.recent_requests()

            selected = getattr(self, "_selected_process_label", "未绑定程序")
            self.request_monitor.insert(tk.END, f"程序: {selected}\n")
            self.request_monitor.insert(tk.END, "最近请求:\n")

            if history:
                for timestamp, source, target, value in history:
                    self.request_monitor.insert(
                        tk.END,
                        f"{timestamp}  {source} -> {target} = {value:.0f}\n",
                    )
            else:
                for target, (source, value) in requests.items():
                    self.request_monitor.insert(tk.END, f"{source} -> {target} = {value:.0f}\n")

        self.request_monitor.config(state=tk.DISABLED)
        self.request_monitor.see(tk.END)

    def _output_type_info(self):
        from output.devices import OUTPUT_DEVICES

        type_map = {
            "xinput": next((d for d in OUTPUT_DEVICES if d.id == "virtual_x360"), None),
            "ds4": next((d for d in OUTPUT_DEVICES if d.id == "virtual_ds4"), None),
            "keyboard": next((d for d in OUTPUT_DEVICES if d.id == "virtual_keyboard"), None),
            "mouse": next((d for d in OUTPUT_DEVICES if d.id == "virtual_mouse"), None),
        }
        return type_map

    def refresh_outputs(self):
        if not hasattr(self, "output_tree"):
            return

        self.output_tree.delete(*self.output_tree.get_children())

        outputs = config_io.load_outputs()
        type_map = self._output_type_info()

        for output in outputs.get("outputs", []):
            name = output.get("name", output.get("id"))
            out_type = output.get("type")

            device_node = self.output_tree.insert(
                "",
                tk.END,
                text=f"{name}  [{out_type}]",
                values=("",),
                tags=("output_device",),
                open=True,
            )

            info = type_map.get(out_type)

            if info:
                profile = config_io.load_profile()
                mappings = profile.get("mappings", {})

                for target, desc in info.targets.items():
                    driver = self._driving_input(mappings, target)

                    self.output_tree.insert(
                        device_node,
                        tk.END,
                        text=f"{target}  ({desc})",
                        values=(driver,),
                        tags=("output_function",),
                    )

    def _driving_input(self, mappings, target):
        for source, mapping in mappings.items():
            items = mapping if isinstance(mapping, list) else [mapping]

            for item in items:
                tgt = item if isinstance(item, str) else item.get("target")

                if tgt == target:
                    return source

        return ""

    def add_output_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("btn_add_output"))
        dialog.geometry("420x240")

        ttk.Label(dialog, text="Output device type:").pack(padx=8, pady=(10, 2))

        types = [
            ("xinput", "XInput-compatible Controller"),
            ("ds4", "DualShock-compatible Controller"),
            ("keyboard", "Virtual Keyboard"),
            ("mouse", "Virtual Mouse"),
        ]

        type_var = tk.StringVar(value="xinput")

        for key, label in types:
            ttk.Radiobutton(
                dialog,
                text=label,
                variable=type_var,
                value=key,
            ).pack(anchor=tk.W, padx=16)

        ttk.Label(dialog, text="Name:").pack(padx=8, pady=(10, 2))
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var).pack(fill=tk.X, padx=8)

        def save():
            output_type = type_var.get()
            name = name_var.get().strip() or {
                "xinput": "XInput-compatible Controller",
                "ds4": "DualShock-compatible Controller",
                "keyboard": "Virtual Keyboard",
                "mouse": "Virtual Mouse",
            }.get(output_type, output_type)

            outputs = config_io.load_outputs()
            entries = outputs.get("outputs", [])

            used_ids = {o.get("id") for o in entries}
            base_id = f"virtual_{output_type}"
            output_id = base_id
            counter = 2
            while output_id in used_ids:
                output_id = f"{base_id}_{counter}"
                counter += 1

            entries.append({
                "id": output_id,
                "type": output_type,
                "name": name,
            })
            config_io.save_outputs({"outputs": entries})

            if self.app is not None and hasattr(self.app, "output_manager"):
                self.app.output_manager.add_runtime(entries[-1])

            self.refresh_outputs()
            self.log(f"Added output: {name}")
            dialog.destroy()

        ttk.Button(dialog, text=self.t("dlg_save"), command=save).pack(padx=8, pady=10)

    def remove_selected_output(self):
        selection = self.output_tree.selection()

        if not selection:
            self.log("Select an output device to remove.")
            return

        item = selection[0]
        node = self.output_tree.item(item)
        tags = node.get("tags", [])

        # 选中功能节点时向上找设备节点
        while "output_device" not in tags:
            item = self.output_tree.parent(item)

            if not item:
                break

            node = self.output_tree.item(item)
            tags = node.get("tags", [])

        if "output_device" not in tags:
            self.log("Select an output device node to remove.")
            return

        device_text = node.get("text")

        outputs = config_io.load_outputs()
        entries = outputs.get("outputs", [])

        device = next(
            (o for o in entries if device_text.startswith(o.get("name", ""))),
            None,
        )

        if device is None:
            self.log("Output device not found.")
            return

        entries.remove(device)
        config_io.save_outputs({"outputs": entries})

        if self.app is not None and hasattr(self.app, "output_manager"):
            self.app.output_manager.remove_runtime(device.get("id"))

        self.refresh_outputs()
        self.log(f"Removed output: {device.get('name', device.get('id'))}")

    def _build_log_panel(self, parent):
        bottom = ttk.Frame(parent)
        bottom.pack(fill=tk.X, padx=12, pady=(0, 10))

        bottom.columnconfigure(0, weight=3)
        bottom.columnconfigure(1, weight=2)

        # 左侧：日志
        logbox = ttk.LabelFrame(bottom, text=self.t("panel_log"))
        logbox.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.log_text = tk.Text(logbox, height=5, state=tk.DISABLED, bg="#0f172a", fg="#94a3b8", relief=tk.FLAT, padx=8, pady=5, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # 右侧：服务功能区（驱动 / Web 服务统一管理）
        services_box = ttk.LabelFrame(bottom, text=self.t("services_panel"))
        services_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self._build_services_panel(services_box)

    def _build_services_panel(self, parent):
        """服务功能区：驱动 + Web 服务，统一 名称:状态 + 启用/停用。"""
        from tools import services
        from tools import drivers

        rows = ttk.Frame(parent)
        rows.pack(fill=tk.X, padx=6, pady=6)

        # ---- 服务项行 ----
        def make_service_row(container, label, row):
            frame = ttk.Frame(container)
            frame.grid(row=row, column=0, sticky="ew", pady=2)
            frame.columnconfigure(1, weight=1)
            ttk.Label(frame, text=label, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W)
            status_label = ttk.Label(frame, text="...", width=14)
            status_label.grid(row=0, column=1, sticky=tk.W, padx=6)
            toggle_btn = ttk.Button(frame, text="...", width=10)
            toggle_btn.grid(row=0, column=2, padx=2)
            return frame, status_label, toggle_btn

        # Web 服务（手机）—— 实例跨重建复用，保持运行状态
        if not hasattr(self, "_web_service") or self._web_service is None:
            self._web_service = services.WebService(port=8765, callback=self._phone_data_callback)
        web_frame, web_status, web_toggle = make_service_row(rows, self.t("svc_web"), 0)
        self._web_status_label = web_status
        self._web_toggle_btn = web_toggle

        # IP 提示
        ip_var = tk.StringVar(value="")
        ttk.Label(rows, textvariable=ip_var, foreground="#94a3b8", font=("Consolas", 8)).grid(
            row=1, column=0, sticky=tk.W, padx=(2, 0)
        )
        self._web_ip_var = ip_var

        def refresh_web():
            info = self._web_service.info()
            running = info["running"]
            self._web_status_label.configure(text=self.t("svc_running") if running else self.t("svc_stopped"))
            self._web_toggle_btn.configure(
                text=self.t("svc_stop") if running else self.t("svc_start"),
                command=lambda: toggle_web(),
            )
            if running:
                # 优先显示最适合的局域网 IP
                best = info.get("best_ip") or ""
                if best:
                    self._web_ip_var.set(f"http://{best}:{info['port']}/")
                else:
                    urls = "  ".join(info["page_urls"])
                    self._web_ip_var.set(urls)
            else:
                # 未运行时也提示可用的本机 IP
                best = info.get("best_ip") or ""
                self._web_ip_var.set(
                    f"IP: {best}" if best else ""
                )

        def toggle_web():
            if self._web_service.is_running():
                ok, msg = self._web_service.stop()
                if ok:
                    self.log("Web service stopped.")
                else:
                    self.log(f"Web stop failed: {msg}")
            else:
                ok, msg = self._web_service.start()
                if ok:
                    self.log(f"Web service started: port {self._web_service.port}")
                else:
                    self.log(f"Web start failed: {msg}")
                    messagebox.showwarning(self.t("menu_services"), msg)
            refresh_web()

        self._web_toggle_btn.configure(command=toggle_web)

        # 分隔
        ttk.Separator(rows, orient=tk.HORIZONTAL).grid(row=2, column=0, sticky="ew", pady=6)

        # ViGEmBus 驱动
        vg_frame, vg_status, vg_toggle = make_service_row(rows, "ViGEmBus", 3)
        self._vg_status_label = vg_status
        self._vg_toggle_btn = vg_toggle

        # HidHide 驱动
        hh_frame, hh_status, hh_toggle = make_service_row(rows, "HidHide", 4)
        self._hh_status_label = hh_status
        self._hh_toggle_btn = hh_toggle

        def refresh_drivers():
            vg = drivers.check_vigembus()
            hh = drivers.check_hidhide()

            self._vg_status_label.configure(text=self.t("svc_installed") if vg else self.t("svc_missing"))
            self._vg_toggle_btn.configure(
                text=self.t("svc_uninstall") if vg else self.t("svc_install"),
                command=lambda: toggle_vigembus(),
            )

            self._hh_status_label.configure(text=self.t("svc_installed") if hh else self.t("svc_missing"))
            self._hh_toggle_btn.configure(
                text=self.t("svc_uninstall") if hh else self.t("svc_install"),
                command=lambda: toggle_hidhide(),
            )

        def toggle_vigembus():
            if drivers.check_vigembus():
                if messagebox.askyesno(self.t("menu_services"), self.t("drivers_vg_uninstall_ask")):
                    drivers.uninstall_vigembus()
                    self.log("ViGEmBus uninstall requested.")
            else:
                drivers_dir = drivers._find_bundled_drivers_dir()
                ok, msg = drivers.install_vigembus(drivers_dir)
                self.log(f"ViGEmBus install: {'OK' if ok else msg}")
            refresh_drivers()

        def toggle_hidhide():
            if drivers.check_hidhide():
                if messagebox.askyesno(self.t("menu_services"), self.t("drivers_hh_uninstall_ask")):
                    drivers.uninstall_hidhide()
                    self.log("HidHide uninstall requested.")
            else:
                drivers_dir = drivers._find_bundled_drivers_dir()
                ok, msg = drivers.install_hidhide(drivers_dir)
                self.log(f"HidHide install: {'OK' if ok else msg}")
            refresh_drivers()

        # 刷新按钮
        refresh_btn = ttk.Button(rows, text=self.t("svc_refresh"), command=lambda: (refresh_web(), refresh_drivers()))
        refresh_btn.grid(row=5, column=0, sticky=tk.E, pady=(4, 0))

        # 保存引用供定时刷新
        self._refresh_web = refresh_web
        self._refresh_drivers = refresh_drivers
        refresh_web()
        refresh_drivers()

    def _phone_data_callback(self, message):
        """Web 服务收到的手机数据：解析并发布到引擎的 event_bus。

        引擎未运行时丢弃（用户可先开 Web 服务，再启动引擎）。
        """
        if self.app is None or not hasattr(self.app, "event_bus"):
            return

        from devices.websocket_connection import PhoneFrameParser

        try:
            parser = PhoneFrameParser(self.app.event_bus)
            parser.parse(message)
        except Exception as error:
            print("[PhoneData] parse failed:", error)

    #
    # Device tree
    #

    def refresh_devices(self):
        self.device_tree.delete(*self.device_tree.get_children())

        data = config_io.load_config()
        packages = config_io.list_package_capabilities()
        profile = config_io.load_profile()
        mappings = profile.get("mappings", {})
        mapped = set(mappings.keys())

        # 引擎运行时：只显示当前在线的设备；未运行时显示 config 记录
        if self.app is not None and hasattr(self.app, "device_manager"):
            online = self.app.device_manager.online_devices()
            devices = online
        else:
            devices = data.get("devices", [])

        def mapped_target(cap_id):
            m = mappings.get(cap_id)

            if m is None:
                return ""

            return config_io.mapping_desc(m)

        for device in devices:
            name = device.get("name", "?")
            package = device.get("package", "")
            conn = config_io.device_conn_label(device)

            device_node = self.device_tree.insert(
                "",
                tk.END,
                text=f"{name}  [{conn}]",
                values=("",),
                tags=("device",),
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
                    values=("",),
                    tags=("group",),
                    open=True,
                )

                for cap in inputs:
                    cap_id = cap.get("id", cap)

                    self.device_tree.insert(
                        input_node,
                        tk.END,
                        text=cap_id,
                        values=(mapped_target(cap_id),),
                        tags=("capability", "mapped") if cap_id in mapped else ("capability",),
                    )

            if outputs:
                output_node = self.device_tree.insert(
                    device_node,
                    tk.END,
                    text=self.t("tree_output"),
                    values=("",),
                    tags=("group",),
                    open=True,
                )

                for cap in outputs:
                    cap_id = cap.get("id", cap)

                    self.device_tree.insert(
                        output_node,
                        tk.END,
                        text=cap_id,
                        values=(mapped_target(cap_id),),
                        tags=("capability", "mapped") if cap_id in mapped else ("capability",),
                    )

        self.device_tree.tag_configure("mapped", foreground="#2e7d32")
        self.device_tree.tag_configure("device", font=("Segoe UI", 10, "bold"))

        self.refresh_mappings()

    def _on_tree_double_click(self, event):
        selection = self.device_tree.selection()

        if not selection:
            return

        item = self.device_tree.item(selection[0])
        tags = item.get("tags", [])

        if "capability" in tags:
            source = item.get("text")
            self._open_map_dialog(source)

    def _on_output_tree_double_click(self, event):
        selection = self.output_tree.selection()

        if not selection:
            return

        item = self.output_tree.item(selection[0])
        tags = item.get("tags", [])

        if "output_function" in tags:
            text = item.get("text")
            target = text.split("  (")[0]
            self._open_reverse_map_dialog(target)

    def _on_output_tree_right_click(self, event):
        item = self.output_tree.identify_row(event.y)
        if item:
            self.output_tree.selection_set(item)
        self.output_tree_menu.tk_popup(event.x_root, event.y_root)

    #
    # Mapping
    #

    def refresh_mappings(self):
        # 映射状态已由设备树显示（已映射 = 绿色）
        # 这里只需更新设备树节点的映射标记
        if not hasattr(self, "device_tree"):
            return

        profile = config_io.load_profile()
        mappings = profile.get("mappings", {})
        mapped = set(mappings.keys())

        for item in self._iter_tree():
            node = self.device_tree.item(item)
            tags = node.get("tags", [])

            if "capability" in tags:
                cap_id = node.get("text")
                m = mappings.get(cap_id)
                target = config_io.mapping_desc(m) if m else ""
                tags = ("capability", "mapped") if cap_id in mapped else ("capability",)
                self.device_tree.item(item, tags=tags, values=(target,))

    def _iter_tree(self, parent=""):
        items = []
        for item in self.device_tree.get_children(parent):
            items.append(item)
            items.extend(self._iter_tree(item))
        return items

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
        from tools.config_io import load_outputs

        enabled_outputs = load_outputs().get("outputs", [])

        # 类型 -> 注册表能力
        type_to_info = {
            "xinput": next((d for d in OUTPUT_DEVICES if d.id == "virtual_x360"), None),
            "ds4": next((d for d in OUTPUT_DEVICES if d.id == "virtual_ds4"), None),
            "keyboard": next((d for d in OUTPUT_DEVICES if d.id == "virtual_keyboard"), None),
            "mouse": next((d for d in OUTPUT_DEVICES if d.id == "virtual_mouse"), None),
        }

        if not enabled_outputs:
            ttk.Label(
                dialog,
                text="(no output devices added - add one in the Output Devices tab)",
                foreground="#c0392b",
            ).pack(anchor=tk.W, padx=16)
            ttk.Button(dialog, text=self.t("dlg_apply"), command=dialog.destroy).pack(padx=8, pady=10)
            return

        device_var = tk.StringVar()

        for entry in enabled_outputs:
            out_id = entry.get("id")
            out_type = entry.get("type")
            out_name = entry.get("name", out_id)

            info = type_to_info.get(out_type)

            if info:
                label = f"{out_name}  [{info.name}]"
            else:
                label = out_name

            ttk.Radiobutton(
                dialog,
                text=label,
                variable=device_var,
                value=out_id,
            ).pack(anchor=tk.W, padx=16)

        ttk.Label(dialog, text=self.t("dlg_output_function")).pack(padx=8, pady=(10, 2))

        target_var = tk.StringVar()

        target_frame = ttk.Frame(dialog)
        target_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        target_combo = ttk.Combobox(target_frame, textvariable=target_var, state="readonly")
        target_combo.pack(fill=tk.X)

        self._device_targets = {}

        def get_entry_info(out_id):
            entry = next((e for e in enabled_outputs if e.get("id") == out_id), None)
            if not entry:
                return None
            return type_to_info.get(entry.get("type"))

        def update_targets(*_args):
            out_id = device_var.get()
            info = get_entry_info(out_id)

            if info:
                self._device_targets = info.targets
                target_combo["values"] = list(info.targets.keys())

                if current:
                    if isinstance(current, list):
                        tgt = current[0].get("target") if current else None
                    elif isinstance(current, str):
                        tgt = current
                    else:
                        tgt = current.get("target")

                    if tgt in info.targets:
                        target_var.set(tgt)
                        return

                if info.targets:
                    target_var.set(list(info.targets.keys())[0])

        if enabled_outputs:
            device_var.set(enabled_outputs[0]["id"])

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
            self._reload_runtime_mapping(profile)

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

    def _open_reverse_map_dialog(self, target):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Map to output: {target}")
        dialog.geometry("460x420")

        ttk.Label(
            dialog,
            text=f"Which input should drive:  {target}?",
        ).pack(padx=8, pady=8)

        profile = config_io.load_profile()
        mappings = profile.get("mappings", {})

        current_source = None
        for src, mapping in mappings.items():
            m = mapping if isinstance(mapping, list) else [mapping]
            for item in m:
                tgt = item if isinstance(item, str) else item.get("target")
                if tgt == target:
                    current_source = src
                    break

        if current_source:
            ttk.Label(
                dialog,
                text=f"Currently: {current_source} -> {target}",
                foreground="#2e7d32",
            ).pack(padx=8)

        ttk.Label(dialog, text="Available inputs:").pack(padx=8, pady=(10, 2))

        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        input_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        input_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=input_list.yview)

        packages = config_io.list_package_capabilities()
        inputs = []

        for pkg, info in packages.items():
            for cap in info["capabilities"]:
                inputs.append(cap)
                input_list.insert(tk.END, f"{cap}  ({pkg})")

        input_list.insert(tk.END, "(unmap / no mapping)")
        inputs.append(None)

        def apply():
            index = input_list.curselection()

            if not index:
                return

            source = inputs[index[0]]
            profile = config_io.load_profile()
            mappings = profile.get("mappings", {})

            # 移除其他指向此 target 的映射
            for src in list(mappings.keys()):
                m = mappings[src] if isinstance(mappings[src], list) else [mappings[src]]
                filtered = [i for i in m if not (i if isinstance(i, str) else i.get("target")) == target]
                if not filtered:
                    del mappings[src]
                else:
                    mappings[src] = filtered if isinstance(mappings[src], list) else filtered[0]

            if source is not None:
                new_mapping = {"target": target, "gain": 1.0, "return_to_center": False}
                existing = mappings.get(source)

                if isinstance(existing, list):
                    mappings[source] = existing + [new_mapping]
                elif isinstance(existing, dict):
                    mappings[source] = [existing, new_mapping]
                else:
                    mappings[source] = [new_mapping]

            profile["mappings"] = mappings
            config_io.save_profile(profile)
            self._reload_runtime_mapping(profile)

            self.refresh_mappings()
            self.log(f"Mapped {source} -> {target}" if source else f"Unmapped {target}")
            dialog.destroy()

        ttk.Button(dialog, text=self.t("dlg_apply"), command=apply).pack(padx=8, pady=8)

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
            self._reload_runtime_mapping(profile)

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
            tags = node.get("tags", []) or []

            if "device" in tags:
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

        # Bottom section contains optional device metadata.
        bottom_frame = ttk.Frame(dialog)
        bottom_frame.pack(fill=tk.X, padx=8, pady=6)

        name_var = tk.StringVar()
        use_library_var = tk.BooleanVar(value=True)
        pkg_var = tk.StringVar(value="motion_demo")
        result_text = tk.StringVar(value="等待连接")

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
            elif conn_key == "xinput":
                try:
                    device_manager = getattr(self.app, "device_manager", None)
                    if device_manager is not None:
                        available = device_manager.detected_xinput_indices()
                    else:
                        from devices.xinput_device import XInputDevice

                        available = XInputDevice.detect_connected()
                except Exception:
                    available = []

                ttk.Label(
                    fields_frame,
                    text="Detected XInput devices:",
                    font=("Segoe UI", 10, "bold"),
                ).pack(anchor=tk.W, pady=(4, 2))

                if not available:
                    ttk.Label(
                        fields_frame,
                        text="(no XInput devices detected - connect a gamepad)",
                        foreground="#c0392b",
                    ).pack(anchor=tk.W, pady=2)
                    hide_bottom()
                else:
                    connected_var = tk.StringVar()
                    field_vars["connected_index"] = connected_var

                    for slot in available:
                        row = ttk.Frame(fields_frame)
                        row.pack(fill=tk.X, padx=4, pady=3)

                        ttk.Label(
                            row,
                            text=f"Controller {slot}",
                            width=14,
                        ).pack(side=tk.LEFT)

                        status_label = ttk.Label(row, text="Not connected", width=12)
                        status_label.pack(side=tk.LEFT)

                        connect_btn = ttk.Button(row, text="Connect")
                        disconnect_btn = ttk.Button(row, text="Disconnect", state="disabled")

                        def make_connect(cbtn, dbtn, slabel, svalue):
                            def connect():
                                save("xinput", int(svalue))
                                show_bottom()
                                slabel.config(text="Connected")
                                cbtn.state(["disabled"])
                                dbtn.state(["!disabled"])
                            return connect

                        def make_disconnect(cbtn, dbtn, slabel):
                            def disconnect():
                                slabel.config(text="Not connected")
                                cbtn.state(["!disabled"])
                                dbtn.state(["disabled"])
                                hide_bottom()
                            return disconnect

                        connect_btn.configure(
                            command=make_connect(connect_btn, disconnect_btn, status_label, str(slot)),
                        )
                        disconnect_btn.configure(
                            command=make_disconnect(connect_btn, disconnect_btn, status_label),
                        )

                        connect_btn.pack(side=tk.LEFT, padx=2)
                        disconnect_btn.pack(side=tk.LEFT, padx=2)
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

            if conn_key != "xinput":
                ttk.Button(
                    fields_frame,
                    text=self.t("dlg_connect"),
                    style="Accent.TButton",
                    command=lambda: save(conn_key),
                ).pack(anchor=tk.E, pady=(12, 4))

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
            ttk.Entry(bottom_frame, textvariable=name_var).pack(fill=tk.X, padx=4)

            # 硬件库检索勾选
            ttk.Checkbutton(
                bottom_frame,
                text=self.t("dlg_use_library"),
                variable=use_library_var,
            ).pack(anchor=tk.W, padx=4, pady=2)

            # 能力包（硬件库命中后自动确定，可留空）
            ttk.Label(bottom_frame, text=self.t("dlg_package")).pack(padx=4, pady=(6, 2))
            ttk.Entry(bottom_frame, textvariable=pkg_var).pack(fill=tk.X, padx=4)

            ttk.Label(
                bottom_frame,
                textvariable=result_text,
                foreground="#2563eb",
                wraplength=460,
            ).pack(fill=tk.X, padx=4, pady=(6, 2))

            ttk.Button(
                bottom_frame,
                text=self.t("dlg_close"),
                command=dialog.destroy,
            ).pack(padx=4, pady=8)

        library_busy = False

        def finish_save(entry, library_result):
            nonlocal library_busy
            library_busy = False

            status, detail = library_result
            if status == "matched":
                result_text.set(f"已连接，硬件库命中：{detail}")
                self.log(f"Library match: {detail}")
            elif status == "not_found":
                result_text.set("已连接，硬件库中未找到匹配设备")
            elif status == "skipped":
                result_text.set("已连接，已跳过硬件库检索")
            else:
                result_text.set(f"已连接，硬件库检索失败：{detail}")
                self.log(f"Library lookup failed: {detail}")

            data = config_io.load_config()
            data.setdefault("devices", []).append(entry)
            config_io.save_config(data)

            if self.app is not None and hasattr(self.app, "device_manager"):
                self.app.device_manager.connect_device(
                    {
                        "type": entry.get("driver"),
                        "index": entry.get("index"),
                        "fingerprint": {"type": entry.get("driver")},
                    },
                    entry,
                )

            self.refresh_devices()
            self.log(f"{self.t('log_added_device')}: {entry.get('name')}")

        def save(conn_key, xinput_index=None):
            nonlocal library_busy
            if library_busy:
                return

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
            elif conn_key == "xinput":
                if xinput_index is None:
                    messagebox.showwarning(
                        self.t("dlg_no_target"),
                        "Connect a controller first",
                    )
                    return

                entry["driver"] = "xinput"
                entry["index"] = int(xinput_index)

            if not use_library_var.get():
                finish_save(entry, ("skipped", ""))
                return

            result_text.set("正在检索 GitHub 硬件库...")
            library_busy = True

            fingerprint = None
            if conn_key == "serial":
                fingerprint = {"type": "serial", "vid": field_vars["port"].get()}
            elif conn_key == "xinput":
                fingerprint = {"type": "xinput"}

            import threading

            def lookup_library():
                try:
                    from devices.device_library import DeviceLibrary

                    library = DeviceLibrary(
                        cache_path=os.path.join(
                            os.path.dirname(config_io.CONFIG_PATH),
                            "device_library_cache.json",
                        ),
                    )
                    library.refresh()
                    matched = library.identify({"fingerprint": fingerprint or {}}) if fingerprint else None
                    if matched:
                        library.install(matched.get("id"), packages_path=config_io.PACKAGES_PATH)
                        entry["package"] = matched.get("package", entry.get("package"))
                        entry["library_id"] = matched.get("id")
                        result = ("matched", matched.get("name", matched.get("id")))
                    else:
                        result = ("not_found", "")
                except Exception as error:
                    result = ("failed", str(error))

                self.root.after(0, lambda: finish_save(entry, result))

            threading.Thread(target=lookup_library, daemon=True).start()

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
        closed = False
        poll_job = None

        def worker_paired():
            try:
                paired = scanner.list_paired_ble()
                result_queue.put(("paired", paired))
            except Exception as error:
                result_queue.put(("error", str(error)))

        def worker_scan():
            try:
                found = scanner.scan_ble(timeout=5)
                result_queue.put(("scan", found))
            except Exception as error:
                result_queue.put(("error", str(error)))

        def poll_queue():
            nonlocal poll_job
            if closed or not dialog.winfo_exists():
                return
            try:
                while True:
                    kind, payload = result_queue.get_nowait()

                    if kind == "error":
                        self.log(f"Bluetooth scan failed: {payload}")
                        self.bt_list.delete(0, tk.END)
                        self.bt_list.insert(tk.END, "(scan failed)")
                        continue

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

            poll_job = self.root.after(100, poll_queue)

        def search_new():
            self.bt_list.delete(0, tk.END)
            devices.clear()
            self.bt_list.insert(tk.END, "(scanning for new BLE devices...)")

            import threading
            threading.Thread(target=worker_scan, daemon=True).start()

        def select():
            index = self.bt_list.curselection()

            if not index or index[0] >= len(devices):
                return

            device_info = devices[index[0]]

            # Bluetooth (RFCOMM): 接受任何蓝牙设备
            # FTMS (BLE trainer): 要求 BLE 设备
            if conn_key == "bluetooth":
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

        def close_dialog():
            nonlocal closed
            closed = True
            if poll_job is not None:
                self.root.after_cancel(poll_job)
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)

        import threading
        threading.Thread(target=worker_paired, daemon=True).start()
        self.root.after(100, poll_queue)

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

    def show_services(self):
        """服务管理对话框：Web 手机服务 + 驱动统一管理。"""
        from tools import services
        from tools import drivers

        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("services_panel"))
        dialog.geometry("520x360")

        ttk.Label(
            dialog,
            text=self.t("services_hint"),
            wraplength=480,
            foreground="#94a3b8",
        ).pack(fill=tk.X, padx=12, pady=(10, 6))

        # 复用底部面板的构建逻辑（在对话框中渲染）
        self._build_services_panel(dialog)

        ttk.Button(dialog, text=self.t("dlg_close"), command=dialog.destroy).pack(pady=(0, 10))

    def show_drivers(self):
        """驱动管理对话框：检测/安装/卸载 ViGEmBus 与 HidHide。"""
        from tools import drivers

        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("menu_drivers"))
        dialog.geometry("620x360")

        ttk.Label(
            dialog,
            text=self.t("drivers_hint"),
            wraplength=580,
            foreground="#94a3b8",
        ).pack(fill=tk.X, padx=12, pady=(10, 6))

        status_frame = ttk.LabelFrame(dialog, text=self.t("drivers_status"))
        status_frame.pack(fill=tk.X, padx=10, pady=6)

        self.drivers_status_var = tk.StringVar()
        ttk.Label(
            status_frame,
            textvariable=self.drivers_status_var,
            wraplength=580,
        ).pack(fill=tk.X, padx=8, pady=6)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

        def refresh():
            vigembus, hidhide = drivers.driver_status()
            drivers_dir = drivers._find_bundled_drivers_dir()

            lines = []
            vg_state = self.t("drivers_installed") if vigembus else self.t("drivers_missing")
            hh_state = self.t("drivers_installed") if hidhide else self.t("drivers_missing")
            lines.append(f"{self.t('drivers_vigembus')}: {vg_state}")
            lines.append(f"{self.t('drivers_hidhide')}: {hh_state}")

            if drivers_dir:
                lines.append(f"{self.t('drivers_source')}: {drivers_dir}")
            else:
                lines.append(self.t("drivers_no_source"))

            self.drivers_status_var.set("\n".join(lines))
            return vigembus, hidhide, drivers_dir

        def do_install_vigembus():
            vigembus, _hh, drivers_dir = refresh()
            if vigembus:
                return
            ok, message = drivers.install_vigembus(drivers_dir)
            if ok:
                self.log("ViGEmBus installed.")
                messagebox.showinfo(self.t("menu_drivers"), self.t("drivers_vg_installed_ok"))
            else:
                messagebox.showwarning(self.t("menu_drivers"), message)
            refresh()

        def do_uninstall_vigembus():
            vigembus, _hh, drivers_dir = refresh()
            if not vigembus:
                return
            if not messagebox.askyesno(self.t("menu_drivers"), self.t("drivers_vg_uninstall_ask")):
                return
            ok, message = drivers.uninstall_vigembus(drivers_dir)
            if ok:
                self.log("ViGEmBus uninstalled.")
                refresh()
            else:
                messagebox.showwarning(self.t("menu_drivers"), message)
                refresh()

        def do_install_hidhide():
            _vg, hidhide, drivers_dir = refresh()
            if hidhide:
                return
            ok, message = drivers.install_hidhide(drivers_dir)
            if ok:
                self.log("HidHide installer launched.")
            else:
                messagebox.showwarning(self.t("menu_drivers"), message)
            refresh()

        def do_uninstall_hidhide():
            _vg, hidhide, _dd = refresh()
            if not hidhide:
                return
            if not messagebox.askyesno(self.t("menu_drivers"), self.t("drivers_hh_uninstall_ask")):
                return
            ok, message = drivers.uninstall_hidhide()
            if ok:
                self.log("HidHide uninstalled.")
            else:
                messagebox.showwarning(self.t("menu_drivers"), message)
            refresh()

        ttk.Button(btn_frame, text=self.t("drivers_refresh"), command=refresh).pack(side=tk.LEFT, padx=3)

        ttk.Label(btn_frame, text=self.t("drivers_vigembus"), font=("Segoe UI", 10, "bold")).pack(
            side=tk.LEFT, padx=(14, 2), pady=6
        )
        ttk.Button(btn_frame, text=self.t("drivers_install"), command=do_install_vigembus).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=self.t("drivers_uninstall"), command=do_uninstall_vigembus).pack(side=tk.LEFT, padx=2)

        ttk.Label(btn_frame, text=self.t("drivers_hidhide"), font=("Segoe UI", 10, "bold")).pack(
            side=tk.LEFT, padx=(14, 2), pady=6
        )
        ttk.Button(btn_frame, text=self.t("drivers_install"), command=do_install_hidhide).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text=self.t("drivers_uninstall"), command=do_uninstall_hidhide).pack(side=tk.LEFT, padx=2)

        ttk.Button(btn_frame, text=self.t("dlg_close"), command=dialog.destroy).pack(side=tk.RIGHT, padx=3)

        refresh()

    def show_hidhide(self):
        """游戏独占模式对话框：管理 HidHide 隐藏物理设备。"""
        from tools import hidhide

        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("menu_hidhide"))
        dialog.geometry("720x520")

        if not hidhide.is_installed():
            ttk.Label(
                dialog,
                text=self.t("hidhide_not_installed"),
                foreground="#c0392b",
                wraplength=640,
            ).pack(padx=16, pady=16)
            ttk.Button(dialog, text=self.t("dlg_close"), command=dialog.destroy).pack()
            return

        admin = hidhide.is_admin()
        self.log(f"HidHide dialog opened (admin={admin})")

        # 状态区
        status_box = ttk.LabelFrame(dialog, text=self.t("hidhide_status"))
        status_box.pack(fill=tk.X, padx=10, pady=6)

        self.hidhide_status_var = tk.StringVar()
        ttk.Label(
            status_box,
            textvariable=self.hidhide_status_var,
            wraplength=660,
        ).pack(fill=tk.X, padx=8, pady=4)

        # 说明
        ttk.Label(
            dialog,
            text=self.t("hidhide_hint"),
            foreground="#94a3b8",
            wraplength=660,
        ).pack(fill=tk.X, padx=12, pady=(4, 0))

        # 设备列表
        list_box = ttk.LabelFrame(dialog, text=self.t("hidhide_devices"))
        list_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        columns = ("status", "type", "path")
        self.hidhide_tree = ttk.Treeview(list_box, columns=columns, show="tree headings")
        self.hidhide_tree.heading("#0", text=self.t("hidhide_col_name"))
        self.hidhide_tree.heading("status", text=self.t("hidhide_col_status"))
        self.hidhide_tree.heading("type", text=self.t("hidhide_col_type"))
        self.hidhide_tree.heading("path", text=self.t("hidhide_col_path"))
        self.hidhide_tree.column("status", width=90, anchor=tk.CENTER)
        self.hidhide_tree.column("type", width=90, anchor=tk.CENTER)
        self.hidhide_tree.column("path", width=320)
        self.hidhide_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # 按钮区
        btn_box = ttk.Frame(dialog)
        btn_box.pack(fill=tk.X, padx=10, pady=(0, 6))

        ttk.Button(
            btn_box,
            text=self.t("hidhide_refresh"),
            command=lambda: self._hidhide_refresh(dialog),
        ).pack(side=tk.LEFT, padx=3)

        ttk.Button(
            btn_box,
            text=self.t("hidhide_hide_selected"),
            command=lambda: self._hidhide_toggle_selected(dialog, True),
        ).pack(side=tk.LEFT, padx=3)

        ttk.Button(
            btn_box,
            text=self.t("hidhide_unhide_selected"),
            command=lambda: self._hidhide_toggle_selected(dialog, False),
        ).pack(side=tk.LEFT, padx=3)

        ttk.Button(
            btn_box,
            text=self.t("hidhide_hide_all"),
            command=lambda: self._hidhide_hide_all(dialog),
        ).pack(side=tk.LEFT, padx=3)

        ttk.Button(
            btn_box,
            text=self.t("hidhide_self_visible"),
            command=lambda: self._hidhide_self_visible(dialog),
        ).pack(side=tk.LEFT, padx=3)

        ttk.Button(
            btn_box,
            text=self.t("dlg_close"),
            command=dialog.destroy,
        ).pack(side=tk.RIGHT, padx=3)

        self._hidhide_refresh(dialog)

    def _hidhide_refresh(self, dialog):
        from tools import hidhide

        status_lines = [
            f"{self.t('hidhide_admin')}: {'yes' if hidhide.is_admin() else 'no'}",
            f"{self.t('hidhide_cloak')}: {hidhide.cloak_state() or 'unknown'}",
            f"{self.t('hidhide_inverse')}: {hidhide.inverse_state() or 'unknown'}",
        ]
        apps = hidhide.list_apps()
        status_lines.append(f"{self.t('hidhide_apps')}: {len(apps)}")
        for app in apps:
            status_lines.append(f"    {app}")

        hidden = set(hidhide.list_hidden())
        self.hidhide_status_var.set("\n".join(status_lines))

        self.hidhide_tree.delete(*self.hidhide_tree.get_children())

        devices = hidhide.list_hid_devices()
        for device in devices:
            instance_id = device["instance_id"]
            is_hidden = instance_id in hidden
            dev_type = "GAMING" if device["gaming"] else "HID"
            status = self.t("hidhide_state_hidden") if is_hidden else self.t("hidhide_state_visible")
            name = device["friendly_name"] or instance_id

            self.hidhide_tree.insert(
                "",
                tk.END,
                text=name,
                values=(status, dev_type, instance_id),
                tags=("hidden",) if is_hidden else ("visible",),
                open=False,
            )

        self.hidhide_tree.tag_configure("hidden", foreground="#fbbf24")
        self.hidhide_tree.tag_configure("visible", foreground="#cbd5e1")

    def _hidhide_toggle_selected(self, dialog, do_hide):
        from tools import hidhide

        selection = self.hidhide_tree.selection()
        if not selection:
            self.log("Select a device first.")
            return

        for item in selection:
            values = self.hidhide_tree.item(item, "values")
            instance_id = values[2] if len(values) > 2 else None
            if not instance_id:
                continue

            if do_hide:
                ok, message = hidhide.hide(instance_id)
            else:
                ok, message = hidhide.unhide(instance_id)

            if not ok:
                messagebox.showwarning(
                    self.t("menu_hidhide"),
                    f"{self.t('hidhide_action_failed')}: {message}",
                )
                self.log(f"HidHide action failed: {message}")
                return

            name = self.hidhide_tree.item(item, "text")
            self.log(f"{'Hidden' if do_hide else 'Unhidden'}: {name}")

        self._hidhide_refresh(dialog)

    def _hidhide_hide_all(self, dialog):
        from tools import hidhide

        ok, message, count = hidhide.hide_all_gaming_devices()
        if ok:
            self.log(f"HidHide hidden {count} gaming devices, cloaking enabled.")
            messagebox.showinfo(
                self.t("menu_hidhide"),
                self.t("hidhide_all_done").format(count),
            )
        else:
            messagebox.showwarning(
                self.t("menu_hidhide"),
                f"{self.t('hidhide_action_failed')}: {message}",
            )
            self.log(f"HidHide hide-all failed: {message}")

        self._hidhide_refresh(dialog)

    def _hidhide_self_visible(self, dialog):
        from tools import hidhide

        ok, message = hidhide.ensure_self_visible()
        if ok:
            self.log("CapabilityNexus registered as exempt app.")
            messagebox.showinfo(self.t("menu_hidhide"), self.t("hidhide_self_done"))
        else:
            self.log(f"HidHide self-visible failed: {message}")

        self._hidhide_refresh(dialog)

    def show_game_profiles(self):
        """游戏配置管理：切换不同游戏的独立映射配置。"""
        from tools import config_io

        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("menu_game_profiles"))
        dialog.geometry("460x360")

        ttk.Label(
            dialog,
            text=self.t("game_profiles_hint"),
            wraplength=420,
            foreground="#94a3b8",
        ).pack(fill=tk.X, padx=12, pady=(10, 6))

        profiles = config_io.list_profiles()
        active = config_io.get_active_profile()

        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        profile_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        profile_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=profile_list.yview)

        for name in profiles:
            marker = " *" if name == active else ""
            profile_list.insert(tk.END, f"{name}{marker}")

        def select_active():
            index = profile_list.curselection()
            if not index:
                return
            name = profiles[index[0]]
            if name == active:
                return
            if not config_io.set_active_profile(name):
                return
            self.log(f"Active game profile: {name}")
            profile_list.delete(0, tk.END)
            for n in config_io.list_profiles():
                marker = " *" if n == name else ""
                profile_list.insert(tk.END, f"{n}{marker}")
            self._reload_profile_config()

        def new_profile():
            dialog2 = tk.Toplevel(dialog)
            dialog2.title(self.t("game_profiles_new"))
            dialog2.geometry("360x120")
            ttk.Label(dialog2, text=self.t("game_profiles_name")).pack(padx=8, pady=(10, 2))
            var = tk.StringVar()
            entry = ttk.Entry(dialog2, textvariable=var)
            entry.pack(fill=tk.X, padx=8)
            entry.focus_set()

            def do_create():
                name = var.get().strip().lower().replace(" ", "_")
                if not name:
                    return
                path = os.path.join(config_io.PROFILES_DIR, f"{name}.json")
                if os.path.exists(path):
                    return
                import json
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"mappings": {}}, f, ensure_ascii=False, indent=4)
                config_io.set_active_profile(name)
                self.log(f"Created game profile: {name}")
                dialog2.destroy()
                dialog.destroy()
                self.show_game_profiles()

            ttk.Button(dialog2, text=self.t("dlg_save"), command=do_create).pack(padx=8, pady=8)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(btn_frame, text=self.t("game_profiles_activate"), command=select_active).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text=self.t("game_profiles_new"), command=new_profile).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text=self.t("game_profiles_tune"), command=self.show_curve_tuner).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text=self.t("dlg_close"), command=dialog.destroy).pack(side=tk.RIGHT, padx=3)

    def _reload_profile_config(self):
        """切换游戏配置后重载引擎映射。"""
        if self.app is None or not hasattr(self.app, "mapping_engine"):
            self.refresh_devices()
            return

        from tools import config_io

        profile = config_io.load_profile()
        self.app.mapping_engine.load_mappings(profile.get("mappings", {}))
        if hasattr(self.app, "reload_processors"):
            self.app.reload_processors()
        if hasattr(self.app, "request_handler"):
            self.app.request_handler.set_mappings(profile.get("mappings", {}))
        self.refresh_devices()
        self.log(self.t("game_profiles_loaded").format(config_io.get_active_profile()))

    def show_tuning_workspace(self, profile_name=None):
        """调优工作区：游戏配置 + 陀螺仪曲线 + 实时监控（从进程双击进入）。"""
        from tools import config_io

        profile_name = profile_name or config_io.get_active_profile()

        dialog = tk.Toplevel(self.root)
        dialog.title(f"{self.t('tuning_workspace_title')} - {profile_name}")
        dialog.geometry("900x640")

        # ---- 顶部：游戏配置选择 ----
        top = ttk.Frame(dialog)
        top.pack(fill=tk.X, padx=10, pady=(10, 4))

        ttk.Label(top, text=self.t("tuning_profile")).pack(side=tk.LEFT, padx=(0, 6))
        profile_var = tk.StringVar(value=profile_name)
        profile_combo = ttk.Combobox(
            top,
            textvariable=profile_var,
            values=config_io.list_profiles(),
            state="readonly",
            width=24,
        )
        profile_combo.pack(side=tk.LEFT)
        profile_combo.bind("<<ComboboxSelected>>", lambda e: self._tuning_switch_profile(
            dialog, profile_var.get(), profile_combo, canvas,
            axis_var, deadzone_var, maxdeg_var, live_var, status_var,
        ))

        ttk.Label(top, text=self.t("tuning_hint"), foreground="#94a3b8").pack(side=tk.LEFT, padx=10)

        # ---- 主体 ----
        main = ttk.Frame(dialog)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        ttk.Label(left, text=self.t("curve_tuner_axis")).pack(anchor=tk.W, pady=(0, 2))
        axis_var = tk.StringVar(value="control.right_x")

        self._curve_axes = {}
        profile = config_io.load_profile_named(profile_name)
        processors = profile.get("processors", {})
        for cap_id in ("control.right_x", "control.right_y"):
            proc_cfg = None
            for p in processors.get(cap_id, []):
                if p.get("type") == "curve":
                    proc_cfg = p
                    break
            self._curve_axes[cap_id] = proc_cfg

        for cap_id in ("control.right_x", "control.right_y"):
            if not self._curve_axes.get(cap_id):
                continue
            label = {
                "control.right_x": self.t("curve_tuner_rx"),
                "control.right_y": self.t("curve_tuner_ry"),
            }.get(cap_id, cap_id)
            ttk.Radiobutton(
                left,
                text=label,
                variable=axis_var,
                value=cap_id,
                command=lambda: self._curve_redraw(canvas, axis_var, deadzone_var, maxdeg_var, status_var),
            ).pack(anchor=tk.W, pady=1)

        params = ttk.LabelFrame(left, text=self.t("curve_tuner_params"))
        params.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(params, text=self.t("curve_tuner_deadzone")).grid(row=0, column=0, sticky=tk.W, padx=6, pady=3)
        deadzone_var = tk.StringVar(value="1.5")
        ttk.Entry(params, textvariable=deadzone_var, width=8).grid(row=0, column=1, padx=6, pady=3)

        ttk.Label(params, text=self.t("curve_tuner_maxdeg")).grid(row=1, column=0, sticky=tk.W, padx=6, pady=3)
        maxdeg_var = tk.StringVar(value="12")
        ttk.Entry(params, textvariable=maxdeg_var, width=8).grid(row=1, column=1, padx=6, pady=3)

        # ---- 右侧：预览 + 实时 ----
        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(right, width=460, height=360, bg="#0f172a", highlightthickness=1, highlightbackground="#334155")
        canvas.pack(fill=tk.BOTH, expand=True)

        live_var = tk.StringVar(value=self.t("curve_tuner_live_idle"))
        ttk.Label(
            right,
            textvariable=live_var,
            foreground="#67e8f9",
            font=("Consolas", 10),
        ).pack(fill=tk.X, padx=6, pady=(6, 0))

        # ---- 底部：状态 + 操作 ----
        bottom = ttk.Frame(dialog)
        bottom.pack(fill=tk.X, padx=12, pady=(0, 8))

        status_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=status_var, foreground="#2563eb").pack(side=tk.LEFT, fill=tk.X, expand=True)

        def save():
            try:
                deadzone = float(deadzone_var.get())
                maxdeg = float(maxdeg_var.get())
            except ValueError:
                messagebox.showwarning(self.t("menu_game_profiles"), self.t("curve_tuner_invalid_num"))
                return

            cap_id = axis_var.get()
            cfg = self._curve_axes.get(cap_id)
            if not cfg:
                return

            old_max = float(cfg.get("max_degrees", 30))
            old_points = cfg.get("points") or []
            new_points = []
            for angle, pct in old_points:
                new_points.append([round(angle / old_max * maxdeg, 2), pct])

            cfg["deadzone"] = deadzone
            cfg["max_degrees"] = maxdeg
            cfg["points"] = new_points
            self._curve_axes[cap_id] = cfg

            profile = config_io.load_profile_named(profile_var.get())
            profile["processors"][cap_id] = [cfg]
            config_io.save_profile_named(profile_var.get(), profile)
            self._reload_profile_config()
            status_var.set(self.t("curve_tuner_saved"))
            self.log(f"Curve tuned: {cap_id} (deadzone={deadzone}, max={maxdeg})")
            self._curve_redraw(canvas, axis_var, deadzone_var, maxdeg_var, status_var)

        ttk.Button(bottom, text=self.t("dlg_save"), command=save).pack(side=tk.RIGHT, padx=3)
        ttk.Button(bottom, text=self.t("dlg_close"), command=dialog.destroy).pack(side=tk.RIGHT, padx=3)

        # 实时刷新
        tuner_job = [None]

        def live_tick():
            if not dialog.winfo_exists():
                return
            cap_id = axis_var.get()
            cfg = self._curve_axes.get(cap_id)
            if cfg and self.app is not None and hasattr(self.app, "status_monitor"):
                monitor = self.app.status_monitor
                raw = monitor.get_input_value(cap_id)
                if raw is not None:
                    from processors.curve import CurveProcessor

                    cp = CurveProcessor(
                        cfg.get("max_degrees", 30),
                        cfg.get("deadzone", 1.5),
                        cfg.get("points"),
                        cfg.get("mode", "step"),
                    )
                    angle = raw / 32767.0 * 180.0
                    out = cp.process(raw)
                    pct = out / 32767.0 * 100.0
                    live_var.set(
                        self.t("curve_tuner_live").format(
                            f"{angle:+.1f}", f"{raw:+.0f}", f"{pct:+.0f}", out
                        )
                    )
                else:
                    live_var.set(self.t("curve_tuner_live_idle"))
            else:
                live_var.set(self.t("curve_tuner_live_idle"))

            tuner_job[0] = dialog.after(200, live_tick)

        def on_close():
            if tuner_job[0] is not None:
                dialog.after_cancel(tuner_job[0])
                tuner_job[0] = None
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_close)
        tuner_job[0] = dialog.after(200, live_tick)

        # 初始化参数显示
        init_cfg = self._curve_axes.get(axis_var.get())
        if init_cfg:
            deadzone_var.set(str(init_cfg.get("deadzone", 1.5)))
            maxdeg_var.set(str(init_cfg.get("max_degrees", 12)))

        self._curve_redraw(canvas, axis_var, deadzone_var, maxdeg_var, status_var)

    def _tuning_switch_profile(self, dialog, name, combo, canvas,
                               axis_var, deadzone_var, maxdeg_var, live_var, status_var):
        """调优工作区里切换游戏配置。"""
        from tools import config_io

        if not config_io.set_active_profile(name):
            return
        self.log(f"Active game profile: {name}")
        self._reload_profile_config()
        dialog.title(f"{self.t('tuning_workspace_title')} - {name}")

        # 重新加载轴的曲线配置
        self._curve_axes = {}
        profile = config_io.load_profile_named(name)
        processors = profile.get("processors", {})
        for cap_id in ("control.right_x", "control.right_y"):
            proc_cfg = None
            for p in processors.get(cap_id, []):
                if p.get("type") == "curve":
                    proc_cfg = p
                    break
            self._curve_axes[cap_id] = proc_cfg

        # 更新参数显示
        init_cfg = self._curve_axes.get(axis_var.get())
        if init_cfg:
            deadzone_var.set(str(init_cfg.get("deadzone", 1.5)))
            maxdeg_var.set(str(init_cfg.get("max_degrees", 12)))

        self._curve_redraw(canvas, axis_var, deadzone_var, maxdeg_var, status_var)

    def show_curve_tuner(self):
        """曲线调优对话框：可视化编辑陀螺仪响应曲线（档位/死区/角度范围）。"""
        from tools import config_io
        import json

        profile_name = config_io.get_active_profile()
        profile = config_io.load_profile_named(profile_name)
        processors = profile.get("processors", {})

        dialog = tk.Toplevel(self.root)
        dialog.title(f"{self.t('curve_tuner_title')} - {profile_name}")
        dialog.geometry("780x560")

        # 顶部说明
        ttk.Label(
            dialog,
            text=self.t("curve_tuner_hint").format(profile_name),
            wraplength=740,
            foreground="#94a3b8",
        ).pack(fill=tk.X, padx=12, pady=(10, 6))

        # 主区域：轴选择 + 预览 + 参数编辑
        main = ttk.Frame(dialog)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        # 左侧：轴选择与参数
        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        ttk.Label(left, text=self.t("curve_tuner_axis")).pack(anchor=tk.W, pady=(0, 2))

        axis_var = tk.StringVar(value="control.right_x")
        self._curve_axes = {}

        for cap_id in ("control.right_x", "control.right_y"):
            proc_cfg = None
            for p in processors.get(cap_id, []):
                if p.get("type") == "curve":
                    proc_cfg = p
                    break
            self._curve_axes[cap_id] = proc_cfg

        # 只有存在 curve 配置的轴才可选
        available = [c for c, cfg in self._curve_axes.items() if cfg]
        if not available:
            ttk.Label(
                dialog,
                text=self.t("curve_tuner_no_curve"),
                foreground="#c0392b",
            ).pack(padx=12, pady=20)
            return

        for cap_id in available:
            label = {
                "control.right_x": self.t("curve_tuner_rx"),
                "control.right_y": self.t("curve_tuner_ry"),
            }.get(cap_id, cap_id)
            ttk.Radiobutton(
                left,
                text=label,
                variable=axis_var,
                value=cap_id,
                command=lambda: self._curve_redraw(canvas, axis_var, deadzone_var, maxdeg_var, status_var),
            ).pack(anchor=tk.W, pady=1)

        params = ttk.LabelFrame(left, text=self.t("curve_tuner_params"))
        params.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(params, text=self.t("curve_tuner_deadzone")).grid(row=0, column=0, sticky=tk.W, padx=6, pady=3)
        deadzone_var = tk.StringVar(value="1.5")
        ttk.Entry(params, textvariable=deadzone_var, width=8).grid(row=0, column=1, padx=6, pady=3)

        ttk.Label(params, text=self.t("curve_tuner_maxdeg")).grid(row=1, column=0, sticky=tk.W, padx=6, pady=3)
        maxdeg_var = tk.StringVar(value="12")
        ttk.Entry(params, textvariable=maxdeg_var, width=8).grid(row=1, column=1, padx=6, pady=3)

        # 右侧：曲线预览 Canvas
        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(right, width=420, height=340, bg="#0f172a", highlightthickness=1, highlightbackground="#334155")
        canvas.pack(fill=tk.BOTH, expand=True)

        # 实时输入显示（读取引擎的 status_monitor）
        live_var = tk.StringVar(value=self.t("curve_tuner_live_idle"))
        ttk.Label(
            right,
            textvariable=live_var,
            foreground="#67e8f9",
            font=("Consolas", 10),
        ).pack(fill=tk.X, padx=6, pady=(6, 0))

        # 底部：状态 + 保存
        bottom = ttk.Frame(dialog)
        bottom.pack(fill=tk.X, padx=12, pady=(0, 8))

        status_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=status_var, foreground="#2563eb").pack(side=tk.LEFT, fill=tk.X, expand=True)

        tuner_job = [None]

        def live_tick():
            if not dialog.winfo_exists():
                return
            cap_id = axis_var.get()
            cfg = self._curve_axes.get(cap_id)
            if cfg and self.app is not None and hasattr(self.app, "status_monitor"):
                monitor = self.app.status_monitor
                raw = monitor.get_input_value(cap_id)
                if raw is not None:
                    from processors.curve import CurveProcessor

                    cp = CurveProcessor(
                        cfg.get("max_degrees", 30),
                        cfg.get("deadzone", 1.5),
                        cfg.get("points"),
                        cfg.get("mode", "step"),
                    )
                    angle = raw / 32767.0 * 180.0
                    out = cp.process(raw)
                    pct = out / 32767.0 * 100.0
                    live_var.set(
                        self.t("curve_tuner_live").format(
                            f"{angle:+.1f}", f"{raw:+.0f}", f"{pct:+.0f}", out
                        )
                    )
                else:
                    live_var.set(self.t("curve_tuner_live_idle"))
            else:
                live_var.set(self.t("curve_tuner_live_idle"))

            tuner_job[0] = dialog.after(200, live_tick)

        tuner_job[0] = dialog.after(200, live_tick)

        def save():
            try:
                deadzone = float(deadzone_var.get())
                maxdeg = float(maxdeg_var.get())
            except ValueError:
                messagebox.showwarning(self.t("menu_game_profiles"), self.t("curve_tuner_invalid_num"))
                return

            cap_id = axis_var.get()
            cfg = self._curve_axes.get(cap_id)
            if not cfg:
                return

            # 更新死区与最大角度；档位百分比按角度比例缩放
            old_max = float(cfg.get("max_degrees", 30))
            old_points = cfg.get("points") or []
            new_points = []
            for angle, pct in old_points:
                new_points.append([round(angle / old_max * maxdeg, 2), pct])

            cfg["deadzone"] = deadzone
            cfg["max_degrees"] = maxdeg
            cfg["points"] = new_points
            self._curve_axes[cap_id] = cfg

            # 写回配置
            profile["processors"][cap_id] = [cfg]
            config_io.save_profile_named(profile_name, profile)
            self._reload_profile_config()
            status_var.set(self.t("curve_tuner_saved"))
            self.log(f"Curve tuned: {cap_id} (deadzone={deadzone}, max={maxdeg})")
            self._curve_redraw(canvas, axis_var, deadzone_var, maxdeg_var, status_var)

        ttk.Button(bottom, text=self.t("dlg_save"), command=save).pack(side=tk.RIGHT, padx=3)
        ttk.Button(bottom, text=self.t("dlg_close"), command=dialog.destroy).pack(side=tk.RIGHT, padx=3)

        def on_close():
            if tuner_job[0] is not None:
                dialog.after_cancel(tuner_job[0])
                tuner_job[0] = None
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_close)

        self._curve_redraw(canvas, axis_var, deadzone_var, maxdeg_var, status_var)

    def _curve_redraw(self, canvas, axis_var, deadzone_var, maxdeg_var, status_var):
        """在 Canvas 上绘制当前曲线的阶梯/线性预览。"""
        from processors.curve import CurveProcessor

        cap_id = axis_var.get()
        cfg = self._curve_axes.get(cap_id)
        if not cfg:
            return

        try:
            deadzone = float(deadzone_var.get())
            maxdeg = float(maxdeg_var.get())
        except ValueError:
            return

        points = cfg.get("points") or []
        mode = cfg.get("mode", "step")

        cp = CurveProcessor(max_degrees=maxdeg, deadzone=deadzone, points=points, mode=mode)

        canvas.delete("all")
        W = canvas.winfo_width() or 420
        H = canvas.winfo_height() or 380
        margin = 40

        # 坐标轴
        mid_x = margin
        mid_y = H // 2
        canvas.create_line(margin, mid_y, W - 10, mid_y, fill="#475569")
        canvas.create_line(margin, 10, margin, H - 10, fill="#475569")

        def px(angle):
            return margin + (angle + maxdeg) / (2 * maxdeg) * (W - margin - 10)

        def py(pct):
            return mid_y - pct / 100.0 * (H - 30) / 2

        # 网格参考线
        canvas.create_line(margin, 10, margin, H - 10, fill="#334155", dash=(4, 4))
        canvas.create_line(px(0), 10, px(0), H - 10, fill="#334155", dash=(4, 4))
        for pct in (-80, -50, -20, 20, 50, 80):
            y = py(pct)
            if 10 <= y <= H - 10:
                canvas.create_line(margin, y, W - 10, y, fill="#1e293b")

        # 采样绘制曲线
        steps = 100
        prev = None
        for i in range(steps + 1):
            angle = -maxdeg + (2 * maxdeg) * i / steps
            value = cp.process(round(angle / 180 * 32767))
            pct = value / 32767.0 * 100.0
            x = px(angle)
            y = py(pct)
            if prev is not None:
                canvas.create_line(prev[0], prev[1], x, y, fill="#38bdf8", width=2)
            prev = (x, y)

        # 标注死区
        dz_x = px(deadzone)
        canvas.create_line(dz_x, 10, dz_x, H - 10, fill="#f59e0b", dash=(2, 2))
        canvas.create_line(px(-deadzone), 10, px(-deadzone), H - 10, fill="#f59e0b", dash=(2, 2))
        canvas.create_text(margin + 30, 20, text=self.t("curve_tuner_dz").format(deadzone), fill="#f59e0b", anchor=tk.W, font=("Segoe UI", 8))

        # 轴标签
        canvas.create_text(W - 20, mid_y - 12, text="+%g°" % maxdeg, fill="#94a3b8", anchor=tk.E)
        canvas.create_text(margin + 20, mid_y + 16, text="-%g°" % maxdeg, fill="#94a3b8", anchor=tk.W)

        status_var.set(f"{self.t('curve_tuner_mode')}: {mode}  {self.t('curve_tuner_maxdeg')}: {maxdeg}°  {self.t('curve_tuner_deadzone')}: {deadzone}°")

    def show_about(self):
        messagebox.showinfo(self.t("about_title"), self.t("about_body"))

    def show_help(self):
        messagebox.showinfo(self.t("help_title"), self.t("help_body"))

    #
    # Engine control + live display
    #

    def start_engine(self):
        if self.app is not None:
            self.log("Engine already running.")
            return

        try:
            from app import CapabilityNexusApp

            self.app = CapabilityNexusApp()
            self.log("Engine started.")
            self._set_engine_badge(True)
        except Exception as e:
            self.log(f"Engine start failed: {e}")
            self._set_engine_badge(False)
            return

        self.refresh_devices()

    def stop_engine(self):
        if self.app is None:
            self.log("Engine not running.")
            return

        try:
            self.app.close()
        except Exception as e:
            self.log(f"Engine stop error: {e}")

        self.app = None
        self.log("Engine stopped.")
        self._set_engine_badge(False)

        self.refresh_devices()

    def _capability_category(self, cap_id):
        if not hasattr(self, "_cat_map"):
            self._cat_map = {}

            packages = config_io.list_package_capabilities()
            for info in packages.values():
                for cap in info.get("capabilities_full", []):
                    self._cat_map[cap.get("id")] = cap.get("category", "axis")
                for cap in info.get("outputs_full", []):
                    self._cat_map[cap.get("id")] = cap.get("category", "motor")

            # 输出目标（虚拟设备功能）类别
            from output.devices import OUTPUT_DEVICES

            for device in OUTPUT_DEVICES:
                for target in device.targets:
                    if target.startswith("button_") or target.startswith("ds4.button"):
                        self._cat_map[target] = "button"
                    elif "trigger" in target:
                        self._cat_map[target] = "trigger"
                    else:
                        self._cat_map[target] = "axis"

        return self._cat_map.get(cap_id, "axis")

    def _format_input(self, cap_id, value):
        category = self._capability_category(cap_id)

        if category == "button":
            return f"{cap_id}: pressed" if value else f"{cap_id}: released"

        return f"{cap_id}: {value:.2f}"

    def _format_output(self, target, value):
        category = self._capability_category(target)

        if category == "button":
            return f"{target}: pressed" if value else f"{target}: released"

        return f"{target}: {value:.2f}"

    def _refresh_live_values(self):
        if self.app is None or not hasattr(self.app, "status_monitor"):
            return

        monitor = self.app.status_monitor

        # 两个监控窗口共用同一逻辑：
        # 只显示"已连接且有真实输入"的通道（当前值偏离基线）。
        # 漂移值（静止非零，等于基线）不显示；
        # 按住按钮 / 推住摇杆（偏离基线）一直显示最新值；
        # 松开回中 / 设备断开后自动消失。
        self._render_monitor(
            self.input_monitor,
            monitor.active_inputs(),
            self._format_input,
        )
        self._render_monitor(
            self.output_monitor,
            monitor.snapshot_outputs(),
            self._format_output,
            show_zero=True,
        )

    def _render_monitor(self, widget, values, formatter, show_zero=False):
        lines = []

        for key, value in values.items():
            category = self._capability_category(key)

            # 按钮：按下才显示；轴/扳机：非零才显示
            if value or show_zero:
                lines.append(formatter(key, value))

        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)

        if lines:
            widget.insert(tk.END, "\n".join(lines))

        widget.config(state=tk.DISABLED)

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
    gui = CapabilityNexusGUI(root)

    def on_close():
        try:
            if hasattr(gui, "_web_service") and gui._web_service is not None:
                gui._web_service.close()
            if hasattr(gui, "app") and gui.app is not None:
                gui.app.close()
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
