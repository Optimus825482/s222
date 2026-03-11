"""
Redis HA Client — Sentinel-backed Redis connection with automatic failover.

Provides:
- Redis Sentinel discovery for master/slave topology
- Automatic failover when master goes down
- Connection pooling with health checks
- Pub/Sub wrapper for EventBus integration
- Graceful fallback to standalone Redis or in-memory

Usage:
    from tools.redis_client import get_redis, get_pubsub

    r = get_redis()
    r.set("key", "value")

    pubsub = get_pubsub()
    pubsub.subscribe("channel")
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from typing import Any, cast

logger = logging.getLogger("redis_client")

# Lazy imports — Redis is optional
_redis_mod = None
_sentinel_mod = None


def _ensure_redis():
    global _redis_mod, _sentinel_mod
    if _redis_mod is None:
        try:
            import redis
            import redis.sentinel
            _redis_mod = redis
            _sentinel_mod = redis.sentinel
        except ImportError:
            raise ImportError(
                "redis package not installed. Run: pip install redis[hiredis]"
            )


# ── Configuration ────────────────────────────────────────────────

def _get_config() -> dict[str, Any]:
    """Read Redis config from environment."""
    return {
        "mode": os.getenv("REDIS_MODE", "standalone"),  # standalone | sentinel | cluster
        "url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        "password": os.getenv("REDIS_PASSWORD", ""),
        "sentinel_hosts": os.getenv("REDIS_SENTINEL_HOSTS", "sentinel-0:26379,sentinel-1:26379,sentinel-2:26379"),
        "sentinel_master": os.getenv("REDIS_SENTINEL_MASTER", "mymaster"),
        "sentinel_password": os.getenv("REDIS_SENTINEL_PASSWORD", ""),
        "db": int(os.getenv("REDIS_DB", "0")),
        "socket_timeout": float(os.getenv("REDIS_SOCKET_TIMEOUT", "5.0")),
        "retry_on_timeout": True,
        "health_check_interval": int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30")),
        "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "20")),
        # Audit stream TTL (days)
        "audit_ttl_days": int(os.getenv("REDIS_AUDIT_TTL_DAYS", "30")),
    }


# ── Singleton ────────────────────────────────────────────────────

_client: Any = None
_sentinel: Any = None
_config: dict[str, Any] | None = None
_fallback_mode = False


def get_redis():
    """
    Get Redis client with HA support.
    Falls back to in-memory dict if Redis unavailable.
    """
    global _client, _sentinel, _config, _fallback_mode

    if _fallback_mode:
        return _get_memory_fallback()

    if _client is not None:
        try:
            _client.ping()
            return _client
        except Exception:
            logger.warning("Redis connection lost, reconnecting...")
            _client = None

    try:
        _ensure_redis()
    except ImportError:
        logger.warning("Redis not installed — using in-memory fallback")
        _fallback_mode = True
        return _get_memory_fallback()

    _config = _get_config()

    try:
        if _config["mode"] == "sentinel":
            _client = _connect_sentinel(_config)
        else:
            _client = _connect_standalone(_config)

        _client.ping()
        logger.info(f"Redis connected (mode={_config['mode']})")
        return _client

    except Exception as e:
        logger.warning(f"Redis connection failed: {e} — using in-memory fallback")
        _fallback_mode = True
        return _get_memory_fallback()


def _connect_sentinel(cfg: dict) -> Any:
    """Connect via Redis Sentinel for HA."""
    _ensure_redis()
    sentinel_module: Any = cast(Any, _sentinel_mod)
    assert sentinel_module is not None
    hosts = []
    for h in cfg["sentinel_hosts"].split(","):
        h = h.strip()
        if ":" in h:
            host, port = h.rsplit(":", 1)
            hosts.append((host, int(port)))
        else:
            hosts.append((h, 26379))

    sentinel_kwargs = {}
    if cfg["sentinel_password"]:
        sentinel_kwargs["password"] = cfg["sentinel_password"]

    sentinel = sentinel_module.Sentinel(
        hosts,
        socket_timeout=cfg["socket_timeout"],
        sentinel_kwargs=sentinel_kwargs,
    )

    master = sentinel.master_for(
        cfg["sentinel_master"],
        socket_timeout=cfg["socket_timeout"],
        password=cfg["password"] or None,
        db=cfg["db"],
        retry_on_timeout=cfg["retry_on_timeout"],
        health_check_interval=cfg["health_check_interval"],
        max_connections=cfg["max_connections"],
    )
    return master


def _connect_standalone(cfg: dict) -> Any:
    """Connect to standalone Redis."""
    _ensure_redis()
    redis_module: Any = cast(Any, _redis_mod)
    assert redis_module is not None
    return redis_module.Redis.from_url(
        cfg["url"],
        password=cfg["password"] or None,
        db=cfg["db"],
        socket_timeout=cfg["socket_timeout"],
        retry_on_timeout=cfg["retry_on_timeout"],
        health_check_interval=cfg["health_check_interval"],
        max_connections=cfg["max_connections"],
        decode_responses=True,
    )


# ── In-Memory Fallback ──────────────────────────────────────────

class _MemoryFallback:
    """Minimal Redis-like interface for when Redis is unavailable."""

    def __init__(self):
        self._store: dict[str, Any] = {}
        self._streams: dict[str, list] = {}
        self._pubsub_handlers: dict[str, list] = {}

    def ping(self) -> bool:
        return True

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def set(self, key: str, value: Any, ex: int | None = None) -> bool:
        self._store[key] = value
        return True

    def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    def xadd(self, name: str, fields: dict, maxlen: int | None = None) -> str:
        if name not in self._streams:
            self._streams[name] = []
        entry_id = f"{int(time.time() * 1000)}-0"
        self._streams[name].append({"id": entry_id, **fields})
        if maxlen and len(self._streams[name]) > maxlen:
            self._streams[name] = self._streams[name][-maxlen:]
        return entry_id

    def xrange(self, name: str, min: str = "-", max: str = "+", count: int | None = None):
        stream = self._streams.get(name, [])
        if count:
            return stream[-count:]
        return stream

    def xlen(self, name: str) -> int:
        return len(self._streams.get(name, []))

    def publish(self, channel: str, message: str) -> int:
        return 0  # No real pub/sub in memory mode

    def pubsub(self):
        return _MemoryPubSub()

    def incr(self, key: str) -> int:
        val = int(self._store.get(key, 0)) + 1
        self._store[key] = val
        return val

    def expire(self, key: str, seconds: int) -> bool:
        return True  # No-op in memory mode

    def pipeline(self):
        return _MemoryPipeline(self)


class _MemoryPubSub:
    """Minimal PubSub stub."""
    def subscribe(self, *channels): pass
    def unsubscribe(self, *channels): pass
    def listen(self): return iter([])
    def get_message(self, timeout=None): return None


class _MemoryPipeline:
    """Minimal pipeline stub."""
    def __init__(self, client):
        self._client = client
        self._ops = []

    def __enter__(self): return self
    def __exit__(self, *a): pass

    def set(self, key, value, ex=None):
        self._ops.append(("set", key, value, ex))
        return self

    def execute(self):
        results = []
        for op in self._ops:
            if op[0] == "set":
                results.append(self._client.set(op[1], op[2], ex=op[3]))
        self._ops.clear()
        return results


_memory_fallback: _MemoryFallback | None = None


def _get_memory_fallback() -> _MemoryFallback:
    global _memory_fallback
    if _memory_fallback is None:
        _memory_fallback = _MemoryFallback()
    return _memory_fallback


# ── Pub/Sub Helper ───────────────────────────────────────────────

def get_pubsub():
    """Get a Redis PubSub instance."""
    return get_redis().pubsub()


# ── Audit Stream ─────────────────────────────────────────────────

def audit_stream_add(event: dict[str, Any], stream_name: str = "audit:events") -> str:
    """
    Add an audit event to Redis Stream with TTL-based trimming.
    Replaces in-memory deque for audit trail.
    """
    r = get_redis()
    cfg = _config or _get_config()
    max_len = 50_000  # Cap stream length instead of relying only on TTL

    # Flatten nested dicts for Redis stream compatibility
    flat = {}
    for k, v in event.items():
        flat[k] = json.dumps(v) if isinstance(v, (dict, list)) else str(v)

    return r.xadd(stream_name, flat, maxlen=max_len)


def audit_stream_read(
    stream_name: str = "audit:events",
    count: int = 100,
) -> list[dict[str, Any]]:
    """Read recent audit events from Redis Stream."""
    r = get_redis()
    entries = r.xrange(stream_name, count=count)
    if isinstance(entries, list) and entries and isinstance(entries[0], dict):
        return entries  # Memory fallback format
    # Real Redis returns list of (id, fields) tuples
    result = []
    for entry in entries:
        if isinstance(entry, tuple) and len(entry) == 2:
            eid, fields = entry
            fields["_stream_id"] = eid
            result.append(fields)
    return result


# ── Health Check ─────────────────────────────────────────────────

def redis_health() -> dict[str, Any]:
    """Health check for Redis connection."""
    try:
        r = get_redis()
        start = time.time()
        r.ping()
        latency_ms = (time.time() - start) * 1000
        return {
            "status": "healthy",
            "mode": (_config or {}).get("mode", "fallback"),
            "fallback": _fallback_mode,
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "fallback": _fallback_mode,
        }


def reset_client() -> None:
    """Force reconnection on next get_redis() call."""
    global _client, _fallback_mode
    _client = None
    _fallback_mode = False
