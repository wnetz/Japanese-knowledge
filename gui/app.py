from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .reviews_screen import ReviewsScreen
from .update_screen import UpdateScreen
from .writing_screen import WritingScreen


class JapaneseKnowledgeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Japanese Knowledge")
        self.geometry("1100x760")
        self.minsize(900, 650)

        self.frames = {}

        self._build_shell()
        self.show_screen("writing")

    def _build_shell(self) -> None:
        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)

        sidebar = ttk.Frame(outer, padding=(12, 14))
        sidebar.pack(side="left", fill="y")

        ttk.Label(
            sidebar,
            text="Japanese\nKnowledge",
            font=("Segoe UI", 16, "bold"),
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

        ttk.Separator(
            outer,
            orient="vertical",
        ).pack(side="left", fill="y")

        self.content = ttk.Frame(outer, padding=20)
        self.content.pack(side="left", fill="both", expand=True)

        self.frames["writing"] = WritingScreen(self.content)

        self.frames["reviews"] = ReviewsScreen(self.content)

        self.frames["update"] = UpdateScreen(
            self.content,
            on_update_complete=self._on_update_complete,
        )

    def _on_update_complete(self) -> None:
        writing = self.frames["writing"]
        reviews = self.frames["reviews"]

        writing.reload_profile(show_errors=False)
        reviews.refresh_reviews()

    def show_screen(self, name: str) -> None:
        for frame in self.frames.values():
            frame.pack_forget()

        frame = self.frames[name]
        frame.pack(fill="both", expand=True)

        if name == "reviews":
            frame.refresh_reviews()
