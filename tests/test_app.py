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


def test_public_demo_replays_sample_without_calling_a_model(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEMO", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import copilot.agent
    monkeypatch.setattr(copilot.agent.Copilot, "run",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("model called")))
    at = AppTest.from_file(APP).run(timeout=30)
    assert len(at.sidebar.selectbox) == 1  # no model or effort picker in the public demo
    at.sidebar.selectbox[0].select_index(1).run()
    at.button[0].click().run(timeout=30)
    assert not at.exception
    assert any("8.9" in m.value for m in at.markdown) or any("8.9" in t.value for t in at.text_area)


def test_public_demo_without_key_explains_live_runs_are_off(monkeypatch):
    monkeypatch.setenv("PUBLIC_DEMO", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    at = AppTest.from_file(APP).run(timeout=30)
    at.text_area[0].input("Does the HX-R6016 support CXL 3.1?").run()
    at.button[0].click().run(timeout=30)
    assert any("aren't configured" in w.value for w in at.warning)
