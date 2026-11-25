from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_app_renders_without_errors_and_without_key():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert at.title[0].value.endswith("Job Application Agent")
    assert len(at.tabs) == 5


def test_reset_button_and_empty_tracker_message():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert any("tracker is empty" in i.value for i in at.info)
    next(b for b in at.sidebar.button if b.label == "Reset demo").click().run()
    assert not at.exception
