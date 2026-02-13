"""
State management — 12-Factor #5 & #12: Unified state, stateless reducer.
JSON file-based persistence for threads.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import Thread

DATA_DIR = Path(__file__).parent.parent / "data"
THREADS_DIR = DATA_DIR / "threads"


def _ensure_dirs() -> None:
    THREADS_DIR.mkdir(parents=True, exist_ok=True)


def save_thread(thread: Thread) -> str:
    """Persist thread to JSON file. Returns thread id."""
    _ensure_dirs()
    path = THREADS_DIR / f"{thread.id}.json"
    path.write_text(thread.model_dump_json(indent=2), encoding="utf-8")
    return thread.id


def load_thread(thread_id: str) -> Thread | None:
    """Load thread from JSON file."""
    path = THREADS_DIR / f"{thread_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Thread.model_validate(data)


def list_threads(limit: int = 50) -> list[dict]:
    """List recent threads with basic info."""
    _ensure_dirs()
    threads = []
    files = sorted(THREADS_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
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


def delete_thread(thread_id: str) -> bool:
    """Delete a thread file."""
    path = THREADS_DIR / f"{thread_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False
