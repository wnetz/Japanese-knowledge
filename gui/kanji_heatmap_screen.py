from __future__ import annotations

import tkinter as tk
from collections import defaultdict
from tkinter import ttk
from typing import Any

from .shared import VOCABULARY_PROFILE_PATH, has_kanji, load_json
from .style import COLORS, style_canvas


def kanji_characters(value: str) -> list[str]:
    result = []
    seen = set()

    for char in value:
        code = ord(char)
        is_kanji = (
            0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF
        )

        if is_kanji and char not in seen:
            result.append(char)
            seen.add(char)

    return result


class KanjiHeatmapScreen(ttk.Frame):
    def __init__(self, parent) -> None:
        super().__init__(parent)

        self.kanji_data: list[dict[str, Any]] = []
        self.visible_data: list[dict[str, Any]] = []

        self.cell_size = 34
        self.cell_gap = 3
        self.columns = 18

        self._build_ui()
        self.refresh_heatmap()

    def _build_ui(self) -> None:
        ttk.Label(
            self,
            text="Kanji Heatmap",
            style="Heading.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            self,
            text=(
                "Each kanji is scored from vocabulary_profile.json. "
                "Its score is the average confidence of scored vocabulary "
                "entries containing that kanji."
            ),
            wraplength=820,
        ).pack(anchor="w", pady=(2, 14))

        controls = ttk.LabelFrame(
            self,
            text="Filters",
            padding=10,
        )
        controls.pack(fill="x", pady=(0, 12))

        row = ttk.Frame(controls)
        row.pack(fill="x")

        self.writable_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            row,
            text="Writable kanji only",
            variable=self.writable_only_var,
            command=self._apply_filters,
        ).pack(side="left", padx=(0, 16))

        self.scored_only_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            row,
            text="Scored only",
            variable=self.scored_only_var,
            command=self._apply_filters,
        ).pack(side="left")

        ttk.Button(
            row,
            text="Refresh",
            command=self.refresh_heatmap,
        ).pack(side="right")

        self.summary_var = tk.StringVar()
        ttk.Label(
            self,
            textvariable=self.summary_var,
        ).pack(anchor="w", pady=(0, 8))

        legend = ttk.Frame(self)
        legend.pack(fill="x", pady=(0, 8))

        ttk.Label(
            legend,
            text="Lower confidence",
        ).pack(side="left")

        self.legend_canvas = tk.Canvas(
            legend,
            width=260,
            height=18,
            highlightthickness=0,
        )
        self.legend_canvas.pack(side="left", padx=8)
        style_canvas(self.legend_canvas, panel=True)

        ttk.Label(
            legend,
            text="Higher confidence",
        ).pack(side="left")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            body,
            highlightthickness=0,
        )

        yscroll = ttk.Scrollbar(
            body,
            orient="vertical",
            command=self.canvas.yview,
        )

        self.canvas.configure(
            yscrollcommand=yscroll.set,
        )

        style_canvas(self.canvas, panel=True)
        self.canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        yscroll.pack(
            side="right",
            fill="y",
        )

        self.canvas.bind(
            "<Configure>",
            self._on_canvas_resize,
        )

        self.canvas.bind(
            "<Motion>",
            self._on_mouse_move,
        )

        self.canvas.bind(
            "<Leave>",
            lambda _event: self._hide_tooltip(),
        )

        # Scroll the heatmap with the mouse wheel whenever the pointer is
        # hovering over the canvas. Windows/macOS use <MouseWheel>; Linux
        # commonly reports wheel movement as Button-4 / Button-5.
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)

        self.tooltip = tk.Toplevel(self)
        self.tooltip.withdraw()
        self.tooltip.overrideredirect(True)

        self.tooltip_label = tk.Label(
            self.tooltip,
            justify="left",
            relief="solid",
            borderwidth=1,
            padx=7,
            pady=5,
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
        )
        self.tooltip_label.pack()

        self._draw_legend()

    def _draw_legend(self) -> None:
        self.legend_canvas.delete("all")

        width = 250
        steps = 50

        for index in range(steps):
            score = index / (steps - 1)
            color = self._color_for_score(score)

            x1 = index * width / steps
            x2 = (index + 1) * width / steps

            self.legend_canvas.create_rectangle(
                x1,
                2,
                x2 + 1,
                16,
                fill=color,
                outline=color,
            )

    @staticmethod
    def _color_for_score(score: float | None) -> str:
        """Map confidence continuously through the requested heatmap scale."""
        if score is None:
            return "#ffffff"

        score = max(0.0, min(1.0, float(score)))

        # 0 confidence is white.
        if score <= 0.0:
            return "#ffffff"

        # Any nonzero score below 0.20 is red.
        if score < 0.20:
            return "#ff0000"

        # Continuous interpolation:
        # 0.20 -> 0.40 : red -> orange
        # 0.40 -> 0.60 : orange -> yellow
        # 0.60 -> 0.80 : yellow -> green
        # 0.80 -> 1.00 : green -> cyan
        stops = (
            (0.20, (255, 0, 0)),
            (0.40, (255, 165, 0)),
            (0.60, (255, 255, 0)),
            (0.80, (0, 200, 0)),
            (1.00, (0, 255, 255)),
        )

        for index in range(len(stops) - 1):
            left_pos, left_color = stops[index]
            right_pos, right_color = stops[index + 1]

            if left_pos <= score <= right_pos:
                amount = (score - left_pos) / (right_pos - left_pos)

                red = round(
                    left_color[0]
                    + (right_color[0] - left_color[0]) * amount
                )
                green = round(
                    left_color[1]
                    + (right_color[1] - left_color[1]) * amount
                )
                blue = round(
                    left_color[2]
                    + (right_color[2] - left_color[2]) * amount
                )

                return f"#{red:02x}{green:02x}{blue:02x}"

        return "#00ffff"

    @staticmethod
    def _text_color(score: float | None) -> str:
        return "black"

    def refresh_heatmap(self) -> None:
        if not VOCABULARY_PROFILE_PATH.exists():
            self.kanji_data = []
            self.visible_data = []
            self.summary_var.set(
                "vocabulary_profile.json was not found."
            )
            self._draw_heatmap()
            return

        profile = load_json(VOCABULARY_PROFILE_PATH)

        scores: dict[str, list[float]] = defaultdict(list)
        words: dict[str, set[str]] = defaultdict(set)
        writable: dict[str, bool] = defaultdict(bool)

        for item in profile.get("vocabulary", []):
            if not isinstance(item, dict):
                continue

            word = str(item.get("word") or "").strip()
            if not word or not has_kanji(word):
                continue

            characters = kanji_characters(word)

            confidence = item.get("confidence")
            numeric_confidence: float | None = None

            if confidence is not None:
                try:
                    numeric_confidence = float(confidence)
                except (TypeError, ValueError):
                    numeric_confidence = None

            for char in characters:
                words[char].add(word)

                if numeric_confidence is not None:
                    scores[char].append(numeric_confidence)

                if item.get("writable") is True:
                    writable[char] = True

        all_kanji = set(words) | set(scores)

        data = []

        for char in all_kanji:
            values = scores.get(char, [])

            score = (
                round(sum(values) / len(values), 4)
                if values
                else None
            )

            data.append(
                {
                    "character": char,
                    "score": score,
                    "sample_count": len(values),
                    "word_count": len(words.get(char, set())),
                    "writable": bool(writable.get(char)),
                    "examples": sorted(words.get(char, set()))[:8],
                }
            )

        # Strongest kanji first by default, then character for stability.
        data.sort(
            key=lambda item: (
                -(item["score"] if item["score"] is not None else -1),
                item["character"],
            )
        )

        self.kanji_data = data
        self._apply_filters()

    def _apply_filters(self) -> None:
        writable_only = self.writable_only_var.get()
        scored_only = self.scored_only_var.get()

        visible = []

        for item in self.kanji_data:
            score = item["score"]

            if scored_only and score is None:
                continue

            if writable_only and not item["writable"]:
                continue

            visible.append(item)

        self.visible_data = visible

        scored = sum(
            1
            for item in self.kanji_data
            if item["score"] is not None
        )

        writable = sum(
            1
            for item in self.kanji_data
            if item["writable"]
        )

        self.summary_var.set(
            f"{len(self.visible_data)} shown · "
            f"{len(self.kanji_data)} total kanji · "
            f"{scored} scored · "
            f"{writable} writable"
        )

        self._draw_heatmap()

    def _on_canvas_resize(self, event) -> None:
        available = max(1, event.width)

        self.columns = max(
            4,
            available // (self.cell_size + self.cell_gap),
        )

        self._draw_heatmap()

    def _draw_heatmap(self) -> None:
        self.canvas.delete("all")

        if not self.visible_data:
            self.canvas.create_text(
                20,
                20,
                anchor="nw",
                text="No kanji match the current filters.",
            )
            self.canvas.configure(
                scrollregion=(0, 0, 1, 60)
            )
            return

        cell = self.cell_size
        gap = self.cell_gap

        for index, item in enumerate(self.visible_data):
            row = index // self.columns
            column = index % self.columns

            x1 = column * (cell + gap) + gap
            y1 = row * (cell + gap) + gap
            x2 = x1 + cell
            y2 = y1 + cell

            color = self._color_for_score(item["score"])

            rect = self.canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=color,
                outline="#9ca3af",
                width=1,
                tags=(f"cell_{index}",),
            )

            text = self.canvas.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=item["character"],
                font=("Yu Gothic UI", 14, "bold"),
                fill=self._text_color(item["score"]),
                tags=(f"cell_{index}",),
            )

            self.canvas.tag_bind(
                rect,
                "<Button-1>",
                lambda _event, i=index: self._show_details(i),
            )

            self.canvas.tag_bind(
                text,
                "<Button-1>",
                lambda _event, i=index: self._show_details(i),
            )

        rows = (
            len(self.visible_data) + self.columns - 1
        ) // self.columns

        height = rows * (cell + gap) + gap

        self.canvas.configure(
            scrollregion=(0, 0, self.canvas.winfo_width(), height)
        )

    def _cell_index_at(self, x: int, y: int) -> int | None:
        cell_span = self.cell_size + self.cell_gap

        column = x // cell_span
        row = y // cell_span

        if column >= self.columns:
            return None

        index = row * self.columns + column

        if index < 0 or index >= len(self.visible_data):
            return None

        return index

    def _on_mousewheel(self, event) -> str:
        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            delta = getattr(event, "delta", 0)
            if delta == 0:
                return "break"

            # Windows typically reports +/-120 per wheel notch. macOS can
            # report smaller values, so always move at least one unit.
            units = -int(delta / 120)
            if units == 0:
                units = -1 if delta > 0 else 1

            units *= 3

        self.canvas.yview_scroll(units, "units")
        self._hide_tooltip()
        return "break"

    def _on_mouse_move(self, event) -> None:
        canvas_y = int(self.canvas.canvasy(event.y))
        canvas_x = int(self.canvas.canvasx(event.x))

        index = self._cell_index_at(
            canvas_x,
            canvas_y,
        )

        if index is None:
            self._hide_tooltip()
            return

        item = self.visible_data[index]

        score_text = (
            "Unscored"
            if item["score"] is None
            else f"{item['score']:.1%}"
        )

        self.tooltip_label.config(
            text=(
                f"{item['character']}\n"
                f"Confidence: {score_text}\n"
                f"Scored vocab: {item['sample_count']}\n"
                f"Vocabulary words: {item['word_count']}\n"
                f"Writable: {'Yes' if item['writable'] else 'No'}"
            )
        )

        self.tooltip.geometry(
            f"+{self.winfo_pointerx() + 12}"
            f"+{self.winfo_pointery() + 12}"
        )

        self.tooltip.deiconify()

    def _hide_tooltip(self) -> None:
        self.tooltip.withdraw()

    def _show_details(self, index: int) -> None:
        if index < 0 or index >= len(self.visible_data):
            return

        item = self.visible_data[index]

        score_text = (
            "Unscored"
            if item["score"] is None
            else f"{item['score']:.1%}"
        )

        examples = "\n".join(
            item["examples"]
        ) or "None"

        window = tk.Toplevel(self)
        window.title(f"Kanji {item['character']}")
        window.geometry("360x320")

        content = ttk.Frame(
            window,
            padding=18,
        )
        content.pack(fill="both", expand=True)

        ttk.Label(
            content,
            text=item["character"],
            font=("Yu Gothic UI", 42, "bold"),
        ).pack()

        ttk.Label(
            content,
            text=f"Confidence: {score_text}",
        ).pack(pady=(8, 2))

        ttk.Label(
            content,
            text=(
                f"Scored vocabulary entries: "
                f"{item['sample_count']}"
            ),
        ).pack()

        ttk.Label(
            content,
            text=(
                f"Writable: "
                f"{'Yes' if item['writable'] else 'No'}"
            ),
        ).pack(pady=(2, 10))

        ttk.Label(
            content,
            text="Example vocabulary",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            content,
            text=examples,
            justify="left",
            wraplength=300,
        ).pack(anchor="w", pady=(4, 0))
