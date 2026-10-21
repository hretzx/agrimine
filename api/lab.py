"""
api/lab.py
----------
Starts the Streamlit technical lab (teachers-lab/) together with the API, so ONE command (python -m api) gives the whole product:
the web app on port 8000 and the lab on port 8501. The web app's "Open in the lab" links go to it.

  * AGRIMINE_LAB=0          do not start the lab (the tests that do not need it set this)
  * AGRIMINE_LAB_PORT=8501  the lab's port
  * AGRIMINE_LAB_URL=...    the address the browser should use, when it differs from http://<same host>:<port>
  * already running?        if something answers on the port (for example `make lab` in another window) we use it and start nothing
  * Streamlit not installed? the API still runs; /api/lab says the lab is not available

A freshly started Streamlit only learns the addresses of its pages when its script first runs. Until then the first deep link
shows a "Page not found" dialog, so after starting we connect once the way a browser does, which runs the script.
"""
import importlib.util
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAB_DIR = ROOT / "teachers-lab"
LOG = Path(tempfile.gettempdir()) / "agrimine-lab.log"


def enabled() -> bool:
    return os.environ.get("AGRIMINE_LAB", "1") != "0"


def port() -> int:
    return int(os.environ.get("AGRIMINE_LAB_PORT", "8501"))


def is_up(number: int | None = None, timeout: float = 0.3) -> bool:
    """Does anything accept connections on the lab's port?"""
    try:
        with socket.create_connection(("127.0.0.1", number or port()), timeout=timeout):
            return True
    except OSError:
        return False


def url(host: str) -> str:
    """The address the browser should open: AGRIMINE_LAB_URL, or the host the browser used for the API plus the lab's port."""
    return os.environ.get("AGRIMINE_LAB_URL", f"http://{host}:{port()}").rstrip("/")


def command(number: int) -> list[str]:
    return [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", str(number),
            "--browser.gatherUsageStats", "false"]


def warm(number: int, timeout: float = 90) -> bool:
    """Connect the way a browser does, so Streamlit runs its script once and registers every page address. Best effort."""
    try:
        from streamlit.proto.BackMsg_pb2 import BackMsg
        from streamlit.proto.ClientState_pb2 import ClientState
        from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
        from websockets.sync.client import connect
    except ImportError:                      # an older Streamlit without these: the lab still works, its first deep link shows one dialog
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with connect(f"ws://127.0.0.1:{number}/_stcore/stream", subprotocols=["streamlit"], open_timeout=5, max_size=None) as ws:
                ws.send(BackMsg(rerun_script=ClientState(query_string="", page_script_hash="", page_name="")).SerializeToString())
                while True:
                    message = ForwardMsg()
                    message.ParseFromString(ws.recv(timeout=max(1.0, deadline - time.time())))
                    if message.WhichOneof("type") == "script_finished":
                        return True
        except Exception:                     # not accepting yet: try again shortly
            time.sleep(0.5)
    return False


class Lab:
    """The lab's process, if we started it."""

    def __init__(self) -> None:
        self.process: subprocess.Popen | None = None
        self.note = ""
        self.ready = threading.Event()      # set when the lab is usable: warmed up, or not ours to warm (already running / disabled)

    @property
    def available(self) -> bool:
        """Answering on its port AND ready, so the first link a person clicks never meets the cold-start dialog."""
        return self.ready.is_set() and is_up()

    def _warm_then_ready(self, number: int) -> None:
        try:
            warm(number)
        finally:
            self.ready.set()                # even if warming failed: the lab itself works, it only shows one dialog on its first link

    def start(self) -> None:
        number = port()
        if not enabled():
            self.note = "disabled (AGRIMINE_LAB=0)"
        elif is_up(number):
            self.note = f"already running on port {number}; using it"
        elif importlib.util.find_spec("streamlit") is None:
            self.note = "Streamlit is not installed (pip install -r requirements.txt)"
        else:
            kwargs = {"cwd": LAB_DIR, "stdout": LOG.open("ab"), "stderr": subprocess.STDOUT, "stdin": subprocess.DEVNULL}
            if sys.platform.startswith("linux"):         # if the API is killed hard, the lab goes with it
                import ctypes
                import signal
                kwargs["preexec_fn"] = lambda: ctypes.CDLL("libc.so.6").prctl(1, signal.SIGTERM)
            self.process = subprocess.Popen(command(number), **kwargs)
            self.note = f"started on port {number} (log: {LOG})"
            threading.Thread(target=self._warm_then_ready, args=(number,), name="lab-warm-up", daemon=True).start()
        if self.process is None:
            self.ready.set()
        print(f"AgriMine lab: {self.note}", flush=True)

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
