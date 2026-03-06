# Agentic Loop — Autonomous Task Chaining

Multi-step autonomous execution where agents chain tool calls without human intervention.

## Problem

Current system requires human approval for each step. Agents should autonomously decompose tasks, execute tool chains, and self-correct — while respecting token budgets and iteration limits.

## Architecture

```
User Request
    │
    ▼
┌──────────────┐
│  Orchestrator │──── Decompose into steps
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│          AGENTIC LOOP                │
│                                      │
│  ┌─────────┐    ┌──────────────┐     │
│  │ Execute │───▶│ Evaluate     │     │
│  │ Step    │    │ Result       │     │
│  └─────────┘    └──────┬───────┘     │
│       ▲                │             │
│       │         ┌──────▼───────┐     │
│       │         │ Next Step?   │     │
│       │         │ ┌──────────┐ │     │
│       └─────────┤ │ Yes      │ │     │
│                 │ └──────────┘ │     │
│                 │ ┌──────────┐ │     │
│                 │ │ No→Done  │ │     │
│                 │ └──────────┘ │     │
│                 └──────────────┘     │
│                                      │
│  Guards:                             │
│  ├─ Max iterations (default: 10)     │
│  ├─ Token budget (cost governor)     │
│  └─ Context window limit             │
└──────────────────────────────────────┘
```

## Backend Implementation

### Core Loop Engine

```python
# agents/agentic_loop.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import time
import asyncio

class LoopStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BUDGET_EXCEEDED = "budget_exceeded"
    ITERATION_LIMIT = "iteration_limit"
    CONTEXT_OVERFLOW = "context_overflow"

@dataclass
class LoopConfig:
    max_iterations: int = 10
    max_tokens_budget: int = 50_000  # total token budget
    context_window_limit: int = 120_000  # model context limit
    context_compress_threshold: float = 0.75  # compress at 75%
    cost_per_1k_tokens: float = 0.002
    max_cost_usd: float = 0.50
    timeout_seconds: int = 300

@dataclass
class LoopState:
    iteration: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    status: LoopStatus = LoopStatus.RUNNING
    steps_completed: list[dict] = field(default_factory=list)
    context_compressions: int = 0
    start_time: float = field(default_factory=time.time)

class AgenticLoop:
    def __init__(self, config: LoopConfig | None = None):
        self.config = config or LoopConfig()
        self.state = LoopState()

    async def run(self, task: str, agent, tools: list[dict]) -> dict:
        """Execute autonomous loop until task complete or guard triggered."""
        plan = await agent.decompose(task)

        for step in plan.steps:
            # Guard checks
            guard = self._check_guards()
            if guard:
                self.state.status = guard
                break

            # Execute step
            result = await self._execute_step(step, agent, tools)
            self.state.steps_completed.append(result)
            self.state.iteration += 1

            # Update token tracking
            self.state.total_tokens_used += result.get("tokens_used", 0)
            self.state.total_cost_usd = (
                self.state.total_tokens_used / 1000 * self.config.cost_per_1k_tokens
            )

            # Context Window Guard
            if self._context_usage_ratio() > self.config.context_compress_threshold:
                await self._compress_context(agent)

            # Evaluate: does agent think task is done?
            if result.get("task_complete", False):
                self.state.status = LoopStatus.COMPLETED
                break

        if self.state.status == LoopStatus.RUNNING:
            self.state.status = LoopStatus.COMPLETED

        return self._build_result()

    def _check_guards(self) -> LoopStatus | None:
        if self.state.iteration >= self.config.max_iterations:
            return LoopStatus.ITERATION_LIMIT
        if self.state.total_tokens_used >= self.config.max_tokens_budget:
            return LoopStatus.BUDGET_EXCEEDED
        if self.state.total_cost_usd >= self.config.max_cost_usd:
            return LoopStatus.BUDGET_EXCEEDED
        elapsed = time.time() - self.state.start_time
        if elapsed > self.config.timeout_seconds:
            return LoopStatus.FAILED
        return None

    def _context_usage_ratio(self) -> float:
        return self.state.total_tokens_used / self.config.context_window_limit

    async def _compress_context(self, agent):
        """Summarize conversation history to free context space."""
        summary = await agent.summarize_context(self.state.steps_completed)
        self.state.steps_completed = [{"type": "context_summary", "content": summary}]
        self.state.context_compressions += 1

    async def _execute_step(self, step, agent, tools) -> dict:
        """Execute a single step with tool calls."""
        try:
            result = await agent.execute_with_tools(step, tools)
            return {
                "step": step,
                "result": result,
                "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                "task_complete": result.get("done", False),
                "error": None,
            }
        except Exception as e:
            return {
                "step": step,
                "result": None,
                "tokens_used": 0,
                "task_complete": False,
                "error": str(e),
            }

    def _build_result(self) -> dict:
        return {
            "status": self.state.status.value,
            "iterations": self.state.iteration,
            "total_tokens": self.state.total_tokens_used,
            "total_cost_usd": round(self.state.total_cost_usd, 4),
            "context_compressions": self.state.context_compressions,
            "steps": self.state.steps_completed,
        }
```

### FastAPI Endpoints

```python
# Add to backend/main.py

from pydantic import BaseModel

class AgenticLoopRequest(BaseModel):
    task: str
    agent_role: str = "orchestrator"
    max_iterations: int = 10
    max_cost_usd: float = 0.50

class AgenticLoopResponse(BaseModel):
    loop_id: str
    status: str
    iterations: int
    total_tokens: int
    total_cost_usd: float
    steps: list[dict]

@app.post("/api/agentic-loop/run", response_model=AgenticLoopResponse)
async def run_agentic_loop(req: AgenticLoopRequest):
    config = LoopConfig(
        max_iterations=req.max_iterations,
        max_cost_usd=req.max_cost_usd,
    )
    loop = AgenticLoop(config)
    result = await loop.run(req.task, get_agent(req.agent_role), get_tools())
    return AgenticLoopResponse(
        loop_id=str(uuid4()),
        **result,
    )

# WebSocket for real-time loop progress
@app.websocket("/ws/agentic-loop/{loop_id}")
async def ws_agentic_loop(websocket: WebSocket, loop_id: str):
    await websocket.accept()
    # Stream step completions in real-time
    async for event in loop_events(loop_id):
        await websocket.send_json(event)
```

## Frontend Component

```tsx
// components/agentic-loop-monitor.tsx

interface LoopStep {
  step: string;
  result: any;
  tokens_used: number;
  task_complete: boolean;
  error: string | null;
}

interface LoopState {
  status:
    | "running"
    | "completed"
    | "failed"
    | "budget_exceeded"
    | "iteration_limit";
  iterations: number;
  total_tokens: number;
  total_cost_usd: number;
  steps: LoopStep[];
}

// Display: progress bar (iterations/max), cost meter, step-by-step log
// Color coding: green=completed, yellow=running, red=failed/budget
// Real-time updates via WebSocket
```

## Context Window Guard

The most critical guard. When context approaches the model's limit:

1. **Monitor**: Track cumulative tokens after each step
2. **Threshold**: At 75% capacity, trigger compression
3. **Compress**: Ask agent to summarize all previous steps into a concise context
4. **Resume**: Continue loop with compressed context

```python
# Context compression prompt
COMPRESS_PROMPT = """Summarize the following task execution history into a concise
context that preserves all critical information needed to continue the task.
Keep: decisions made, results obtained, remaining steps.
Drop: verbose tool outputs, intermediate reasoning."""
```

## Cost Governor

Prevents runaway token spending:

```python
# Per-model cost rates (USD per 1K tokens)
COST_RATES = {
    "qwen/qwen3-next-80b": 0.002,
    "minimaxai/minimax-m2.1": 0.003,
    "stepfun-ai/step-3.5-flash": 0.001,
    "z-ai/glm4.7": 0.002,
    "nvidia/nemotron-3-nano-30b": 0.002,
    "deepseek-chat": 0.001,
}
```

## Implementation Checklist

- [ ] Create `agents/agentic_loop.py` with `AgenticLoop` class
- [ ] Add `LoopConfig` to `config.py`
- [ ] Add `/api/agentic-loop/run` POST endpoint
- [ ] Add `/ws/agentic-loop/{loop_id}` WebSocket endpoint
- [ ] Implement Context Window Guard with compression
- [ ] Add cost tracking per model
- [ ] Frontend: `AgenticLoopMonitor` component
- [ ] Add loop history to PostgreSQL
- [ ] Integration tests for guard triggers
