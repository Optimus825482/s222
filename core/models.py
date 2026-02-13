"""
Core data models — 12-Factor Agent principles.
Thread-based unified state, event serialization, task decomposition.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ────────────────────────────────────────────────────────

class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"   # Qwen3 80B
    THINKER = "thinker"             # MiniMax M2.1
    SPEED = "speed"                 # Step 3.5 Flash
    RESEARCHER = "researcher"       # GLM 4.7
    REASONER = "reasoner"           # Nemotron 3 Nano


class TaskStatus(str, Enum):
    PENDING = "pending"
    ROUTING = "routing"
    RUNNING = "running"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineType(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONSENSUS = "consensus"
    ITERATIVE = "iterative"
    AUTO = "auto"  # Orchestrator decides


class EventType(str, Enum):
    USER_MESSAGE = "user_message"
    ROUTING_DECISION = "routing_decision"
    AGENT_START = "agent_start"
    AGENT_THINKING = "agent_thinking"
    AGENT_RESPONSE = "agent_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PIPELINE_START = "pipeline_start"
    PIPELINE_STEP = "pipeline_step"
    PIPELINE_COMPLETE = "pipeline_complete"
    SYNTHESIS = "synthesis"
    ERROR = "error"
    HUMAN_REQUEST = "human_request"
    HUMAN_RESPONSE = "human_response"


# ── Event ────────────────────────────────────────────────────────

class Event(BaseModel):
    """Single event in the thread — 12-Factor #3: own your context window."""
    id: str = Field(default_factory=_uid)
    timestamp: datetime = Field(default_factory=_now)
    event_type: EventType
    agent_role: AgentRole | None = None
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ── SubTask & Task ───────────────────────────────────────────────

class SubTask(BaseModel):
    """Decomposed sub-task assigned to a specialist agent."""
    id: str = Field(default_factory=_uid)
    description: str
    assigned_agent: AgentRole
    priority: int = 1
    depends_on: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)  # Skill IDs to inject
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    token_usage: int = 0
    latency_ms: float = 0.0


class Task(BaseModel):
    """Top-level user task with pipeline and sub-tasks."""
    id: str = Field(default_factory=_uid)
    user_input: str
    pipeline_type: PipelineType = PipelineType.AUTO
    sub_tasks: list[SubTask] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    final_result: str | None = None
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    created_at: datetime = Field(default_factory=_now)
    completed_at: datetime | None = None


# ── Metrics ──────────────────────────────────────────────────────

class AgentMetrics(BaseModel):
    """Per-agent cumulative metrics."""
    total_calls: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    success_count: int = 0
    error_count: int = 0
    last_active: datetime | None = None

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(self.total_calls, 1)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.error_count
        return self.success_count / max(total, 1)


# ── Thread ───────────────────────────────────────────────────────

class Thread(BaseModel):
    """
    12-Factor #5: Unified execution + business state.
    Single source of truth — serializable, forkable, resumable.
    """
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    events: list[Event] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    agent_metrics: dict[str, AgentMetrics] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)

    def add_event(
        self,
        event_type: EventType,
        content: str,
        agent_role: AgentRole | None = None,
        **meta: Any,
    ) -> Event:
        event = Event(
            event_type=event_type,
            agent_role=agent_role,
            content=content,
            metadata=meta,
        )
        self.events.append(event)
        return event

    def last_event(self) -> Event | None:
        return self.events[-1] if self.events else None

    def events_for_agent(self, role: AgentRole) -> list[Event]:
        """Filter events relevant to a specific agent."""
        return [e for e in self.events if e.agent_role == role or e.agent_role is None]

    def update_metrics(self, role: AgentRole, tokens: int, latency_ms: float, success: bool) -> None:
        key = role.value
        if key not in self.agent_metrics:
            self.agent_metrics[key] = AgentMetrics()
        m = self.agent_metrics[key]
        m.total_calls += 1
        m.total_tokens += tokens
        m.total_latency_ms += latency_ms
        if success:
            m.success_count += 1
        else:
            m.error_count += 1
        m.last_active = _now()
