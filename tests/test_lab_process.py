"""
tests/test_lab_process.py
-------------------------
`python -m api` starts the Streamlit technical lab next to itself (api/lab.py) and GET /api/lab says whether it is up and where.
Here the process handling is tested without starting Streamlit: disabled, already running (use it, start nothing), the exact
command and working folder, the address the browser gets, Streamlit missing. The real thing (a real Streamlit, a real browser)
is web/e2e/lab.spec.ts. Run: pytest tests/test_lab_process.py
"""
import socket
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import core.db.warehouse as warehouse  # noqa: E402
from api import lab  # noqa: E402


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextmanager
def _listening():
    """Something that answers on a port, standing in for a lab started by `make lab`."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    try:
        yield server.getsockname()[1]
    finally:
        server.close()


@contextmanager
def _api(monkeypatch, *, enabled="1", port=None, base_url="http://127.0.0.1"):
    warehouse.DB_PATH = Path(tempfile.mkdtemp()) / "lab-process.db"
    monkeypatch.setenv("AGRIMINE_LAB", enabled)
    monkeypatch.setenv("AGRIMINE_LAB_PORT", str(port or _free_port()))
    monkeypatch.delenv("AGRIMINE_LAB_URL", raising=False)
    from api.main import app
    with TestClient(app, base_url=base_url) as client:
        yield client


class FakeProcess:
    def __init__(self, command, **kwargs):
        self.command, self.kwargs, self.stopped = command, kwargs, False

    def poll(self):
        return None

    def terminate(self):
        self.stopped = True

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.stopped = True


def test_disabled_means_nothing_is_started_and_the_web_app_is_told_so(monkeypatch):
    monkeypatch.setattr(lab.subprocess, "Popen", lambda *a, **k: pytest.fail("the lab must not start when AGRIMINE_LAB=0"))
    with _api(monkeypatch, enabled="0") as c:
        status = c.get("/api/lab").json()
    assert status["available"] is False and "disabled" in status["note"]


def test_a_lab_that_is_already_running_is_used_and_nothing_else_is_started(monkeypatch):
    monkeypatch.setattr(lab.subprocess, "Popen", lambda *a, **k: pytest.fail("a second lab must not be started on a busy port"))
    with _listening() as port, _api(monkeypatch, port=port) as c:
        status = c.get("/api/lab").json()
    assert status["available"] is True and "already running" in status["note"]
    assert status["url"] == f"http://127.0.0.1:{port}"


def test_it_starts_streamlit_in_the_lab_folder_on_the_chosen_port_and_stops_it_with_the_api(monkeypatch):
    started = []
    monkeypatch.setattr(lab.subprocess, "Popen", lambda command, **kwargs: started.append(FakeProcess(command, **kwargs)) or started[-1])
    monkeypatch.setattr(lab, "warm", lambda number, timeout=90: False)            # no real Streamlit here
    port = _free_port()
    with _api(monkeypatch, port=port) as c:
        assert len(started) == 1
        command, kwargs = started[0].command, started[0].kwargs
        assert command[:5] == [sys.executable, "-m", "streamlit", "run", "app.py"]
        assert command[command.index("--server.port") + 1] == str(port) and "--server.headless" in command
        assert kwargs["cwd"] == lab.LAB_DIR and (lab.LAB_DIR / "app.py").exists()
        assert "started on port" in c.get("/api/lab").json()["note"]
        assert not started[0].stopped
    assert started[0].stopped                                                       # leaving the API stops the lab it started


def test_not_available_until_the_lab_has_been_warmed_up_and_answers(monkeypatch):
    """'Answers on its port' is not enough: until the first run has registered the pages, the first link shows a dialog."""
    import threading
    release = threading.Event()
    monkeypatch.setattr(lab.subprocess, "Popen", lambda command, **kwargs: FakeProcess(command, **kwargs))
    monkeypatch.setattr(lab, "warm", lambda number, timeout=90: release.wait(10))
    with _listening() as port:
        monkeypatch.setenv("AGRIMINE_LAB", "1")
        monkeypatch.setenv("AGRIMINE_LAB_PORT", str(port))
        current = lab.Lab()
        monkeypatch.setattr(lab, "is_up", lambda number=None, timeout=0.3: current.process is not None)   # port open, as soon as we start it
        current.start()
        assert current.available is False
        release.set()
        assert current.ready.wait(5) and current.available is True


def test_the_address_follows_the_host_the_browser_used(monkeypatch):
    with _api(monkeypatch, enabled="0", port=8501, base_url="http://farm-laptop.local:8000") as c:
        assert c.get("/api/lab").json()["url"] == "http://farm-laptop.local:8501"
    monkeypatch.setenv("AGRIMINE_LAB_URL", "https://lab.example.org/")
    assert lab.url("anything") == "https://lab.example.org"                           # an explicit address wins, without a trailing slash


def test_without_streamlit_the_api_still_runs_and_says_why(monkeypatch):
    monkeypatch.setattr(lab.importlib.util, "find_spec", lambda name: None)
    with _api(monkeypatch) as c:
        assert c.get("/api/health").json()["status"] == "ok"
        status = c.get("/api/lab").json()
    assert status["available"] is False and "not installed" in status["note"]
