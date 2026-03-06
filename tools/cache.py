"""
In-memory LRU response cache with TTL for multi-agent pipeline.

Thread-safe via asyncio.Lock. Keyed on normalized query + pipeline type.
No external dependencies — pure stdlib implementation.

Usage:
    from tools.cache import get_cached_response, cache_response, cache_stats

    cached = await get_cached_response("What is Python?", "research")
    if cached is None:
        result = await run_pipeline(...)
        await cache_response("What is Python?", result, "research", confidence=0.9)
"""

from __future__ import annotations

import hashlib
import re
import time
import asyncio
from collections import OrderedDict
from typing import Any


# Precompiled regex for query normalization
_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")


class ResponseCache:
    """In-memory LRU cache with TTL for agent responses."""

    __slots__ = (
        "_cache",
        "_lock",
        "_max_size",
        "_default_ttl",
        "_hits",
        "_misses",
    )

    def __init__(self, max_size: int = 500, default_ttl: int = 300) -> None:
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._max_size = max(1, max_size)
        self._default_ttl = max(1, default_ttl)
        self._hits: int = 0
        self._misses: int = 0

    # ── Key Generation ───────────────────────────────────────────

    @staticmethod
    def _normalize_query(query: str) -> str:
        """Lowercase, strip punctuation, collapse whitespace."""
        text = query.lower().strip()
        text = _PUNCTUATION_RE.sub("", text)
        text = _WHITESPACE_RE.sub(" ", text).strip()
        return text

    def _make_key(self, query: str, pipeline_type: str = "auto") -> str:
        """Normalize query and create a deterministic cache key."""
        normalized = self._normalize_query(query)
        raw = f"{normalized}::{pipeline_type.lower().strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ── Core Operations ──────────────────────────────────────────

    async def get(self, query: str, pipeline_type: str = "auto") -> dict[str, Any] | None:
        """Get cached response. Returns None on miss or expiry."""
        key = self._make_key(query, pipeline_type)

        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            # TTL check (monotonic clock — immune to wall-clock drift)
            elapsed = time.monotonic() - entry["cached_at"]
            if elapsed > entry["ttl"]:
                del self._cache[key]
                self._misses += 1
                return None

            # LRU: move to end on access
            self._cache.move_to_end(key)
            entry["hits"] += 1
            self._hits += 1

            return {
                "response": entry["response"],
                "confidence": entry["confidence"],
                "cached_at": entry["cached_at"],
                "ttl": entry["ttl"],
                "hits": entry["hits"],
                "metadata": entry.get("metadata", {}),
            }

    async def set(
        self,
        query: str,
        response: str,
        pipeline_type: str = "auto",
        confidence: float = 0.0,
        ttl: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Cache a response with metadata. Skips error responses."""
        # Never cache error/timeout responses
        if isinstance(response, str) and response.lstrip().startswith(("[Error]", "[Timeout]")):
            return

        key = self._make_key(query, pipeline_type)
        effective_ttl = ttl if ttl is not None and ttl > 0 else self._default_ttl

        async with self._lock:
            # Update existing or insert new
            self._cache[key] = {
                "response": response,
                "confidence": confidence,
                "cached_at": time.monotonic(),
                "ttl": effective_ttl,
                "hits": 0,
                "metadata": metadata or {},
            }
            self._cache.move_to_end(key)

            # Evict oldest entries if over capacity
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    async def invalidate(self, query: str, pipeline_type: str = "auto") -> bool:
        """Remove a specific cache entry. Returns True if found."""
        key = self._make_key(query, pipeline_type)

        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> int:
        """Clear all cache entries. Returns count cleared."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
            "default_ttl": self._default_ttl,
        }


# ── Module-level Singleton ───────────────────────────────────────

_cache = ResponseCache()


async def get_cached_response(
    query: str, pipeline_type: str = "auto"
) -> dict[str, Any] | None:
    """Retrieve a cached response or None."""
    return await _cache.get(query, pipeline_type)


async def cache_response(
    query: str,
    response: str,
    pipeline_type: str = "auto",
    confidence: float = 0.0,
    ttl: int | None = None,
) -> None:
    """Store a response in cache."""
    await _cache.set(query, response, pipeline_type, confidence, ttl)


async def invalidate_cache(query: str, pipeline_type: str = "auto") -> bool:
    """Invalidate a specific cached entry."""
    return await _cache.invalidate(query, pipeline_type)


async def clear_cache() -> int:
    """Clear the entire cache. Returns count of entries removed."""
    return await _cache.clear()


def cache_stats() -> dict[str, Any]:
    """Get current cache statistics."""
    return _cache.stats()
