"""In-memory report-generation progress, polled by the frontend during the
single long-running generate-from-session call (D5's pipeline has no other
way to surface intermediate state). Single-user desktop app — no
persistence needed; each session_id's entry is simply overwritten by its
next run.
"""

import threading

_lock = threading.Lock()
_progress: dict[str, dict[str, int | str]] = {}


def set_progress(session_id: str, percent: int, stage: str) -> None:
    with _lock:
        _progress[session_id] = {"percent": percent, "stage": stage}


def get_progress(session_id: str) -> dict[str, int | str]:
    with _lock:
        return dict(_progress.get(session_id, {"percent": 0, "stage": "idle"}))
