"""Shared in-memory state used across route modules."""

import logging
import os
import time
from collections import deque as _deque
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("shared_state")

# ── Shared Constants ─────────────────────────────────────────────

_AGENT_ROLES = ["orchestrator", "thinker", "speed", "researcher", "reasoner", "critic"]

# ── Adaptive Sliding Window ──────────────────────────────────────
# Window size adapts based on traffic: low=2000, normal=5000, high=10000
# Configurable via AUDIT_WINDOW_SIZE env var (default: adaptive)

_AUDIT_WINDOW_BASE = int(os.getenv("AUDIT_WINDOW_SIZE", "5000"))
_AUDIT_WINDOW_MIN = 2000
_AUDIT_WINDOW_MAX = 15000

# ── Shared Mutable State ─────────────────────────────────────────

_AUDIT_LOG: _deque[dict[str, Any]] = _deque(maxlen=_AUDIT_WINDOW_BASE)
_APP_START_TIME: float = time.time()
_AUDIT_RATE_COUNTER: int = 0
_AUDIT_RATE_WINDOW_START: float = time.time()


# ── Helpers ──────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _adapt_window_size() -> None:
    """
    Dynamically resize audit window based on event rate.
    High traffic (>100 events/min) → expand to 15000
    Low traffic (<10 events/min) → shrink to 2000
    Normal → keep at base (5000)
    """
    global _AUDIT_LOG, _AUDIT_RATE_COUNTER, _AUDIT_RATE_WINDOW_START

    _AUDIT_RATE_COUNTER += 1
    now = time.time()
    elapsed = now - _AUDIT_RATE_WINDOW_START

    # Check every 60 seconds
    if elapsed < 60:
        return

    rate_per_min = _AUDIT_RATE_COUNTER / (elapsed / 60)
    _AUDIT_RATE_COUNTER = 0
    _AUDIT_RATE_WINDOW_START = now

    if rate_per_min > 100:
        new_max = _AUDIT_WINDOW_MAX
    elif rate_per_min < 10:
        new_max = _AUDIT_WINDOW_MIN
    else:
        new_max = _AUDIT_WINDOW_BASE

    if _AUDIT_LOG.maxlen != new_max:
        old_items = list(_AUDIT_LOG)
        _AUDIT_LOG = _deque(old_items[-new_max:], maxlen=new_max)
        logger.debug(f"Audit window resized: {len(old_items)} → maxlen={new_max} (rate={rate_per_min:.0f}/min)")


def _audit(event_type: str, user_id: str, detail: str = "", **extra: Any) -> None:
    """
    Append an audit entry. Uses Redis Stream if available, falls back to in-memory deque.
    Adaptive window prevents data loss under high traffic.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "detail": detail,
        **extra,
    }

    # Try Redis Stream first (persistent, survives restarts)
    try:
        from tools.redis_client import audit_stream_add
        audit_stream_add(entry)
    except Exception:
        pass  # Redis unavailable — fall through to in-memory

    # Always keep in-memory copy for fast access
    _adapt_window_size()
    _AUDIT_LOG.append(entry)


def get_audit_stats() -> dict[str, Any]:
    """Get audit log statistics."""
    return {
        "in_memory_count": len(_AUDIT_LOG),
        "max_size": _AUDIT_LOG.maxlen,
        "oldest": _AUDIT_LOG[0]["timestamp"] if _AUDIT_LOG else None,
        "newest": _AUDIT_LOG[-1]["timestamp"] if _AUDIT_LOG else None,
    }
