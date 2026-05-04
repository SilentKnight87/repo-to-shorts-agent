from __future__ import annotations

import json
import socket
import threading
from pathlib import Path
from urllib.request import urlopen

from repo_to_shorts.web import run_web_server


def test_progress_unknown_session_is_waiting_response(tmp_path: Path):
    # This captures the regression where frontend polling before POST creation
    # displayed "Session not found" as a hard error.
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    thread = threading.Thread(target=run_web_server, args=("127.0.0.1", port, tmp_path), daemon=True)
    thread.start()

    with urlopen(f"http://127.0.0.1:{port}/progress?session=race-session", timeout=5) as response:  # noqa: S310
        data = json.loads(response.read().decode())

    assert data["session_id"] == "race-session"
    assert data["error"] is None
    assert data["active_detail"] == "Waiting for generation to start…"
    assert data["percent"] == 0
    assert len(data["stages"]) >= 1
