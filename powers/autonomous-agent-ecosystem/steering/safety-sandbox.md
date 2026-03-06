# Safety Sandbox — Kill Switch & Emergent Behavior Monitoring

Guardrails for autonomous agent systems. Prevents runaway behavior while allowing emergent intelligence.

## Problem

Autonomous agents can:

- Enter infinite loops consuming tokens endlessly
- Generate harmful or nonsensical outputs
- Develop unexpected collective behaviors (like Moltbook's Crustafarianism)
- Exceed cost budgets without warning
- Make irreversible changes to data or systems

A safety layer must exist that monitors, limits, and can instantly halt agent activity.

## Architecture

```
┌──────────────────────────────────────────────┐
│           Human Oversight Dashboard           │
│  ┌────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ Kill   │ │ Activity │ │ Emergent      │  │
│  │ Switch │ │ Monitor  │ │ Behavior Log  │  │
│  └───┬────┘ └────┬─────┘ └──────┬────────┘  │
└──────┼───────────┼──────────────┼────────────┘
       │           │              │
┌──────▼───────────▼──────────────▼────────────┐
│              Safety Sandbox                    │
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │  Rate Limiter                           │  │
│  │  ├─ Max LLM calls/minute: 30           │  │
│  │  ├─ Max tokens/hour: 500K              │  │
│  │  └─ Max cost/day: $5.00                │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │  Behavior Monitor                       │  │
│  │  ├─ Repetition detector                │  │
│  │  ├─ Sentiment drift tracker            │  │
│  │  ├─ Output quality scorer              │  │
│  │  └─ Anomaly pattern matcher            │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │  Kill Switch                            │  │
│  │  ├─ Instant: halt all agent activity   │  │
│  │  ├─ Selective: halt specific agent     │  │
│  │  ├─ Gradual: reduce autonomy level     │  │
│  │  └─ Auto: triggered by safety rules    │  │
│  └─────────────────────────────────────────┘  │
└───────────────────────────────────────────────┘
```

## Backend Implementation

### Safety Engine

```python
# tools/safety_sandbox.py

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

class SafetyLevel(str, Enum):
    NORMAL = "normal"         # full autonomy
    CAUTIOUS = "cautious"     # reduced iteration limits
    SUPERVISED = "supervised" # human approval required
    HALTED = "halted"         # all activity stopped

class KillSwitchMode(str, Enum):
    INSTANT = "instant"     # halt everything now
    SELECTIVE = "selective"  # halt specific agent
    GRADUAL = "gradual"     # reduce autonomy over time
    AUTO = "auto"           # triggered by safety rules

@dataclass
class SafetyConfig:
    max_llm_calls_per_minute: int = 30
    max_tokens_per_hour: int = 500_000
    max_cost_per_day_usd: float = 5.00
    max_consecutive_errors: int = 5
    repetition_threshold: int = 3  # same output 3x = flag
    min_output_quality: float = 0.3
    auto_halt_on_budget_exceed: bool = True

@dataclass
class SafetyState:
    level: SafetyLevel = SafetyLevel.NORMAL
    halted_agents: set = field(default_factory=set)
    llm_calls_window: deque = field(default_factory=lambda: deque(maxlen=1000))
    tokens_window: deque = field(default_factory=lambda: deque(maxlen=1000))
    daily_cost_usd: float = 0.0
    daily_cost_reset: datetime = field(default_factory=datetime.now)
    consecutive_errors: dict = field(default_factory=dict)  # agent -> count
    anomalies: list = field(default_factory=list)
    kill_switch_history: list = field(default_factory=list)

class SafetySandbox:
    def __init__(self, config: SafetyConfig | None = None):
        self.config = config or SafetyConfig()
        self.state = SafetyState()

    # ── Pre-execution Check ──

    async def check_before_execute(self, agent_role: str) -> dict:
        """Call before every LLM call. Returns allow/deny + reason."""
        if self.state.level == SafetyLevel.HALTED:
            return {"allowed": False, "reason": "System halted by kill switch"}
        if agent_role in self.state.halted_agents:
            return {"allowed": False, "reason": f"Agent {agent_role} halted"}
        if self._rate_limit_exceeded():
            return {"allowed": False, "reason": "Rate limit exceeded"}
        if self._budget_exceeded():
            if self.config.auto_halt_on_budget_exceed:
                await self.kill_switch(KillSwitchMode.INSTANT, "Budget exceeded")
            return {"allowed": False, "reason": "Daily budget exceeded"}
        return {"allowed": True, "reason": None}

    # ── Post-execution Monitor ──

    async def record_execution(self, agent_role: str, result: dict):
        """Call after every LLM call to track metrics."""
        now = datetime.now()
        tokens = result.get("tokens_used", 0)
        cost = result.get("cost_usd", 0.0)

        self.state.llm_calls_window.append(now)
        self.state.tokens_window.append((now, tokens))
        self.state.daily_cost_usd += cost

        # Reset daily cost at midnight
        if now.date() > self.state.daily_cost_reset.date():
            self.state.daily_cost_usd = 0.0
            self.state.daily_cost_reset = now

        # Track errors
        if result.get("error"):
            self.state.consecutive_errors[agent_role] = (
                self.state.consecutive_errors.get(agent_role, 0) + 1
            )
            if self.state.consecutive_errors[agent_role] >= self.config.max_consecutive_errors:
                await self.kill_switch(
                    KillSwitchMode.SELECTIVE,
                    f"{agent_role}: {self.config.max_consecutive_errors} consecutive errors",
                    agent_role=agent_role,
                )
        else:
            self.state.consecutive_errors[agent_role] = 0

        # Check for repetition
        await self._check_repetition(agent_role, result)

    # ── Kill Switch ──

    async def kill_switch(
        self, mode: KillSwitchMode, reason: str, agent_role: str | None = None
    ):
        """Activate kill switch."""
        event = {
            "mode": mode.value,
            "reason": reason,
            "agent": agent_role,
            "timestamp": datetime.now().isoformat(),
        }
        self.state.kill_switch_history.append(event)

        if mode == KillSwitchMode.INSTANT:
            self.state.level = SafetyLevel.HALTED
        elif mode == KillSwitchMode.SELECTIVE and agent_role:
            self.state.halted_agents.add(agent_role)
        elif mode == KillSwitchMode.GRADUAL:
            self.state.level = SafetyLevel.CAUTIOUS
        # Broadcast to WebSocket
        await self._broadcast_safety_event(event)

    async def resume(self, agent_role: str | None = None):
        """Resume after kill switch."""
        if agent_role:
            self.state.halted_agents.discard(agent_role)
        else:
            self.state.level = SafetyLevel.NORMAL
            self.state.halted_agents.clear()

    # ── Emergent Behavior Detection ──

    async def detect_emergent_behavior(self, social_data: dict) -> list[dict]:
        """Analyze agent social network for unexpected patterns."""
        anomalies = []
        # Check for: unusual topic clustering, rapid consensus, echo chambers
        discussions = social_data.get("discussions", [])
        for disc in discussions:
            msgs = disc.get("messages", [])
            if len(msgs) > 20:
                # Check sentiment convergence
                anomalies.append({
                    "type": "high_activity_discussion",
                    "discussion_id": disc["id"],
                    "message_count": len(msgs),
                    "severity": "info",
                })
        proposals = social_data.get("proposals", [])
        for prop in proposals:
            votes = prop.get("votes", {})
            if len(votes) >= 4 and all(v == "agree" for v in votes.values()):
                anomalies.append({
                    "type": "unanimous_consensus",
                    "proposal_id": prop["id"],
                    "severity": "warning",
                    "note": "All agents agreed — possible echo chamber",
                })
        self.state.anomalies.extend(anomalies)
        return anomalies

    # ── Internal Helpers ──

    def _rate_limit_exceeded(self) -> bool:
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        recent = sum(1 for t in self.state.llm_calls_window if t > cutoff)
        return recent >= self.config.max_llm_calls_per_minute

    def _budget_exceeded(self) -> bool:
        return self.state.daily_cost_usd >= self.config.max_cost_per_day_usd

    async def _check_repetition(self, agent_role: str, result: dict):
        """Flag if agent produces same output repeatedly."""
        pass  # Compare last N outputs for similarity

    async def _broadcast_safety_event(self, event: dict):
        """Push safety events to WebSocket."""
        pass
```

### FastAPI Endpoints

```python
# Add to backend/main.py

sandbox = SafetySandbox()

@app.get("/api/safety/status")
async def safety_status():
    return {
        "level": sandbox.state.level.value,
        "halted_agents": list(sandbox.state.halted_agents),
        "daily_cost_usd": round(sandbox.state.daily_cost_usd, 4),
        "budget_limit_usd": sandbox.config.max_cost_per_day_usd,
        "anomalies_count": len(sandbox.state.anomalies),
        "kill_switch_history": sandbox.state.kill_switch_history[-10:],
    }

@app.post("/api/safety/kill-switch")
async def activate_kill_switch(mode: str, reason: str, agent_role: str | None = None):
    await sandbox.kill_switch(KillSwitchMode(mode), reason, agent_role)
    return {"status": "activated", "mode": mode}

@app.post("/api/safety/resume")
async def resume_agents(agent_role: str | None = None):
    await sandbox.resume(agent_role)
    return {"status": "resumed"}

@app.get("/api/safety/anomalies")
async def list_anomalies():
    return sandbox.state.anomalies[-50:]

@app.patch("/api/safety/config")
async def update_safety_config(
    max_cost_per_day: float | None = None,
    max_calls_per_minute: int | None = None,
):
    if max_cost_per_day is not None:
        sandbox.config.max_cost_per_day_usd = max_cost_per_day
    if max_calls_per_minute is not None:
        sandbox.config.max_llm_calls_per_minute = max_calls_per_minute
    return {"status": "updated"}
```

## Frontend Component

```tsx
// components/safety-dashboard.tsx

// Layout:
// Top bar: Safety level indicator (green/yellow/orange/red)
// Big red KILL SWITCH button (instant halt)
//
// Sections:
// 1. Durum — current safety level, halted agents, daily cost meter
// 2. Anomaliler — emergent behavior log with severity badges
// 3. Kill Switch Geçmişi — timeline of past activations
// 4. Ayarlar — configurable limits (cost, rate, error threshold)
//
// Real-time: WebSocket updates for safety events
// Color coding: NORMAL=green, CAUTIOUS=yellow, SUPERVISED=orange, HALTED=red
```

## Safety Rules Summary

| Rule          | Trigger                     | Action                 |
| ------------- | --------------------------- | ---------------------- |
| Rate limit    | >30 LLM calls/min           | Block new calls        |
| Token budget  | >500K tokens/hour           | Block + alert          |
| Cost budget   | >$5/day                     | Auto kill switch       |
| Error streak  | 5 consecutive errors        | Halt that agent        |
| Repetition    | Same output 3x              | Flag + reduce autonomy |
| Echo chamber  | Unanimous vote (all agents) | Warning alert          |
| High activity | >20 messages in discussion  | Info alert             |

## Implementation Checklist

- [ ] Create `tools/safety_sandbox.py` with `SafetySandbox`
- [ ] Integrate `check_before_execute()` into all agent LLM calls
- [ ] Integrate `record_execution()` after all LLM calls
- [ ] Kill switch with 4 modes (instant, selective, gradual, auto)
- [ ] Emergent behavior detection for social network
- [ ] REST endpoints for safety management
- [ ] Frontend: `SafetyDashboard` component
- [ ] WebSocket broadcast for safety events
- [ ] Daily cost reset at midnight
- [ ] Kill switch history in PostgreSQL
