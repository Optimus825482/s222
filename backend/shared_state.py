"""Shared in-memory state used across route modules."""

import time
from collections import deque as _deque
from datetime import datetime, timezone
from typing import Any

# ── Shared Constants ─────────────────────────────────────────────

_AGENT_ROLES = ["orchestrator", "thinker", "speed", "researcher", "reasoner", "critic"]

# ── Shared Mutable State ─────────────────────────────────────────

_AUDIT_LOG: _deque[dict[str, Any]] = _deque(maxlen=1000)
_APP_START_TIME: float = time.time()


# ── Helpers ──────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _audit(event_type: str, user_id: str, detail: str = "", **extra: Any) -> None:
    """Append an audit entry to the in-memory FIFO log."""
    _AUDIT_LOG.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "detail": detail,
        **extra,
    })
