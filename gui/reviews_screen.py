from __future__ import annotations

import tkinter as tk
from collections import Counter
from datetime import datetime, time, timedelta
from tkinter import ttk
from typing import Any

from .style import COLORS

from .shared import (
    ANKI_INDEX_PATH,
    BUNPRO_FALLBACK_PATH,
    BUNPRO_PRIMARY_PATH,
    WANIKANI_INDEX_PATH,
    load_json,
    parse_iso_datetime,
)


class ReviewsScreen(ttk.Frame):
    def __init__(self, parent) -> None:
        super().__init__(parent)

        self.figure = None
        self.canvas = None

        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(
            self,
            text="Upcoming Reviews",
            style="Heading.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            self,
            text=(
                "Reviews due across Anki, WaniKani, and Bunpro. "
                "The 24-hour view uses exact timestamps only. "
                "Day-only Anki review cards are included in daily views but "
                "excluded from the hourly graph."
            ),
            wraplength=820,
        ).pack(anchor="w", pady=(2, 14))

        controls = ttk.LabelFrame(self, text="Filters", padding=10)
        controls.pack(fill="x", pady=(0, 12))

        source_row = ttk.Frame(controls)
        source_row.pack(fill="x")

        self.review_anki_var = tk.BooleanVar(value=True)
        self.review_wanikani_var = tk.BooleanVar(value=True)
        self.review_bunpro_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(
            source_row,
            text="Anki",
            variable=self.review_anki_var,
            command=self.refresh_reviews,
        ).pack(side="left", padx=(0, 12))

        ttk.Checkbutton(
            source_row,
            text="WaniKani",
            variable=self.review_wanikani_var,
            command=self.refresh_reviews,
        ).pack(side="left", padx=(0, 12))

        ttk.Checkbutton(
            source_row,
            text="Bunpro",
            variable=self.review_bunpro_var,
            command=self.refresh_reviews,
        ).pack(side="left", padx=(0, 18))

        ttk.Label(source_row, text="Show:").pack(side="left")

        self.review_horizon_var = tk.StringVar(value="30 days")
        horizon = ttk.Combobox(
            source_row,
            textvariable=self.review_horizon_var,
            values=["24 hours", "7 days", "30 days", "90 days", "All"],
            state="readonly",
            width=10,
        )
        horizon.pack(side="left", padx=(6, 12))
        horizon.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.refresh_reviews(),
        )

        ttk.Button(
            source_row,
            text="Refresh",
            command=self.refresh_reviews,
        ).pack(side="right")

        mode_row = ttk.Frame(controls)
        mode_row.pack(fill="x", pady=(10, 0))

        self.show_total_var = tk.BooleanVar(value=True)
        self.running_sum_var = tk.BooleanVar(value=False)
        self.new_only_var = tk.BooleanVar(value=False)

        ttk.Checkbutton(
            mode_row,
            text="Show total line",
            variable=self.show_total_var,
            command=self.refresh_reviews,
        ).pack(side="left", padx=(0, 16))

        ttk.Checkbutton(
            mode_row,
            text="Running sum",
            variable=self.running_sum_var,
            command=self.refresh_reviews,
        ).pack(side="left", padx=(0, 16))

        ttk.Checkbutton(
            mode_row,
            text="New reviews only",
            variable=self.new_only_var,
            command=self.refresh_reviews,
        ).pack(side="left")

        self.review_summary_var = tk.StringVar()
        ttk.Label(
            self,
            textvariable=self.review_summary_var,
        ).pack(anchor="w", pady=(0, 8))

        self.graph_frame = ttk.Frame(self)
        self.graph_frame.pack(fill="both", expand=True)

        self.graph_message_var = tk.StringVar()
        self.graph_message = ttk.Label(
            self.graph_frame,
            textvariable=self.graph_message_var,
            justify="center",
        )
        self.graph_message.pack(expand=True)

    # ------------------------------------------------------------------
    # Review loading
    # ------------------------------------------------------------------
    def _load_anki_reviews(self) -> list[dict[str, Any]]:
        if not ANKI_INDEX_PATH.exists():
            return []

        data = load_json(ANKI_INDEX_PATH)
        reviews: list[dict[str, Any]] = []

        for note in data.get("notes", []):
            if not isinstance(note, dict):
                continue

            study = note.get("study") or {}
            if not isinstance(study, dict):
                continue

            # Time-specific Anki learning/relearning cards.
            due_at = parse_iso_datetime(study.get("due_at"))
            if due_at is not None:
                reviews.append(
                    {
                        "due": due_at,
                        "source": "Anki",
                        "exact": True,
                        "precision": "hour",
                    }
                )
                continue

            # Normal Anki review cards are scheduled by calendar day.
            due_date_text = study.get("due_date")
            if due_date_text:
                try:
                    due_date = datetime.fromisoformat(
                        str(due_date_text)
                    ).date()
                except ValueError:
                    due_date = None

                if due_date is not None:
                    reviews.append(
                        {
                            "due": datetime.combine(
                                due_date,
                                time.min,
                            ).astimezone(),
                            "source": "Anki",
                            "exact": True,
                            "precision": "day",
                        }
                    )

        return reviews

    def _load_wanikani_reviews(self) -> list[dict[str, Any]]:
        if not WANIKANI_INDEX_PATH.exists():
            return []

        data = load_json(WANIKANI_INDEX_PATH)
        reviews: list[dict[str, Any]] = []

        for subject in data.get("subjects", []):
            if not isinstance(subject, dict):
                continue

            assignment = subject.get("assignment") or {}
            if not isinstance(assignment, dict):
                continue

            if assignment.get("hidden"):
                continue

            if (
                assignment.get("burned_at")
                or int(assignment.get("srs_stage") or 0) >= 9
            ):
                continue

            due = parse_iso_datetime(assignment.get("available_at"))
            if due is None:
                continue

            reviews.append(
                {
                    "due": due,
                    "source": "WaniKani",
                    "exact": True,
                    "precision": "hour",
                }
            )

        return reviews

    def _load_bunpro_reviews(self) -> list[dict[str, Any]]:
        path = (
            BUNPRO_PRIMARY_PATH
            if BUNPRO_PRIMARY_PATH.exists()
            else BUNPRO_FALLBACK_PATH
        )

        if not path.exists():
            return []

        data = load_json(path)
        reviews: list[dict[str, Any]] = []

        for collection_name in ("grammar", "vocabulary"):
            for item in data.get(collection_name, []):
                if not isinstance(item, dict):
                    continue

                study = item.get("study") or {}
                if not isinstance(study, dict):
                    continue

                due = parse_iso_datetime(study.get("next_review"))
                if due is None:
                    continue

                reviews.append(
                    {
                        "due": due,
                        "source": "Bunpro",
                        "exact": True,
                        "precision": "hour",
                    }
                )

        return reviews

    def _selected_reviews(self) -> tuple[list[dict[str, Any]], list[str]]:
        reviews: list[dict[str, Any]] = []
        errors: list[str] = []

        loaders = []

        if self.review_anki_var.get():
            loaders.append(("Anki", self._load_anki_reviews))

        if self.review_wanikani_var.get():
            loaders.append(("WaniKani", self._load_wanikani_reviews))

        if self.review_bunpro_var.get():
            loaders.append(("Bunpro", self._load_bunpro_reviews))

        for source, loader in loaders:
            try:
                reviews.extend(loader())
            except Exception as exc:
                errors.append(
                    f"{source}: {type(exc).__name__}: {exc}"
                )

        return reviews, errors

    # ------------------------------------------------------------------
    # Graph ranges
    # ------------------------------------------------------------------
    def _is_hourly_view(self) -> bool:
        return self.review_horizon_var.get() == "24 hours"

    def _review_horizon_days(self) -> int | None:
        value = self.review_horizon_var.get()

        if value == "7 days":
            return 7
        if value == "30 days":
            return 30
        if value == "90 days":
            return 90

        return None

    @staticmethod
    def _hour_floor(value: datetime) -> datetime:
        local = value.astimezone()
        return local.replace(
            minute=0,
            second=0,
            microsecond=0,
        )

    def _hour_range(self) -> list[datetime]:
        start = self._hour_floor(datetime.now().astimezone())
        return [
            start + timedelta(hours=offset)
            for offset in range(25)
        ]

    def _date_range(
        self,
        reviews: list[dict[str, Any]],
    ) -> list:
        today = datetime.now().astimezone().date()
        horizon_days = self._review_horizon_days()

        if horizon_days is not None:
            return [
                today + timedelta(days=offset)
                for offset in range(horizon_days + 1)
            ]

        future_dates = [
            item["due"].astimezone().date()
            for item in reviews
            if item["due"].astimezone().date() >= today
        ]

        if not future_dates:
            return [today]

        last_date = max(future_dates)

        # Cap "All" at one year so a bad imported schedule cannot create
        # thousands of points.
        max_last_date = today + timedelta(days=365)
        last_date = min(last_date, max_last_date)

        days = (last_date - today).days

        return [
            today + timedelta(days=offset)
            for offset in range(days + 1)
        ]

    def _include_review_for_mode(
        self,
        item: dict[str, Any],
        *,
        now: datetime,
    ) -> bool:
        if self.new_only_var.get() and item["due"] < now:
            return False
        return True

    @staticmethod
    def _running(values: list[int]) -> list[int]:
        total = 0
        result = []
        for value in values:
            total += value
            result.append(total)
        return result

    def _series_values(
        self,
        counts: dict[str, Counter],
        buckets: list,
        source: str,
    ) -> list[int]:
        values = [counts[source][bucket] for bucket in buckets]
        if self.running_sum_var.get():
            values = self._running(values)
        return values

    def _total_values(
        self,
        counts: dict[str, Counter],
        buckets: list,
    ) -> list[int]:
        values = [
            sum(
                counts[source][bucket]
                for source in self._selected_source_names()
            )
            for bucket in buckets
        ]
        if self.running_sum_var.get():
            values = self._running(values)
        return values

    # ------------------------------------------------------------------
    # Graph drawing
    # ------------------------------------------------------------------
    def _prepare_canvas(self):
        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
        except ImportError:
            self.graph_message_var.set(
                "The review graph requires matplotlib.\n\n"
                "Install it with:\n"
                "python -m pip install matplotlib"
            )
            self.graph_message.pack(expand=True)
            return None, None, None

        self.graph_message.pack_forget()

        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None

        figure = Figure(figsize=(8.8, 5.4), dpi=100)
        axis = figure.add_subplot(111)
        figure.patch.set_facecolor(COLORS["bg"])
        axis.set_facecolor(COLORS["panel"])
        axis.tick_params(colors=COLORS["text"])
        axis.xaxis.label.set_color(COLORS["text"])
        axis.yaxis.label.set_color(COLORS["text"])
        axis.title.set_color(COLORS["text"])
        for spine in axis.spines.values():
            spine.set_color(COLORS["border"])

        return FigureCanvasTkAgg, figure, axis

    @staticmethod
    def _line_color(source: str) -> str:
        return {
            "WaniKani": COLORS["wanikani"],
            "Bunpro": COLORS["bunpro"],
            "Anki": COLORS["anki"],
            "Total": COLORS["total"],
        }.get(source, COLORS["text"])

    def _selected_source_names(self) -> list[str]:
        selected = []

        if self.review_anki_var.get():
            selected.append("Anki")

        if self.review_wanikani_var.get():
            selected.append("WaniKani")

        if self.review_bunpro_var.get():
            selected.append("Bunpro")

        return selected

    def _draw_hourly_graph(
        self,
        reviews: list[dict[str, Any]],
    ) -> None:
        FigureCanvasTkAgg, figure, axis = self._prepare_canvas()
        if figure is None:
            return

        hours = self._hour_range()
        start = hours[0]
        end = hours[-1]

        counts: dict[str, Counter] = {
            "Anki": Counter(),
            "WaniKani": Counter(),
            "Bunpro": Counter(),
        }

        now = datetime.now().astimezone()

        for item in reviews:
            # Only time-specific reviews belong on an hourly graph.
            if item.get("precision") != "hour":
                continue

            if not self._include_review_for_mode(item, now=now):
                continue

            due = item["due"].astimezone()

            if due < start:
                # In ordinary mode, overdue reviews are folded into the first
                # bucket. New-only mode has already excluded them above.
                bucket = start
            elif due <= end:
                bucket = self._hour_floor(due)
            else:
                continue

            counts[item["source"]][bucket] += 1

        for source in self._selected_source_names():
            values = self._series_values(counts, hours, source)
            axis.plot(
                hours,
                values,
                marker="o",
                markersize=3,
                linewidth=1.8,
                color=self._line_color(source),
                label=source,
            )

        if self.show_total_var.get():
            total_values = self._total_values(counts, hours)
            axis.plot(
                hours,
                total_values,
                linewidth=2.4,
                linestyle="-",
                color=self._line_color("Total"),
                label="Total",
            )

        axis.set_title(
            "Reviews becoming due in the next 24 hours"
            + (" — running sum" if self.running_sum_var.get() else "")
        )
        axis.set_xlabel("Hour")
        axis.set_ylabel(
            "Reviews accumulated"
            if self.running_sum_var.get()
            else "Reviews due"
        )
        axis.grid(True, alpha=0.25)
        legend = axis.legend()
        if legend is not None:
            legend.get_frame().set_facecolor(COLORS["panel_alt"])
            legend.get_frame().set_edgecolor(COLORS["border"])
            for item in legend.get_texts():
                item.set_color(COLORS["text"])
        axis.set_ylim(bottom=0)

        tick_hours = hours[::3]
        if hours[-1] not in tick_hours:
            tick_hours.append(hours[-1])

        axis.set_xticks(tick_hours)
        axis.set_xticklabels(
            [
                value.strftime("%a %H:%M")
                for value in tick_hours
            ],
            rotation=45,
            ha="right",
        )

        figure.tight_layout()

        self.figure = figure
        self.canvas = FigureCanvasTkAgg(
            figure,
            master=self.graph_frame,
        )
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(
            fill="both",
            expand=True,
        )

    def _draw_daily_graph(
        self,
        reviews: list[dict[str, Any]],
    ) -> None:
        FigureCanvasTkAgg, figure, axis = self._prepare_canvas()
        if figure is None:
            return

        dates = self._date_range(reviews)
        date_set = set(dates)

        counts: dict[str, Counter] = {
            "Anki": Counter(),
            "WaniKani": Counter(),
            "Bunpro": Counter(),
        }

        now = datetime.now().astimezone()
        today = now.date()

        for item in reviews:
            if not self._include_review_for_mode(item, now=now):
                continue

            due_date = item["due"].astimezone().date()
            graph_date = today if due_date < today else due_date

            if graph_date in date_set:
                counts[item["source"]][graph_date] += 1

        for source in self._selected_source_names():
            values = self._series_values(counts, dates, source)
            axis.plot(
                dates,
                values,
                marker="o",
                markersize=3,
                linewidth=1.8,
                color=self._line_color(source),
                label=source,
            )

        if self.show_total_var.get():
            total_values = self._total_values(counts, dates)
            axis.plot(
                dates,
                total_values,
                linewidth=2.4,
                linestyle="-",
                color=self._line_color("Total"),
                label="Total",
            )

        axis.set_title(
            "Upcoming reviews by day"
            + (" — running sum" if self.running_sum_var.get() else "")
        )
        axis.set_xlabel("Date")
        axis.set_ylabel(
            "Reviews accumulated"
            if self.running_sum_var.get()
            else "Reviews due"
        )
        axis.grid(True, alpha=0.25)
        legend = axis.legend()
        if legend is not None:
            legend.get_frame().set_facecolor(COLORS["panel_alt"])
            legend.get_frame().set_edgecolor(COLORS["border"])
            for item in legend.get_texts():
                item.set_color(COLORS["text"])
        axis.set_ylim(bottom=0)

        if len(dates) <= 10:
            tick_step = 1
        elif len(dates) <= 35:
            tick_step = 3
        elif len(dates) <= 100:
            tick_step = 7
        else:
            tick_step = 14

        tick_dates = dates[::tick_step]

        if dates[-1] not in tick_dates:
            tick_dates.append(dates[-1])

        axis.set_xticks(tick_dates)
        axis.set_xticklabels(
            [
                date.strftime("%b %d")
                for date in tick_dates
            ],
            rotation=45,
            ha="right",
        )

        figure.tight_layout()

        self.figure = figure
        self.canvas = FigureCanvasTkAgg(
            figure,
            master=self.graph_frame,
        )
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(
            fill="both",
            expand=True,
        )

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------
    def refresh_reviews(self) -> None:
        reviews, errors = self._selected_reviews()
        now = datetime.now().astimezone()

        if self._is_hourly_view():
            start = self._hour_floor(now)
            end = start + timedelta(hours=24)

            exact_hourly = [
                item
                for item in reviews
                if item.get("precision") == "hour"
                and item["due"] <= end
                and self._include_review_for_mode(item, now=now)
            ]

            day_only_anki = sum(
                1
                for item in reviews
                if item["source"] == "Anki"
                and item.get("precision") == "day"
            )

            by_source = Counter(
                item["source"]
                for item in exact_hourly
            )

            due_now = sum(
                1
                for item in exact_hourly
                if item["due"] <= now
            )

            parts = [
                f"{len(exact_hourly)} hourly-scheduled reviews",
                f"{due_now} due now",
            ]

            for source in self._selected_source_names():
                parts.append(
                    f"{source}: {by_source[source]}"
                )

            if (
                self.review_anki_var.get()
                and day_only_anki
            ):
                parts.append(
                    f"{day_only_anki} Anki day-only reviews omitted from hourly view"
                )

            if self.running_sum_var.get():
                parts.append("running sum")
            if self.new_only_var.get():
                parts.append("new reviews only")
            if self.show_total_var.get():
                parts.append("total line shown")

            if errors:
                parts.extend(errors)

            self.review_summary_var.set(" · ".join(parts))
            self._draw_hourly_graph(exact_hourly)
            return

        horizon_days = self._review_horizon_days()

        if horizon_days is None:
            visible = reviews
        else:
            cutoff = now + timedelta(days=horizon_days)
            visible = [
                item
                for item in reviews
                if item["due"] <= cutoff
            ]

        if self.new_only_var.get():
            visible = [
                item
                for item in visible
                if item["due"] >= now
            ]

        due_now = sum(
            1
            for item in visible
            if item["due"] <= now
        )

        by_source = Counter(
            item["source"]
            for item in visible
        )

        parts = [
            f"{len(visible)} reviews",
            f"{due_now} due now",
        ]

        for source in self._selected_source_names():
            parts.append(
                f"{source}: {by_source[source]}"
            )

        if self.running_sum_var.get():
            parts.append("running sum")
        if self.new_only_var.get():
            parts.append("new reviews only")
        if self.show_total_var.get():
            parts.append("total line shown")

        if errors:
            parts.extend(errors)

        self.review_summary_var.set(" · ".join(parts))
        self._draw_daily_graph(visible)
