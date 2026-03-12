"""
Federated Aggregator — Central Model Aggregation Server.

Aggregates model deltas from multiple Nexus deployments
using various strategies (FedAvg, FedProx, etc.).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .model_updater import ModelDelta

logger = logging.getLogger(__name__)


class AggregationStrategy(Enum):
    """Federated aggregation strategies."""
    FEDAVG = "fedavg"  # Standard Federated Averaging
    FEDPROX = "fedprox"  # FedProx with proximal term
    FEDADAM = "fedadam"  # Federated Adam
    FEDYOGI = "fedyogi"  # Federated Yogi
    SCAFFOLD = "scaffold"  # SCAFFOLD with variance reduction
    WEIGHTED = "weighted"  # Weighted by sample count


class AggregationStatus(Enum):
    """Status of aggregation process."""
    PENDING = "pending"
    COLLECTING = "collecting"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AggregationRound:
    """Represents a single federated learning round."""
    round_number: int
    status: AggregationStatus
    start_time: str
    end_time: str | None = None
    min_participants: int = 3
    max_participants: int = 100
    timeout_seconds: int = 3600  # 1 hour default
    
    # Collected deltas
    deltas: list[ModelDelta] = field(default_factory=list)
    node_ids: list[str] = field(default_factory=list)
    
    # Aggregation result
    aggregated_model: dict[str, Any] | None = None
    new_model_version: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "round_number": self.round_number,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "min_participants": self.min_participants,
            "max_participants": self.max_participants,
            "timeout_seconds": self.timeout_seconds,
            "n_deltas": len(self.deltas),
            "node_ids": self.node_ids,
            "new_model_version": self.new_model_version,
            "metrics": self.metrics,
        }


@dataclass
class NodeState:
    """State of a federated learning node."""
    node_id: str
    last_seen: str
    current_round: int
    total_deltas_submitted: int = 0
    reputation_score: float = 1.0
    is_active: bool = True
    
    # Quality metrics
    avg_training_loss: float = 0.0
    avg_validation_loss: float = 0.0
    avg_samples_per_round: int = 0


class AggregationAlgorithm(ABC):
    """Base class for aggregation algorithms."""
    
    @abstractmethod
    async def aggregate(
        self,
        deltas: list[ModelDelta],
        current_model: dict[str, Any],
    ) -> dict[str, Any]:
        """Aggregate deltas into new model."""
        pass


class FedAvgAlgorithm(AggregationAlgorithm):
    """
    Federated Averaging (FedAvg) algorithm.
    
    Weighted average of model updates based on sample counts.
    Formula: w_new = w_global + Σ (n_k / n_total) * Δ_k
    """
    
    def __init__(self, learning_rate: float = 1.0):
        self.learning_rate = learning_rate
    
    async def aggregate(
        self,
        deltas: list[ModelDelta],
        current_model: dict[str, Any],
    ) -> dict[str, Any]:
        if not deltas:
            return current_model
        
        # Compute total samples
        total_samples = sum(d.samples_used for d in deltas)
        
        # Weighted average of deltas
        aggregated = {}
        for layer_name in current_model.keys():
            weighted_sum = 0.0
            for delta in deltas:
                if layer_name in delta.delta_data:
                    weight = delta.samples_used / total_samples
                    layer_update = delta.delta_data[layer_name].get("mean", 0)
                    weighted_sum += weight * layer_update
            
            # Apply learning rate
            aggregated[layer_name] = {
                **current_model[layer_name],
                "value": current_model[layer_name].get("value", 0) + self.learning_rate * weighted_sum,
            }
        
        return aggregated


class FedProxAlgorithm(AggregationAlgorithm):
    """
    FedProx algorithm with proximal term.
    
    Adds regularization to prevent models from drifting too far:
    min ||w - w_global||² + μ * proximal_term
    """
    
    def __init__(self, learning_rate: float = 1.0, mu: float = 0.01):
        self.learning_rate = learning_rate
        self.mu = mu  # Proximal term coefficient
    
    async def aggregate(
        self,
        deltas: list[ModelDelta],
        current_model: dict[str, Any],
    ) -> dict[str, Any]:
        if not deltas:
            return current_model
        
        total_samples = sum(d.samples_used for d in deltas)
        aggregated = {}
        
        for layer_name in current_model.keys():
            weighted_sum = 0.0
            for delta in deltas:
                if layer_name in delta.delta_data:
                    weight = delta.samples_used / total_samples
                    layer_update = delta.delta_data[layer_name].get("mean", 0)
                    # Apply proximal term damping
                    damped_update = layer_update / (1 + self.mu)
                    weighted_sum += weight * damped_update
            
            aggregated[layer_name] = {
                **current_model[layer_name],
                "value": current_model[layer_name].get("value", 0) + self.learning_rate * weighted_sum,
            }
        
        return aggregated


class FederatedAggregator:
    """
    Central aggregator for federated learning.
    
    Responsibilities:
    - Collect deltas from nodes
    - Validate and filter deltas
    - Aggregate using selected strategy
    - Detect malicious nodes (model poisoning)
    - Distribute updated global model
    """
    
    def __init__(
        self,
        strategy: AggregationStrategy = AggregationStrategy.FEDAVG,
        storage_path: Path | None = None,
        min_participants_per_round: int = 3,
        round_timeout_seconds: int = 3600,
    ):
        self.strategy = strategy
        self.storage_path = storage_path or Path("./data/federated/aggregator")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.min_participants = min_participants_per_round
        self.round_timeout = round_timeout_seconds
        
        # State
        self._current_round: AggregationRound | None = None
        self._global_model: dict[str, Any] = {}
        self._model_version: str = "0.0.0"
        self._nodes: dict[str, NodeState] = {}
        self._round_history: list[AggregationRound] = []
        self._aggregation_task: asyncio.Task | None = None
        self._round_lock = asyncio.Lock()
        
        # Algorithm
        self._algorithm = self._create_algorithm(strategy)
        
        # Security
        self._malicious_threshold: float = 3.0  # Standard deviations
        self._min_reputation: float = 0.5
        
    def _create_algorithm(self, strategy: AggregationStrategy) -> AggregationAlgorithm:
        """Create aggregation algorithm based on strategy."""
        algorithms = {
            AggregationStrategy.FEDAVG: FedAvgAlgorithm(),
            AggregationStrategy.FEDPROX: FedProxAlgorithm(),
            AggregationStrategy.FEDADAM: FedAvgAlgorithm(),  # Simplified
            AggregationStrategy.WEIGHTED: FedAvgAlgorithm(),
        }
        return algorithms.get(strategy, FedAvgAlgorithm())
    
    @property
    def current_round_number(self) -> int:
        return self._current_round.round_number if self._current_round else 0
    
    @property
    def model_version(self) -> str:
        return self._model_version
    
    @property
    def registered_nodes(self) -> int:
        return len(self._nodes)
    
    async def initialize_global_model(
        self,
        model_data: dict[str, Any],
        version: str = "1.0.0",
    ) -> None:
        """Initialize or reset the global model."""
        self._global_model = model_data
        self._model_version = version
        logger.info(f"Initialized global model v{version} with {len(model_data)} layers")
        
        # Save initial model
        await self._save_model(model_data, version)
    
    async def start_round(
        self,
        min_participants: int | None = None,
        timeout_seconds: int | None = None,
    ) -> AggregationRound:
        """
        Start a new federated learning round.
        
        Nodes will be notified to start local training.
        """
        async with self._round_lock:
            if self._current_round and self._current_round.status in [
                AggregationStatus.COLLECTING,
                AggregationStatus.AGGREGATING,
            ]:
                if self._is_round_timed_out(self._current_round):
                    logger.warning(
                        f"Round {self._current_round.round_number} timed out; marking as failed and starting a new round"
                    )
                    self._current_round.status = AggregationStatus.FAILED
                    self._current_round.end_time = datetime.utcnow().isoformat()
                    self._round_history.append(self._current_round)
                    self._current_round = None
                else:
                    logger.info(
                        f"Round {self._current_round.round_number} still in progress"
                    )
                    return self._current_round

            round_number = self.current_round_number + 1
            self._current_round = AggregationRound(
                round_number=round_number,
                status=AggregationStatus.COLLECTING,
                start_time=datetime.utcnow().isoformat(),
                min_participants=min_participants or self.min_participants,
                timeout_seconds=timeout_seconds or self.round_timeout,
            )

            logger.info(
                f"Started round {round_number}, waiting for {self._current_round.min_participants} participants"
            )
            return self._current_round

    def _is_round_timed_out(self, round_state: AggregationRound) -> bool:
        """Return True when a collecting/aggregating round exceeded its timeout window."""
        try:
            started = datetime.fromisoformat(round_state.start_time)
        except Exception:
            return False
        return (
            datetime.utcnow() - started
        ).total_seconds() > round_state.timeout_seconds

    async def register_node(
        self,
        node_id: str,
        node_info: dict | None = None,
    ) -> bool:
        """Register a new federated learning node."""
        if node_id in self._nodes:
            # Update existing node
            self._nodes[node_id].last_seen = datetime.utcnow().isoformat()
            self._nodes[node_id].is_active = True
            logger.debug(f"Node {node_id} reconnected")
        else:
            # New node
            self._nodes[node_id] = NodeState(
                node_id=node_id,
                last_seen=datetime.utcnow().isoformat(),
                current_round=self.current_round_number,
            )
            logger.info(f"Registered new node: {node_id}")
        
        return True
    
    async def submit_delta(
        self,
        delta: ModelDelta,
        node_id: str,
    ) -> tuple[bool, str]:
        """
        Submit a model delta from a node.
        
        Returns:
            (success, message) tuple
        """
        if not self._current_round:
            return False, "No active round"
        
        if self._current_round.status != AggregationStatus.COLLECTING:
            return False, f"Round not accepting deltas (status: {self._current_round.status.value})"
        
        # Validate delta
        is_valid, message = await self._validate_delta(delta)
        if not is_valid:
            logger.warning(f"Invalid delta from {node_id}: {message}")
            return False, message
        
        # Check for malicious behavior
        is_malicious, anomaly_score = await self._detect_anomaly(delta)
        if is_malicious:
            logger.warning(f"Potential malicious delta from {node_id}, score={anomaly_score:.2f}")
            self._nodes[node_id].reputation_score *= 0.9  # Reduce reputation
            return False, "Delta rejected due to anomaly detection"
        
        # Store delta
        self._current_round.deltas.append(delta)
        if node_id not in self._current_round.node_ids:
            self._current_round.node_ids.append(node_id)
        
        # Update node state
        if node_id in self._nodes:
            self._nodes[node_id].total_deltas_submitted += 1
            self._nodes[node_id].last_seen = datetime.utcnow().isoformat()
            self._nodes[node_id].current_round = self._current_round.round_number
        
        logger.info(f"Accepted delta from {node_id}, total deltas: {len(self._current_round.deltas)}")
        
        # Check if we have enough participants
        if len(self._current_round.deltas) >= self._current_round.min_participants:
            # Trigger aggregation once; avoid duplicate tasks from concurrent submissions.
            if self._aggregation_task is None or self._aggregation_task.done():
                self._aggregation_task = asyncio.create_task(
                    self._aggregate_and_complete()
                )
        
        return True, f"Delta accepted, {len(self._current_round.deltas)} total"
    
    async def _validate_delta(self, delta: ModelDelta) -> tuple[bool, str]:
        """Validate a submitted delta."""
        # Check version match
        if delta.model_version != self._model_version:
            return False, f"Version mismatch: {delta.model_version} != {self._model_version}"
        
        # Check checksum
        expected_checksum = delta.compute_checksum()
        if delta.checksum and delta.checksum != expected_checksum:
            return False, "Checksum verification failed"
        
        # Check round number
        if delta.round_number != self.current_round_number:
            return False, f"Wrong round: {delta.round_number} != {self.current_round_number}"
        
        # Check delta size
        max_size = 100 * 1024 * 1024  # 100MB
        if delta.delta_size_bytes > max_size:
            return False, f"Delta too large: {delta.delta_size_bytes} > {max_size}"
        
        return True, "Valid"
    
    async def _detect_anomaly(self, delta: ModelDelta) -> tuple[bool, float]:
        """
        Detect anomalous/malicious deltas using statistical methods.
        
        Returns:
            (is_anomaly, anomaly_score)
        """
        if not self._current_round or len(self._current_round.deltas) < 3:
            return False, 0.0
        
        # Compare with existing deltas
        existing_losses = [d.training_loss for d in self._current_round.deltas]
        mean_loss = sum(existing_losses) / len(existing_losses)
        std_loss = (sum((l - mean_loss) ** 2 for l in existing_losses) / len(existing_losses)) ** 0.5
        
        if std_loss > 0:
            z_score = abs(delta.training_loss - mean_loss) / std_loss
            is_anomaly = z_score > self._malicious_threshold
            return is_anomaly, z_score
        
        return False, 0.0
    
    async def _aggregate_and_complete(self) -> None:
        """Execute aggregation and complete the round."""
        if not self._current_round:
            return
        
        self._current_round.status = AggregationStatus.AGGREGATING
        logger.info(f"Aggregating {len(self._current_round.deltas)} deltas")
        
        try:
            # Run aggregation algorithm
            new_model = await self._algorithm.aggregate(
                self._current_round.deltas,
                self._global_model,
            )
            
            # Update version
            parts = self._model_version.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            new_version = ".".join(parts)
            
            # Compute metrics
            metrics = {
                "avg_training_loss": sum(d.training_loss for d in self._current_round.deltas) / len(self._current_round.deltas),
                "total_samples": sum(d.samples_used for d in self._current_round.deltas),
                "n_participants": len(self._current_round.deltas),
                "avg_delta_size_mb": sum(d.delta_size_bytes for d in self._current_round.deltas) / len(self._current_round.deltas) / 1024 / 1024,
            }
            
            # Save results
            await self._save_model(new_model, new_version)
            
            # Update state
            self._global_model = new_model
            self._model_version = new_version
            self._current_round.aggregated_model = new_model
            self._current_round.new_model_version = new_version
            self._current_round.metrics = metrics
            self._current_round.status = AggregationStatus.COMPLETED
            self._current_round.end_time = datetime.utcnow().isoformat()
            
            # Archive round
            self._round_history.append(self._current_round)
            
            logger.info(f"Round {self._current_round.round_number} completed, new version: {new_version}")

        except Exception as e:
            logger.error(f"Aggregation failed: {e}")
            self._current_round.status = AggregationStatus.FAILED
            self._current_round.end_time = datetime.utcnow().isoformat()
        finally:
            self._aggregation_task = None
    
    async def _save_model(self, model: dict[str, Any], version: str) -> None:
        """Save model to storage."""
        import pickle
        
        file_path = self.storage_path / f"model_v{version}.pkl"
        with open(file_path, "wb") as f:
            pickle.dump({"model": model, "version": version}, f)
        logger.debug(f"Saved model to {file_path}")
    
    async def get_global_model(self) -> tuple[dict[str, Any], str]:
        """Get current global model and version."""
        return self._global_model, self._model_version
    
    async def get_round_status(self) -> AggregationRound | None:
        """Get current round status."""
        return self._current_round
    
    def get_node_states(self) -> list[dict]:
        """Get all registered node states."""
        return [
            {
                "node_id": ns.node_id,
                "last_seen": ns.last_seen,
                "current_round": ns.current_round,
                "total_deltas": ns.total_deltas_submitted,
                "reputation": ns.reputation_score,
                "is_active": ns.is_active,
            }
            for ns in self._nodes.values()
        ]
    
    def get_round_history(self, limit: int = 10) -> list[dict]:
        """Get aggregation round history."""
        return [r.to_dict() for r in self._round_history[-limit:]]