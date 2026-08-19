from __future__ import annotations

import json
import random
import re
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent
VOCABULARY_PROFILE_PATH = PROJECT_DIR / "output" / "vocabulary_profile.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def save_json(path: Path, value: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temp.replace(path)


def has_kanji(value: str) -> bool:
    for char in value:
        code = ord(char)
        if (
            0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF
        ):
            return True
    return False


def katakana_to_hiragana(value: str) -> str:
    result = []
    for char in value:
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:
            result.append(chr(code - 0x60))
        else:
            result.append(char)
    return "".join(result)


class JMDictReader:
    def __init__(self) -> None:
        try:
            from jamdict import Jamdict
        except ImportError as exc:
            raise RuntimeError(
                "JMdict support is not installed.\n\n"
                "Run:\n"
                "python -m pip install jamdict jamdict-data"
            ) from exc
        self.jam = Jamdict()

    @staticmethod
    def _reading_from_entry_text(entry: Any, word: str) -> str | None:
        # Jamdict's display form is typically:
        # [id#1358280] たべる (食べる) : ...
        text = str(entry)
        escaped = re.escape(word)
        match = re.search(r"\]\s+([ぁ-ゖァ-ヺー]+)\s+\(" + escaped + r"\)\s*:", text)
        if match:
            return katakana_to_hiragana(match.group(1))

        # Kana-only entry fallback.
        match = re.search(r"\]\s+([ぁ-ゖァ-ヺー]+)\s*:", text)
        if match and not has_kanji(word):
            return katakana_to_hiragana(match.group(1))
        return None

    def reading(self, word: str) -> str | None:
        result = self.jam.lookup(word)

        # Prefer an exact written-form match. The string representation is used as
        # a compatibility layer because jamdict object attributes vary by release.
        exact: list[str] = []
        fallback: list[str] = []
        for entry in result.entries:
            reading = self._reading_from_entry_text(entry, word)
            if reading:
                if f"({word})" in str(entry):
                    exact.append(reading)
                else:
                    fallback.append(reading)

        if exact:
            return exact[0]
        if fallback:
            return fallback[0]
        return None


class WritingReview(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Japanese Writing Review")
        self.geometry("760x700")
        self.minsize(620, 620)

        if not VOCABULARY_PROFILE_PATH.exists():
            messagebox.showerror(
                "Missing vocabulary profile",
                f"Could not find:\n{VOCABULARY_PROFILE_PATH}",
            )
            self.destroy()
            return

        self.profile = load_json(VOCABULARY_PROFILE_PATH)
        self.all_entries = [
            item
            for item in self.profile.get("vocabulary", [])
            if isinstance(item, dict)
            and item.get("writable") is True
            and str(item.get("word") or "").strip()
            and has_kanji(str(item.get("word") or ""))
        ]
        self.entries = list(self.all_entries)

        self.entries = list(self.all_entries)

        if not self.entries:
            messagebox.showerror(
                "No writable vocabulary",
                "No vocabulary entries have writable: true.",
            )
            self.destroy()
            return

        try:
            self.dictionary = JMDictReader()
        except Exception as exc:
            messagebox.showerror("JMdict unavailable", str(exc))
            self.destroy()
            return

        self.current: dict[str, Any] | None = None
        self.previous_key: tuple[str, str] | None = None
        self.answer_revealed = False

        self._build_ui()
        self.next_question()

    def _build_ui(self) -> None:
        frame = tk.Frame(self, padx=24, pady=18)
        frame.pack(fill="both", expand=True)

        filter_box = tk.LabelFrame(
            frame,
            text="Quiz Confidence Filter",
            padx=12,
            pady=10,
        )
        filter_box.pack(fill="x", pady=(0, 14))

        self.require_confidence_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            filter_box,
            text="Require confidence score",
            variable=self.require_confidence_var,
            command=self.apply_confidence_filter,
            anchor="w",
        ).pack(fill="x", anchor="w")

        slider_header = tk.Frame(filter_box)
        slider_header.pack(fill="x", pady=(8, 2))

        tk.Label(
            slider_header,
            text="Minimum confidence",
            font=("Segoe UI", 10),
        ).pack(side="left")

        self.confidence_value_var = tk.StringVar(value="0.00")
        tk.Label(
            slider_header,
            textvariable=self.confidence_value_var,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="right")

        self.confidence_scale = tk.Scale(
            filter_box,
            from_=0.0,
            to=1.0,
            resolution=0.005,
            orient="horizontal",
            showvalue=False,
            command=self._on_confidence_slider,
        )
        self.confidence_scale.set(0.0)
        self.confidence_scale.pack(fill="x")

        self.progress_var = tk.StringVar()
        tk.Label(
            frame,
            textvariable=self.progress_var,
            font=("Segoe UI", 10),
        ).pack(pady=(0, 8))

        tk.Label(
            frame,
            text="Write this word in Japanese",
            font=("Segoe UI", 17, "bold"),
        ).pack(pady=(8, 12))

        self.reading_var = tk.StringVar()
        tk.Label(
            frame,
            textvariable=self.reading_var,
            font=("Yu Gothic UI", 30),
        ).pack(pady=(6, 6))

        self.meaning_var = tk.StringVar()
        tk.Label(
            frame,
            textvariable=self.meaning_var,
            font=("Segoe UI", 14),
            wraplength=650,
            justify="center",
        ).pack(pady=(4, 14))

        self.answer_var = tk.StringVar()
        tk.Label(
            frame,
            textvariable=self.answer_var,
            font=("Yu Gothic UI", 38, "bold"),
        ).pack(pady=(8, 14))

        self.reveal_button = tk.Button(
            frame,
            text="Reveal Answer",
            command=self.reveal_answer,
            width=20,
            height=2,
        )
        self.reveal_button.pack(pady=(0, 14))

        buttons = tk.Frame(frame)
        buttons.pack()

        self.fail_button = tk.Button(
            buttons,
            text="Fail",
            command=lambda: self.record_result(False),
            state="disabled",
            width=14,
            height=2,
        )
        self.fail_button.grid(row=0, column=0, padx=12)

        self.pass_button = tk.Button(
            buttons,
            text="Pass",
            command=lambda: self.record_result(True),
            state="disabled",
            width=14,
            height=2,
        )
        self.pass_button.grid(row=0, column=1, padx=12)

        self.stats_var = tk.StringVar()
        tk.Label(
            frame,
            textvariable=self.stats_var,
            font=("Segoe UI", 10),
        ).pack(pady=(18, 0))

        self.bind("<space>", lambda _event: self.reveal_answer())
        self.bind("<Left>", lambda _event: self.record_result(False))
        self.bind("<Right>", lambda _event: self.record_result(True))

    def _on_confidence_slider(self, value: str) -> None:
        numeric = float(value)
        self.confidence_value_var.set(f"{numeric:.2f}")
        if self.require_confidence_var.get():
            self.apply_confidence_filter()

    def apply_confidence_filter(self) -> None:
        if not self.require_confidence_var.get():
            self.entries = list(self.all_entries)
        else:
            minimum = float(self.confidence_scale.get())
            filtered = []
            for item in self.all_entries:
                confidence = item.get("confidence")
                if confidence is None:
                    continue
                try:
                    confidence_value = float(confidence)
                except (TypeError, ValueError):
                    continue
                if confidence_value >= minimum:
                    filtered.append(item)
            self.entries = filtered

        if not self.entries:
            self.current = None
            self.progress_var.set("0 words match the current confidence filter")
            self.reading_var.set("")
            self.meaning_var.set("")
            self.answer_var.set("")
            self.stats_var.set("")
            self.reveal_button.config(state="disabled")
            self.pass_button.config(state="disabled")
            self.fail_button.config(state="disabled")
            return

        self.next_question()

    @staticmethod
    def _score(item: dict[str, Any]) -> dict[str, Any]:
        value = item.get("write_score")
        return value if isinstance(value, dict) else {}

    def _pick_entry(self) -> dict[str, Any]:
        if len(self.entries) == 1:
            return self.entries[0]

        candidates = [
            item for item in self.entries
            if (
                str(item.get("word") or ""),
                str(item.get("reading") or ""),
            ) != self.previous_key
        ]
        return random.choice(candidates or self.entries)

    def next_question(self) -> None:
        self.current = self._pick_entry()
        word = str(self.current.get("word") or "").strip()
        stored_reading = str(self.current.get("reading") or "").strip()
        self.previous_key = (word, stored_reading)

        dictionary_reading = self.dictionary.reading(word)
        self.reading_var.set(dictionary_reading or "Reading unavailable")

        meanings = [
            str(value).strip()
            for value in self.current.get("meanings", [])
            if str(value).strip()
        ]
        self.meaning_var.set(", ".join(meanings) if meanings else "")

        self.answer_revealed = False
        self.answer_var.set("")
        self.reveal_button.config(state="normal")
        self.pass_button.config(state="disabled")
        self.fail_button.config(state="disabled")

        score = self._score(self.current)
        attempts = int(score.get("attempts") or 0)
        passes = int(score.get("passes") or 0)
        fails = int(score.get("fails") or 0)
        value = score.get("score")
        score_text = "unreviewed" if value is None else f"{float(value):.1%}"
        self.stats_var.set(
            f"{attempts} attempts · {passes} passed · {fails} failed · "
            f"score {score_text}"
        )

        reviewed = sum(
            1 for item in self.entries if int(self._score(item).get("attempts") or 0) > 0
        )
        if self.require_confidence_var.get():
            minimum = float(self.confidence_scale.get())
            filter_text = f" · confidence ≥ {minimum:.2f}"
        else:
            filter_text = ""
        self.progress_var.set(
            f"{len(self.entries)} eligible writable words · {reviewed} reviewed{filter_text}"
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

        score = dict(self._score(self.current))
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
                f"The review result was not saved:\n{type(exc).__name__}: {exc}",
            )
            return

        self.next_question()


if __name__ == "__main__":
    app = WritingReview()
    if app.winfo_exists():
        app.mainloop()