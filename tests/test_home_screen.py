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
