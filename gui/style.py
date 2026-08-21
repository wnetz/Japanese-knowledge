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
    "purple_light": "#b89cff",
    "purple_dark": "#5930b8",
    "green": "#42c77a",
    "green_hover": "#59d98d",
    "well_known": "#315a9b",
    "well_known_hover": "#3f70bd",
    "well_known_pressed": "#244578",
    "close": "#d29b3d",
    "close_hover": "#e0ad52",
    "close_pressed": "#ad7d2e",
    "red": "#ef5350",
    "yellow": "#f4d35e",
    "cyan": "#26d9d9",
    "wanikani": "#ff69b4",
    "bunpro": "#e85d3f",
    "anki": "#4a90e2",
    "writing": "#42c77a",
    "status_blue": "#4a90e2",
    "total": "#b388ff",
    "input_bg": "#242424",
    "selection": "#523b78",
}


# SRS history graph palettes.
# Keep graph appearance here so history_screen.py contains only graph behavior.
WANIKANI_STAGE_STYLES = {
    "lesson": {"color": "#9e9e9e", "linestyle": "-"},
    "apprentice_1": {"color": "#ef5350", "linestyle": "-"},
    "apprentice_2": {"color": "#ff8c42", "linestyle": "-"},
    "apprentice_3": {"color": "#f4d35e", "linestyle": "-"},
    "apprentice_4": {"color": "#42c77a", "linestyle": "-"},
    "guru_1": {"color": "#26c6da", "linestyle": "-"},
    "guru_2": {"color": "#4a90e2", "linestyle": "-"},
    "master": {"color": "#5c6bc0", "linestyle": "-"},
    "enlightened": {"color": "#8e5cd9", "linestyle": "-"},
    "burned": {"color": "#4b237a", "linestyle": "-"},
}

ANKI_STAGE_STYLES = {
    "new": {"color": "#26d9d9", "linestyle": "-"},
    "learning": {"color": "#42c77a", "linestyle": "-"},
    "review": {"color": "#ef5350", "linestyle": "-"},
    "relearning": {"color": "#d0d0d0", "linestyle": "-"},
}

BUNPRO_STAGE_STYLES = {
    "beginner": {"color": "#ef5350", "linestyle": "-"},
    "adept": {"color": "#ff9f43", "linestyle": "-"},
    "seasoned": {"color": "#f4d35e", "linestyle": "-"},
    "expert": {"color": "#42c77a", "linestyle": "-"},
    "master": {"color": "#7e57c2", "linestyle": "-"},
    "ghost": {"color": "#ffffff", "linestyle": ":"},
    "self_study": {"color": "#9e9e9e", "linestyle": "-"},
}


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def daily_goal_progress_color(progress: float) -> str:
    """Interpolate partial completion from light purple to dark purple."""
    progress = max(0.0, min(1.0, float(progress)))
    start = _hex_to_rgb(COLORS["purple_light"])
    end = _hex_to_rgb(COLORS["purple_dark"])
    rgb = tuple(
        round(start[index] + (end[index] - start[index]) * progress)
        for index in range(3)
    )
    return _rgb_to_hex(rgb)



DAILY_GOAL_CALENDAR_COLORS = {
    # Reuse the application's existing palette.
    "complete": COLORS["purple_dark"],
    "partial": COLORS["purple_hover"],
    "missed": COLORS["panel_alt"],
    "untracked": COLORS["panel_alt"],
    "future": COLORS["panel"],
    "selected_border": COLORS["purple"],
    "day_text": COLORS["text"],
    "muted_day_text": COLORS["muted"],
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
        "TRadiobutton",
        background=COLORS["bg"],
        foreground=COLORS["text"],
    )
    style.map(
        "TRadiobutton",
        background=[("active", COLORS["bg"])],
        foreground=[("active", COLORS["text"])],
    )

    style.configure(
        "WellKnown.TButton",
        background=COLORS["well_known"],
        foreground="#111111",
        bordercolor=COLORS["well_known"],
        lightcolor=COLORS["well_known"],
        darkcolor=COLORS["well_known"],
        focuscolor=COLORS["well_known"],
        focusthickness=0,
        borderwidth=0,
        relief="flat",
        padding=(12, 8),
    )
    style.map(
        "WellKnown.TButton",
        background=[
            ("active", COLORS["well_known_hover"]),
            ("pressed", COLORS["well_known_pressed"]),
        ],
        foreground=[
            ("active", "#111111"),
            ("pressed", "#111111"),
        ],
        bordercolor=[
            ("active", COLORS["well_known_hover"]),
            ("pressed", COLORS["well_known_pressed"]),
        ],
        lightcolor=[
            ("active", COLORS["well_known_hover"]),
            ("pressed", COLORS["well_known_pressed"]),
        ],
        darkcolor=[
            ("active", COLORS["well_known_hover"]),
            ("pressed", COLORS["well_known_pressed"]),
        ],
    )

    style.configure(
        "Close.TButton",
        background=COLORS["close"],
        foreground="#111111",
        bordercolor=COLORS["close"],
        lightcolor=COLORS["close"],
        darkcolor=COLORS["close"],
        focuscolor=COLORS["close"],
        focusthickness=0,
        borderwidth=0,
        relief="flat",
        padding=(12, 8),
    )
    style.map(
        "Close.TButton",
        background=[
            ("active", COLORS["close_hover"]),
            ("pressed", COLORS["close_pressed"]),
        ],
        foreground=[
            ("active", "#111111"),
            ("pressed", "#111111"),
        ],
        bordercolor=[
            ("active", COLORS["close_hover"]),
            ("pressed", COLORS["close_pressed"]),
        ],
        lightcolor=[
            ("active", COLORS["close_hover"]),
            ("pressed", COLORS["close_pressed"]),
        ],
        darkcolor=[
            ("active", COLORS["close_hover"]),
            ("pressed", COLORS["close_pressed"]),
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