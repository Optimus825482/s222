"""
Federated Learning Core — Aggregator, Protocol, and Models.

Provides FederatedAggregator for model aggregation across distributed nodes,
AggregatorProtocol for inter-node communication, and supporting data classes.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────

class AggregationStrategy(str, Enum):
    FEDAVG = "fedavg"
    FEDPROX = "fedprox"
    SCAFFOLD = "scaffold"


class RoundStatus(str, Enum):
    WAITING = "waiting"
    COLLECTING = "collecting"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Data Classes ─────────────────────────────────────────────────

@dataclass
class ModelDelta:
    delta_id: str
    node_id: str
    model_version: str
    timestamp: str
    round_number: int
    delta_type: str
    delta_data: dict[str, Any] = field(default_factory=dict)
    delta_size_bytes: int = 0
    samples_used: int = 0
    training_loss: float = 0.0
    validation_loss: float | None = None
    checksum: str = ""
    differential_privacy_applied: bool = False


@dataclass
class RoundInfo:
    round_number: int
    status: RoundStatus = RoundStatus.WAITING
    min_participants: int = 3
    timeout_seconds: int = 3600
    started_at: str = ""
    completed_at: str = ""
    participants: list[str] = field(default_factory=list)
    deltas_received: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_number": self.round_number,
            "status": self.status.value,
            "min_participants": self.min_participants,
            "timeout_seconds": self.timeout_seconds,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "participants": self.participants,
            "deltas_received": self.deltas_received,
        }


@dataclass
class TrainingConfig:
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 5
    optimizer: str = "adam"
    min_samples: int = 100
    differential_privacy: bool = False
    dp_epsilon: float = 1.0


# ── Federated Aggregator ─────────────────────────────────────────

class FederatedAggregator:
    """Manages federated learning rounds and model aggregation."""

    def __init__(self, strategy: AggregationStrategy = AggregationStrategy.FEDAVG):
        self.strategy = strategy
        self.nodes: dict[str, dict[str, Any]] = {}
        self.global_model: dict[str, Any] = {}
        self.model_version: str = "0.0.0"
        self.current_round_number: int = 0
        self._current_round: RoundInfo | None = None
        self._round_history: list[dict[str, Any]] = []
        self._deltas: list[ModelDelta] = []

    @property
    def registered_nodes(self) -> int:
        return len(self.nodes)

    async def register_node(self, node_id: str, info: dict[str, Any]) -> bool:
        self.nodes[node_id] = {
            "node_id": node_id,
            "registered_at": datetime.utcnow().isoformat(),
            "status": "active",
            **info,
        }
        logger.info(f"Node registered: {node_id}")
        return True

    def get_node_states(self) -> list[dict[str, Any]]:
        return list(self.nodes.values())

    async def get_global_model(self) -> tuple[dict[str, Any], str]:
        return self.global_model, self.model_version

    async def initialize_global_model(self, model_data: dict[str, Any], version: str) -> None:
        self.global_model = model_data
        self.model_version = version
        logger.info(f"Global model initialized: v{version}")

    async def submit_delta(self, delta: ModelDelta, node_id: str) -> tuple[bool, str]:
        if not self._current_round:
            return False, "No active round"
        if self._current_round.status != RoundStatus.COLLECTING:
            return False, f"Round not collecting (status={self._current_round.status.value})"
        self._deltas.append(delta)
        self._current_round.deltas_received += 1
        if node_id not in self._current_round.participants:
            self._current_round.participants.append(node_id)
        return True, "Delta accepted"

    async def start_round(self, min_participants: int = 3, timeout_seconds: int = 3600) -> RoundInfo:
        self.current_round_number += 1
        self._deltas = []
        self._current_round = RoundInfo(
            round_number=self.current_round_number,
            status=RoundStatus.COLLECTING,
            min_participants=min_participants,
            timeout_seconds=timeout_seconds,
            started_at=datetime.utcnow().isoformat(),
        )
        logger.info(f"Round {self.current_round_number} started")
        return self._current_round

    async def get_round_status(self) -> RoundInfo | None:
        return self._current_round

    def get_round_history(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._round_history[-limit:]


# ── Aggregator Protocol ──────────────────────────────────────────

class AggregatorProtocol:
    """Handles inter-node federated communication."""

    def __init__(self):
        self._nodes: dict[str, dict[str, Any]] = {}
        self._message_log: list[dict[str, Any]] = []

    def unregister_node(self, node_id: str) -> None:
        self._nodes.pop(node_id, None)
        logger.info(f"Node unregistered: {node_id}")

    async def notify_round_start(
        self, round_number: int, min_participants: int, timeout_seconds: int
    ) -> None:
        logger.info(
            f"Notifying nodes: round {round_number} started "
            f"(min_participants={min_participants}, timeout={timeout_seconds}s)"
        )

    async def receive_message(self, message: dict[str, Any]) -> _MessageResult | None:
        msg_id = message.get("message_id", str(uuid.uuid4()))
        self._message_log.append({"message_id": msg_id, **message})
        return _MessageResult(message_id=msg_id)


@dataclass
class _MessageResult:
    message_id: str
