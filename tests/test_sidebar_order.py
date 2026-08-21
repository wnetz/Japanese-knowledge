from pathlib import Path


def test_sidebar_button_order() -> None:
    source = Path("gui/app.py").read_text(encoding="utf-8")

    labels = [
        'text="Home"',
        'text="Update Profile"',
        'text="Daily Goals"',
        'text="Writing Quiz"',
        'text="Grammar Review"',
        'text="Upcoming Reviews"',
        'text="SRS History"',
        'text="Kanji Heatmap"',
    ]

    positions = [source.index(label) for label in labels]
    assert positions == sorted(positions)
