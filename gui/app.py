from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .style import configure_root, COLORS, PADDING

from .reviews_screen import ReviewsScreen
from .kanji_heatmap_screen import KanjiHeatmapScreen
from .update_screen import UpdateScreen
from .writing_screen import WritingScreen


class JapaneseKnowledgeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Japanese Knowledge")
        self.geometry("1100x760")
        self.minsize(900, 650)
        configure_root(self)

        self.frames = {}

        self._build_shell()
        self.show_screen("writing")

    def _build_shell(self) -> None:
        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)

        sidebar = ttk.Frame(
            outer,
            padding=(PADDING["sidebar_x"], PADDING["sidebar_y"]),
            style="Panel.TFrame",
        )
        sidebar.pack(side="left", fill="y")

        ttk.Label(
            sidebar,
            text="Japanese\nKnowledge",
            font=("Segoe UI", 16, "bold"),
            foreground=COLORS["purple_hover"],
            background=COLORS["panel"],
            justify="left",
        ).pack(anchor="w", pady=(0, 22))

        ttk.Button(
            sidebar,
            text="Writing Quiz",
            command=lambda: self.show_screen("writing"),
            width=22,
        ).pack(fill="x", pady=4)

        ttk.Button(
            sidebar,
            text="Update Profiles",
            command=lambda: self.show_screen("update"),
            width=22,
        ).pack(fill="x", pady=4)

        ttk.Button(
            sidebar,
            text="Upcoming Reviews",
            command=lambda: self.show_screen("reviews"),
            width=22,
        ).pack(fill="x", pady=4)

        ttk.Button(
            sidebar,
            text="Kanji Heatmap",
            command=lambda: self.show_screen("heatmap"),
            width=22,
        ).pack(fill="x", pady=4)

        ttk.Separator(
            outer,
            orient="vertical",
        ).pack(side="left", fill="y")

        self.content = ttk.Frame(outer, padding=PADDING["outer"])
        self.content.pack(side="left", fill="both", expand=True)

        self.frames["writing"] = WritingScreen(self.content)

        self.frames["reviews"] = ReviewsScreen(self.content)

        self.frames["heatmap"] = KanjiHeatmapScreen(self.content)

        self.frames["update"] = UpdateScreen(
            self.content,
            on_update_complete=self._on_update_complete,
        )

    def _on_update_complete(self) -> None:
        writing = self.frames["writing"]
        reviews = self.frames["reviews"]

        writing.reload_profile(show_errors=False)
        reviews.refresh_reviews()

        heatmap = self.frames.get("heatmap")
        if heatmap is not None:
            heatmap.refresh_heatmap()

    def show_screen(self, name: str) -> None:
        for frame in self.frames.values():
            frame.pack_forget()

        frame = self.frames[name]
        frame.pack(fill="both", expand=True)

        if name == "reviews":
            frame.refresh_reviews()
        elif name == "heatmap":
            frame.refresh_heatmap()
