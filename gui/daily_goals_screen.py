from __future__ import annotations

import calendar
from datetime import date
import tkinter as tk
from tkinter import messagebox, ttk

from goals.tracker import (
    completion_ratio,
    day_status,
    ensure_goal_file,
    goals_for_date,
    save_day_record,
    streaks,
)
from .shared import DAILY_GOALS_PATH, DAILY_GOAL_SCHEDULE_PATH
from .style import (
    COLORS,
    DAILY_GOAL_CALENDAR_COLORS,
    daily_goal_progress_color,
)


class HoverTooltip:
    def __init__(self, widget, text: str, *, delay_ms: int = 350) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.after_id = None
        self.window = None

        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self.after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self) -> None:
        if self.after_id is not None:
            try:
                self.widget.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None

    def _show(self) -> None:
        self.after_id = None
        if self.window is not None or not self.text:
            return

        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        try:
            self.window.attributes("-topmost", True)
        except tk.TclError:
            pass

        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.window.wm_geometry(f"+{x}+{y}")

        tk.Label(
            self.window,
            text=self.text,
            justify="left",
            anchor="w",
            wraplength=360,
            bg=COLORS["input_bg"],
            fg=COLORS["text"],
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=8,
            font=("Segoe UI", 9),
        ).pack()

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self.window is not None:
            try:
                self.window.destroy()
            except tk.TclError:
                pass
            self.window = None


class DailyGoalsScreen(ttk.Frame):
    def __init__(self, parent) -> None:
        super().__init__(parent)

        today = date.today()
        self.view_year = today.year
        self.view_month = today.month
        self.selected_date = today
        self.goal_vars: dict[str, tk.BooleanVar] = {}

        self.data = ensure_goal_file(
            DAILY_GOALS_PATH,
            start_date=today,
            schedule_path=DAILY_GOAL_SCHEDULE_PATH,
        )

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x")

        ttk.Label(
            header,
            text="Daily Goals",
            style="Heading.TLabel",
        ).pack(side="left")

        streak_frame = ttk.Frame(header)
        streak_frame.pack(side="right")

        self.current_streak_var = tk.StringVar(value="0")
        self.longest_streak_var = tk.StringVar(value="0")

        ttk.Label(
            streak_frame,
            text="Current streak:",
            style="Muted.TLabel",
        ).grid(row=0, column=0)
        ttk.Label(
            streak_frame,
            textvariable=self.current_streak_var,
            font=("Segoe UI", 18, "bold"),
            foreground=COLORS["green"],
        ).grid(row=0, column=1, padx=(6, 18))

        ttk.Label(
            streak_frame,
            text="Longest:",
            style="Muted.TLabel",
        ).grid(row=0, column=2)
        ttk.Label(
            streak_frame,
            textvariable=self.longest_streak_var,
            font=("Segoe UI", 18, "bold"),
            foreground=COLORS["purple_hover"],
        ).grid(row=0, column=3, padx=(6, 0))

        ttk.Label(
            self,
            text=(
                "A day counts toward the streak when every scheduled goal "
                "for that day is complete. Click any date to review or edit it."
            ),
            wraplength=820,
        ).pack(anchor="w", pady=(4, 14))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        calendar_panel = ttk.LabelFrame(
            body,
            text="Calendar",
            padding=10,
        )
        calendar_panel.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 8),
        )

        nav = ttk.Frame(calendar_panel)
        nav.pack(fill="x", pady=(0, 8))

        ttk.Button(
            nav,
            text="‹",
            width=4,
            command=self._previous_month,
        ).pack(side="left")

        self.month_var = tk.StringVar()
        ttk.Label(
            nav,
            textvariable=self.month_var,
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left", expand=True)

        ttk.Button(
            nav,
            text="Today",
            command=self._go_today,
        ).pack(side="right", padx=(8, 0))

        ttk.Button(
            nav,
            text="›",
            width=4,
            command=self._next_month,
        ).pack(side="right")

        self.calendar_grid = tk.Frame(
            calendar_panel,
            bg=COLORS["panel"],
        )
        self.calendar_grid.pack(fill="both", expand=True)

        legend = ttk.Frame(calendar_panel)
        legend.pack(fill="x", pady=(8, 0))
        for label, key in (
            ("Complete", "complete"),
            ("Partial", "partial"),
            ("Missed", "missed"),
            ("Untracked", "untracked"),
        ):
            tk.Label(
                legend,
                width=2,
                bg=DAILY_GOAL_CALENDAR_COLORS[key],
            ).pack(side="left", padx=(0, 4))
            ttk.Label(
                legend,
                text=label,
                style="Muted.TLabel",
            ).pack(side="left", padx=(0, 12))

        detail_panel = ttk.LabelFrame(
            body,
            text="Selected day",
            padding=12,
        )
        detail_panel.pack(
            side="left",
            fill="y",
            padx=(8, 0),
        )

        self.selected_title_var = tk.StringVar()
        ttk.Label(
            detail_panel,
            textvariable=self.selected_title_var,
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")

        self.approx_var = tk.StringVar()
        ttk.Label(
            detail_panel,
            textvariable=self.approx_var,
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 10))

        self.goals_frame = ttk.Frame(detail_panel)
        self.goals_frame.pack(fill="x")

        buttons = ttk.Frame(detail_panel)
        buttons.pack(fill="x", pady=(12, 0))

        self.mark_all_button = ttk.Button(
            buttons,
            text="Mark All",
            command=self._mark_all,
        )
        self.mark_all_button.pack(side="left")

        self.clear_button = ttk.Button(
            buttons,
            text="Clear",
            command=self._clear_all,
        )
        self.clear_button.pack(side="left", padx=(6, 0))

        self.save_button = ttk.Button(
            buttons,
            text="Save Day",
            command=self._save_selected_day,
            style="Success.TButton",
        )
        self.save_button.pack(side="right")

        ttk.Label(
            detail_panel,
            text="Notes",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(14, 4))

        self.notes_text = tk.Text(
            detail_panel,
            height=5,
            width=36,
            wrap="word",
            bg=COLORS["input_bg"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["selection"],
            selectforeground="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        self.notes_text.pack(fill="x")

        self.day_status_var = tk.StringVar()
        ttk.Label(
            detail_panel,
            textvariable=self.day_status_var,
            style="Muted.TLabel",
            wraplength=290,
        ).pack(anchor="w", pady=(10, 0))

    def refresh(self) -> None:
        self.data = ensure_goal_file(
            DAILY_GOALS_PATH,
            schedule_path=DAILY_GOAL_SCHEDULE_PATH,
        )
        current, longest = streaks(
            self.data,
            schedule_path=DAILY_GOAL_SCHEDULE_PATH,
        )
        self.current_streak_var.set(str(current))
        self.longest_streak_var.set(str(longest))
        self._render_calendar()
        self._load_selected_day()

    def _render_calendar(self) -> None:
        for child in self.calendar_grid.winfo_children():
            child.destroy()

        self.month_var.set(
            date(self.view_year, self.view_month, 1).strftime("%B %Y")
        )

        for column, weekday in enumerate(
            ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        ):
            tk.Label(
                self.calendar_grid,
                text=weekday,
                bg=COLORS["panel"],
                fg=COLORS["muted"],
                font=("Segoe UI", 9, "bold"),
                pady=5,
            ).grid(row=0, column=column, sticky="nsew")
            self.calendar_grid.grid_columnconfigure(
                column,
                weight=1,
                uniform="calendar",
            )

        weeks = calendar.Calendar(
            firstweekday=calendar.MONDAY
        ).monthdatescalendar(
            self.view_year,
            self.view_month,
        )
        today = date.today()

        for row, week in enumerate(weeks, start=1):
            self.calendar_grid.grid_rowconfigure(
                row,
                weight=1,
                uniform="calendar_row",
            )

            for column, target_date in enumerate(week):
                in_month = target_date.month == self.view_month
                status = day_status(
                    self.data,
                    target_date,
                    today=today,
                    schedule_path=DAILY_GOAL_SCHEDULE_PATH,
                )

                progress = completion_ratio(
                    self.data,
                    target_date,
                    schedule_path=DAILY_GOAL_SCHEDULE_PATH,
                )
                if progress > 0:
                    bg = daily_goal_progress_color(progress)
                else:
                    bg = DAILY_GOAL_CALENDAR_COLORS.get(
                        status,
                        DAILY_GOAL_CALENDAR_COLORS["untracked"],
                    )

                if not in_month:
                    bg = COLORS["panel"]
                    fg = COLORS["muted"]
                elif status in {"complete", "partial", "missed"}:
                    fg = DAILY_GOAL_CALENDAR_COLORS["day_text"]
                else:
                    fg = DAILY_GOAL_CALENDAR_COLORS["muted_day_text"]

                selected = target_date == self.selected_date

                tk.Button(
                    self.calendar_grid,
                    text=str(target_date.day),
                    command=lambda d=target_date: self._select_date(d),
                    bg=bg,
                    fg=fg,
                    activebackground=COLORS["purple_hover"],
                    activeforeground="#111111",
                    relief="solid",
                    borderwidth=2 if selected else 1,
                    highlightthickness=2 if selected else 0,
                    highlightbackground=DAILY_GOAL_CALENDAR_COLORS["selected_border"],
                    highlightcolor=DAILY_GOAL_CALENDAR_COLORS["selected_border"],
                    font=(
                        "Segoe UI",
                        10,
                        "bold" if target_date == today else "normal",
                    ),
                    padx=8,
                    pady=8,
                ).grid(
                    row=row,
                    column=column,
                    padx=2,
                    pady=2,
                    sticky="nsew",
                )

    def _load_selected_day(self) -> None:
        for child in self.goals_frame.winfo_children():
            child.destroy()
        self.goal_vars = {}

        schedule = goals_for_date(
            self.data,
            self.selected_date,
            schedule_path=DAILY_GOAL_SCHEDULE_PATH,
        )

        self.selected_title_var.set(
            self.selected_date.strftime("%A, %B %d, %Y").replace(" 0", " ")
        )
        self.approx_var.set(
            f"Planned study time: {schedule['approx']}"
        )

        record = (
            (self.data.get("records") or {})
            .get(self.selected_date.isoformat())
            or {}
        )
        completed = set(record.get("completed") or [])

        editable = self.selected_date <= date.today()

        self.goals_frame.grid_columnconfigure(0, weight=1)

        for index, goal in enumerate(schedule["goals"]):
            goal_id = str(goal.get("id"))
            variable = tk.BooleanVar(
                value=goal_id in completed,
            )
            self.goal_vars[goal_id] = variable

            row = ttk.Frame(self.goals_frame)
            row.grid(
                row=index,
                column=0,
                sticky="ew",
                pady=3,
            )
            row.grid_columnconfigure(0, weight=1)

            activity = str(goal.get("display") or goal.get("activity") or goal_id)
            target = str(goal.get("estimated_time") or "").strip()

            checkbox = ttk.Checkbutton(
                row,
                variable=variable,
                text=activity,
                state="normal" if editable else "disabled",
            )
            checkbox.grid(
                row=0,
                column=0,
                sticky="w",
            )

            target_label = ttk.Label(
                row,
                text=target,
                style="Muted.TLabel",
            )
            target_label.grid(
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
            HoverTooltip(target_label, tooltip_text)

        self.notes_text.config(state="normal")
        self.notes_text.delete("1.0", "end")
        self.notes_text.insert(
            "1.0",
            str(record.get("notes") or ""),
        )
        if not editable:
            self.notes_text.config(state="disabled")

        status = day_status(
            self.data,
            self.selected_date,
            schedule_path=DAILY_GOAL_SCHEDULE_PATH,
        )
        self.day_status_var.set(
            f"Status: {status.replace('_', ' ').title()}"
        )

        state = "normal" if editable else "disabled"
        self.save_button.config(state=state)
        self.mark_all_button.config(state=state)
        self.clear_button.config(state=state)

    def _select_date(self, target_date: date) -> None:
        self.selected_date = target_date

        if (
            target_date.year != self.view_year
            or target_date.month != self.view_month
        ):
            self.view_year = target_date.year
            self.view_month = target_date.month

        self._render_calendar()
        self._load_selected_day()

    def _previous_month(self) -> None:
        if self.view_month == 1:
            self.view_year -= 1
            self.view_month = 12
        else:
            self.view_month -= 1
        self._render_calendar()

    def _next_month(self) -> None:
        if self.view_month == 12:
            self.view_year += 1
            self.view_month = 1
        else:
            self.view_month += 1
        self._render_calendar()

    def _go_today(self) -> None:
        today = date.today()
        self.view_year = today.year
        self.view_month = today.month
        self.selected_date = today
        self.refresh()

    def _mark_all(self) -> None:
        for variable in self.goal_vars.values():
            variable.set(True)

    def _clear_all(self) -> None:
        for variable in self.goal_vars.values():
            variable.set(False)

    def _save_selected_day(self) -> None:
        if self.selected_date > date.today():
            return

        completed = {
            goal_id
            for goal_id, variable in self.goal_vars.items()
            if variable.get()
        }

        try:
            self.data = save_day_record(
                DAILY_GOALS_PATH,
                self.selected_date,
                completed,
                notes=self.notes_text.get("1.0", "end").strip(),
                schedule_path=DAILY_GOAL_SCHEDULE_PATH,
            )
        except Exception as exc:
            messagebox.showerror(
                "Daily Goals",
                f"Could not save day:\n{type(exc).__name__}: {exc}",
            )
            return

        self.refresh()
