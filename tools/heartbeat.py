"""
Heartbeat System — Proaktif agent davranışı (Faz 11.2).
Cron-tabanlı zamanlanmış görevler, sabah brifingi, agent sağlık kontrolü,
maliyet izleme, anomali algılama. Multi-parallel orchestration ile uyumlu.

Extended with scheduled_tasks integration for dynamic task scheduling.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable, Optional

logger = logging.getLogger(__name__)

_utc = timezone.utc


class HeartbeatFrequency(str, Enum):
    MINUTELY = "minutely"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class HeartbeatTask:
    name: str
    frequency: HeartbeatFrequency
    handler: Callable[[], Awaitable[dict]]
    enabled: bool = True
    last_run: datetime | None = None
    run_count: int = 0
    error_count: int = 0


# Son heartbeat event'leri (WebSocket / API için)
_heartbeat_events: list[dict] = []
_MAX_EVENTS = 100


def _get_events() -> list[dict]:
    return _heartbeat_events.copy()


def _append_event(event: dict) -> None:
    global _heartbeat_events
    _heartbeat_events.append(event)
    if len(_heartbeat_events) > _MAX_EVENTS:
        _heartbeat_events[:] = _heartbeat_events[-_MAX_EVENTS:]


class HeartbeatScheduler:
    def __init__(self) -> None:
        self.tasks: dict[str, HeartbeatTask] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._task_runners: dict[str, asyncio.Task] = {}

    def register(self, task: HeartbeatTask) -> None:
        self.tasks[task.name] = task
        if self._running and task.name not in self._task_runners:
            self._task_runners[task.name] = asyncio.create_task(
                self._task_loop(task.name)
            )

    def _interval_seconds(self, freq: HeartbeatFrequency) -> int:
        return {
            HeartbeatFrequency.MINUTELY: 60,
            HeartbeatFrequency.HOURLY: 3600,
            HeartbeatFrequency.DAILY: 86400,
            HeartbeatFrequency.WEEKLY: 604800,
        }[freq]

    def _should_run(self, task: HeartbeatTask, now: datetime) -> bool:
        if not task.enabled:
            return False
        if task.last_run is None:
            return True
        delta = (now - task.last_run).total_seconds()
        return delta >= self._interval_seconds(task.frequency)

    async def _execute(self, task: HeartbeatTask) -> None:
        try:
            result = await task.handler()
            task.last_run = datetime.now(_utc)
            task.run_count += 1
            event = {
                "type": "heartbeat",
                "task": task.name,
                "timestamp": datetime.now(_utc).isoformat(),
                "result": result,
                "run_count": task.run_count,
            }
            _append_event(event)
            logger.info("[Heartbeat] %s ok (run_count=%d)", task.name, task.run_count)
        except Exception as e:
            task.error_count += 1
            _append_event(
                {
                    "type": "heartbeat",
                    "task": task.name,
                    "timestamp": datetime.now(_utc).isoformat(),
                    "error": str(e),
                    "error_count": task.error_count,
                }
            )
            logger.warning("[Heartbeat] %s failed: %s", task.name, e)

    async def _task_loop(self, task_name: str) -> None:
        while self._running:
            task = self.tasks.get(task_name)
            if task is None:
                return
            if not task.enabled:
                await asyncio.sleep(5)
                continue

            now = datetime.now(_utc)
            if task.last_run is None:
                delay = 0
            else:
                elapsed = (now - task.last_run).total_seconds()
                delay = max(self._interval_seconds(task.frequency) - elapsed, 0)

            if delay > 0:
                await asyncio.sleep(delay)
                continue

            await self._execute(task)

    async def _loop(self) -> None:
        """Coordinate task runners without direct scheduling - each task manages its own timing."""
        while self._running:
            # Clean up finished tasks and start new ones as needed
            for task_name, task in self.tasks.items():
                runner = self._task_runners.get(task_name)
                if task.enabled and (runner is None or runner.done()):
                    self._task_runners[task_name] = asyncio.create_task(
                        self._task_loop(task_name)
                    )
                elif not task.enabled and runner is not None:
                    runner.cancel()
                    try:
                        await runner
                    except asyncio.CancelledError:
                        pass
                    self._task_runners.pop(task_name, None)
            await asyncio.sleep(10)  # Longer sleep since individual tasks handle timing

    async def start(self) -> None:
        self._running = True
        # Start individual task runners immediately
        for task_name in self.tasks:
            if task_name not in self._task_runners:
                self._task_runners[task_name] = asyncio.create_task(
                    self._task_loop(task_name)
                )
        # Start coordination loop
        self._task = asyncio.create_task(self._loop())
        logger.info("[Heartbeat] Scheduler started with %d tasks", len(self.tasks))

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        for task_name, runner in list(self._task_runners.items()):
            runner.cancel()
            try:
                await runner
            except asyncio.CancelledError:
                pass
            self._task_runners.pop(task_name, None)
        logger.info("[Heartbeat] Scheduler stopped")

    def list_tasks(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "frequency": t.frequency.value,
                "enabled": t.enabled,
                "last_run": t.last_run.isoformat() if t.last_run else None,
                "run_count": t.run_count,
                "error_count": t.error_count,
            }
            for t in self.tasks.values()
        ]


# ── Built-in handlers (orchestration + DB/analytics) ─────────────────────


async def daily_briefing() -> dict:
    """Günlük özet: görev sayısı, başarı oranı, öneriler."""
    out: dict = {
        "type": "daily_briefing",
        "tasks_completed_24h": 0,
        "avg_success_rate": 0.0,
        "active_agents": [],
        "top_skills_used": [],
        "anomalies_detected": [],
        "recommendations": [],
    }
    try:
        from tools.agent_eval import get_performance_baseline
        from config import MODELS

        total_tasks = 0
        success_sum = 0.0
        for role in MODELS:
            b = get_performance_baseline(role)
            total_tasks += b.get("total_tasks", 0)
            success_sum += b.get("task_success_rate_pct", 0)
        out["tasks_completed_24h"] = total_tasks
        if MODELS:
            out["avg_success_rate"] = round(success_sum / len(MODELS), 1)
        out["active_agents"] = list(MODELS.keys())
    except Exception as e:
        out["error"] = str(e)
    return out


async def agent_health_check() -> dict:
    """Tüm agent'ların circuit breaker durumu."""
    out: dict = {"agents": {}}
    try:
        from tools.circuit_breaker import get_circuit_breaker
        from config import MODELS

        cb = get_circuit_breaker()
        status = cb.status()
        for role in MODELS:
            s = status.get(role, {})
            out["agents"][role] = {
                "state": s.get("state", "unknown"),
                "failures": s.get("failure_count", 0),
            }
    except Exception as e:
        out["error"] = str(e)
    return out


async def cost_monitor() -> dict:
    """Token/maliyet izleme — son 24h tahmini."""
    out: dict = {
        "total_tokens_24h": 0,
        "total_cost_usd": 0.0,
        "budget_remaining_pct": 100.0,
        "alert": None,
    }
    try:
        from tools.pg_connection import get_conn, release_conn

        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(SUM(tokens_used), 0) AS total
                    FROM tool_usage
                    WHERE timestamp >= NOW() - INTERVAL '24 hours'
                """)
                row = cur.fetchone()
                out["total_tokens_24h"] = row[0] if row else 0
        finally:
            release_conn(conn)
        out["total_cost_usd"] = round(out["total_tokens_24h"] / 1000 * 0.002, 4)
        if out["total_tokens_24h"] > 500_000:
            out["alert"] = "Yüksek token kullanımı (24h)"
            out["budget_remaining_pct"] = 50.0
    except Exception as e:
        out["error"] = str(e)
    return out


async def anomaly_detector() -> dict:
    """Anomali: hata artışı, gecikme bozulması."""
    out: dict = {
        "error_rate_spike": False,
        "latency_degradation": False,
        "unusual_tool_usage": False,
        "details": [],
    }
    try:
        from tools.circuit_breaker import get_circuit_breaker

        cb = get_circuit_breaker()
        status = cb.status()
        for role, data in status.items():
            if data.get("state") == "open":
                out["error_rate_spike"] = True
                out["details"].append(
                    f"{role}: circuit open (failures={data.get('failure_count', 0)})"
                )
    except Exception as e:
        out["details"].append(f"check failed: {e}")
    return out


_scheduler: HeartbeatScheduler | None = None


def get_heartbeat_scheduler() -> HeartbeatScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = HeartbeatScheduler()
        _scheduler.register(
            HeartbeatTask(
                name="daily_briefing",
                frequency=HeartbeatFrequency.DAILY,
                handler=daily_briefing,
            )
        )
        _scheduler.register(
            HeartbeatTask(
                name="agent_health",
                frequency=HeartbeatFrequency.MINUTELY,
                handler=agent_health_check,
            )
        )
        _scheduler.register(
            HeartbeatTask(
                name="cost_monitor",
                frequency=HeartbeatFrequency.HOURLY,
                handler=cost_monitor,
            )
        )
        _scheduler.register(
            HeartbeatTask(
                name="anomaly_detector",
                frequency=HeartbeatFrequency.HOURLY,
                handler=anomaly_detector,
            )
        )
    return _scheduler


def get_heartbeat_events(limit: int = 50) -> list[dict]:
    return list(reversed(_heartbeat_events[-limit:]))


# ── Scheduled Tasks Integration ─────────────────────────────────

async def register_heartbeat_as_scheduled_task(
    task_name: str,
    cron_expr: str,
    user_id: str | None = None,
) -> dict:
    """
    Register an existing heartbeat task as a scheduled task.
    This allows dynamic cron-based scheduling via API.

    Args:
        task_name: Name of the heartbeat task (e.g., 'daily_briefing')
        cron_expr: Standard 5-field cron expression
        user_id: Optional user ID for ownership

    Returns:
        The created scheduled task as dict
    """
    from tools.scheduled_tasks import (
        get_scheduled_task_scheduler,
        TaskType,
        register_handler,
    )

    # Verify heartbeat task exists
    scheduler = get_heartbeat_scheduler()
    if task_name not in scheduler.tasks:
        raise ValueError(f"Heartbeat task '{task_name}' not found")

    task = scheduler.tasks[task_name]

    # Create a wrapper handler for scheduled_tasks
    async def heartbeat_wrapper(**kwargs) -> dict:
        return await task.handler()

    # Register handler with unique name
    handler_name = f"heartbeat_{task_name}"
    register_handler(handler_name, heartbeat_wrapper)

    # Create scheduled task (async)
    sts = get_scheduled_task_scheduler()
    scheduled = await sts.create_task(
        name=f"Heartbeat: {task_name}",
        task_type=TaskType.HEARTBEAT,
        cron_expr=cron_expr,
        handler_ref=task_name,  # Reference to heartbeat task name
        user_id=user_id,
        tags=["heartbeat", "auto"],
    )

    return sts._task_to_dict(scheduled)


async def sync_heartbeat_to_scheduled_tasks() -> int:
    """
    Sync all heartbeat tasks to scheduled_tasks system.
    Creates corresponding scheduled tasks for enabled heartbeat tasks.

    Returns number of synced tasks.
    """
    from tools.scheduled_tasks import (
        get_scheduled_task_scheduler,
        TaskType,
        register_handler,
    )

    hb = get_heartbeat_scheduler()
    sts = get_scheduled_task_scheduler()

    # Ensure scheduler is started
    await sts.start()

    synced = 0
    for name, task in hb.tasks.items():
        if not task.enabled:
            continue

        # Register handler with closure capturing the task
        handler_name = f"heartbeat_{name}"
        task_ref = task  # Capture in closure

        async def make_wrapper(t: HeartbeatTask) -> Callable[..., Awaitable[dict]]:
            async def wrapper(**kwargs) -> dict:
                return await t.handler()
            return wrapper

        register_handler(handler_name, await make_wrapper(task_ref))

        # Default cron based on frequency
        cron_map = {
            HeartbeatFrequency.MINUTELY: "* * * * *",      # Every minute
            HeartbeatFrequency.HOURLY: "0 * * * *",        # Hourly at :00
            HeartbeatFrequency.DAILY: "0 6 * * *",         # Daily at 6 AM UTC
            HeartbeatFrequency.WEEKLY: "0 6 * * 1",        # Monday 6 AM UTC
        }
        default_cron = cron_map.get(task.frequency, "0 * * * *")

        # Check if scheduled task already exists
        existing = await sts.get_task(f"heartbeat-{name}")
        if existing:
            continue

        try:
            await sts.create_task(
                name=f"Heartbeat: {name}",
                task_type=TaskType.HEARTBEAT,
                cron_expr=default_cron,
                handler_ref=name,
                enabled=task.enabled,
                task_id=f"heartbeat-{name}",
                tags=["heartbeat", "auto"],
            )
            synced += 1
        except Exception as e:
            logger.warning("[Heartbeat] Failed to sync task '%s': %s", name, e)

    logger.info("[Heartbeat] Synced %d tasks to scheduled_tasks", synced)
    return synced


async def get_combined_task_status() -> dict:
    """
    Get combined status of heartbeat and scheduled tasks.
    Useful for dashboard views.
    """
    from tools.scheduled_tasks import get_scheduled_task_scheduler

    hb = get_heartbeat_scheduler()
    sts = get_scheduled_task_scheduler()

    heartbeat_tasks = hb.list_tasks()
    scheduled_tasks = await sts.list_tasks_dicts_async()

    return {
        "heartbeat": {
            "count": len(heartbeat_tasks),
            "enabled": sum(1 for t in heartbeat_tasks if t["enabled"]),
            "tasks": heartbeat_tasks,
        },
        "scheduled": {
            "count": len(scheduled_tasks),
            "enabled": sum(1 for t in scheduled_tasks if t.get("enabled")),
            "tasks": scheduled_tasks,
        },
        "recent_events": get_heartbeat_events(limit=20),
    }
