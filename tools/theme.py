import tkinter as tk
from tkinter import ttk


class Theme:

    #
    # CapabilityNexus 深色主题
    #

    COLORS = {
        "bg": "#1e1e2e",
        "bg_panel": "#27293d",
        "bg_hover": "#313244",
        "fg": "#cdd6f4",
        "fg_dim": "#a6adc8",
        "fg_bright": "#ffffff",
        "accent": "#89b4fa",
        "accent_dark": "#5b7db1",
        "success": "#a6e3a1",
        "warning": "#f9e2af",
        "error": "#f38ba8",
        "border": "#45475a",
        "selection": "#45475a",
    }

    FONT = {
        "normal": ("Segoe UI", 10),
        "bold": ("Segoe UI", 10, "bold"),
        "title": ("Segoe UI", 11, "bold"),
        "mono": ("Consolas", 10),
    }

    @staticmethod
    def c(name):
        return Theme.COLORS.get(name, Theme.COLORS["fg"])


def apply_theme(root):
    style = ttk.Style(root)

    try:
        style.theme_use("clam")
    except Exception:
        pass

    c = Theme.COLORS

    root.configure(bg=c["bg"])

    style.configure(".", background=c["bg"], foreground=c["fg"],
                    font=Theme.FONT["normal"])

    style.configure("TFrame", background=c["bg"])
    style.configure("TLabel", background=c["bg"], foreground=c["fg"])
    style.configure("TLabelframe", background=c["bg"], foreground=c["fg"],
                    bordercolor=c["border"])
    style.configure("TLabelframe.Label", background=c["bg"],
                    foreground=c["accent"], font=Theme.FONT["bold"])

    style.configure("TButton", background=c["bg_panel"], foreground=c["fg"],
                    bordercolor=c["border"], padding=(10, 5))
    style.map("TButton",
              background=[("active", c["bg_hover"])],
              foreground=[("active", c["fg_bright"])])

    style.configure("Accent.TButton", background=c["accent_dark"],
                    foreground=c["fg_bright"])
    style.map("Accent.TButton",
              background=[("active", c["accent"])])

    style.configure("Treeview", background=c["bg_panel"], fieldbackground=c["bg_panel"],
                    foreground=c["fg"], bordercolor=c["border"])
    style.map("Treeview",
              background=[("selected", c["selection"])],
              foreground=[("selected", c["fg_bright"])])
    style.configure("Treeview.Heading", background=c["bg_hover"],
                    foreground=c["accent"], font=Theme.FONT["bold"])

    style.configure("TEntry", fieldbackground=c["bg_panel"], foreground=c["fg"],
                    insertcolor=c["fg"], bordercolor=c["border"])

    style.configure("TCombobox", fieldbackground=c["bg_panel"], foreground=c["fg"],
                    background=c["bg_panel"], arrowcolor=c["fg"])
    style.map("TCombobox",
              fieldbackground=[("readonly", c["bg_panel"])],
              foreground=[("readonly", c["fg"])])

    style.configure("TCheckbutton", background=c["bg"], foreground=c["fg"])

    style.configure("TRadiobutton", background=c["bg"], foreground=c["fg"])

    style.configure("TScrollbar", background=c["bg_panel"], troughcolor=c["bg"],
                    bordercolor=c["border"], arrowcolor=c["fg"])

    style.configure("TNotebook", background=c["bg"], bordercolor=c["border"])
    style.configure("TNotebook.Tab", background=c["bg_panel"], foreground=c["fg"],
                    padding=(12, 6))
    style.map("TNotebook.Tab",
              background=[("selected", c["bg_hover"])],
              foreground=[("selected", c["fg_bright"])])

    style.configure("TProgressbar", background=c["accent"], troughcolor=c["bg_panel"],
                    bordercolor=c["border"])

    return style
