from __future__ import annotations

import random
import re
import tkinter as tk
from datetime import datetime, timezone
from tkinter import messagebox, ttk
from typing import Any

from .style import COLORS, FONTS, style_scale

from .shared import (
    VOCABULARY_PROFILE_PATH,
    has_kanji,
    load_json,
    save_json,
)


class WritingScreen(ttk.Frame):
    def __init__(self, parent) -> None:
        super().__init__(parent)

        self.profile: dict[str, Any] = {}
        self.all_writable_entries: list[dict[str, Any]] = []
        self.quiz_entries: list[dict[str, Any]] = []
        self.current: dict[str, Any] | None = None
        self.previous_key: tuple[str, str] | None = None
        self.answer_revealed = False

        self._build_ui()
        self.reload_profile(show_errors=False)

    def _build_ui(self) -> None:
        ttk.Label(
            self,
            text="Writing Quiz",
            style="Heading.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            self,
            text="Practice vocabulary whose kanji are marked writable.",
        ).pack(anchor="w", pady=(2, 14))

        filter_box = ttk.LabelFrame(self, text="Quiz Filter", padding=12)
        filter_box.pack(fill="x", pady=(0, 14))

        self.require_confidence_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            filter_box,
            text="Require confidence score",
            variable=self.require_confidence_var,
            command=self.apply_confidence_filter,
        ).pack(anchor="w")

        slider_row = ttk.Frame(filter_box)
        slider_row.pack(fill="x", pady=(8, 0))

        ttk.Label(slider_row, text="Minimum confidence").pack(side="left")

        self.confidence_value_var = tk.StringVar(value="0.00")
        ttk.Label(
            slider_row,
            textvariable=self.confidence_value_var,
            width=5,
        ).pack(side="right")

        self.confidence_scale = tk.Scale(
            filter_box,
            from_=0.0,
            to=1.0,
            resolution=0.05,
            orient="horizontal",
            showvalue=False,
            command=self._on_confidence_slider,
        )
        self.confidence_scale.set(0.0)
        self.confidence_scale.pack(fill="x")
        style_scale(self.confidence_scale)

        self.quiz_progress_var = tk.StringVar()
        ttk.Label(self, textvariable=self.quiz_progress_var).pack(
            pady=(4, 8)
        )

        ttk.Label(
            self,
            text="Write this word in Japanese",
            style="Subheading.TLabel",
        ).pack(pady=(10, 8))

        self.reading_var = tk.StringVar()
        ttk.Label(
            self,
            textvariable=self.reading_var,
            font=FONTS["japanese_large"],
        ).pack(pady=(6, 5))

        self.meaning_var = tk.StringVar()
        ttk.Label(
            self,
            textvariable=self.meaning_var,
            font=("Segoe UI", 13),
            wraplength=700,
            justify="center",
        ).pack(pady=(2, 16))

        self.answer_var = tk.StringVar()
        ttk.Label(
            self,
            textvariable=self.answer_var,
            font=FONTS["japanese_answer"],
        ).pack(pady=(8, 16))

        self.reveal_button = ttk.Button(
            self,
            text="Reveal Answer",
            command=self.reveal_answer,
            style="Accent.TButton",
        )
        self.reveal_button.pack(ipadx=18, ipady=7)

        buttons = ttk.Frame(self)
        buttons.pack(pady=16)

        self.fail_button = ttk.Button(
            buttons,
            text="Fail",
            style="Danger.TButton",
            command=lambda: self.record_result(False),
            state="disabled",
        )
        self.fail_button.grid(row=0, column=0, padx=8, ipadx=18, ipady=6)

        self.pass_button = ttk.Button(
            buttons,
            text="Pass",
            style="Success.TButton",
            command=lambda: self.record_result(True),
            state="disabled",
        )
        self.pass_button.grid(row=0, column=1, padx=8, ipadx=18, ipady=6)

        self.quiz_stats_var = tk.StringVar()
        ttk.Label(self, textvariable=self.quiz_stats_var).pack(pady=(8, 0))

    @staticmethod
    def _dictionary_lookup_candidates(word: str) -> list[str]:
        candidates = [word]

        # Many imported deck entries may contain grammar scaffolding such as
        # "N + を + 食べる". JMdict will not match the full expression, so try
        # Japanese-looking lexical segments from right to left.
        parts = re.findall(r"[一-龯々〆ヵヶぁ-ゖァ-ヺー]+", word)

        for part in reversed(parts):
            cleaned = part.strip()
            if cleaned and cleaned not in candidates:
                candidates.append(cleaned)

        return candidates

    def _ensure_dictionary(self) -> bool:
        if self.dictionary is not None:
            return True
        try:
            self.dictionary = JMDictReader()
            return True
        except Exception as exc:
            messagebox.showerror("JMdict unavailable", str(exc))
            return False

    def reload_profile(self, *, show_errors: bool = True) -> None:
        try:
            self.profile = load_json(VOCABULARY_PROFILE_PATH)
        except Exception as exc:
            if show_errors:
                messagebox.showerror(
                    "Could not load vocabulary profile",
                    f"{type(exc).__name__}: {exc}",
                )
            self.profile = {}
            self.all_writable_entries = []
            self.quiz_entries = []
            return

        self.all_writable_entries = [
            item
            for item in self.profile.get("vocabulary", [])
            if isinstance(item, dict)
            and item.get("writable") is True
            and str(item.get("word") or "").strip()
            and has_kanji(str(item.get("word") or ""))
            and str(item.get("reading") or "").strip()
            and any(
                str(value).strip()
                for value in item.get("meanings", [])
            )
        ]
        self.apply_confidence_filter()

    def _on_confidence_slider(self, value: str) -> None:
        self.confidence_value_var.set(f"{float(value):.2f}")
        if self.require_confidence_var.get():
            self.apply_confidence_filter()

    def apply_confidence_filter(self) -> None:
        if not self.require_confidence_var.get():
            self.quiz_entries = list(self.all_writable_entries)
        else:
            minimum = float(self.confidence_scale.get())
            filtered = []
            for item in self.all_writable_entries:
                confidence = item.get("confidence")
                if confidence is None:
                    continue
                try:
                    confidence_value = float(confidence)
                except (TypeError, ValueError):
                    continue
                if confidence_value >= minimum:
                    filtered.append(item)
            self.quiz_entries = filtered

        if not self.quiz_entries:
            self.current = None
            self.quiz_progress_var.set("0 words match the current filter")
            self.reading_var.set("")
            self.meaning_var.set("")
            self.answer_var.set("")
            self.quiz_stats_var.set("")
            self.reveal_button.config(state="disabled")
            self.pass_button.config(state="disabled")
            self.fail_button.config(state="disabled")
            return

        self.next_question()

    @staticmethod
    def _write_score(item: dict[str, Any]) -> dict[str, Any]:
        score = item.get("write_score")
        return score if isinstance(score, dict) else {}

    def _pick_quiz_entry(self) -> dict[str, Any]:
        if len(self.quiz_entries) == 1:
            return self.quiz_entries[0]

        candidates = [
            item
            for item in self.quiz_entries
            if (
                str(item.get("word") or ""),
                str(item.get("reading") or ""),
            ) != self.previous_key
        ]
        return random.choice(candidates or self.quiz_entries)

    def next_question(self) -> None:
        if not self.quiz_entries:
            return
        self.current = self._pick_quiz_entry()
        word = str(self.current.get("word") or "").strip()
        stored_reading = str(self.current.get("reading") or "").strip()
        self.previous_key = (word, stored_reading)

        self.reading_var.set(stored_reading)

        meanings = [
            str(value).strip()
            for value in self.current.get("meanings", [])
            if str(value).strip()
        ]
        self.meaning_var.set(", ".join(meanings))

        self.answer_revealed = False
        self.answer_var.set("")
        self.reveal_button.config(state="normal")
        self.pass_button.config(state="disabled")
        self.fail_button.config(state="disabled")

        score = self._write_score(self.current)
        attempts = int(score.get("attempts") or 0)
        passes = int(score.get("passes") or 0)
        fails = int(score.get("fails") or 0)
        value = score.get("score")
        score_text = "unreviewed" if value is None else f"{float(value):.1%}"

        self.quiz_stats_var.set(
            f"{attempts} attempts · {passes} passed · "
            f"{fails} failed · write score {score_text}"
        )

        reviewed = sum(
            1
            for item in self.quiz_entries
            if int(self._write_score(item).get("attempts") or 0) > 0
        )

        filter_text = ""
        if self.require_confidence_var.get():
            filter_text = (
                f" · confidence ≥ {float(self.confidence_scale.get()):.2f}"
            )

        self.quiz_progress_var.set(
            f"{len(self.quiz_entries)} eligible words · "
            f"{reviewed} reviewed{filter_text}"
        )

    def reveal_answer(self) -> None:
        if not self.current or self.answer_revealed:
            return

        self.answer_revealed = True
        self.answer_var.set(str(self.current.get("word") or ""))
        self.reveal_button.config(state="disabled")
        self.pass_button.config(state="normal")
        self.fail_button.config(state="normal")

    def record_result(self, passed: bool) -> None:
        if not self.current or not self.answer_revealed:
            return

        score = dict(self._write_score(self.current))
        attempts = int(score.get("attempts") or 0) + 1
        passes = int(score.get("passes") or 0) + (1 if passed else 0)
        fails = int(score.get("fails") or 0) + (0 if passed else 1)

        self.current["write_score"] = {
            "attempts": attempts,
            "passes": passes,
            "fails": fails,
            "score": round(passes / attempts, 4),
            "last_result": "pass" if passed else "fail",
            "last_reviewed": datetime.now(timezone.utc).isoformat(),
        }

        try:
            save_json(VOCABULARY_PROFILE_PATH, self.profile)
        except Exception as exc:
            messagebox.showerror(
                "Could not save",
                f"The review result was not saved:\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        self.next_question()
