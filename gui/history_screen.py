from __future__ import annotations

import math
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from history.progress_series import (
    ANKI_STATES,
    BUNPRO_STAGES,
    WANIKANI_STAGES,
    WRITING_STAGES,
    available_anki_decks,
    build_series,
)
from .shared import SRS_HISTORY_PATH, load_json
from .style import (
    ANKI_STAGE_STYLES,
    BUNPRO_STAGE_STYLES,
    COLORS,
    WANIKANI_STAGE_STYLES,
)


DISPLAY_NAMES = {
    "lesson": "Lesson",
    "apprentice_1": "Apprentice 1",
    "apprentice_2": "Apprentice 2",
    "apprentice_3": "Apprentice 3",
    "apprentice_4": "Apprentice 4",
    "guru_1": "Guru 1",
    "guru_2": "Guru 2",
    "master": "Master",
    "enlightened": "Enlightened",
    "burned": "Burned",
    "new": "New",
    "learning": "Learning",
    "relearning": "Relearning",
    "review": "Review",
    "beginner": "Beginner",
    "adept": "Adept",
    "seasoned": "Seasoned",
    "expert": "Expert",
    "ghost": "Ghost",
    "self_study": "Self Study",
    "new_active": "New",
    "stage_1": "Stage 1",
    "stage_2": "Stage 2",
    "stage_3": "Stage 3",
    "stage_4": "Stage 4",
    "stage_5": "Stage 5",
    "stage_6": "Stage 6",
    "stage_7": "Stage 7",
    "stage_8": "Stage 8",
}

SOURCE_LABELS = {
    "wanikani": "WaniKani",
    "anki": "Anki",
    "bunpro": "Bunpro",
    "writing": "Writing",
}


class HistoryScreen(ttk.Frame):
    def __init__(self, parent) -> None:
        super().__init__(parent)

        self.history: dict[str, Any] = {}
        self.canvas = None

        self.source_var = tk.StringVar(value="wanikani")
        self.selection_var = tk.StringVar(value="Total")
        self.bunpro_type_var = tk.StringVar(value="Grammar")
        self.anki_include_new_var = tk.BooleanVar(value=False)

        self._build_ui()
        self.refresh_history(show_errors=False)

    def _build_ui(self) -> None:
        ttk.Label(
            self,
            text="SRS History",
            style="Heading.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            self,
            text=(
                "Track how the distribution of items across each source's "
                "native SRS levels changes over time."
            ),
            wraplength=800,
        ).pack(anchor="w", pady=(2, 14))

        controls = ttk.Frame(self)
        controls.pack(fill="x", pady=(0, 12))

        ttk.Label(controls, text="Source:").pack(side="left")

        for value, label in (
            ("wanikani", "WaniKani"),
            ("anki", "Anki"),
            ("bunpro", "Bunpro"),
            ("writing", "Writing"),
        ):
            ttk.Radiobutton(
                controls,
                text=label,
                variable=self.source_var,
                value=value,
                command=self._source_changed,
            ).pack(side="left", padx=(8, 0))

        ttk.Label(
            controls,
            text="View:",
        ).pack(side="left", padx=(26, 6))

        self.selection_combo = ttk.Combobox(
            controls,
            textvariable=self.selection_var,
            state="readonly",
            width=30,
        )
        self.selection_combo.pack(side="left")
        self.selection_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.refresh_graph(),
        )

        self.bunpro_type_label = ttk.Label(
            controls,
            text="Content:",
        )
        self.bunpro_type_combo = ttk.Combobox(
            controls,
            textvariable=self.bunpro_type_var,
            values=["Grammar", "Vocabulary", "Both"],
            state="readonly",
            width=12,
        )
        self.bunpro_type_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.refresh_graph(),
        )

        self.anki_new_toggle = ttk.Checkbutton(
            controls,
            text="Include New",
            variable=self.anki_include_new_var,
            command=self.refresh_graph,
        )

        ttk.Button(
            controls,
            text="Refresh",
            command=self.refresh_history,
        ).pack(side="right")

        self.status_var = tk.StringVar(value="")
        ttk.Label(
            self,
            textvariable=self.status_var,
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        self.graph_frame = ttk.Frame(self)
        self.graph_frame.pack(fill="both", expand=True)

    def refresh_history(self, *, show_errors: bool = True) -> None:
        try:
            self.history = (
                load_json(SRS_HISTORY_PATH)
                if SRS_HISTORY_PATH.exists()
                else {"schema_version": 1, "days": {}}
            )
        except Exception as exc:
            self.history = {"schema_version": 1, "days": {}}
            if show_errors:
                messagebox.showerror(
                    "SRS History",
                    f"Could not load SRS history:\n"
                    f"{type(exc).__name__}: {exc}",
                )

        self._configure_selection()
        self.refresh_graph()

    def _source_changed(self) -> None:
        self.selection_var.set("Total")
        if self.source_var.get() == "bunpro":
            self.bunpro_type_var.set("Grammar")
        self._configure_selection()
        self.refresh_graph()

    def _configure_selection(self) -> None:
        source = self.source_var.get()

        if source == "wanikani":
            values = [
                "Total",
                "kana_vocabulary",
                "radical",
                "vocabulary",
                "kanji",
            ]
            state = "readonly"
        elif source == "anki":
            values = ["Total"] + available_anki_decks(self.history)
            state = "readonly"
        elif source == "bunpro":
            values = ["Total", "N5", "N4", "N3", "N2", "N1"]
            state = "readonly"
        else:
            values = ["Total"]
            state = "disabled"

        self.selection_combo["values"] = values
        self.selection_combo.config(state=state)

        if source == "bunpro":
            self.bunpro_type_label.pack(side="left", padx=(18, 6))
            self.bunpro_type_combo.pack(side="left")
        else:
            self.bunpro_type_label.pack_forget()
            self.bunpro_type_combo.pack_forget()

        if source == "anki":
            self.anki_new_toggle.pack(side="left", padx=(18, 0))
        else:
            self.anki_new_toggle.pack_forget()

        if self.selection_var.get() not in values:
            self.selection_var.set("Total")

    def _clear_graph(self) -> None:
        if self.canvas is not None:
            try:
                self.canvas.get_tk_widget().destroy()
            except Exception:
                pass
            self.canvas = None

        for child in self.graph_frame.winfo_children():
            child.destroy()

    def _prepare_canvas(self):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        figure = Figure(figsize=(9.0, 5.7), dpi=100)
        axis = figure.add_subplot(111)

        figure.patch.set_facecolor(COLORS["bg"])
        axis.set_facecolor(COLORS["panel"])
        axis.tick_params(colors=COLORS["text"])
        axis.xaxis.label.set_color(COLORS["text"])
        axis.yaxis.label.set_color(COLORS["text"])
        axis.title.set_color(COLORS["text"])

        for spine in axis.spines.values():
            spine.set_color(COLORS["border"])

        axis.grid(
            True,
            axis="y",
            alpha=0.18,
        )

        return FigureCanvasTkAgg, figure, axis

    @staticmethod
    def _date_labels(dates: list[str]) -> list[str]:
        labels = []
        for value in dates:
            try:
                parsed = datetime.strptime(value, "%Y-%m-%d")
                labels.append(f"{parsed.strftime('%b')} {parsed.day}")
            except ValueError:
                labels.append(value)
        return labels

    @staticmethod
    def _series_style(source: str, stage: str) -> dict[str, str]:
        if source == "wanikani":
            return WANIKANI_STAGE_STYLES.get(stage, {})
        if source == "anki":
            return ANKI_STAGE_STYLES.get(stage, {})
        if source == "bunpro":
            return BUNPRO_STAGE_STYLES.get(stage, {})
        return {}

    def refresh_graph(self) -> None:
        self._clear_graph()

        source = self.source_var.get()
        selection = self.selection_var.get() or "Total"

        days = self.history.get("days") or {}
        if not days:
            self.status_var.set("No history has been recorded yet.")
            ttk.Label(
                self.graph_frame,
                text="No SRS history available yet.",
                style="Subheading.TLabel",
            ).pack(expand=True)
            return

        try:
            dates, series = build_series(
                self.history,
                source,
                selection,
                bunpro_content_type=self.bunpro_type_var.get().lower(),
            )
        except Exception as exc:
            self.status_var.set("Could not build history graph.")
            ttk.Label(
                self.graph_frame,
                text=f"{type(exc).__name__}: {exc}",
            ).pack(expand=True)
            return

        FigureCanvasTkAgg, figure, axis = self._prepare_canvas()

        labels = self._date_labels(dates)
        x_values = list(range(len(dates)))

        plotted = 0
        for stage, values in series.items():
            if (
                source == "anki"
                and stage == "new"
                and not self.anki_include_new_var.get()
            ):
                continue

            numeric = [
                math.nan if value is None else value
                for value in values
            ]

            if all(math.isnan(value) for value in numeric):
                continue

            line_style = self._series_style(source, stage)
            axis.plot(
                x_values,
                numeric,
                marker="o",
                linewidth=2,
                color=line_style.get("color"),
                linestyle=line_style.get("linestyle", "-"),
                label=DISPLAY_NAMES.get(stage, stage),
            )
            plotted += 1

        title = SOURCE_LABELS.get(source, source.title())
        if source == "bunpro":
            title += f" · {self.bunpro_type_var.get()} · {selection}"
        elif source != "writing":
            title += f" · {selection}"

        axis.set_title(
            title,
            fontfamily="Yu Gothic UI",
        )
        axis.set_ylabel("Items")
        axis.set_xlabel("Date")

        axis.set_xticks(x_values)
        axis.set_xticklabels(
            labels,
            rotation=35 if len(labels) > 8 else 0,
            ha="right" if len(labels) > 8 else "center",
            fontfamily="Yu Gothic UI",
        )

        if plotted:
            legend = axis.legend(
                loc="upper left",
                ncol=2,
            )
            legend.get_frame().set_facecolor(COLORS["panel_alt"])
            legend.get_frame().set_edgecolor(COLORS["border"])
            for item in legend.get_texts():
                item.set_color(COLORS["text"])
                item.set_fontfamily("Yu Gothic UI")
        else:
            axis.text(
                0.5,
                0.5,
                "No data available for this selection.",
                transform=axis.transAxes,
                ha="center",
                va="center",
                color=COLORS["muted"],
            )

        figure.tight_layout()

        self.canvas = FigureCanvasTkAgg(
            figure,
            master=self.graph_frame,
        )
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(
            fill="both",
            expand=True,
        )

        self.status_var.set(
            f"{len(dates)} day"
            + ("" if len(dates) == 1 else "s")
            + " recorded"
        )
