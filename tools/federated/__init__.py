"""
Federated Learning Module — Multi-Nexus Model Sharing.

Enables distributed model improvement across multiple Nexus deployments
while preserving data privacy.

Components:
- ModelUpdater: Local training & delta computation
- Aggregator: Central model aggregation server
- Protocol: Communication layer
- Crypto: Secure delta exchange
"""

from .model_updater import ModelUpdater, TrainingConfig, ModelDelta
from .aggregator import FederatedAggregator, AggregationStrategy
from .protocol import FederatedProtocol, NodeInfo, MessageType
from .crypto import DeltaEncryptor, SecureChannel

__all__ = [
    "ModelUpdater",
    "TrainingConfig",
    "ModelDelta",
    "FederatedAggregator",
    "AggregationStrategy",
    "FederatedProtocol",
    "NodeInfo",
    "MessageType",
    "DeltaEncryptor",
    "SecureChannel",
]