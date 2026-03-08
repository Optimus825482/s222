"""Shared dependencies for all route modules."""

import sys
from pathlib import Path

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

import base64
from bisect import bisect_right
import hashlib
import hmac
import os
import time
from collections import defaultdict

import bcrypt
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from config import MODELS
from core.models import Thread, PipelineType, EventType, AgentRole, AgentMetrics
from core.state import (
    save_thread,
    load_thread,
    list_threads,
    delete_thread,
    delete_all_threads,
)


# ── Rate Limiting ────────────────────────────────────────────────


class _RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._request_count = 0

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self._window
        hits = self._hits[key]

        first_valid_idx = bisect_right(hits, cutoff)
        if first_valid_idx:
            del hits[:first_valid_idx]

        if len(hits) >= self._max:
            self._request_count += 1
            if self._request_count % 256 == 0:
                self.cleanup(now=now)
            return False

        hits.append(now)
        self._request_count += 1
        if self._request_count % 256 == 0:
            self.cleanup(now=now)
        return True

    def cleanup(self, now: float | None = None) -> None:
        """Trim expired hit lists and remove inactive keys to avoid memory growth."""
        current_time = now if now is not None else time.time()
        cutoff = current_time - self._window

        for key in list(self._hits.keys()):
            hits = self._hits.get(key)
            if not hits:
                self._hits.pop(key, None)
                continue

            first_valid_idx = bisect_right(hits, cutoff)
            if first_valid_idx:
                del hits[:first_valid_idx]

            if not hits:
                self._hits.pop(key, None)


rate_limiter = _RateLimiter(max_requests=120, window_seconds=60)


# ── Auth ─────────────────────────────────────────────────────────

_BCRYPT_518518 = "$2b$12$.aDl7KHhQH7/x67LuKwnE.RKH7zrd5ezNuSNX/yS.MwoKEI2oiviK"

USERS = {
    "erkan": {
        "password_hash": _BCRYPT_518518,
        "full_name": "Erkan Erdem",
        "user_id": "erkan",
    },
    "yigit": {
        "password_hash": _BCRYPT_518518,
        "full_name": "Yiğit Avcı",
        "user_id": "yigit",
    },
}

_active_tokens: dict[str, str] = {}
_revoked_tokens: set[str] = set()

_TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", str(7 * 24 * 60 * 60)))
_TOKEN_SECRET = os.getenv("AUTH_TOKEN_SECRET", "dev-insecure-change-me")


def _issue_signed_token(user_id: str, ttl_seconds: int = _TOKEN_TTL_SECONDS) -> str:
    exp = int(time.time()) + int(ttl_seconds)
    user_b64 = (
        base64.urlsafe_b64encode(user_id.encode("utf-8")).decode("ascii").rstrip("=")
    )
    body = f"{user_b64}.{exp}"
    sig = hmac.new(
        _TOKEN_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"v1.{body}.{sig}"


def _validate_signed_token(token: str) -> str | None:
    if not token or token in _revoked_tokens:
        return None
    if not token.startswith("v1."):
        return None
    parts = token.split(".")
    if len(parts) != 4:
        return None
    _, user_b64, exp_raw, sig = parts
    body = f"{user_b64}.{exp_raw}"
    expected_sig = hmac.new(
        _TOKEN_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return None
    try:
        exp = int(exp_raw)
    except ValueError:
        return None
    if exp < int(time.time()):
        return None
    padded = user_b64 + "=" * (-len(user_b64) % 4)
    try:
        user_id = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    except Exception:
        return None
    return user_id if user_id in USERS else None


def _extract_bearer_token(authorization: str | None) -> str:
    raw = (authorization or "").strip()
    if raw.lower().startswith("bearer "):
        return raw[7:].strip()
    return ""


def _get_user_from_token(token: str) -> dict | None:
    if not token:
        return None
    user_id = _active_tokens.get(token)
    if user_id:
        return USERS.get(user_id)
    user_id = _validate_signed_token(token)
    if not user_id:
        return None
    return USERS.get(user_id)


def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(401, "Missing or invalid Authorization header")
    user = _get_user_from_token(token)
    if not user:
        raise HTTPException(401, "Invalid or expired token")
    return {"user_id": user["user_id"], "full_name": user["full_name"]}


# ── Audit Helper ─────────────────────────────────────────────────
# Delegate to shared_state for a single audit log (avoids split data).

from shared_state import (
    _audit as _shared_audit,
    _AUDIT_LOG as _shared_audit_log,
    _utcnow,
)  # noqa: E402

_audit_log = (
    _shared_audit_log  # alias so existing `deps.get_audit_log()` callers still work
)


def _audit(action: str, user_id: str, detail: str = "", **extra):
    _shared_audit(action, user_id, detail, **extra)


def get_audit_log() -> list[dict]:
    return list(_shared_audit_log)
