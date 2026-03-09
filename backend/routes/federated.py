"""
Federated Learning API Endpoints.

REST API for multi-Nexus model sharing.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/federated", tags=["federated"])


# ── Pydantic Models ─────────────────────────────────────────────

class NodeRegisterRequest(BaseModel):
    """Request to register a federated node."""
    node_id: str
    endpoint: str
    public_key: str | None = None
    capabilities: dict[str, Any] = Field(default_factory=dict)


class DeltaSubmitRequest(BaseModel):
    """Request to submit a model delta."""
    delta_id: str
    node_id: str
    model_version: str
    round_number: int
    delta_type: str
    delta_data: dict[str, Any]
    delta_size_bytes: int
    samples_used: int
    training_loss: float
    validation_loss: float | None = None
    checksum: str = ""
    differential_privacy_applied: bool = False


class RoundStartRequest(BaseModel):
    """Request to start a new aggregation round."""
    min_participants: int = Field(default=3, ge=1, le=100)
    timeout_seconds: int = Field(default=3600, ge=60, le=86400)


class ConfigUpdateRequest(BaseModel):
    """Request to update federated config."""
    learning_rate: float | None = None
    batch_size: int | None = None
    epochs: int | None = None
    min_samples: int | None = None
    differential_privacy: bool | None = None
    dp_epsilon: float | None = None


# ── Global State (will be replaced with proper DI) ──────────────

_aggregator = None
_protocol = None


def get_aggregator():
    """Get or create aggregator instance."""
    global _aggregator
    if _aggregator is None:
        from tools.federated import FederatedAggregator, AggregationStrategy
        _aggregator = FederatedAggregator(
            strategy=AggregationStrategy.FEDAVG,
        )
    return _aggregator


def get_protocol():
    """Get or create protocol instance."""
    global _protocol
    if _protocol is None:
        from tools.federated import AggregatorProtocol
        _protocol = AggregatorProtocol()
    return _protocol


# ── Node Management ─────────────────────────────────────────────

@router.post("/register")
async def register_node(
    request: NodeRegisterRequest,
    aggregator = Depends(get_aggregator),
):
    """Register a new federated learning node."""
    success = await aggregator.register_node(
        request.node_id,
        {
            "endpoint": request.endpoint,
            "public_key": request.public_key,
            "capabilities": request.capabilities,
        }
    )
    
    if success:
        return {
            "status": "registered",
            "node_id": request.node_id,
            "current_round": aggregator.current_round_number,
            "model_version": aggregator.model_version,
        }
    else:
        raise HTTPException(400, "Failed to register node")


@router.get("/nodes")
async def list_nodes(
    aggregator = Depends(get_aggregator),
):
    """List all registered nodes."""
    return {
        "nodes": aggregator.get_node_states(),
        "total": aggregator.registered_nodes,
    }


@router.delete("/nodes/{node_id}")
async def unregister_node(
    node_id: str,
    protocol = Depends(get_protocol),
):
    """Unregister a node."""
    protocol.unregister_node(node_id)
    return {"status": "unregistered", "node_id": node_id}


# ── Model Management ───────────────────────────────────────────

@router.get("/model")
async def get_global_model(
    aggregator = Depends(get_aggregator),
):
    """Get current global model and version."""
    model, version = await aggregator.get_global_model()
    return {
        "model_version": version,
        "model_layers": len(model),
        "current_round": aggregator.current_round_number,
    }


@router.post("/model/initialize")
async def initialize_model(
    model_data: dict[str, Any],
    version: str = "1.0.0",
    aggregator = Depends(get_aggregator),
):
    """Initialize global model (admin only)."""
    await aggregator.initialize_global_model(model_data, version)
    return {
        "status": "initialized",
        "version": version,
    }


# ── Delta Submission ────────────────────────────────────────────

@router.post("/delta")
async def submit_delta(
    request: DeltaSubmitRequest,
    background_tasks: BackgroundTasks,
    aggregator = Depends(get_aggregator),
):
    """Submit a model delta from local training."""
    from tools.federated import ModelDelta
    
    delta = ModelDelta(
        delta_id=request.delta_id,
        node_id=request.node_id,
        model_version=request.model_version,
        timestamp=datetime.utcnow().isoformat(),
        round_number=request.round_number,
        delta_type=request.delta_type,
        delta_data=request.delta_data,
        delta_size_bytes=request.delta_size_bytes,
        samples_used=request.samples_used,
        training_loss=request.training_loss,
        validation_loss=request.validation_loss,
        checksum=request.checksum,
        differential_privacy_applied=request.differential_privacy_applied,
    )
    
    success, message = await aggregator.submit_delta(delta, request.node_id)
    
    if success:
        return {
            "status": "accepted",
            "delta_id": request.delta_id,
            "message": message,
        }
    else:
        raise HTTPException(400, message)


# ── Round Management ────────────────────────────────────────────

@router.post("/round/start")
async def start_round(
    request: RoundStartRequest,
    background_tasks: BackgroundTasks,
    aggregator = Depends(get_aggregator),
    protocol = Depends(get_protocol),
):
    """Start a new federated learning round."""
    round_info = await aggregator.start_round(
        min_participants=request.min_participants,
        timeout_seconds=request.timeout_seconds,
    )
    
    # Notify all nodes
    background_tasks.add_task(
        protocol.notify_round_start,
        round_info.round_number,
        request.min_participants,
        request.timeout_seconds,
    )
    
    return {
        "round_number": round_info.round_number,
        "status": round_info.status.value,
        "min_participants": round_info.min_participants,
        "timeout_seconds": round_info.timeout_seconds,
    }


@router.get("/round/status")
async def get_round_status(
    aggregator = Depends(get_aggregator),
):
    """Get current round status."""
    round_info = await aggregator.get_round_status()
    if round_info:
        return round_info.to_dict()
    else:
        return {
            "round_number": 0,
            "status": "no_active_round",
        }


@router.get("/round/history")
async def get_round_history(
    limit: int = 10,
    aggregator = Depends(get_aggregator),
):
    """Get aggregation round history."""
    return {
        "rounds": aggregator.get_round_history(limit),
    }


# ── Configuration ───────────────────────────────────────────────

@router.get("/config")
async def get_config():
    """Get current federated learning configuration."""
    from tools.federated import TrainingConfig
    config = TrainingConfig()
    return {
        "learning_rate": config.learning_rate,
        "batch_size": config.batch_size,
        "epochs": config.epochs,
        "optimizer": config.optimizer,
        "min_samples": config.min_samples,
        "differential_privacy": config.differential_privacy,
        "dp_epsilon": config.dp_epsilon,
    }


@router.put("/config")
async def update_config(
    request: ConfigUpdateRequest,
):
    """Update federated learning configuration."""
    # This would update a global config in production
    updated = {}
    if request.learning_rate is not None:
        updated["learning_rate"] = request.learning_rate
    if request.batch_size is not None:
        updated["batch_size"] = request.batch_size
    if request.epochs is not None:
        updated["epochs"] = request.epochs
    if request.min_samples is not None:
        updated["min_samples"] = request.min_samples
    if request.differential_privacy is not None:
        updated["differential_privacy"] = request.differential_privacy
    if request.dp_epsilon is not None:
        updated["dp_epsilon"] = request.dp_epsilon
    
    return {
        "status": "updated",
        "changes": updated,
    }


# ── Statistics & Monitoring ─────────────────────────────────────

@router.get("/stats")
async def get_stats(
    aggregator = Depends(get_aggregator),
):
    """Get federated learning statistics."""
    return {
        "registered_nodes": aggregator.registered_nodes,
        "current_round": aggregator.current_round_number,
        "model_version": aggregator.model_version,
        "total_rounds": len(aggregator.get_round_history(100)),
    }


@router.get("/health")
async def health_check():
    """Health check for federated learning module."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Message Handler ─────────────────────────────────────────────

@router.post("/message")
async def handle_message(
    message: dict[str, Any],
    protocol = Depends(get_protocol),
):
    """Handle incoming federated protocol message."""
    result = await protocol.receive_message(message)
    
    if result:
        return {"status": "processed", "message_id": result.message_id}
    else:
        raise HTTPException(400, "Failed to process message")