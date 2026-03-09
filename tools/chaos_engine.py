"""
Chaos Engineering Framework — Controlled fault injection for resilience testing.

Scenarios:
- Agent timeout simulation
- Memory pressure on event bus
- Network latency injection (tool calls)
- Random agent failure
- Database connection drop

Usage:
    from tools.chaos_engine import chaos

    # Run a specific scenario
    result = await chaos.inject("agent_timeout", target="researcher", duration_s=10)

    # Run random chaos (for scheduled testing)
    result = await chaos.random_inject()

    # Get resilience report
    report = chaos.get_report()
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("chaos_engine")


class ChaosScenario(str, Enum):
    AGENT_TIMEOUT = "agent_timeout"
    EVENT_BUS_OVERLOAD = "event_bus_overload"
    TOOL_LATENCY = "tool_latency"
    AGENT_CRASH = "agent_crash"
    DB_CONNECTION_DROP = "db_connection_drop"
    MEMORY_PRESSURE = "memory_pressure"


class ChaosResult:
    def __init__(self, scenario: str, target: str, success: bool, detail: str = "", recovery_ms: float = 0):
        self.scenario = scenario
        self.target = target
        self.success = success
        self.detail = detail
        self.recovery_ms = recovery_ms
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "target": self.target,
            "success": self.success,
            "detail": self.detail,
            "recovery_ms": self.recovery_ms,
            "timestamp": self.timestamp,
        }


class ChaosEngine:
    """Controlled fault injection engine for resilience testing."""

    def __init__(self):
        self._enabled = False
        self._history: list[dict[str, Any]] = []
        self._max_history = 100
        self._active_injections: dict[str, float] = {}

    def enable(self) -> None:
        self._enabled = True
        logger.warning("Chaos engineering ENABLED — fault injection active")

    def disable(self) -> None:
        self._enabled = False
        self._active_injections.clear()
        logger.info("Chaos engineering disabled")

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    async def inject(
        self,
        scenario: str,
        target: str = "",
        duration_s: float = 5.0,
        intensity: float = 0.5,
    ) -> ChaosResult:
        """
        Inject a specific fault scenario.
        intensity: 0.0 (mild) to 1.0 (severe)
        """
        if not self._enabled:
            return ChaosResult(scenario, target, False, "Chaos engine not enabled")

        handler = {
            ChaosScenario.AGENT_TIMEOUT: self._inject_agent_timeout,
            ChaosScenario.EVENT_BUS_OVERLOAD: self._inject_bus_overload,
            ChaosScenario.TOOL_LATENCY: self._inject_tool_latency,
            ChaosScenario.AGENT_CRASH: self._inject_agent_crash,
            ChaosScenario.DB_CONNECTION_DROP: self._inject_db_drop,
            ChaosScenario.MEMORY_PRESSURE: self._inject_memory_pressure,
        }.get(scenario)

        if not handler:
            return ChaosResult(scenario, target, False, f"Unknown scenario: {scenario}")

        start = time.time()
        try:
            result = await handler(target, duration_s, intensity)
            result.recovery_ms = (time.time() - start) * 1000
            self._record(result)
            return result
        except Exception as e:
            r = ChaosResult(scenario, target, False, f"Injection failed: {e}")
            r.recovery_ms = (time.time() - start) * 1000
            self._record(r)
            return r

    async def random_inject(self) -> ChaosResult:
        """Inject a random fault scenario for scheduled chaos testing."""
        if not self._enabled:
            return ChaosResult("random", "", False, "Chaos engine not enabled")

        scenario = random.choice(list(ChaosScenario))
        targets = ["orchestrator", "researcher", "thinker", "reasoner", "speed", "critic"]
        target = random.choice(targets)
        duration = random.uniform(2.0, 10.0)
        intensity = random.uniform(0.3, 0.8)

        return await self.inject(scenario.value, target, duration, intensity)

    # ── Scenario Implementations ─────────────────────────────────

    async def _inject_agent_timeout(self, target: str, duration_s: float, intensity: float) -> ChaosResult:
        """Simulate agent becoming unresponsive."""
        self._active_injections[f"timeout:{target}"] = time.time() + duration_s
        logger.warning(f"CHAOS: Agent {target} timeout injected for {duration_s}s")

        # The actual timeout is checked by is_agent_degraded()
        await asyncio.sleep(min(duration_s, 2.0))  # Don't actually block long
        return ChaosResult(
            ChaosScenario.AGENT_TIMEOUT, target, True,
            f"Agent {target} marked as timed out for {duration_s}s",
        )

    async def _inject_bus_overload(self, target: str, duration_s: float, intensity: float) -> ChaosResult:
        """Flood event bus with dummy messages to test backpressure."""
        try:
            from core.event_bus import get_event_bus
            from core.protocols import MessageEnvelope, MessageType, ChannelType
            bus = get_event_bus()
            msg_count = int(50 * intensity)

            for i in range(msg_count):
                msg = MessageEnvelope(
                    source_agent="chaos_engine",
                    channel="chaos:test",
                    channel_type=ChannelType.BROADCAST,
                    message_type=MessageType.HEARTBEAT,
                    payload={"chaos": True, "seq": i},
                )
                await bus.publish(msg)

            return ChaosResult(
                ChaosScenario.EVENT_BUS_OVERLOAD, "event_bus", True,
                f"Sent {msg_count} flood messages to event bus",
            )
        except Exception as e:
            return ChaosResult(ChaosScenario.EVENT_BUS_OVERLOAD, "event_bus", False, str(e))

    async def _inject_tool_latency(self, target: str, duration_s: float, intensity: float) -> ChaosResult:
        """Add artificial latency to tool calls."""
        delay_ms = int(1000 * intensity * duration_s)
        self._active_injections[f"latency:{target}"] = time.time() + duration_s
        logger.warning(f"CHAOS: Tool latency +{delay_ms}ms injected for {target}")
        return ChaosResult(
            ChaosScenario.TOOL_LATENCY, target, True,
            f"Added {delay_ms}ms latency to {target} tools for {duration_s}s",
        )

    async def _inject_agent_crash(self, target: str, duration_s: float, intensity: float) -> ChaosResult:
        """Simulate agent crash by unsubscribing from event bus."""
        try:
            from core.event_bus import get_event_bus
            bus = get_event_bus()
            removed = bus.unsubscribe_all(target)
            self._active_injections[f"crash:{target}"] = time.time() + duration_s
            logger.warning(f"CHAOS: Agent {target} crashed (removed {removed} subscriptions)")
            return ChaosResult(
                ChaosScenario.AGENT_CRASH, target, True,
                f"Agent {target} unsubscribed ({removed} subs removed), recovery in {duration_s}s",
            )
        except Exception as e:
            return ChaosResult(ChaosScenario.AGENT_CRASH, target, False, str(e))

    async def _inject_db_drop(self, target: str, duration_s: float, intensity: float) -> ChaosResult:
        """Simulate database connection failure."""
        self._active_injections["db_drop"] = time.time() + duration_s
        logger.warning(f"CHAOS: DB connection drop simulated for {duration_s}s")
        return ChaosResult(
            ChaosScenario.DB_CONNECTION_DROP, "postgres", True,
            f"DB drop flag set for {duration_s}s — queries will see simulated failures",
        )

    async def _inject_memory_pressure(self, target: str, duration_s: float, intensity: float) -> ChaosResult:
        """Simulate memory pressure by allocating temporary buffers."""
        size_mb = int(10 * intensity)
        _pressure = [bytearray(1024 * 1024) for _ in range(size_mb)]
        await asyncio.sleep(min(duration_s, 3.0))
        del _pressure
        return ChaosResult(
            ChaosScenario.MEMORY_PRESSURE, "system", True,
            f"Allocated {size_mb}MB for {min(duration_s, 3.0)}s then released",
        )

    # ── Query Methods ────────────────────────────────────────────

    def is_agent_degraded(self, agent_role: str) -> str | None:
        """Check if an agent has active chaos injection. Returns scenario name or None."""
        now = time.time()
        for key, expires in list(self._active_injections.items()):
            if now > expires:
                del self._active_injections[key]
                continue
            if agent_role in key:
                return key.split(":")[0]
        return None

    def get_tool_latency_ms(self, tool_name: str) -> int:
        """Get additional latency to inject for a tool (0 if none)."""
        now = time.time()
        for key, expires in self._active_injections.items():
            if key.startswith("latency:") and now < expires:
                return 500  # Fixed 500ms injection
        return 0

    def _record(self, result: ChaosResult) -> None:
        self._history.append(result.to_dict())
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_report(self) -> dict[str, Any]:
        """Get chaos testing report."""
        total = len(self._history)
        successful = sum(1 for h in self._history if h["success"])
        by_scenario: dict[str, int] = {}
        for h in self._history:
            by_scenario[h["scenario"]] = by_scenario.get(h["scenario"], 0) + 1

        return {
            "enabled": self._enabled,
            "total_injections": total,
            "successful": successful,
            "failed": total - successful,
            "active_injections": len(self._active_injections),
            "by_scenario": by_scenario,
            "recent": self._history[-10:],
        }


# ── Singleton ────────────────────────────────────────────────────

_chaos: ChaosEngine | None = None


def get_chaos_engine() -> ChaosEngine:
    global _chaos
    if _chaos is None:
        _chaos = ChaosEngine()
    return _chaos


chaos = get_chaos_engine()
