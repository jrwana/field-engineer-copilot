from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_renders_without_error():
    at = AppTest.from_file(APP).run(timeout=30)
    assert not at.exception
    assert at.title[0].value == "Field Engineer Copilot"


def test_sample_email_fills_text_area():
    at = AppTest.from_file(APP).run(timeout=30)
    at.sidebar.selectbox[2].select_index(1).run()
    assert "HX-R6016" in at.text_area[0].value
