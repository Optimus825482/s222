# Heartbeat System — Proactive Agent Behavior

Agents that don't just respond — they proactively monitor, alert, and brief.

## Problem

Current agents are purely reactive (user asks → agent responds). A production autonomous system needs agents that:

- Run scheduled tasks without user prompting
- Send proactive alerts when anomalies are detected
- Deliver daily briefings summarizing system state
- Monitor health of other agents and infrastructure

## Architecture

```
┌──────────────────────────────────────────┐
│           Heartbeat Scheduler            │
│                                          │
│  ┌────────────┐  ┌───────────────────┐   │
│  │ Cron Jobs  │  │ Event Triggers    │   │
│  │            │  │                   │   │
│  │ • daily    │  │ • error_spike     │   │
│  │ • hourly   │  │ • cost_threshold  │   │
│  │ • weekly   │  │ • agent_down      │   │
│  └─────┬──────┘  └────────┬──────────┘   │
│        │                  │              │
│        ▼                  ▼              │
│  ┌─────────────────────────────────┐     │
│  │      Task Queue (asyncio)       │     │
│  └──────────────┬──────────────────┘     │
│                 │                        │
│        ┌────────▼────────┐               │
│        │  Agent Executor  │               │
│        │  (Observer role) │               │
│        └────────┬────────┘               │
│                 │                        │
│        ┌────────▼────────┐               │
│        │  Notification    │               │
│        │  ├─ WebSocket    │               │
│        │  ├─ DB Log       │               │
│        │  └─ Frontend     │               │
│        └─────────────────┘               │
└──────────────────────────────────────────┘
```

## Backend Implementation

### Heartbeat Scheduler

```python
# tools/heartbeat.py

import asyncio
from datetime import datetime, time as dtime
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Awaitable

class HeartbeatFrequency(str, Enum):
    MINUTELY = "minutely"   # for health checks
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

class HeartbeatScheduler:
    def __init__(self):
        self.tasks: dict[str, HeartbeatTask] = {}
        self._running = False

    def register(self, task: HeartbeatTask):
        self.tasks[task.name] = task

    async def start(self):
        """Start the heartbeat loop — call from FastAPI lifespan."""
        self._running = True
        while self._running:
            now = datetime.now()
            for task in self.tasks.values():
                if not task.enabled:
                    continue
                if self._should_run(task, now):
                    asyncio.create_task(self._execute(task))
            await asyncio.sleep(30)  # check every 30s

    async def stop(self):
        self._running = False

    def _should_run(self, task: HeartbeatTask, now: datetime) -> bool:
        if task.last_run is None:
            return True
        elapsed = (now - task.last_run).total_seconds()
        intervals = {
            HeartbeatFrequency.MINUTELY: 60,
            HeartbeatFrequency.HOURLY: 3600,
            HeartbeatFrequency.DAILY: 86400,
            HeartbeatFrequency.WEEKLY: 604800,
        }
        return elapsed >= intervals[task.frequency]

    async def _execute(self, task: HeartbeatTask):
        try:
            result = await task.handler()
            task.last_run = datetime.now()
            task.run_count += 1
            await self._notify(task.name, result)
        except Exception as e:
            task.error_count += 1
            await self._notify(task.name, {"error": str(e)})

    async def _notify(self, task_name: str, result: dict):
        """Push to WebSocket + store in DB."""
        event = {
            "type": "heartbeat",
            "task": task_name,
            "timestamp": datetime.now().isoformat(),
            "result": result,
        }
        # broadcast to connected WebSocket clients
        await broadcast_event(event)

# ── Built-in Heartbeat Tasks ──

async def daily_briefing() -> dict:
    """Generate morning briefing with system stats."""
    # Gather: task count, success rate, active agents, memory usage
    return {
        "type": "daily_briefing",
        "tasks_completed_24h": 0,  # query from DB
        "avg_success_rate": 0.0,
        "active_agents": [],
        "top_skills_used": [],
        "anomalies_detected": [],
        "recommendations": [],
    }

async def agent_health_check() -> dict:
    """Check all agents are responsive."""
    results = {}
    for agent_name in ["orchestrator", "thinker", "speed", "researcher", "reasoner", "observer"]:
        try:
            # Ping agent with minimal prompt
            start = asyncio.get_event_loop().time()
            # await agent.ping()
            latency = asyncio.get_event_loop().time() - start
            results[agent_name] = {"status": "healthy", "latency_ms": round(latency * 1000)}
        except Exception as e:
            results[agent_name] = {"status": "unhealthy", "error": str(e)}
    return {"agents": results}

async def cost_monitor() -> dict:
    """Track token spending and alert if threshold exceeded."""
    # Query last 24h token usage from DB
    return {
        "total_tokens_24h": 0,
        "total_cost_usd": 0.0,
        "budget_remaining_pct": 100.0,
        "alert": None,  # "WARNING: 80% budget consumed"
    }

async def anomaly_detector() -> dict:
    """Detect unusual patterns in agent behavior."""
    return {
        "error_rate_spike": False,
        "latency_degradation": False,
        "unusual_tool_usage": False,
        "details": [],
    }
```

### FastAPI Integration

```python
# Add to backend/main.py lifespan

from contextlib import asynccontextmanager

heartbeat = HeartbeatScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register built-in tasks
    heartbeat.register(HeartbeatTask(
        name="daily_briefing",
        frequency=HeartbeatFrequency.DAILY,
        handler=daily_briefing,
    ))
    heartbeat.register(HeartbeatTask(
        name="agent_health",
        frequency=HeartbeatFrequency.MINUTELY,
        handler=agent_health_check,
    ))
    heartbeat.register(HeartbeatTask(
        name="cost_monitor",
        frequency=HeartbeatFrequency.HOURLY,
        handler=cost_monitor,
    ))
    heartbeat.register(HeartbeatTask(
        name="anomaly_detector",
        frequency=HeartbeatFrequency.HOURLY,
        handler=anomaly_detector,
    ))
    # Start scheduler
    task = asyncio.create_task(heartbeat.start())
    yield
    await heartbeat.stop()

# REST endpoints
@app.get("/api/heartbeat/tasks")
async def list_heartbeat_tasks():
    return [
        {
            "name": t.name,
            "frequency": t.frequency.value,
            "enabled": t.enabled,
            "last_run": t.last_run.isoformat() if t.last_run else None,
            "run_count": t.run_count,
            "error_count": t.error_count,
        }
        for t in heartbeat.tasks.values()
    ]

@app.post("/api/heartbeat/tasks/{name}/trigger")
async def trigger_heartbeat(name: str):
    task = heartbeat.tasks.get(name)
    if not task:
        raise HTTPException(404, f"Task {name} not found")
    result = await task.handler()
    return {"task": name, "result": result}

@app.patch("/api/heartbeat/tasks/{name}")
async def toggle_heartbeat(name: str, enabled: bool):
    task = heartbeat.tasks.get(name)
    if not task:
        raise HTTPException(404)
    task.enabled = enabled
    return {"name": name, "enabled": enabled}
```

## Frontend Component

```tsx
// components/heartbeat-dashboard.tsx

interface HeartbeatTask {
  name: string;
  frequency: string;
  enabled: boolean;
  last_run: string | null;
  run_count: number;
  error_count: number;
}

// Display: task list with toggle switches, last run time, run/error counts
// Manual trigger button per task
// Real-time heartbeat events via WebSocket (pulse animation)
// Daily briefing card with expandable details
```

## Implementation Checklist

- [ ] Create `tools/heartbeat.py` with `HeartbeatScheduler`
- [ ] Register in FastAPI lifespan
- [ ] Implement 4 built-in tasks (briefing, health, cost, anomaly)
- [ ] Add REST endpoints for task management
- [ ] WebSocket broadcast for heartbeat events
- [ ] Frontend: `HeartbeatDashboard` component
- [ ] Store heartbeat history in PostgreSQL
- [ ] Add heartbeat tab to Sistem sekmesi
