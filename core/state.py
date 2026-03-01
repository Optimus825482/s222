"""
State management — 12-Factor #5 & #12: Unified state, stateless reducer.
JSON file-based persistence for threads. User-isolated storage.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import Thread

DATA_DIR = Path(__file__).parent.parent / "data"
THREADS_DIR = DATA_DIR / "threads"


def _threads_dir(user_id: str | None = None) -> Path:
    if user_id:
        return THREADS_DIR / user_id
    return THREADS_DIR


def _ensure_dirs(user_id: str | None = None) -> None:
    _threads_dir(user_id).mkdir(parents=True, exist_ok=True)


def save_thread(thread: Thread, user_id: str | None = None) -> str:
    """Persist thread to JSON file. Returns thread id."""
    _ensure_dirs(user_id)
    path = _threads_dir(user_id) / f"{thread.id}.json"
    path.write_text(thread.model_dump_json(indent=2), encoding="utf-8")
    return thread.id


def load_thread(thread_id: str, user_id: str | None = None) -> Thread | None:
    """Load thread from JSON file."""
    path = _threads_dir(user_id) / f"{thread_id}.json"
    if not path.exists():
        # Fallback: try root threads dir (backward compat)
        path = THREADS_DIR / f"{thread_id}.json"
        if not path.exists():
            return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Thread.model_validate(data)


def list_threads(limit: int = 50, user_id: str | None = None) -> list[dict]:
    """List recent threads with basic info."""
    _ensure_dirs(user_id)
    threads = []
    files = sorted(_threads_dir(user_id).glob("*.json"), key=os.path.getmtime, reverse=True)
    for f in files[:limit]:
        try:
            data = json.loads(f.read_text(encoding="utf-8")) 
            first_msg = ""
            for ev in data.get("events", []):
                if ev.get("event_type") == "user_message":
                    first_msg = ev.get("content", "")[:80]
                    break
            threads.append({
                "id": data["id"],
                "preview": first_msg,
                "created_at": data.get("created_at", ""),
                "task_count": len(data.get("tasks", [])),
                "event_count": len(data.get("events", [])),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return threads


def delete_thread(thread_id: str, user_id: str | None = None) -> bool:
    """Delete a thread file."""
    path = _threads_dir(user_id) / f"{thread_id}.json"
    if path.exists():
        path.unlink()
        return True
    # Fallback: root dir
    path = THREADS_DIR / f"{thread_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def delete_all_threads(user_id: str | None = None) -> int:
    """Delete all thread files for a user. Returns count of deleted threads."""
    _ensure_dirs(user_id)
    count = 0
    for f in _threads_dir(user_id).glob("*.json"):
        try:
            f.unlink()
            count += 1
        except OSError:
            continue
    return count
