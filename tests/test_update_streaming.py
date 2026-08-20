from pathlib import Path


def test_update_gui_streams_child_output() -> None:
    source = Path("gui/update_screen.py").read_text(encoding="utf-8")
    assert "subprocess.Popen(" in source
    assert 'sys.executable,\n            "-u",' in source
    assert "stdout=subprocess.PIPE" in source
    assert "stderr=subprocess.STDOUT" in source
    assert "for line in iter(process.stdout.readline" in source


def test_update_profile_flushes_progress() -> None:
    source = Path("update_profile.py").read_text(encoding="utf-8")
    assert "def progress(message: str)" in source
    assert "print(message, flush=True)" in source
