from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from grammar.mastery import (
    load_mastery,
    parse_review_block,
    save_review_event,
    textbook_items,
)
from .shared import (
    GRAMMAR_USE_INDEX_PATH,
    TEXTBOOK_INDEX_PATH,
    load_json,
)
from .style import FONTS, style_text_widget


SCORE_LABELS = {
    0: "0 · Wrong",
    1: "1 · Major help",
    2: "2 · Minor issue",
    3: "3 · Correct",
}


class GrammarReviewScreen(ttk.Frame):
    def __init__(self, parent) -> None:
        super().__init__(parent)

        self.textbook_index: dict[str, Any] = {}
        self.items: list[dict[str, str]] = []
        self.items_by_lesson: dict[str, list[dict[str, str]]] = {}
        self.pending: list[dict[str, Any]] = []

        self._build_ui()
        self.reload_data(show_errors=False)

    def _build_ui(self) -> None:
        # Keep the review logger compact enough to fit the application's
        # default 1100x760 window without requiring a resize.
        ttk.Label(
            self,
            text="Grammar Review Logger",
            style="Heading.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            self,
            text=(
                "Log target and incidental grammar observations from each "
                "review answer."
            ),
            wraplength=800,
        ).pack(anchor="w", pady=(2, 7))

        paste_box = ttk.LabelFrame(
            self,
            text="Paste review results + prompt + response",
            padding=8,
        )
        paste_box.pack(fill="x", pady=(0, 7))

        self.results_text = tk.Text(
            paste_box,
            height=4,
            wrap="word",
            font=FONTS["mono"],
        )
        style_text_widget(self.results_text)
        self.results_text.pack(fill="x")

        ttk.Button(
            paste_box,
            text="Add Parsed Results",
            command=self._add_parsed_results,
            style="Accent.TButton",
        ).pack(anchor="e", pady=(5, 0))

        # Review context is intentionally near the top of the page so the
        # prompt/response populated by the paste parser are visible immediately.
        details = ttk.LabelFrame(
            self,
            text="Review context",
            padding=8,
        )
        details.pack(fill="x", pady=(0, 7))

        fields = ttk.Frame(details)
        fields.pack(fill="x")
        fields.grid_columnconfigure(0, weight=1, uniform="review_context")
        fields.grid_columnconfigure(1, weight=1, uniform="review_context")

        left = ttk.Frame(fields)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ttk.Label(left, text="Prompt").pack(anchor="w")
        self.prompt_text = tk.Text(left, height=2, wrap="word")
        style_text_widget(self.prompt_text)
        self.prompt_text.pack(fill="x")

        right = ttk.Frame(fields)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        ttk.Label(right, text="Your response").pack(anchor="w")
        self.response_text = tk.Text(right, height=2, wrap="word")
        style_text_widget(self.response_text)
        self.response_text.pack(fill="x")

        context_buttons = ttk.Frame(details)
        context_buttons.pack(fill="x", pady=(5, 0))
        ttk.Button(
            context_buttons,
            text="Clear",
            command=self._clear_context,
        ).pack(side="right")

        manual = ttk.LabelFrame(
            self,
            text="Add one observation manually",
            padding=8,
        )
        manual.pack(fill="x", pady=(0, 7))

        row1 = ttk.Frame(manual)
        row1.pack(fill="x")

        ttk.Label(row1, text="Lesson").pack(side="left")

        self.lesson_var = tk.StringVar(value="Custom")
        self.lesson_combo = ttk.Combobox(
            row1,
            textvariable=self.lesson_var,
            state="readonly",
            width=11,
        )
        self.lesson_combo.pack(side="left", padx=(6, 12))
        self.lesson_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._lesson_changed(),
        )

        ttk.Label(row1, text="Grammar item").pack(side="left")

        self.grammar_var = tk.StringVar()
        self.grammar_combo = ttk.Combobox(
            row1,
            textvariable=self.grammar_var,
            state="normal",
            width=48,
        )
        self.grammar_combo.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(6, 0),
        )

        row2 = ttk.Frame(manual)
        row2.pack(fill="x", pady=(6, 0))

        ttk.Label(row2, text="Mode").pack(side="left")
        self.mode_var = tk.StringVar(value="production")
        ttk.Combobox(
            row2,
            textvariable=self.mode_var,
            values=["production", "recognition"],
            state="readonly",
            width=12,
        ).pack(side="left", padx=(6, 14))

        ttk.Label(row2, text="Score").pack(side="left")
        self.score_var = tk.IntVar(value=3)

        for score in range(4):
            ttk.Radiobutton(
                row2,
                text=SCORE_LABELS[score],
                variable=self.score_var,
                value=score,
            ).pack(side="left", padx=(4, 2))

        ttk.Button(
            row2,
            text="Add",
            command=self._add_manual_observation,
            style="Accent.TButton",
        ).pack(side="right", padx=(10, 0))

        pending_box = ttk.LabelFrame(
            self,
            text="Pending observations",
            padding=8,
        )
        pending_box.pack(fill="both", expand=True, pady=(0, 7))

        columns = ("lesson", "grammar", "mode", "score")
        self.pending_tree = ttk.Treeview(
            pending_box,
            columns=columns,
            show="headings",
            height=4,
        )
        self.pending_tree.heading("lesson", text="Lesson")
        self.pending_tree.heading("grammar", text="Grammar item")
        self.pending_tree.heading("mode", text="Mode")
        self.pending_tree.heading("score", text="Score")
        self.pending_tree.column("lesson", width=75, stretch=False)
        self.pending_tree.column("grammar", width=400)
        self.pending_tree.column("mode", width=100, stretch=False)
        self.pending_tree.column("score", width=60, stretch=False)
        self.pending_tree.pack(fill="both", expand=True)

        pending_buttons = ttk.Frame(pending_box)
        pending_buttons.pack(fill="x", pady=(5, 0))
        ttk.Button(
            pending_buttons,
            text="Remove Selected",
            command=self._remove_selected,
        ).pack(side="left")
        ttk.Button(
            pending_buttons,
            text="Clear",
            command=self._clear_pending,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            pending_buttons,
            text="Clear All",
            command=self._clear_all_review,
        ).pack(side="left", padx=(6, 0))

        ttk.Button(
            pending_buttons,
            text="Save Review",
            command=self._save_review,
            style="Success.TButton",
        ).pack(side="right", ipadx=12, ipady=2)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x")

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(
            bottom,
            textvariable=self.status_var,
        ).pack(side="left")


    def reload_data(self, *, show_errors: bool = True) -> None:
        try:
            self.textbook_index = (
                load_json(TEXTBOOK_INDEX_PATH)
                if TEXTBOOK_INDEX_PATH.exists()
                else {}
            )
            self.items = textbook_items(self.textbook_index)
        except Exception as exc:
            self.textbook_index = {}
            self.items = []
            if show_errors:
                messagebox.showerror(
                    "Grammar review",
                    f"Could not load textbook grammar:\n"
                    f"{type(exc).__name__}: {exc}",
                )

        self.items_by_lesson = {}
        for item in self.items:
            self.items_by_lesson.setdefault(
                item["lesson_id"],
                [],
            ).append(item)

        lessons = sorted(
            self.items_by_lesson,
            key=self._lesson_sort_key,
        )
        self.lesson_combo["values"] = ["Custom"] + lessons

        if self.lesson_var.get() not in self.lesson_combo["values"]:
            self.lesson_var.set("Custom")

        self._lesson_changed()
        self._refresh_status()

    @staticmethod
    def _lesson_sort_key(value: str) -> tuple:
        parts = []
        for part in value.split("-"):
            try:
                parts.append((0, int(part)))
            except ValueError:
                parts.append((1, part))
        return tuple(parts)

    def _lesson_changed(self) -> None:
        lesson = self.lesson_var.get()
        if lesson == "Custom":
            self.grammar_combo["values"] = []
            return

        values = [
            item["text"]
            for item in self.items_by_lesson.get(lesson, [])
        ]
        self.grammar_combo["values"] = values

        if values and self.grammar_var.get() not in values:
            self.grammar_var.set(values[0])

    def _find_textbook_item(
        self,
        lesson: str,
        grammar: str,
    ) -> dict[str, str] | None:
        for item in self.items_by_lesson.get(lesson, []):
            if item["text"] == grammar:
                return item
        return None

    def _add_observation(self, observation: dict[str, Any]) -> None:
        self.pending.append(observation)
        index = len(self.pending) - 1
        self.pending_tree.insert(
            "",
            "end",
            iid=str(index),
            values=(
                observation.get("lesson_id") or "—",
                observation.get("grammar") or observation.get("item_id"),
                observation.get("mode"),
                observation.get("score"),
            ),
        )
        self._refresh_status()

    def _add_parsed_results(self) -> None:
        raw = self.results_text.get("1.0", "end").strip()
        parsed_block = parse_review_block(raw)
        parsed = parsed_block["observations"]

        if not parsed and not parsed_block["prompt"] and not parsed_block["response"]:
            messagebox.showinfo(
                "No review data found",
                "No valid grammar results, prompt, or response were found.\n\n"
                "Example:\n"
                "～と思います    3    target\n"
                "prompt: I think...\n"
                "response: ～と思います",
            )
            return

        for observation in parsed:
            # If a pasted line has a textbook lesson prefix, enrich it with
            # the canonical textbook item where possible.
            lesson = observation.get("lesson_id") or ""
            grammar = observation.get("grammar") or ""
            item = self._find_textbook_item(lesson, grammar)
            if item:
                observation["item_id"] = item["item_id"]
                observation["grammar"] = item["text"]

            self._add_observation(observation)

        prompt = parsed_block["prompt"]
        response = parsed_block["response"]

        if prompt:
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.insert("1.0", prompt)

        if response:
            self.response_text.delete("1.0", "end")
            self.response_text.insert("1.0", response)

        self.results_text.delete("1.0", "end")
        self._refresh_status()

    def _add_manual_observation(self) -> None:
        lesson = self.lesson_var.get()
        grammar = self.grammar_var.get().strip()

        if not grammar:
            messagebox.showinfo(
                "Grammar item required",
                "Enter or select a grammar item.",
            )
            return

        if lesson == "Custom":
            item_id = grammar
            lesson_id = ""
        else:
            item = self._find_textbook_item(lesson, grammar)
            item_id = item["item_id"] if item else f"{lesson}::{grammar}"
            lesson_id = lesson

        self._add_observation(
            {
                "item_id": item_id,
                "lesson_id": lesson_id,
                "grammar": grammar,
                "mode": self.mode_var.get(),
                "score": int(self.score_var.get()),
            }
        )

    def _rebuild_pending_tree(self) -> None:
        for iid in self.pending_tree.get_children():
            self.pending_tree.delete(iid)

        for index, observation in enumerate(self.pending):
            self.pending_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    observation.get("lesson_id") or "—",
                    observation.get("grammar") or observation.get("item_id"),
                    observation.get("mode"),
                    observation.get("score"),
                ),
            )

    def _remove_selected(self) -> None:
        selected = sorted(
            (int(iid) for iid in self.pending_tree.selection()),
            reverse=True,
        )
        for index in selected:
            if 0 <= index < len(self.pending):
                self.pending.pop(index)
        self._rebuild_pending_tree()
        self._refresh_status()

    def _clear_pending(self) -> None:
        self.pending = []
        self._rebuild_pending_tree()
        self._refresh_status()

    def _clear_context(self) -> None:
        self.prompt_text.delete("1.0", "end")
        self.response_text.delete("1.0", "end")
        self._refresh_status()

    def _clear_all_review(self) -> None:
        self._clear_pending()
        self._clear_context()

    def _save_review(self) -> None:
        if not self.pending:
            messagebox.showinfo(
                "Nothing to save",
                "Add at least one grammar observation first.",
            )
            return

        try:
            save_review_event(
                GRAMMAR_USE_INDEX_PATH,
                list(self.pending),
                prompt=self.prompt_text.get("1.0", "end").strip(),
                response=self.response_text.get("1.0", "end").strip(),
            )
        except Exception as exc:
            messagebox.showerror(
                "Could not save review",
                f"{type(exc).__name__}: {exc}",
            )
            return

        count = len(self.pending)
        self._clear_pending()
        self.prompt_text.delete("1.0", "end")
        self.response_text.delete("1.0", "end")
        self.status_var.set(
            f"Saved review with {count} observation"
            + ("" if count == 1 else "s")
            + "."
        )

    def _refresh_status(self) -> None:
        data = load_mastery(GRAMMAR_USE_INDEX_PATH)
        event_count = len(data.get("events", []))
        item_count = len(data.get("items", {}))
        self.status_var.set(
            f"{len(self.pending)} pending · "
            f"{event_count} saved reviews · "
            f"{item_count} scored grammar items"
        )