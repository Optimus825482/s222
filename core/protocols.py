"""
Agent Communication Protocols — Message types, envelopes, delivery semantics.

Ajan-arası iletişimin temel yapı taşları:
- MessageEnvelope: Her mesajın sarmalayıcısı (routing, TTL, priority)
- MessageType: Kanal bazlı mesaj tipleri
- DeliveryGuarantee: At-most-once / at-least-once / exactly-once
- Channel: Topic-based pub-sub kanalları
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


# ── Message Types ────────────────────────────────────────────────

class MessageType(str, Enum):
    """Ajan iletişim mesaj tipleri."""
    # Core communication
    TASK_REQUEST = "task_request"          # Agent → Agent: görev ata
    TASK_RESULT = "task_result"            # Agent → Agent: görev sonucu
    TASK_PROGRESS = "task_progress"        # Agent → Bus: ilerleme bildirimi

    # Handoff
    HANDOFF_REQUEST = "handoff_request"    # Agent A → Agent B: işi devret
    HANDOFF_ACCEPT = "handoff_accept"      # Agent B → Agent A: devraldım
    HANDOFF_REJECT = "handoff_reject"      # Agent B → Agent A: devralamam
    HANDOFF_COMPLETE = "handoff_complete"  # Agent B → Bus: devir tamamlandı

    # Coordination
    BROADCAST = "broadcast"               # Agent → All: genel duyuru
    QUERY = "query"                       # Agent → Agent: bilgi sor
    QUERY_RESPONSE = "query_response"     # Agent → Agent: bilgi yanıtı

    # System
    HEARTBEAT = "heartbeat"               # Agent → Bus: hayattayım
    ERROR = "error"                       # Agent → Bus: hata bildirimi
    CANCEL = "cancel"                     # Orchestrator → Agent: görevi iptal et


class DeliveryGuarantee(str, Enum):
    """Mesaj teslim garantisi."""
    AT_MOST_ONCE = "at_most_once"      # Fire-and-forget (heartbeat, progress)
    AT_LEAST_ONCE = "at_least_once"    # Retry on failure (task_request, handoff)
    EXACTLY_ONCE = "exactly_once"      # Dedup + ack (task_result, critical ops)


class MessagePriority(int, Enum):
    """Mesaj öncelik seviyeleri."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


# ── Channel Definition ───────────────────────────────────────────

class ChannelType(str, Enum):
    """Kanal tipleri."""
    UNICAST = "unicast"       # 1:1 — doğrudan agent'a
    MULTICAST = "multicast"   # 1:N — belirli subscriber grubuna
    BROADCAST = "broadcast"   # 1:All — tüm agent'lara


# ── Message Envelope ─────────────────────────────────────────────

class MessageEnvelope(BaseModel):
    """
    Her mesajın sarmalayıcısı — routing, TTL, priority, delivery guarantee.
    Agent'lar arası tüm iletişim bu envelope üzerinden akar.
    """
    id: str = Field(default_factory=_uid)
    timestamp: datetime = Field(default_factory=_now)

    # Routing
    source_agent: str                          # Gönderen agent role
    target_agent: str | None = None            # Hedef agent (unicast) veya None (broadcast)
    channel: str = "default"                   # Topic/channel adı
    channel_type: ChannelType = ChannelType.UNICAST

    # Payload
    message_type: MessageType
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None          # Request-response eşleştirme

    # Delivery
    priority: MessagePriority = MessagePriority.NORMAL
    delivery: DeliveryGuarantee = DeliveryGuarantee.AT_LEAST_ONCE
    ttl_seconds: int = 300                     # 5 dakika default TTL
    retry_count: int = 0
    max_retries: int = 3

    # State
    acknowledged: bool = False
    delivered_at: datetime | None = None
    error: str | None = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    @property
    def is_expired(self) -> bool:
        age = (_now() - self.timestamp).total_seconds()
        return age > self.ttl_seconds

    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries and not self.is_expired


# ── Handoff Context ──────────────────────────────────────────────

class HandoffContext(BaseModel):
    """
    Agent handoff sırasında aktarılan bağlam.
    Ne yapıldı, ne kaldı, neden devrediliyor — hepsi burada.
    """
    id: str = Field(default_factory=_uid)
    timestamp: datetime = Field(default_factory=_now)

    # Handoff parties
    from_agent: str
    to_agent: str
    reason: str                                # Neden devrediliyor

    # Context transfer
    task_description: str                      # Orijinal görev
    work_completed: str = ""                   # Şimdiye kadar yapılan iş
    work_remaining: str = ""                   # Kalan iş
    partial_result: str = ""                   # Varsa kısmi sonuç
    context_data: dict[str, Any] = Field(default_factory=dict)  # Ek veri

    # Thread reference
    thread_id: str | None = None
    relevant_event_ids: list[str] = Field(default_factory=list)

    # Status
    accepted: bool = False
    completed: bool = False


# ── Task Delegation ──────────────────────────────────────────────

class DelegatedTask(BaseModel):
    """
    Asenkron görev delegasyonu — bir agent başka bir agent'a iş atar,
    sonucu callback/future ile alır.
    """
    id: str = Field(default_factory=_uid)
    created_at: datetime = Field(default_factory=_now)

    # Task info
    delegator: str                             # Görevi atayan agent
    delegate: str                              # Görevi alan agent
    description: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL

    # Execution
    status: str = "pending"                    # pending, running, completed, failed, cancelled, timed_out
    result: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Retry & queue
    retry_count: int = 0
    max_retries: int = 3
    queued_at: datetime = Field(default_factory=_now)
    assigned_at: datetime | None = None

    # Timeout
    timeout_seconds: int = 120                 # 2 dakika default

    @property
    def is_timed_out(self) -> bool:
        if self.started_at and self.status == "running":
            elapsed = (_now() - self.started_at).total_seconds()
            return elapsed > self.timeout_seconds
        return False
