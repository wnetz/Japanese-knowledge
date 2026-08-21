from datetime import date

from goals.tracker import completion_ratio, empty_goal_data
from gui.style import COLORS, daily_goal_progress_color


def test_progress_color_moves_light_to_dark_purple() -> None:
    assert daily_goal_progress_color(0.0) == COLORS["purple_hover"]
    assert daily_goal_progress_color(1.0) == COLORS["purple_dark"]
    assert daily_goal_progress_color(0.5) not in {
        COLORS["purple_hover"],
        COLORS["purple_dark"],
    }


def test_completion_ratio_uses_number_of_scheduled_goals() -> None:
    target = date(2026, 8, 21)  # Friday: four goals
    data = empty_goal_data(start_date=target)
    data["records"][target.isoformat()] = {
        "completed": ["grammar", "reading"],
    }
    assert completion_ratio(data, target) == 0.5
