from pathlib import Path


def test_app_has_daily_goals_page() -> None:
    source = Path("gui/app.py").read_text(encoding="utf-8")
    assert "DailyGoalsScreen" in source
    assert 'text="Daily Goals"' in source
    assert 'self.frames["daily_goals"]' in source


def test_calendar_dates_are_clickable_and_past_dates_editable() -> None:
    source = Path("gui/daily_goals_screen.py").read_text(encoding="utf-8")
    assert "monthdatescalendar" in source
    assert "command=lambda d=target_date: self._select_date(d)" in source
    assert "self.selected_date <= date.today()" in source
    assert 'text="Save Day"' in source


def test_calendar_colors_are_centralized() -> None:
    style = Path("gui/style.py").read_text(encoding="utf-8")
    screen = Path("gui/daily_goals_screen.py").read_text(encoding="utf-8")
    assert "DAILY_GOAL_CALENDAR_COLORS = {" in style
    assert "DAILY_GOAL_CALENDAR_COLORS = {" not in screen


def test_calendar_uses_existing_palette() -> None:
    style = Path("gui/style.py").read_text(encoding="utf-8")
    assert '"complete": COLORS["purple_dark"]' in style
    assert '"partial": COLORS["purple_hover"]' in style
    assert '"missed": COLORS["panel_alt"]' in style
    assert '"untracked": COLORS["panel_alt"]' in style
    assert '"future": COLORS["panel"]' in style


def test_goal_option_uses_activity_text_and_hover_details() -> None:
    source = Path("gui/daily_goals_screen.py").read_text(encoding="utf-8")
    assert "text=activity" in source
    assert "What to do:" in source
    assert "Main purpose:" in source
    assert "HoverTooltip(" in source


def test_goal_rows_use_estimated_time() -> None:
    source = Path("gui/daily_goals_screen.py").read_text(encoding="utf-8")
    assert 'goal.get("estimated_time")' in source
