from __future__ import annotations

import tkinter as tk
import re
import time
from collections import Counter
from datetime import date, datetime
from tkinter import messagebox, ttk

from goals.tracker import (
    completed_goal_ids,
    ensure_goal_file,
    goals_for_date,
    save_day_record,
)

from .daily_goals_screen import HoverTooltip
from .reviews_screen import ReviewsScreen
from .shared import DAILY_GOALS_PATH, DAILY_GOAL_SCHEDULE_PATH
from .style import TIMER_SEGMENT_COLORS


class SegmentTimerDisplay(tk.Canvas):
    """Compact digital countdown rendered with segmented numerals."""

    DIGIT_SEGMENTS = {
        "0": "abcdef",
        "1": "bc",
        "2": "abdeg",
        "3": "abcdg",
        "4": "bcfg",
        "5": "acdfg",
        "6": "acdefg",
        "7": "abc",
        "8": "abcdefg",
        "9": "abcdfg",
    }

    def __init__(self, parent) -> None:
        super().__init__(
            parent,
            width=104,
            height=34,
            bg=TIMER_SEGMENT_COLORS["background"],
            highlightthickness=0,
            borderwidth=0,
        )
        self._value = "00:00"
        self.bind("<Configure>", lambda _event: self._draw())
        self._draw()

    def set_value(self, value: str) -> None:
        self._value = value
        self._draw()

    @staticmethod
    def _segment_points(
        x: float,
        y: float,
        width: float,
        height: float,
        thickness: float,
    ) -> dict[str, tuple[float, ...]]:
        # Classic digital display geometry. The visual reads as an
        # eight-segment-style timer face; the colon is drawn separately.
        mid = y + height / 2
        right = x + width
        bottom = y + height
        half = thickness / 2

        return {
            "a": (x + thickness, y, right - thickness, y + thickness),
            "b": (right - thickness, y + thickness, right, mid - half),
            "c": (right - thickness, mid + half, right, bottom - thickness),
            "d": (x + thickness, bottom - thickness, right - thickness, bottom),
            "e": (x, mid + half, x + thickness, bottom - thickness),
            "f": (x, y + thickness, x + thickness, mid - half),
            "g": (
                x + thickness,
                mid - half,
                right - thickness,
                mid + half,
            ),
        }

    def _draw_digit(
        self,
        digit: str,
        x: float,
        y: float,
        width: float,
        height: float,
        thickness: float,
    ) -> None:
        active = self.DIGIT_SEGMENTS.get(digit, "")
        segments = self._segment_points(x, y, width, height, thickness)

        for name, points in segments.items():
            self.create_rectangle(
                *points,
                fill=(
                    TIMER_SEGMENT_COLORS["on"]
                    if name in active
                    else TIMER_SEGMENT_COLORS["off"]
                ),
                outline="",
            )

    def _draw(self) -> None:
        self.delete("all")
        value = self._value if len(self._value) == 5 else "00:00"

        digit_width = 18
        digit_height = 28
        thickness = 4
        y = 3
        x_positions = [3, 25, 59, 81]

        digits = [value[0], value[1], value[3], value[4]]
        for digit, x in zip(digits, x_positions):
            self._draw_digit(
                digit,
                x,
                y,
                digit_width,
                digit_height,
                thickness,
            )

        colon_x = 52
        for colon_y in (12, 22):
            self.create_oval(
                colon_x - 2,
                colon_y - 2,
                colon_x + 2,
                colon_y + 2,
                fill=TIMER_SEGMENT_COLORS["on"],
                outline="",
            )


class HomeReviewsGraph(ReviewsScreen):
    """Upcoming-review graph with the Home page's fixed filter set."""

    def _build_ui(self) -> None:
        # These intentionally mirror the requested Upcoming Reviews defaults.
        # Home exposes no controls for changing them.
        self.review_anki_var = tk.BooleanVar(value=True)
        self.review_wanikani_var = tk.BooleanVar(value=True)
        self.review_bunpro_var = tk.BooleanVar(value=True)
        self.review_writing_var = tk.BooleanVar(value=True)
        self.review_horizon_var = tk.StringVar(value="24 hours")
        self.show_total_var = tk.BooleanVar(value=False)
        self.running_sum_var = tk.BooleanVar(value=False)
        self.new_only_var = tk.BooleanVar(value=True)

        self.review_summary_var = tk.StringVar()
        self.graph_message_var = tk.StringVar()

        self.graph_frame = ttk.Frame(self)
        self.graph_frame.pack(fill="both", expand=True)

        self.graph_message = ttk.Label(
            self.graph_frame,
            textvariable=self.graph_message_var,
            justify="center",
        )
        self.graph_message.pack(expand=True)

    def _draw_hourly_graph(self, reviews) -> None:
        """Draw Home's fixed 24-hour review view as stacked source bars."""
        FigureCanvasTkAgg, figure, axis = self._prepare_canvas()
        if figure is None:
            return

        hours = self._hour_range()
        start = hours[0]
        end = hours[-1]

        counts = {
            "Anki": Counter(),
            "WaniKani": Counter(),
            "Bunpro": Counter(),
            "Writing": Counter(),
        }

        now = datetime.now().astimezone()

        for item in reviews:
            if item.get("precision") != "hour":
                continue
            if not self._include_review_for_mode(item, now=now):
                continue

            due = item["due"].astimezone()
            if due < start:
                bucket = start
            elif due <= end:
                bucket = self._hour_floor(due)
            else:
                continue

            counts[item["source"]][bucket] += 1

        bottoms = [0] * len(hours)

        # Matplotlib stacks later series on top, so draw bottom -> top.
        stack_order = ["Writing", "Bunpro", "WaniKani", "Anki"]
        selected_sources = set(self._selected_source_names())

        for source in stack_order:
            if source not in selected_sources:
                continue

            values = [
                counts[source].get(hour, 0)
                for hour in hours
            ]
            axis.bar(
                hours,
                values,
                bottom=bottoms,
                width=0.032,
                color=self._line_color(source),
                label=source,
                align="center",
            )
            bottoms = [
                bottom + value
                for bottom, value in zip(bottoms, values)
            ]

        axis.set_title("Reviews becoming due in the next 24 hours")
        axis.set_xlabel("Hour")
        axis.set_ylabel("Reviews due")
        axis.grid(True, axis="y", alpha=0.25)

        # Matplotlib's legend follows draw order (bottom -> top). Reverse it
        # so the key visually matches the stack from top -> bottom.
        handles, labels = axis.get_legend_handles_labels()
        legend = axis.legend(handles[::-1], labels[::-1])
        if legend is not None:
            from .style import COLORS
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


class HomeScreen(ttk.Frame):
    def __init__(self, parent) -> None:
        super().__init__(parent)

        self.goal_vars: dict[str, tk.BooleanVar] = {}

        # Timer state is kept independently of the rendered goal rows so a
        # checkbox autosave/refresh does not reset an active countdown.
        self.timer_state: dict[str, dict] = {}
        self.timer_widgets: dict[str, dict] = {}
        self.timer_day: str | None = None
        self._timer_after_id: str | None = None

        self.data = ensure_goal_file(
            DAILY_GOALS_PATH,
            schedule_path=DAILY_GOAL_SCHEDULE_PATH,
        )

        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(
            self,
            text="Home",
            style="Heading.TLabel",
        ).pack(anchor="w")

        goals_panel = ttk.LabelFrame(
            self,
            text="Today's Goals",
            padding=12,
        )
        goals_panel.pack(fill="x", pady=(12, 12))

        self.goals_frame = ttk.Frame(goals_panel)
        self.goals_frame.pack(fill="x")

        actions = ttk.Frame(goals_panel)
        actions.pack(fill="x", pady=(8, 0))

        ttk.Button(
            actions,
            text="Mark All",
            command=self._mark_all,
        ).pack(side="left")

        ttk.Button(
            actions,
            text="Clear",
            command=self._clear_all,
        ).pack(side="left", padx=(8, 0))

        reviews_panel = ttk.LabelFrame(
            self,
            text="Upcoming Reviews — Next 24 Hours",
            padding=10,
        )
        reviews_panel.pack(fill="both", expand=True)

        self.reviews_graph = HomeReviewsGraph(reviews_panel)
        self.reviews_graph.pack(fill="both", expand=True)

    def refresh(self) -> None:
        self.data = ensure_goal_file(
            DAILY_GOALS_PATH,
            schedule_path=DAILY_GOAL_SCHEDULE_PATH,
        )
        self._render_today_goals()
        self.reviews_graph.refresh_reviews()

    def refresh_reviews(self) -> None:
        self.reviews_graph.refresh_reviews()

    def _render_today_goals(self) -> None:
        for child in self.goals_frame.winfo_children():
            child.destroy()

        self.goal_vars = {}
        self.timer_widgets = {}
        today = date.today()
        today_key = today.isoformat()

        if self.timer_day != today_key:
            self._reset_timer_state()
            self.timer_day = today_key

        schedule = goals_for_date(
            self.data,
            today,
            schedule_path=DAILY_GOAL_SCHEDULE_PATH,
        )
        completed = completed_goal_ids(self.data, today)

        self.goals_frame.grid_columnconfigure(0, weight=1)

        for index, goal in enumerate(schedule["goals"]):
            goal_id = str(goal.get("id") or "")
            if not goal_id:
                continue

            variable = tk.BooleanVar(value=goal_id in completed)
            self.goal_vars[goal_id] = variable

            row = ttk.Frame(self.goals_frame)
            row.grid(row=index, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(0, weight=1)

            activity = str(
                goal.get("display")
                or goal.get("activity")
                or goal_id
            )
            estimated_time = str(
                goal.get("estimated_time") or ""
            ).strip()

            checkbox = ttk.Checkbutton(
                row,
                text=activity,
                variable=variable,
                command=self._save_today,
            )
            checkbox.grid(row=0, column=0, sticky="w")

            timer_seconds = self._estimated_seconds(estimated_time)
            if timer_seconds is not None:
                state = self.timer_state.setdefault(
                    goal_id,
                    {
                        "initial_seconds": timer_seconds,
                        "remaining_seconds": timer_seconds,
                        "running": False,
                        "deadline": None,
                    },
                )

                # If the schedule changes while the app is open, use the new
                # duration only for a timer that has not yet been started.
                if (
                    not state["running"]
                    and state["remaining_seconds"] == state["initial_seconds"]
                    and state["initial_seconds"] != timer_seconds
                ):
                    state["initial_seconds"] = timer_seconds
                    state["remaining_seconds"] = timer_seconds

                timer_display = SegmentTimerDisplay(row)
                timer_display.set_value(
                    self._format_seconds(
                        self._current_remaining(goal_id)
                    )
                )
                timer_display.grid(
                    row=0,
                    column=1,
                    sticky="e",
                    padx=(12, 8),
                )

                start_button = ttk.Button(
                    row,
                    text="Start",
                    width=7,
                    command=lambda gid=goal_id: self._start_timer(gid),
                )
                start_button.grid(
                    row=0,
                    column=2,
                    padx=(0, 4),
                )

                pause_button = ttk.Button(
                    row,
                    text="Pause",
                    width=7,
                    command=lambda gid=goal_id: self._pause_timer(gid),
                )
                pause_button.grid(
                    row=0,
                    column=3,
                )

                self.timer_widgets[goal_id] = {
                    "display": timer_display,
                    "start": start_button,
                    "pause": pause_button,
                }
                self._update_timer_controls(goal_id)
                time_label = timer_display
            else:
                time_label = ttk.Label(
                    row,
                    text=estimated_time,
                    style="Muted.TLabel",
                )
                time_label.grid(
                    row=0,
                    column=1,
                    sticky="e",
                    padx=(12, 0),
                )

            tooltip_text = (
                f"What to do: {goal.get('what_to_do') or ''}\n"
                f"Main purpose: {goal.get('main_purpose') or ''}"
            )
            HoverTooltip(checkbox, tooltip_text)
            HoverTooltip(time_label, tooltip_text)

    @staticmethod
    def _estimated_seconds(estimated_time: str) -> int | None:
        """Convert schedule values such as '20m' into countdown seconds."""
        match = re.fullmatch(r"\s*(\d+)\s*m\s*", estimated_time, re.IGNORECASE)
        if not match:
            return None
        minutes = int(match.group(1))
        return minutes * 60 if minutes > 0 else None

    @staticmethod
    def _format_seconds(seconds: int) -> str:
        seconds = max(0, int(seconds))
        minutes, secs = divmod(seconds, 60)
        return f"{minutes:02d}:{secs:02d}"

    def _current_remaining(self, goal_id: str) -> int:
        state = self.timer_state[goal_id]
        if not state["running"] or state["deadline"] is None:
            return int(state["remaining_seconds"])

        remaining = max(
            0,
            int(round(state["deadline"] - time.monotonic())),
        )
        if remaining == 0:
            state["remaining_seconds"] = 0
            state["running"] = False
            state["deadline"] = None
        return remaining

    def _start_timer(self, goal_id: str) -> None:
        state = self.timer_state.get(goal_id)
        if state is None or state["running"]:
            return

        if state["remaining_seconds"] <= 0:
            state["remaining_seconds"] = state["initial_seconds"]

        state["running"] = True
        state["deadline"] = (
            time.monotonic() + state["remaining_seconds"]
        )
        self._update_timer_controls(goal_id)
        self._ensure_timer_tick()

    def _pause_timer(self, goal_id: str) -> None:
        state = self.timer_state.get(goal_id)
        if state is None or not state["running"]:
            return

        state["remaining_seconds"] = self._current_remaining(goal_id)
        state["running"] = False
        state["deadline"] = None
        self._update_timer_controls(goal_id)

    def _update_timer_controls(self, goal_id: str) -> None:
        state = self.timer_state.get(goal_id)
        widgets = self.timer_widgets.get(goal_id)
        if state is None or widgets is None:
            return

        remaining = self._current_remaining(goal_id)
        widgets["display"].set_value(self._format_seconds(remaining))

        if state["running"]:
            widgets["start"].config(state="disabled")
            widgets["pause"].config(state="normal")
        else:
            widgets["start"].config(state="normal")
            widgets["pause"].config(state="disabled")

    def _ensure_timer_tick(self) -> None:
        if self._timer_after_id is None:
            self._timer_after_id = self.after(250, self._timer_tick)

    def _timer_tick(self) -> None:
        self._timer_after_id = None
        any_running = False

        for goal_id, state in self.timer_state.items():
            if state["running"]:
                any_running = True
                self._update_timer_controls(goal_id)

        if any_running:
            self._ensure_timer_tick()

    def _reset_timer_state(self) -> None:
        if self._timer_after_id is not None:
            try:
                self.after_cancel(self._timer_after_id)
            except tk.TclError:
                pass
            self._timer_after_id = None
        self.timer_state.clear()
        self.timer_widgets.clear()

    def _mark_all(self) -> None:
        for variable in self.goal_vars.values():
            variable.set(True)
        self._save_today()

    def _clear_all(self) -> None:
        for variable in self.goal_vars.values():
            variable.set(False)
        self._save_today()

    def _save_today(self) -> None:
        completed = {
            goal_id
            for goal_id, variable in self.goal_vars.items()
            if variable.get()
        }

        # Home does not edit notes. Preserve any note already attached to today.
        record = (
            (self.data.get("records") or {})
            .get(date.today().isoformat())
            or {}
        )
        notes = str(record.get("notes") or "")

        try:
            self.data = save_day_record(
                DAILY_GOALS_PATH,
                date.today(),
                completed,
                notes=notes,
                schedule_path=DAILY_GOAL_SCHEDULE_PATH,
            )
        except Exception as exc:
            messagebox.showerror(
                "Today's Goals",
                f"Could not update today's goals:\n{type(exc).__name__}: {exc}",
            )
            return

        self._render_today_goals()