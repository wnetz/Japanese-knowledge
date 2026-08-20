from __future__ import annotations

import random
import tkinter as tk
from datetime import datetime, timezone
from tkinter import messagebox, ttk

from config import load_config
from typing import Any

from .shared import (
    VOCABULARY_PROFILE_PATH,
    WRITING_PROFILE_PATH,
    has_kanji,
    load_json,
)
from .style import COLORS, FONTS
from writing.profile import (
    choose_context,
    choose_target_kanji,
    due_counts,
    is_new_kanji,
    valid_contexts_for_target,
    context_performance,
    kanji_occurrences,
    kanji_performance,
    kanji_srs,
    load_writing_profile,
    record_occurrence_result,
    save_writing_profile,
)
from writing.srs import (
    RESULT_CLOSE,
    RESULT_CORRECT,
    RESULT_FORGOT,
    RESULT_WELL_KNOWN,
    stage_label,
)


RESULT_LABELS = {
    RESULT_WELL_KNOWN: "Well Known",
    RESULT_CORRECT: "Correct",
    RESULT_CLOSE: "Close",
    RESULT_FORGOT: "Forgot",
}
RESULT_SEVERITY = {
    RESULT_WELL_KNOWN: -1,
    RESULT_CORRECT: 0,
    RESULT_CLOSE: 1,
    RESULT_FORGOT: 2,
}


class WritingScreen(ttk.Frame):
    def __init__(self, parent) -> None:
        super().__init__(parent)

        self.app_config = load_config()
        self.daily_new_limit = self.app_config.writing.daily_new_limit
        self.new_fail_cooldown_min = min(
            self.app_config.writing.new_fail_cooldown_min,
            self.app_config.writing.new_fail_cooldown_max,
        )
        self.new_fail_cooldown_max = max(
            self.app_config.writing.new_fail_cooldown_min,
            self.app_config.writing.new_fail_cooldown_max,
        )
        # Session-only: kanji -> number of OTHER questions to show before
        # this failed New kanji is eligible again.
        self.new_fail_cooldowns: dict[str, int] = {}

        self.profile: dict[str, Any] = {}
        self.writing_profile: dict[str, Any] = {}
        self.all_writable_entries: list[dict[str, Any]] = []
        self.quiz_entries: list[dict[str, Any]] = []
        self.contexts_by_kanji: dict[str, list[dict[str, Any]]] = {}

        self.current: dict[str, Any] | None = None
        self.target_kanji: str | None = None
        self.previous_target: str | None = None
        self.previous_key: tuple[str, str] | None = None
        self.answer_revealed = False
        self.grade_vars: list[tuple[int, str, tk.StringVar, dict[str, ttk.Button]]] = []

        self._build_ui()
        self.reload_profile(show_errors=False)

    def _build_ui(self) -> None:
        ttk.Label(
            self,
            text="Writing SRS",
            style="Heading.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            self,
            text=(
                "A kanji becomes due, then the quiz chooses a known vocabulary "
                "context containing it. Grade each written kanji separately."
            ),
        ).pack(anchor="w", pady=(2, 14))

        status_row = ttk.Frame(self)
        status_row.pack(pady=(2, 6))

        ttk.Label(
            status_row,
            text="New:",
        ).pack(side="left")

        self.new_due_var = tk.StringVar(value="0")
        ttk.Label(
            status_row,
            textvariable=self.new_due_var,
            foreground=COLORS["status_blue"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=(4, 16))

        ttk.Label(
            status_row,
            text="Reviews:",
        ).pack(side="left")

        self.reviews_due_var = tk.StringVar(value="0")
        ttk.Label(
            status_row,
            textvariable=self.reviews_due_var,
            foreground=COLORS["green"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=(4, 0))

        self.target_var = tk.StringVar()
        ttk.Label(
            self,
            textvariable=self.target_var,
            style="Subheading.TLabel",
        ).pack(pady=(6, 3))

        self.reading_var = tk.StringVar()
        ttk.Label(
            self,
            textvariable=self.reading_var,
            font=FONTS["japanese_large"],
        ).pack(pady=(4, 3))

        self.meaning_var = tk.StringVar()
        ttk.Label(
            self,
            textvariable=self.meaning_var,
            font=("Segoe UI", 13),
            wraplength=700,
            justify="center",
        ).pack(pady=(2, 10))

        self.answer_var = tk.StringVar()
        ttk.Label(
            self,
            textvariable=self.answer_var,
            font=FONTS["japanese_answer"],
        ).pack(pady=(4, 8))

        self.reveal_button = ttk.Button(
            self,
            text="Reveal Answer",
            command=self.reveal_answer,
            style="Accent.TButton",
        )
        self.reveal_button.pack(ipadx=18, ipady=5)

        self.grading_box = ttk.LabelFrame(
            self,
            text="Grade each kanji",
            padding=10,
        )
        self.grading_box.pack(fill="x", pady=(12, 8))

        self.grade_rows = ttk.Frame(self.grading_box)
        self.grade_rows.pack(fill="x")

        shortcut_row = ttk.Frame(self.grading_box)
        shortcut_row.pack(pady=(8, 0))

        self.all_well_known_button = ttk.Button(
            shortcut_row,
            text="All Well Known",
            style="WellKnown.TButton",
            command=lambda: self._set_all_grades_and_submit(RESULT_WELL_KNOWN),
            state="disabled",
        )
        self.all_well_known_button.pack(side="left", padx=5)

        self.all_correct_button = ttk.Button(
            shortcut_row,
            text="All Correct",
            style="Success.TButton",
            command=lambda: self._set_all_grades_and_submit(RESULT_CORRECT),
            state="disabled",
        )
        self.all_correct_button.pack(side="left", padx=5)

        self.all_forgot_button = ttk.Button(
            shortcut_row,
            text="Forgot All",
            style="Danger.TButton",
            command=lambda: self._set_all_grades_and_submit(RESULT_FORGOT),
            state="disabled",
        )
        self.all_forgot_button.pack(side="left", padx=5)

        self.submit_button = ttk.Button(
            shortcut_row,
            text="Submit Review",
            style="Accent.TButton",
            command=self.submit_review,
            state="disabled",
        )
        self.submit_button.pack(side="left", padx=(18, 5))

        self.quiz_stats_var = tk.StringVar()
        ttk.Label(self, textvariable=self.quiz_stats_var).pack(pady=(5, 0))

    def reload_profile(self, *, show_errors: bool = True) -> None:
        try:
            self.profile = load_json(VOCABULARY_PROFILE_PATH)
            self.writing_profile = load_writing_profile(WRITING_PROFILE_PATH)
        except Exception as exc:
            if show_errors:
                messagebox.showerror(
                    "Could not load writing data",
                    f"{type(exc).__name__}: {exc}",
                )
            self.profile = {}
            self.writing_profile = {}
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
            and any(str(value).strip() for value in item.get("meanings", []))
        ]
        self.apply_confidence_filter()

    def apply_confidence_filter(self) -> None:
        # Writing practice always requires a real confidence score. This
        # automatically excludes incomplete/Migaku-only entries that do not
        # have enough information to make a reliable writing prompt.
        self.quiz_entries = [
            item
            for item in self.all_writable_entries
            if item.get("confidence") is not None
        ]

        self._rebuild_context_index()

        if not self.quiz_entries or not self.contexts_by_kanji:
            self.current = None
            self.target_kanji = None
            self.new_due_var.set("0")
            self.reviews_due_var.set("0")
            self.target_var.set("")
            self.reading_var.set("")
            self.meaning_var.set("")
            self.answer_var.set("")
            self._clear_grade_rows()
            self.reveal_button.config(state="disabled")
            return

        self.next_question()

    def _rebuild_context_index(self) -> None:
        mapping: dict[str, list[dict[str, Any]]] = {}
        for item in self.quiz_entries:
            word = str(item.get("word") or "")
            seen: set[str] = set()
            for _, character in kanji_occurrences(word):
                if character in seen:
                    continue
                seen.add(character)
                mapping.setdefault(character, []).append(item)
        self.contexts_by_kanji = mapping

    def _set_new_fail_cooldown(self, character: str) -> None:
        self.new_fail_cooldowns[character] = random.randint(
            self.new_fail_cooldown_min,
            self.new_fail_cooldown_max,
        )

    def _advance_new_fail_cooldowns(self, shown_character: str) -> None:
        expired: list[str] = []
        for character, remaining in self.new_fail_cooldowns.items():
            if character == shown_character:
                continue
            remaining -= 1
            if remaining <= 0:
                expired.append(character)
            else:
                self.new_fail_cooldowns[character] = remaining
        for character in expired:
            self.new_fail_cooldowns.pop(character, None)

    def _cooldown_filtered_contexts(
        self,
        contexts_by_kanji: dict[str, list[dict[str, Any]]],
    ) -> dict[str, list[dict[str, Any]]]:
        """Prefer respecting cooldowns, but never dead-end the quiz.

        If every currently selectable kanji is cooling down, the kanji with
        the smallest remaining cooldown is released early. This preserves the
        requested 3-5-other-kanji spacing when enough material exists while
        still allowing practice to continue with a small queue.
        """
        blocked = {
            char
            for char, remaining in self.new_fail_cooldowns.items()
            if remaining > 0
        }
        filtered = {
            char: contexts
            for char, contexts in contexts_by_kanji.items()
            if char not in blocked
        }
        if filtered or not contexts_by_kanji:
            return filtered

        eligible_blocked = [
            char for char in contexts_by_kanji
            if char in blocked
        ]
        if not eligible_blocked:
            return contexts_by_kanji

        release = min(
            eligible_blocked,
            key=lambda char: self.new_fail_cooldowns.get(char, 0),
        )
        self.new_fail_cooldowns.pop(release, None)
        return {release: contexts_by_kanji[release]}

    def _show_no_reviews_state(self) -> None:
        self.current = None
        self.target_kanji = None
        self.answer_revealed = False

        self.new_due_var.set("0")
        self.reviews_due_var.set("0")

        self.target_var.set("No writing reviews due")
        self.reading_var.set("")
        self.meaning_var.set("")
        self.answer_var.set("")

        self._clear_grade_rows()
        self.reveal_button.config(state="disabled")
        self._set_grading_state(False)
        self.quiz_stats_var.set("You're caught up.")

    def next_question(self) -> None:
        selection_contexts = self._cooldown_filtered_contexts(
            self.contexts_by_kanji
        )
        target = choose_target_kanji(
            self.writing_profile,
            selection_contexts,
            daily_new_limit=self.daily_new_limit,
            previous=self.previous_target,
        )
        if target is None:
            self._show_no_reviews_state()
            return

        valid_contexts = valid_contexts_for_target(
            self.writing_profile,
            target,
            selection_contexts[target],
        )

        context = choose_context(
            self.writing_profile,
            target,
            valid_contexts,
            previous_key=self.previous_key,
        )
        if context is None:
            self._show_no_reviews_state()
            return

        self.current = context
        self.target_kanji = target
        self.previous_target = target
        self._advance_new_fail_cooldowns(target)

        word = str(context.get("word") or "").strip()
        reading = str(context.get("reading") or "").strip()
        self.previous_key = (word, reading)

        meanings = [
            str(value).strip()
            for value in context.get("meanings", [])
            if str(value).strip()
        ]

        srs = kanji_srs(self.writing_profile, target)
        stage = int(srs.get("stage") or 0)
        self.target_var.set(
            f"Writing review · {stage_label(stage)}"
        )
        self.reading_var.set(reading)
        self.meaning_var.set(", ".join(meanings))

        self.answer_revealed = False
        self.answer_var.set("")
        self._clear_grade_rows()
        self.reveal_button.config(state="normal")
        self._set_grading_state(False)

        perf = kanji_performance(self.writing_profile, target)
        attempts = int(perf.get("attempts") or 0)
        score = perf.get("score")
        score_text = "unreviewed" if score is None else f"{float(score):.1%}"

        new_due, ongoing_due = due_counts(
            self.writing_profile,
            self.contexts_by_kanji,
            daily_new_limit=self.daily_new_limit,
        )
        self.new_due_var.set(str(new_due))
        self.reviews_due_var.set(str(ongoing_due))
        self.quiz_stats_var.set(
            f"{attempts} observed attempts · writing score {score_text}"
        )

    def _is_due(self, character: str) -> bool:
        from writing.srs import is_due
        return is_due(kanji_srs(self.writing_profile, character))

    def reveal_answer(self) -> None:
        if not self.current or not self.target_kanji or self.answer_revealed:
            return

        self.answer_revealed = True
        word = str(self.current.get("word") or "")
        self.answer_var.set(word)
        self.reveal_button.config(state="disabled")

        self._build_grade_rows(word)
        self._set_grading_state(True)

    def _clear_grade_rows(self) -> None:
        for child in self.grade_rows.winfo_children():
            child.destroy()
        self.grade_vars = []

    def _build_grade_rows(self, word: str) -> None:
        self._clear_grade_rows()

        for row_index, (position, character) in enumerate(kanji_occurrences(word)):
            var = tk.StringVar(value="")
            buttons: dict[str, ttk.Button] = {}
            self.grade_vars.append((position, character, var, buttons))

            label_text = character
            if character == self.target_kanji:
                label_text += "  TARGET"

            ttk.Label(
                self.grade_rows,
                text=label_text,
                width=12,
                font=("Yu Gothic UI", 14, "bold"),
            ).grid(
                row=row_index,
                column=0,
                padx=(4, 12),
                pady=4,
                sticky="w",
            )

            choices = (
                (RESULT_WELL_KNOWN, "Well Known", "WellKnown.TButton"),
                (RESULT_CORRECT, "Correct", "Success.TButton"),
                (RESULT_CLOSE, "Close", "Close.TButton"),
                (RESULT_FORGOT, "Forgot", "Danger.TButton"),
            )

            for column, (result, label, button_style) in enumerate(
                choices,
                start=1,
            ):
                button = ttk.Button(
                    self.grade_rows,
                    text=label,
                    style=button_style,
                    command=lambda i=row_index, r=result: self._grade_clicked(i, r),
                    width=12,
                )
                button.grid(
                    row=row_index,
                    column=column,
                    padx=5,
                    pady=4,
                    sticky="ew",
                )
                buttons[result] = button

        for column in range(1, 5):
            self.grade_rows.columnconfigure(column, weight=1)

    def _grade_clicked(self, row_index: int, result: str) -> None:
        if row_index < 0 or row_index >= len(self.grade_vars):
            return

        _, _, var, buttons = self.grade_vars[row_index]
        var.set(result)
        self._refresh_grade_button_labels(row_index)

        # A single-kanji word needs no separate Submit click.
        if len(self.grade_vars) == 1:
            self.submit_review()
            return

        self._update_submit_state()

    def _refresh_grade_button_labels(self, row_index: int) -> None:
        _, _, var, buttons = self.grade_vars[row_index]
        selected = var.get()

        labels = {
            RESULT_WELL_KNOWN: "Well Known",
            RESULT_CORRECT: "Correct",
            RESULT_CLOSE: "Close",
            RESULT_FORGOT: "Forgot",
        }

        for result, button in buttons.items():
            label = labels[result]
            if result == selected:
                label = "✓ " + label
            button.config(text=label)

    def _set_all_grades(self, result: str) -> None:
        for row_index, (_, _, var, _) in enumerate(self.grade_vars):
            var.set(result)
            self._refresh_grade_button_labels(row_index)
        self._update_submit_state()

    def _set_all_grades_and_submit(self, result: str) -> None:
        if not self.grade_vars:
            return
        self._set_all_grades(result)
        self.submit_review()

    def _set_grading_state(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.all_well_known_button.config(state=state)
        self.all_correct_button.config(state=state)
        self.all_forgot_button.config(state=state)
        self.submit_button.config(state="disabled")

    def _update_submit_state(self) -> None:
        complete = bool(self.grade_vars) and all(
            var.get() in RESULT_LABELS
            for _, _, var, _ in self.grade_vars
        )
        self.submit_button.config(state="normal" if complete else "disabled")

    def submit_review(self) -> None:
        if (
            not self.current
            or not self.target_kanji
            or not self.answer_revealed
            or not self.grade_vars
        ):
            return

        if not all(var.get() in RESULT_LABELS for _, _, var, _ in self.grade_vars):
            return

        word = str(self.current.get("word") or "")
        reading = str(self.current.get("reading") or "")
        reviewed_at = datetime.now(timezone.utc)

        # First record every occurrence as performance evidence. This keeps
        # repeated kanji positions separate (for example 日 at positions 0 and
        # 2 in 日曜日) without changing any SRS schedule yet.
        results_by_character: dict[str, list[str]] = {}

        new_before_review = {
            character: is_new_kanji(self.writing_profile, character)
            for _, character, _, _ in self.grade_vars
        }

        for position, character, var, _ in self.grade_vars:
            result = var.get()
            results_by_character.setdefault(character, []).append(result)

            record_occurrence_result(
                self.writing_profile,
                character=character,
                word=word,
                reading=reading,
                position=position,
                result=result,
                targeted=False,
                update_schedule=False,
                reviewed_at=reviewed_at,
            )
            if (
                character == self.target_kanji
                and new_before_review.get(character, False)
                and result in (RESULT_CLOSE, RESULT_FORGOT)
            ):
                self._set_new_fail_cooldown(character)

        # Then update each unique kanji's schedule exactly once using the worst
        # result observed for that character in this word.
        from writing.srs import apply_result

        for character, results in results_by_character.items():
            worst_result = max(
                results,
                key=lambda result: RESULT_SEVERITY[result],
            )

            record = self.writing_profile["kanji"][character]

            if character == self.target_kanji:
                record["srs"] = apply_result(
                    record.get("srs"),
                    worst_result,
                    targeted=True,
                    now=reviewed_at,
                )
            elif worst_result != RESULT_CORRECT:
                # Incidental success never advances a schedule. Incidental
                # Close/Forgot can regress it and pull the review sooner.
                record["srs"] = apply_result(
                    record.get("srs"),
                    worst_result,
                    targeted=False,
                    now=reviewed_at,
                )

        try:
            save_writing_profile(WRITING_PROFILE_PATH, self.writing_profile)
        except Exception as exc:
            messagebox.showerror(
                "Could not save",
                f"The writing review was not saved:\n"
                f"{type(exc).__name__}: {exc}",
            )
            return

        # Fully reset the grading controls before selecting the next item.
        # This matters when the same sole queue item is immediately selected
        # again after a failed New review.
        self.answer_revealed = False
        self._clear_grade_rows()
        self._set_grading_state(False)
        self.next_question()
