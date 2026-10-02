from pathlib import Path

from streamlit.testing.v1 import AppTest

from research.cli import offline_run


def test_streamlit_offline_views(tmp_path, monkeypatch):
    monkeypatch.setattr("dotenv.dotenv_values", lambda path: {})
    monkeypatch.setenv("RESEARCH_DB", str(tmp_path / "ui.db"))
    state = offline_run(db=tmp_path / "run.db")
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=20)
    app.session_state["state"] = state
    app.run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Report",
        "Sources",
        "Evidence and claims",
        "Metrics",
    ]
    assert any("Citation integrity passed" in message.value for message in app.success)
    assert any("Offline demo" in message.value for message in app.info)
    assert len(app.get("download_button")) == 1


def test_streamlit_failed_run_has_no_download(tmp_path, monkeypatch):
    monkeypatch.setattr("dotenv.dotenv_values", lambda path: {})
    monkeypatch.setenv("RESEARCH_DB", str(tmp_path / "ui.db"))
    state = offline_run("unavailable", tmp_path / "run.db")
    app = AppTest.from_file(Path("app.py").resolve(), default_timeout=20)
    app.session_state["state"] = state
    app.run()
    assert not app.exception
    assert app.error
    assert len(app.get("download_button")) == 0
