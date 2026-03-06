"""
Circuit breaker for multi-agent pipeline reliability.

Prevents cascade failures by tracking per-agent error rates and
temporarily disabling agents that exceed the failure threshold.

States:
    CLOSED    → Normal operation, calls pass through.
    OPEN      → Agent failing, calls rejected immediately.
    HALF_OPEN → Recovery probe: limited calls allowed to test health.

Usage:
    from tools.circuit_breaker import get_circuit_breaker

    cb = get_circuit_breaker()
    if cb.is_available("researcher"):
        try:
            result = await call_agent("researcher", ...)
            cb.record_success("researcher")
        except Exception as e:
            cb.record_failure("researcher", str(e))
    else:
        fallback = cb.get_fallback_agent("researcher")
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failing — reject calls
    HALF_OPEN = "half_open"  # Testing recovery


# Agent fallback mapping — semantically similar roles
_FALLBACK_MAP: dict[str, str] = {
    "researcher": "thinker",   # both do analysis
    "thinker": "reasoner",     # both do deep thinking
    "reasoner": "thinker",     # bidirectional
    "speed": "researcher",     # both can format
}


class CircuitBreaker:
    """Per-agent circuit breaker to prevent cascade failures."""

    __slots__ = (
        "_breakers",
        "_failure_threshold",
        "_recovery_timeout",
        "_success_threshold",
    )

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ) -> None:
        self._breakers: dict[str, dict[str, Any]] = {}
        self._failure_threshold = max(1, failure_threshold)
        self._recovery_timeout = max(1.0, recovery_timeout)
        self._success_threshold = max(1, success_threshold)

    # ── Internal Helpers ─────────────────────────────────────────

    def _ensure_breaker(self, agent_role: str) -> dict[str, Any]:
        """Lazily initialize a breaker entry for an agent role."""
        if agent_role not in self._breakers:
            self._breakers[agent_role] = {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": 0.0,
                "last_error": "",
                "total_failures": 0,
                "total_successes": 0,
            }
        return self._breakers[agent_role]

    def _try_transition_to_half_open(self, breaker: dict[str, Any]) -> None:
        """Transition OPEN → HALF_OPEN if recovery timeout has elapsed."""
        if breaker["state"] is not CircuitState.OPEN:
            return
        elapsed = time.monotonic() - breaker["last_failure_time"]
        if elapsed >= self._recovery_timeout:
            breaker["state"] = CircuitState.HALF_OPEN
            breaker["success_count"] = 0

    # ── Public API ───────────────────────────────────────────────

    def get_state(self, agent_role: str) -> CircuitState:
        """Get current circuit state for an agent."""
        breaker = self._ensure_breaker(agent_role)
        self._try_transition_to_half_open(breaker)
        return breaker["state"]

    def record_success(self, agent_role: str) -> None:
        """Record a successful call. May close a half-open circuit."""
        breaker = self._ensure_breaker(agent_role)
        breaker["total_successes"] += 1

        if breaker["state"] is CircuitState.HALF_OPEN:
            breaker["success_count"] += 1
            if breaker["success_count"] >= self._success_threshold:
                # Recovered — close the circuit
                breaker["state"] = CircuitState.CLOSED
                breaker["failure_count"] = 0
                breaker["success_count"] = 0

        elif breaker["state"] is CircuitState.CLOSED:
            # Reset consecutive failure count on success
            breaker["failure_count"] = 0

    def record_failure(self, agent_role: str, error: str = "") -> None:
        """Record a failed call. May open the circuit."""
        breaker = self._ensure_breaker(agent_role)
        breaker["total_failures"] += 1
        breaker["last_failure_time"] = time.monotonic()
        breaker["last_error"] = error

        if breaker["state"] is CircuitState.HALF_OPEN:
            # Recovery probe failed — back to open
            breaker["state"] = CircuitState.OPEN
            breaker["success_count"] = 0

        elif breaker["state"] is CircuitState.CLOSED:
            breaker["failure_count"] += 1
            if breaker["failure_count"] >= self._failure_threshold:
                breaker["state"] = CircuitState.OPEN

    def is_available(self, agent_role: str) -> bool:
        """Check if agent is available (circuit not fully open)."""
        state = self.get_state(agent_role)
        return state is not CircuitState.OPEN

    def get_fallback_agent(self, failed_role: str) -> str | None:
        """Suggest a fallback agent when one fails.

        Returns None if no fallback is available or the fallback
        itself has an open circuit.
        """
        fallback = _FALLBACK_MAP.get(failed_role)
        if fallback is None:
            return None
        # Only suggest if the fallback is actually available
        if self.is_available(fallback):
            return fallback
        return None

    def status(self) -> dict[str, dict[str, Any]]:
        """Get status of all tracked circuit breakers."""
        result: dict[str, dict[str, Any]] = {}
        for role, breaker in self._breakers.items():
            self._try_transition_to_half_open(breaker)
            result[role] = {
                "state": breaker["state"].value,
                "failure_count": breaker["failure_count"],
                "success_count": breaker["success_count"],
                "last_failure_time": breaker["last_failure_time"],
                "last_error": breaker["last_error"],
                "total_failures": breaker["total_failures"],
                "total_successes": breaker["total_successes"],
            }
        return result

    def reset(self, agent_role: str | None = None) -> None:
        """Reset circuit breaker(s).

        If agent_role is given, reset only that agent.
        If None, reset all breakers.
        """
        if agent_role is not None:
            if agent_role in self._breakers:
                self._breakers[agent_role] = {
                    "state": CircuitState.CLOSED,
                    "failure_count": 0,
                    "success_count": 0,
                    "last_failure_time": 0.0,
                    "last_error": "",
                    "total_failures": 0,
                    "total_successes": 0,
                }
        else:
            self._breakers.clear()


# ── Module-level Singleton ───────────────────────────────────────

_breaker = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    """Get the global circuit breaker instance."""
    return _breaker
