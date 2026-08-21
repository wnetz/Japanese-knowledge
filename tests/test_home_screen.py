from pathlib import Path


def test_home_is_first_sidebar_button_and_start_screen() -> None:
    source = Path("gui/app.py").read_text(encoding="utf-8")
    assert 'self.show_screen("home")' in source
    home = source.index('text="Home"')
    update = source.index('text="Update Profile"')
    assert home < update
    assert 'self.frames["home"] = HomeScreen(self.content)' in source


def test_home_goals_share_daily_goal_storage_and_autosave() -> None:
    source = Path("gui/home_screen.py").read_text(encoding="utf-8")
    assert "DAILY_GOALS_PATH" in source
    assert "DAILY_GOAL_SCHEDULE_PATH" in source
    assert "save_day_record(" in source
    assert "command=self._save_today" in source
    assert "notes = str(record.get(\"notes\") or \"\")" in source


def test_home_review_graph_has_fixed_requested_filters_and_no_controls() -> None:
    source = Path("gui/home_screen.py").read_text(encoding="utf-8")
    assert 'self.review_anki_var = tk.BooleanVar(value=True)' in source
    assert 'self.review_wanikani_var = tk.BooleanVar(value=True)' in source
    assert 'self.review_bunpro_var = tk.BooleanVar(value=True)' in source
    assert 'self.review_writing_var = tk.BooleanVar(value=True)' in source
    assert 'self.review_horizon_var = tk.StringVar(value="24 hours")' in source
    assert 'self.new_only_var = tk.BooleanVar(value=True)' in source
    assert "ttk.Checkbutton(" not in source.split("class HomeReviewsGraph", 1)[1].split("class HomeScreen", 1)[0]
    assert "ttk.Combobox(" not in source.split("class HomeReviewsGraph", 1)[1].split("class HomeScreen", 1)[0]


def test_home_review_graph_hides_total_line() -> None:
    source = Path("gui/home_screen.py").read_text(encoding="utf-8")
    assert 'self.show_total_var = tk.BooleanVar(value=False)' in source


def test_home_review_graph_is_stacked_bar_chart() -> None:
    source = Path("gui/home_screen.py").read_text(encoding="utf-8")
    assert "def _draw_hourly_graph" in source
    assert "axis.bar(" in source
    assert "bottom=bottoms" in source
    assert 'width=0.032' in source
    assert 'self.show_total_var = tk.BooleanVar(value=False)' in source


def test_home_stack_order() -> None:
    source = Path("gui/home_screen.py").read_text(encoding="utf-8")
    assert 'stack_order = ["Writing", "Bunpro", "WaniKani", "Anki"]' in source


def test_home_legend_matches_visual_stack_order() -> None:
    source = Path("gui/home_screen.py").read_text(encoding="utf-8")
    assert 'stack_order = ["Writing", "Bunpro", "WaniKani", "Anki"]' in source
    assert 'axis.legend(handles[::-1], labels[::-1])' in source


def test_home_goal_countdown_timers() -> None:
    source = Path("gui/home_screen.py").read_text(encoding="utf-8")
    assert "def _estimated_seconds" in source
    assert "def _start_timer" in source
    assert "def _pause_timer" in source
    assert 'text="Start"' in source
    assert 'text="Pause"' in source
    assert "datetime.fromisoformat" in source
    assert "save_goal_timer(" in source
    assert 're.fullmatch(r"\\s*(\\d+)\\s*m\\s*"' in source


def test_home_only_adds_timers_for_goals_with_estimated_minutes() -> None:
    source = Path("gui/home_screen.py").read_text(encoding="utf-8")
    assert "timer_seconds = self._estimated_seconds(estimated_time)" in source
    assert "if timer_seconds is not None:" in source


def test_home_timers_use_segment_display() -> None:
    source = Path("gui/home_screen.py").read_text(encoding="utf-8")
    assert "class SegmentTimerDisplay(tk.Canvas)" in source
    assert "DIGIT_SEGMENTS" in source
    assert 'widgets["display"].set_value' in source
    assert "TIMER_SEGMENT_COLORS" in source


def test_timer_segments_use_dark_purple_from_style() -> None:
    source = Path("gui/style.py").read_text(encoding="utf-8")
    assert '"on": COLORS["purple_dark"]' in source


def test_timer_background_matches_app_background() -> None:
    source = Path("gui/style.py").read_text(encoding="utf-8")
    assert '"off": COLORS["bg"]' in source
    assert '"background": COLORS["bg"]' in source


def test_home_timer_persists_and_completes_goal() -> None:
    source = Path("gui/home_screen.py").read_text(encoding="utf-8")
    assert "goal_timers(" in source
    assert "save_goal_timer(" in source
    assert 'messagebox.showinfo(' in source
    assert '"Timer Complete"' in source
    assert "variable.set(True)" in source
    assert "deadline" in source
    assert "datetime.fromisoformat" in source
