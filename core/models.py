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
    ORCHESTRATOR = "orchestrator"   # DeepSeek Chat — intent analysis, routing, synthesis
    THINKER = "thinker"             # MiniMax M2.1
    SPEED = "speed"                 # Step 3.5 Flash
    RESEARCHER = "researcher"       # GLM 4.7
    REASONER = "reasoner"           # Nemotron 3 Nano
    CRITIC = "critic"               # Qwen3 80B — quality review, skill creation, fact-check


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
    DEEP_RESEARCH = "deep_research"  # Phase 1: parallel gather → Phase 2: synthesize
    IDEA_TO_PROJECT = "idea_to_project"  # Idea → PRD → Architecture → Tasks → Scaffold
    BRAINSTORM = "brainstorm"  # Multi-round debate: perspectives → cross-challenge → synthesis
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
    TEACHING = "teaching"
    CODE_EXECUTION = "code_execution"
    RAG_QUERY = "rag_query"
    EVALUATION = "evaluation"
    # Agent Communication Protocol (Faz 15)
    HANDOFF_INITIATED = "handoff_initiated"
    HANDOFF_ACCEPTED = "handoff_accepted"
    HANDOFF_REJECTED = "handoff_rejected"
    HANDOFF_COMPLETED = "handoff_completed"
    TASK_DELEGATED = "task_delegated"
    TASK_DELEGATION_RESULT = "task_delegation_result"
    BUS_MESSAGE = "bus_message"

    # Skill Marketplace & Self-Improvement Loop (Faz 16)
    METRIC_RECORDED = "metric_recorded"
    EXPERIMENT_CONCLUDED = "experiment_concluded"
    OPTIMIZATION_APPLIED = "optimization_applied"
    ROUTING_WEIGHT_LOW = "routing_weight_low"


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
    metadata: dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """Top-level user task with pipeline and sub-tasks."""
    id: str = Field(default_factory=_uid)
    user_input: str
    pipeline_type: PipelineType = PipelineType.AUTO
    sub_tasks: list[SubTask] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    final_result: str | None = None
    confidence_footer: str | None = None
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
    parent_thread_id: str | None = None
    root_thread_id: str | None = None
    branch_label: str | None = None
    compacted_summary: str | None = None
    last_compacted_at: datetime | None = None

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


# ── Agent Health & Monitoring ────────────────────────────────────


class AgentStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    OFFLINE = "offline"
    ERROR = "error"


class AgentHealth(BaseModel):
    """Real-time health status for an agent."""
    role: AgentRole
    name: str
    status: AgentStatus = AgentStatus.OFFLINE
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    total_calls: int = 0
    error_count: int = 0
    last_active: datetime | None = None
    uptime_pct: float = 0.0


class AuditLogEntry(BaseModel):
    """Security audit log entry."""
    id: str = Field(default_factory=_uid)
    timestamp: datetime = Field(default_factory=_now)
    event_type: str  # login, logout, api_call, auth_failure, anomaly
    user_id: str = ""
    details: str = ""
    ip: str | None = None
    severity: str = "info"  # info, warning, critical


class SystemStats(BaseModel):
    """System-wide statistics snapshot."""
    active_threads: int = 0
    total_tasks: int = 0
    total_events: int = 0
    memory_usage_mb: float = 0.0
    db_status: str = "unknown"
    uptime_seconds: float = 0.0
    agents_active: int = 0
    agents_total: int = 5


class Anomaly(BaseModel):
    """Detected anomalous behavior."""
    type: str  # high_error_rate, slow_response, token_spike, unusual_pattern
    agent_role: AgentRole
    severity: str = "low"  # low, medium, high
    description: str = ""
    detected_at: datetime = Field(default_factory=_now)
    metric_value: float = 0.0
    threshold: float = 0.0


class AnomalyReport(BaseModel):
    """Collection of detected anomalies with overall health assessment."""
    anomalies: list[Anomaly] = Field(default_factory=list)
    overall_health: str = "healthy"  # healthy, degraded, critical


class AgentLeaderboardEntry(BaseModel):
    """Agent ranking entry."""
    role: AgentRole
    name: str
    score: float = 0.0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    efficiency: float = 0.0  # tokens per successful task
    rank: int = 0


class SkillRecommendation(BaseModel):
    """Skill recommendation for a given context."""
    skill_id: str
    name: str
    description: str = ""
    relevance_score: float = 0.0
    category: str = "custom"
    recommended_agent: AgentRole | None = None


class ThreadAnalytics(BaseModel):
    """Detailed analytics for a thread."""
    thread_id: str
    duration_ms: float = 0.0
    agent_participation: dict[str, dict[str, Any]] = Field(default_factory=dict)
    pipeline_types_used: list[PipelineType] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    event_timeline: list[dict[str, Any]] = Field(default_factory=list)
    total_tokens: int = 0
    total_cost_estimate: float = 0.0
