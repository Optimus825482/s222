"""
Agent Retry and Fallback Mechanisms.
Provides resilience for agent failures with retry logic and fallback agents.

Features:
- Automatic retry with exponential backoff
- Fallback to alternative agents when primary fails
- Circuit breaker pattern to prevent cascade failures
- Error classification for smart retry decisions
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of errors for retry decisions."""
    TRANSIENT = "transient"      # Network, timeout, rate limit - RETRY
    PERMANENT = "permanent"      # Auth, invalid request - NO RETRY
    UNKNOWN = "unknown"          # Unknown error - RETRY with caution


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay_ms: float = 1000.0      # Initial delay
    max_delay_ms: float = 30000.0      # Maximum delay
    exponential_base: float = 2.0       # Exponential backoff multiplier
    jitter: bool = True                 # Add random jitter to prevent thundering herd
    
    # Error-specific retry counts
    rate_limit_retries: int = 5         # More retries for rate limits
    timeout_retries: int = 3
    network_retries: int = 3


@dataclass
class FallbackConfig:
    """Configuration for fallback agent behavior."""
    enabled: bool = True
    # Primary agent -> Fallback agent mapping
    fallback_map: dict[str, str] = field(default_factory=lambda: {
        "thinker": "researcher",
        "researcher": "thinker",
        "reasoner": "thinker",
        "speed": "researcher",
        "critic": "thinker",
        "orchestrator": "thinker",  # Orchestrator falls back to thinker
    })
    # Agents that should NOT be used as fallbacks
    excluded_fallbacks: list[str] = field(default_factory=lambda: ["critic"])
    # Maximum fallback attempts before giving up
    max_fallbacks: int = 2


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""
    enabled: bool = True
    failure_threshold: int = 5          # Open after this many failures
    recovery_timeout_ms: float = 60000.0  # Time before attempting recovery
    half_open_requests: int = 1          # Requests to test in half-open state


@dataclass
class CircuitBreakerState:
    """State for a single agent's circuit breaker."""
    failures: int = 0
    last_failure_time: float = 0.0
    is_open: bool = False
    half_open_successes: int = 0


# Global circuit breaker state per agent
_circuit_breakers: dict[str, CircuitBreakerState] = {}


def classify_error(error: Exception) -> ErrorType:
    """Classify an error to determine if retry is appropriate."""
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()
    
    # Transient errors - retry is appropriate
    transient_indicators = [
        "timeout", "timed out", "connection", "network", "socket",
        "rate limit", "429", "503", "502", "504", "overloaded",
        "temporarily", "unavailable", "reset", "broken pipe",
    ]
    
    # Permanent errors - don't retry
    permanent_indicators = [
        "auth", "unauthorized", "forbidden", "401", "403",
        "invalid", "malformed", "bad request", "400",
        "not found", "404", "api key", "permission",
    ]
    
    for indicator in transient_indicators:
        if indicator in error_str or indicator in error_type:
            return ErrorType.TRANSIENT
    
    for indicator in permanent_indicators:
        if indicator in error_str or indicator in error_type:
            return ErrorType.PERMANENT
    
    return ErrorType.UNKNOWN


def calculate_delay(
    attempt: int,
    config: RetryConfig,
    error_type: ErrorType
) -> float:
    """Calculate delay for retry with exponential backoff."""
    if error_type == ErrorType.PERMANENT:
        return 0  # No delay for permanent errors (won't retry anyway)
    
    # Exponential backoff
    delay = config.base_delay_ms * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay_ms)
    
    # Add jitter (±25%)
    if config.jitter:
        import random
        jitter = delay * 0.25 * (random.random() * 2 - 1)
        delay = delay + jitter
    
    return max(0, delay)


def should_retry(
    error: Exception,
    attempt: int,
    config: RetryConfig
) -> tuple[bool, float]:
    """Determine if should retry and how long to wait."""
    error_type = classify_error(error)
    
    if error_type == ErrorType.PERMANENT:
        return False, 0
    
    max_retries = config.max_retries
    error_str = str(error).lower()
    
    # Adjust max retries based on error type
    if "rate limit" in error_str or "429" in error_str:
        max_retries = config.rate_limit_retries
    elif "timeout" in error_str:
        max_retries = config.timeout_retries
    elif "network" in error_str or "connection" in error_str:
        max_retries = config.network_retries
    
    if attempt >= max_retries:
        return False, 0
    
    delay = calculate_delay(attempt, config, error_type)
    return True, delay


def get_circuit_breaker(agent_role: str) -> CircuitBreakerState:
    """Get or create circuit breaker for an agent."""
    if agent_role not in _circuit_breakers:
        _circuit_breakers[agent_role] = CircuitBreakerState()
    return _circuit_breakers[agent_role]


def is_circuit_open(agent_role: str, config: CircuitBreakerConfig | None) -> bool:
    """Check if circuit breaker is open for an agent."""
    if config is None or not config.enabled:
        return False
    
    cb = get_circuit_breaker(agent_role)
    
    if not cb.is_open:
        return False
    
    # Check if recovery timeout has passed
    elapsed = (time.time() * 1000) - cb.last_failure_time
    if elapsed >= config.recovery_timeout_ms:
        # Transition to half-open
        cb.is_open = False  # Will be set back to open if test fails
        cb.half_open_successes = 0
        logger.info(f"Circuit breaker for {agent_role} entering half-open state")
        return False
    
    return True


def record_success(agent_role: str, config: CircuitBreakerConfig | None) -> None:
    """Record a successful call, potentially closing the circuit."""
    if config is None or not config.enabled:
        return
    
    cb = get_circuit_breaker(agent_role)
    cb.failures = 0
    cb.is_open = False
    cb.half_open_successes = 0


def record_failure(agent_role: str, config: CircuitBreakerConfig | None) -> None:
    """Record a failed call, potentially opening the circuit."""
    if config is None or not config.enabled:
        return
    
    cb = get_circuit_breaker(agent_role)
    cb.failures += 1
    cb.last_failure_time = time.time() * 1000
    
    if cb.failures >= config.failure_threshold:
        cb.is_open = True
        logger.warning(
            f"Circuit breaker OPEN for {agent_role} after {cb.failures} failures"
        )


def get_fallback_agent(
    primary_agent: str,
    config: FallbackConfig
) -> Optional[str]:
    """Get the fallback agent for a failed primary agent."""
    if not config.enabled:
        return None
    
    fallback = config.fallback_map.get(primary_agent)
    
    if not fallback:
        return None
    
    # Check if fallback is excluded
    if fallback in config.excluded_fallbacks:
        # Try to find a non-excluded fallback
        for agent, fb in config.fallback_map.items():
            if agent == primary_agent and fb not in config.excluded_fallbacks:
                return fb
        return None
    
    return fallback


async def execute_with_retry(
    agent_role: str,
    execute_fn: Callable,
    *args,
    retry_config: Optional[RetryConfig] = None,
    circuit_config: Optional[CircuitBreakerConfig] = None,
    **kwargs
) -> tuple[bool, Any, Optional[str]]:
    """
    Execute a function with retry logic and circuit breaker.
    
    Returns:
        (success, result, error_message)
    """
    retry_config = retry_config or RetryConfig()
    circuit_config = circuit_config or CircuitBreakerConfig()
    
    # Check circuit breaker
    if is_circuit_open(agent_role, circuit_config):
        return False, None, f"Circuit breaker open for {agent_role}"
    
    last_error = None
    
    for attempt in range(retry_config.max_retries + 1):
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(execute_fn):
                result = await execute_fn(*args, **kwargs)
            else:
                result = execute_fn(*args, **kwargs)
            
            # Success - record and return
            record_success(agent_role, circuit_config)
            return True, result, None
            
        except Exception as e:
            last_error = e
            error_str = f"{type(e).__name__}: {e}"
            
            # Check if should retry
            should, delay = should_retry(e, attempt, retry_config)
            
            if not should:
                logger.error(
                    f"Agent {agent_role} failed permanently on attempt {attempt + 1}: {error_str}"
                )
                record_failure(agent_role, circuit_config)
                return False, None, error_str
            
            logger.warning(
                f"Agent {agent_role} failed on attempt {attempt + 1}, "
                f"retrying in {delay:.0f}ms: {error_str}"
            )
            
            # Wait before retry
            if delay > 0:
                await asyncio.sleep(delay / 1000)
    
    # All retries exhausted
    record_failure(agent_role, circuit_config)
    return False, None, f"All retries exhausted: {last_error}"


# ── Convenience Functions ────────────────────────────────────────

# Default configurations
DEFAULT_RETRY_CONFIG = RetryConfig()
DEFAULT_FALLBACK_CONFIG = FallbackConfig()
DEFAULT_CIRCUIT_CONFIG = CircuitBreakerConfig()


def reset_circuit_breakers() -> None:
    """Reset all circuit breaker states."""
    global _circuit_breakers
    _circuit_breakers = {}


def get_agent_health() -> dict[str, dict]:
    """Get health status of all agents based on circuit breaker state."""
    result = {}
    for agent_role, cb in _circuit_breakers.items():
        result[agent_role] = {
            "failures": cb.failures,
            "is_open": cb.is_open,
            "last_failure_time": cb.last_failure_time,
            "status": "unhealthy" if cb.is_open else "healthy",
        }
    return result