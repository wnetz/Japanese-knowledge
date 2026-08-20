from __future__ import annotations

import tkinter as tk
from tkinter import ttk


COLORS = {
    "bg": "#2b2b2b",
    "panel": "#333333",
    "panel_alt": "#3a3a3a",
    "border": "#4a4a4a",
    "text": "#f0f0f0",
    "muted": "#b8b8b8",
    "purple": "#6d3fd8",
    "purple_hover": "#7d55df",
    "purple_dark": "#5930b8",
    "green": "#42c77a",
    "green_hover": "#59d98d",
    "red": "#ef5350",
    "yellow": "#f4d35e",
    "cyan": "#26d9d9",
    "wanikani": "#ff69b4",
    "bunpro": "#e85d3f",
    "anki": "#4a90e2",
    "total": "#b388ff",
    "input_bg": "#242424",
    "selection": "#523b78",
}

FONTS = {
    "body": ("Segoe UI", 10),
    "body_small": ("Segoe UI", 9),
    "heading": ("Segoe UI", 20, "bold"),
    "subheading": ("Segoe UI", 11, "bold"),
    "japanese_large": ("Yu Gothic UI", 30),
    "japanese_answer": ("Yu Gothic UI", 38, "bold"),
    "mono": ("Consolas", 9),
}

PADDING = {
    "outer": 20,
    "panel": 12,
    "sidebar_x": 14,
    "sidebar_y": 16,
}


def configure_root(root: tk.Tk) -> None:
    root.configure(bg=COLORS["bg"])

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        ".",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        fieldbackground=COLORS["input_bg"],
        font=FONTS["body"],
    )

    style.configure(
        "TFrame",
        background=COLORS["bg"],
    )

    style.configure(
        "Panel.TFrame",
        background=COLORS["panel"],
    )

    style.configure(
        "TLabel",
        background=COLORS["bg"],
        foreground=COLORS["text"],
    )

    style.configure(
        "Muted.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["muted"],
    )

    style.configure(
        "Heading.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        font=FONTS["heading"],
    )

    style.configure(
        "Subheading.TLabel",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        font=FONTS["subheading"],
    )

    style.configure(
        "TLabelframe",
        background=COLORS["panel"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        relief="solid",
        borderwidth=1,
    )

    style.configure(
        "TLabelframe.Label",
        background=COLORS["panel"],
        foreground=COLORS["purple_hover"],
        font=FONTS["subheading"],
    )

    style.configure(
        "TButton",
        background=COLORS["panel_alt"],
        foreground=COLORS["text"],
        bordercolor=COLORS["border"],
        padding=(10, 7),
    )
    style.map(
        "TButton",
        background=[
            ("active", COLORS["purple_hover"]),
            ("pressed", COLORS["purple_dark"]),
        ],
        foreground=[
            ("active", "#ffffff"),
            ("pressed", "#ffffff"),
        ],
    )

    # Filled action buttons. Border and focus colors match the fill so
    # ttk/clam does not draw a light box around the colored button.
    style.configure(
        "Accent.TButton",
        background=COLORS["purple"],
        foreground="#111111",
        bordercolor=COLORS["purple"],
        lightcolor=COLORS["purple"],
        darkcolor=COLORS["purple"],
        focuscolor=COLORS["purple"],
        focusthickness=0,
        borderwidth=0,
        relief="flat",
        padding=(12, 8),
    )
    style.map(
        "Accent.TButton",
        background=[
            ("active", COLORS["purple_hover"]),
            ("pressed", COLORS["purple_dark"]),
        ],
        foreground=[
            ("active", "#111111"),
            ("pressed", "#111111"),
        ],
        bordercolor=[
            ("active", COLORS["purple_hover"]),
            ("pressed", COLORS["purple_dark"]),
        ],
        lightcolor=[
            ("active", COLORS["purple_hover"]),
            ("pressed", COLORS["purple_dark"]),
        ],
        darkcolor=[
            ("active", COLORS["purple_hover"]),
            ("pressed", COLORS["purple_dark"]),
        ],
    )

    style.configure(
        "Success.TButton",
        background=COLORS["green"],
        foreground="#111111",
        bordercolor=COLORS["green"],
        lightcolor=COLORS["green"],
        darkcolor=COLORS["green"],
        focuscolor=COLORS["green"],
        focusthickness=0,
        borderwidth=0,
        relief="flat",
        padding=(12, 8),
    )
    style.map(
        "Success.TButton",
        background=[
            ("active", COLORS["green_hover"]),
            ("pressed", COLORS["green"]),
        ],
        foreground=[
            ("active", "#111111"),
            ("pressed", "#111111"),
        ],
        bordercolor=[
            ("active", COLORS["green_hover"]),
            ("pressed", COLORS["green"]),
        ],
        lightcolor=[
            ("active", COLORS["green_hover"]),
            ("pressed", COLORS["green"]),
        ],
        darkcolor=[
            ("active", COLORS["green_hover"]),
            ("pressed", COLORS["green"]),
        ],
    )

    style.configure(
        "Danger.TButton",
        background=COLORS["red"],
        foreground="#111111",
        bordercolor=COLORS["red"],
        lightcolor=COLORS["red"],
        darkcolor=COLORS["red"],
        focuscolor=COLORS["red"],
        focusthickness=0,
        borderwidth=0,
        relief="flat",
        padding=(12, 8),
    )
    style.map(
        "Danger.TButton",
        background=[
            ("active", "#ff6b68"),
            ("pressed", "#c93f3c"),
        ],
        foreground=[
            ("active", "#111111"),
            ("pressed", "#111111"),
        ],
        bordercolor=[
            ("active", "#ff6b68"),
            ("pressed", "#c93f3c"),
        ],
        lightcolor=[
            ("active", "#ff6b68"),
            ("pressed", "#c93f3c"),
        ],
        darkcolor=[
            ("active", "#ff6b68"),
            ("pressed", "#c93f3c"),
        ],
    )

    style.configure(
        "TCheckbutton",
        background=COLORS["bg"],
        foreground=COLORS["text"],
    )
    style.map(
        "TCheckbutton",
        background=[("active", COLORS["bg"])],
        foreground=[("active", COLORS["text"])],
    )

    style.configure(
        "TCombobox",
        fieldbackground=COLORS["input_bg"],
        background=COLORS["panel_alt"],
        foreground=COLORS["text"],
        arrowcolor=COLORS["text"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[
            ("readonly", COLORS["input_bg"]),
        ],
        foreground=[
            ("readonly", COLORS["text"]),
        ],
    )

    style.configure(
        "Treeview",
        background=COLORS["panel"],
        fieldbackground=COLORS["panel"],
        foreground=COLORS["text"],
        rowheight=26,
        bordercolor=COLORS["border"],
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["selection"])],
        foreground=[("selected", "#ffffff")],
    )

    style.configure(
        "Treeview.Heading",
        background=COLORS["panel_alt"],
        foreground=COLORS["purple_hover"],
        bordercolor=COLORS["border"],
        font=FONTS["subheading"],
    )

    style.configure(
        "TSeparator",
        background=COLORS["border"],
    )

    root.option_add("*TCombobox*Listbox.background", COLORS["input_bg"])
    root.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", COLORS["selection"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")


def style_text_widget(widget: tk.Text) -> None:
    widget.configure(
        background=COLORS["input_bg"],
        foreground=COLORS["text"],
        insertbackground=COLORS["text"],
        selectbackground=COLORS["selection"],
        selectforeground="#ffffff",
        relief="flat",
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["purple"],
    )


def style_scale(widget: tk.Scale) -> None:
    widget.configure(
        bg=COLORS["panel"],
        fg=COLORS["text"],
        troughcolor=COLORS["input_bg"],
        activebackground=COLORS["purple_hover"],
        highlightthickness=0,
    )


def style_canvas(widget: tk.Canvas, *, panel: bool = False) -> None:
    widget.configure(
        bg=COLORS["panel"] if panel else COLORS["bg"],
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["purple"],
    )
