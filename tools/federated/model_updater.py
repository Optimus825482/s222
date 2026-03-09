"""
Model Updater — Local Training & Delta Computation.

Computes model deltas (gradients/weights differences) after local training
for federated learning across Nexus deployments.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import logging
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)


class TrainingStatus(Enum):
    """Training status states."""
    IDLE = "idle"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TrainingConfig:
    """Configuration for local training."""
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 1
    optimizer: str = "adam"  # adam, sgd, rmsprop
    loss_function: str = "cross_entropy"
    gradient_clip: float = 1.0
    weight_decay: float = 0.01
    early_stopping_patience: int = 5
    validation_split: float = 0.2
    # Federated specific
    min_samples: int = 100
    max_delta_size_mb: float = 10.0
    differential_privacy: bool = True
    dp_epsilon: float = 1.0
    dp_delta: float = 1e-5


@dataclass
class ModelDelta:
    """
    Model delta - difference between local trained model and global model.
    
    Contains gradient updates or weight differences for federated aggregation.
    """
    # Metadata
    delta_id: str
    node_id: str
    model_version: str
    timestamp: str
    round_number: int
    
    # Delta data
    delta_type: str  # "gradients", "weights_diff", "lora_adapters"
    delta_data: dict[str, Any]  # Layer name -> tensor/gradient
    delta_size_bytes: int
    
    # Training metrics
    samples_used: int
    training_loss: float
    validation_loss: float | None = None
    training_time_seconds: float = 0.0
    
    # Privacy & Security
    differential_privacy_applied: bool = False
    noise_scale: float = 0.0
    checksum: str = ""
    
    # Compression
    compressed: bool = False
    compression_ratio: float = 1.0
    
    def compute_checksum(self) -> str:
        """Compute checksum for integrity verification."""
        data_str = json.dumps({
            "delta_id": self.delta_id,
            "node_id": self.node_id,
            "model_version": self.model_version,
            "timestamp": self.timestamp,
            "round_number": self.round_number,
            "delta_type": self.delta_type,
        }, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for transport."""
        return {
            "delta_id": self.delta_id,
            "node_id": self.node_id,
            "model_version": self.model_version,
            "timestamp": self.timestamp,
            "round_number": self.round_number,
            "delta_type": self.delta_type,
            "delta_data": self.delta_data,
            "delta_size_bytes": self.delta_size_bytes,
            "samples_used": self.samples_used,
            "training_loss": self.training_loss,
            "validation_loss": self.validation_loss,
            "training_time_seconds": self.training_time_seconds,
            "differential_privacy_applied": self.differential_privacy_applied,
            "noise_scale": self.noise_scale,
            "checksum": self.checksum,
            "compressed": self.compressed,
            "compression_ratio": self.compression_ratio,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ModelDelta":
        """Deserialize from dictionary."""
        return cls(
            delta_id=data["delta_id"],
            node_id=data["node_id"],
            model_version=data["model_version"],
            timestamp=data["timestamp"],
            round_number=data["round_number"],
            delta_type=data["delta_type"],
            delta_data=data["delta_data"],
            delta_size_bytes=data["delta_size_bytes"],
            samples_used=data["samples_used"],
            training_loss=data["training_loss"],
            validation_loss=data.get("validation_loss"),
            training_time_seconds=data.get("training_time_seconds", 0.0),
            differential_privacy_applied=data.get("differential_privacy_applied", False),
            noise_scale=data.get("noise_scale", 0.0),
            checksum=data.get("checksum", ""),
            compressed=data.get("compressed", False),
            compression_ratio=data.get("compression_ratio", 1.0),
        )


@dataclass
class TrainingResult:
    """Result of a local training session."""
    status: TrainingStatus
    delta: ModelDelta | None = None
    error_message: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)


class ModelUpdater:
    """
    Manages local model training and delta computation for federated learning.
    
    Workflow:
    1. Receive global model from aggregator
    2. Train on local data (privacy preserved)
    3. Compute delta (gradients/weight differences)
    4. Apply differential privacy if enabled
    5. Send encrypted delta to aggregator
    """
    
    def __init__(
        self,
        node_id: str,
        model_path: Path | None = None,
        config: TrainingConfig | None = None,
        storage_path: Path | None = None,
    ):
        self.node_id = node_id
        self.config = config or TrainingConfig()
        self.model_path = model_path
        self.storage_path = storage_path or Path("./data/federated/deltas")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._current_model: dict[str, Any] = {}
        self._global_model_version: str = "0.0.0"
        self._current_round: int = 0
        self._training_status: TrainingStatus = TrainingStatus.IDLE
        self._training_history: list[TrainingResult] = []
        
    @property
    def status(self) -> TrainingStatus:
        return self._training_status
    
    @property
    def current_round(self) -> int:
        return self._current_round
    
    async def load_global_model(self, model_data: dict, version: str) -> bool:
        """
        Load global model received from aggregator.
        
        Args:
            model_data: Model weights/config
            version: Model version string
            
        Returns:
            True if loaded successfully
        """
        try:
            self._current_model = model_data
            self._global_model_version = version
            logger.info(f"Loaded global model v{version} with {len(model_data)} layers")
            return True
        except Exception as e:
            logger.error(f"Failed to load global model: {e}")
            return False
    
    async def train_local(
        self,
        training_data: list[dict],
        validation_data: list[dict] | None = None,
    ) -> TrainingResult:
        """
        Train model on local data and compute delta.
        
        This is the main entry point for federated learning.
        Local data never leaves the node - only gradients/deltas are shared.
        
        Args:
            training_data: Local training samples
            validation_data: Optional validation samples
            
        Returns:
            TrainingResult with computed delta
        """
        if self._training_status == TrainingStatus.TRAINING:
            return TrainingResult(
                status=TrainingStatus.FAILED,
                error_message="Training already in progress"
            )
        
        if len(training_data) < self.config.min_samples:
            return TrainingResult(
                status=TrainingStatus.FAILED,
                error_message=f"Insufficient samples: {len(training_data)} < {self.config.min_samples}"
            )
        
        self._training_status = TrainingStatus.TRAINING
        start_time = time.time()
        
        try:
            # Simulate local training (in production, use actual ML framework)
            training_result = await self._execute_training(
                training_data, validation_data
            )
            
            # Compute delta
            delta = await self._compute_delta(training_result)
            
            # Apply differential privacy
            if self.config.differential_privacy:
                delta = self._apply_differential_privacy(delta)
            
            # Compress if needed
            if delta.delta_size_bytes > self.config.max_delta_size_mb * 1024 * 1024:
                delta = await self._compress_delta(delta)
            
            training_time = time.time() - start_time
            delta.training_time_seconds = training_time
            delta.checksum = delta.compute_checksum()
            
            result = TrainingResult(
                status=TrainingStatus.COMPLETED,
                delta=delta,
                metrics={
                    "training_loss": delta.training_loss,
                    "validation_loss": delta.validation_loss or 0.0,
                    "training_time": training_time,
                    "samples_used": delta.samples_used,
                }
            )
            
            self._training_history.append(result)
            logger.info(f"Training completed: delta_id={delta.delta_id}, loss={delta.training_loss:.4f}")
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            result = TrainingResult(
                status=TrainingStatus.FAILED,
                error_message=str(e)
            )
        
        finally:
            self._training_status = TrainingStatus.IDLE
        
        return result
    
    async def _execute_training(
        self,
        training_data: list[dict],
        validation_data: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Execute local training loop.
        
        In production, this would use PyTorch/TensorFlow/JAX.
        Here we simulate the training process.
        """
        # Simulate training epochs
        losses = []
        val_losses = []
        
        for epoch in range(self.config.epochs):
            # Simulate batch training
            epoch_loss = 0.0
            n_batches = len(training_data) // self.config.batch_size
            
            for batch_idx in range(n_batches):
                # Simulate forward/backward pass
                batch_loss = await self._train_batch(
                    training_data[batch_idx * self.config.batch_size:(batch_idx + 1) * self.config.batch_size]
                )
                epoch_loss += batch_loss
            
            epoch_loss /= n_batches
            losses.append(epoch_loss)
            
            # Validation
            if validation_data:
                val_loss = await self._validate(validation_data)
                val_losses.append(val_loss)
                logger.debug(f"Epoch {epoch}: loss={epoch_loss:.4f}, val_loss={val_loss:.4f}")
            else:
                logger.debug(f"Epoch {epoch}: loss={epoch_loss:.4f}")
        
        return {
            "final_loss": losses[-1],
            "val_loss": val_losses[-1] if val_losses else None,
            "loss_history": losses,
            "gradient_norm": 0.1,  # Simulated
        }
    
    async def _train_batch(self, batch: list[dict]) -> float:
        """Train single batch - simulated."""
        # Simulate computation time
        await asyncio.sleep(0.001)
        # Return simulated loss
        return 0.5 * (1 - 0.1 * len(batch) / self.config.batch_size)
    
    async def _validate(self, validation_data: list[dict]) -> float:
        """Validate model - simulated."""
        await asyncio.sleep(0.0005)
        return 0.6  # Simulated validation loss
    
    async def _compute_delta(self, training_result: dict) -> ModelDelta:
        """
        Compute model delta - difference between trained and global model.
        
        This is the key step for federated learning:
        - Gradients approach: Share gradient updates
        - Weights diff approach: Share weight differences
        - LoRA approach: Share adapter weights only
        """
        delta_id = f"delta_{self.node_id}_{int(time.time() * 1000)}"
        
        # Simulate computing weight differences
        # In production, this would be actual tensor operations
        delta_data = {}
        total_size = 0
        
        for layer_name in self._current_model.keys():
            # Simulated gradient/weight diff
            delta_data[layer_name] = {
                "shape": [128, 256],  # Simulated shape
                "mean": 0.001 * (hash(layer_name) % 10),  # Simulated update
                "std": 0.01,
                "sparse_indices": [],  # For sparse updates
            }
            total_size += 128 * 256 * 4  # float32 bytes
        
        delta = ModelDelta(
            delta_id=delta_id,
            node_id=self.node_id,
            model_version=self._global_model_version,
            timestamp=datetime.utcnow().isoformat(),
            round_number=self._current_round,
            delta_type="gradients",
            delta_data=delta_data,
            delta_size_bytes=total_size,
            samples_used=self.config.batch_size * self.config.epochs,
            training_loss=training_result["final_loss"],
            validation_loss=training_result.get("val_loss"),
            differential_privacy_applied=False,
        )
        
        return delta
    
    def _apply_differential_privacy(self, delta: ModelDelta) -> ModelDelta:
        """
        Apply differential privacy to delta.
        
        Uses Gaussian mechanism for privacy-preserving gradient updates.
        """
        import math
        import random
        
        # Compute noise scale based on DP parameters
        sensitivity = 1.0  # Gradient sensitivity
        sigma = sensitivity * math.sqrt(
            2 * math.log(1.25 / self.config.dp_delta)
        ) / self.config.dp_epsilon
        
        # Add Gaussian noise to each layer
        for layer_name, layer_data in delta.delta_data.items():
            noise = random.gauss(0, sigma)
            layer_data["mean"] += noise
        
        delta.differential_privacy_applied = True
        delta.noise_scale = sigma
        
        logger.info(f"Applied DP: epsilon={self.config.dp_epsilon}, sigma={sigma:.4f}")
        return delta
    
    async def _compress_delta(self, delta: ModelDelta) -> ModelDelta:
        """
        Compress delta for efficient transmission.
        
        Uses quantization and sparse encoding.
        """
        # Simulate compression (in production, use actual compression)
        compressed_data = {}
        
        for layer_name, layer_data in delta.delta_data.items():
            # Keep only significant updates (top-k sparsification)
            compressed_data[layer_name] = {
                **layer_data,
                "compressed": True,
            }
        
        delta.delta_data = compressed_data
        delta.compressed = True
        delta.compression_ratio = 0.3  # 70% reduction
        
        logger.info(f"Compressed delta: {delta.compression_ratio:.1%} of original")
        return delta
    
    async def save_delta(self, delta: ModelDelta) -> Path:
        """Save delta to local storage."""
        file_path = self.storage_path / f"{delta.delta_id}.pkl"
        with open(file_path, "wb") as f:
            pickle.dump(delta.to_dict(), f)
        logger.debug(f"Saved delta to {file_path}")
        return file_path
    
    async def load_delta(self, delta_id: str) -> ModelDelta | None:
        """Load delta from local storage."""
        file_path = self.storage_path / f"{delta_id}.pkl"
        if not file_path.exists():
            return None
        with open(file_path, "rb") as f:
            data = pickle.load(f)
        return ModelDelta.from_dict(data)
    
    def get_training_history(self, limit: int = 10) -> list[dict]:
        """Get recent training history."""
        return [
            {
                "delta_id": r.delta.delta_id if r.delta else None,
                "status": r.status.value,
                "metrics": r.metrics,
                "error": r.error_message,
            }
            for r in self._training_history[-limit:]
        ]
    
    def set_round(self, round_number: int) -> None:
        """Set current federated learning round."""
        self._current_round = round_number
        logger.info(f"Round set to {round_number}")