"""
Federated Protocol — Communication Layer.

Handles secure communication between Nexus nodes and aggregator.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Message types for federated communication."""
    # Registration
    REGISTER_NODE = "register_node"
    NODE_HEARTBEAT = "node_heartbeat"
    UNREGISTER_NODE = "unregister_node"
    
    # Model distribution
    MODEL_BROADCAST = "model_broadcast"
    MODEL_REQUEST = "model_request"
    MODEL_RESPONSE = "model_response"
    
    # Delta submission
    DELTA_SUBMIT = "delta_submit"
    DELTA_ACK = "delta_ack"
    DELTA_REJECT = "delta_reject"
    
    # Round management
    ROUND_START = "round_start"
    ROUND_STATUS = "round_status"
    ROUND_COMPLETE = "round_complete"
    
    # Control
    AGGREGATION_TRIGGER = "aggregation_trigger"
    CONFIG_UPDATE = "config_update"
    ERROR = "error"


@dataclass
class NodeInfo:
    """Information about a federated learning node."""
    node_id: str
    endpoint: str
    public_key: str | None = None
    capabilities: dict[str, Any] = field(default_factory=dict)
    last_heartbeat: str | None = None
    is_online: bool = True
    
    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "endpoint": self.endpoint,
            "public_key": self.public_key,
            "capabilities": self.capabilities,
            "last_heartbeat": self.last_heartbeat,
            "is_online": self.is_online,
        }


@dataclass
class FederatedMessage:
    """Message for federated communication."""
    message_type: MessageType
    sender_id: str
    recipient_id: str  # "aggregator" for aggregator, node_id for node
    timestamp: str
    payload: dict[str, Any]
    message_id: str = ""
    signature: str | None = None
    requires_ack: bool = False
    
    def __post_init__(self):
        if not self.message_id:
            self.message_id = hashlib.sha256(
                f"{self.message_type.value}{self.sender_id}{self.timestamp}".encode()
            ).hexdigest()[:16]
    
    def to_dict(self) -> dict:
        return {
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "message_id": self.message_id,
            "signature": self.signature,
            "requires_ack": self.requires_ack,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "FederatedMessage":
        return cls(
            message_type=MessageType(data["message_type"]),
            sender_id=data["sender_id"],
            recipient_id=data["recipient_id"],
            timestamp=data["timestamp"],
            payload=data["payload"],
            message_id=data.get("message_id", ""),
            signature=data.get("signature"),
            requires_ack=data.get("requires_ack", False),
        )


@dataclass
class ProtocolConfig:
    """Configuration for federated protocol."""
    heartbeat_interval_seconds: int = 30
    message_timeout_seconds: int = 60
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    max_message_size_mb: int = 100
    compression_enabled: bool = True
    encryption_enabled: bool = True


class FederatedProtocol:
    """
    Handles communication between nodes and aggregator.
    
    Features:
    - Secure message passing
    - Heartbeat monitoring
    - Automatic retry
    - Message compression
    """
    
    def __init__(
        self,
        node_id: str,
        aggregator_url: str | None = None,
        config: ProtocolConfig | None = None,
    ):
        self.node_id = node_id
        self.aggregator_url = aggregator_url
        self.config = config or ProtocolConfig()
        
        self._known_nodes: dict[str, NodeInfo] = {}
        self._message_handlers: dict[MessageType, Callable] = {}
        self._pending_acks: dict[str, asyncio.Event] = {}
        self._heartbeat_task: asyncio.Task | None = None
        self._is_running: bool = False
        
    def register_handler(
        self,
        message_type: MessageType,
        handler: Callable[[FederatedMessage], Any],
    ) -> None:
        """Register a handler for a message type."""
        self._message_handlers[message_type] = handler
        logger.debug(f"Registered handler for {message_type.value}")
    
    async def start(self) -> None:
        """Start the protocol - begin heartbeat and message processing."""
        self._is_running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Protocol started for node {self.node_id}")
    
    async def stop(self) -> None:
        """Stop the protocol."""
        self._is_running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Protocol stopped for node {self.node_id}")
    
    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat to aggregator."""
        while self._is_running:
            try:
                if self.aggregator_url:
                    await self._send_heartbeat()
                await asyncio.sleep(self.config.heartbeat_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
    
    async def _send_heartbeat(self) -> None:
        """Send heartbeat to aggregator."""
        message = FederatedMessage(
            message_type=MessageType.NODE_HEARTBEAT,
            sender_id=self.node_id,
            recipient_id="aggregator",
            timestamp=datetime.utcnow().isoformat(),
            payload={
                "node_id": self.node_id,
                "status": "healthy",
                "current_round": 0,
            },
        )
        await self.send_message(message)
    
    async def send_message(
        self,
        message: FederatedMessage,
        endpoint: str | None = None,
    ) -> bool:
        """
        Send a message to aggregator or another node.
        
        Args:
            message: Message to send
            endpoint: Target endpoint (default: aggregator)
            
        Returns:
            True if sent successfully
        """
        target_url = endpoint or self.aggregator_url
        if not target_url:
            logger.warning("No target URL for message")
            return False
        
        try:
            async with httpx.AsyncClient(timeout=self.config.message_timeout_seconds) as client:
                response = await client.post(
                    f"{target_url}/api/federated/message",
                    json=message.to_dict(),
                    headers={"Content-Type": "application/json"},
                )
                
                if response.status_code == 200:
                    logger.debug(f"Sent {message.message_type.value} to {target_url}")
                    return True
                else:
                    logger.warning(f"Message failed: {response.status_code}")
                    return False
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout sending message to {target_url}")
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    async def send_with_retry(
        self,
        message: FederatedMessage,
        endpoint: str | None = None,
    ) -> bool:
        """Send message with automatic retry."""
        for attempt in range(self.config.retry_attempts):
            if await self.send_message(message, endpoint):
                return True
            
            if attempt < self.config.retry_attempts - 1:
                await asyncio.sleep(self.config.retry_delay_seconds)
                logger.info(f"Retrying message (attempt {attempt + 2}/{self.config.retry_attempts})")
        
        return False
    
    async def receive_message(self, message_data: dict) -> FederatedMessage | None:
        """
        Process incoming message.
        
        Args:
            message_data: Raw message data
            
        Returns:
            Parsed message or None if invalid
        """
        try:
            message = FederatedMessage.from_dict(message_data)
            
            # Verify signature if present
            if message.signature:
                # TODO: Implement signature verification
                pass
            
            # Dispatch to handler
            handler = self._message_handlers.get(message.message_type)
            if handler:
                await handler(message)
            else:
                logger.warning(f"No handler for {message.message_type.value}")
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return None
    
    def register_node(self, node_info: NodeInfo) -> None:
        """Register a known node."""
        self._known_nodes[node_info.node_id] = node_info
        logger.info(f"Registered node: {node_info.node_id}")
    
    def unregister_node(self, node_id: str) -> None:
        """Unregister a node."""
        if node_id in self._known_nodes:
            del self._known_nodes[node_id]
            logger.info(f"Unregistered node: {node_id}")
    
    def get_node(self, node_id: str) -> NodeInfo | None:
        """Get node info by ID."""
        return self._known_nodes.get(node_id)
    
    def get_all_nodes(self) -> list[NodeInfo]:
        """Get all known nodes."""
        return list(self._known_nodes.values())
    
    async def broadcast_to_nodes(
        self,
        message_type: MessageType,
        payload: dict[str, Any],
        exclude_nodes: list[str] | None = None,
    ) -> int:
        """
        Broadcast message to all known nodes.
        
        Returns:
            Number of successful deliveries
        """
        exclude_nodes = exclude_nodes or []
        successful = 0
        
        for node in self._known_nodes.values():
            if node.node_id in exclude_nodes:
                continue
            if not node.is_online:
                continue
            
            message = FederatedMessage(
                message_type=message_type,
                sender_id=self.node_id,
                recipient_id=node.node_id,
                timestamp=datetime.utcnow().isoformat(),
                payload=payload,
            )
            
            if await self.send_message(message, node.endpoint):
                successful += 1
        
        return successful


class AggregatorProtocol(FederatedProtocol):
    """
    Protocol handler for the aggregator.
    
    Extends base protocol with aggregator-specific functionality.
    """
    
    def __init__(
        self,
        node_id: str = "aggregator",
        config: ProtocolConfig | None = None,
    ):
        super().__init__(node_id, aggregator_url=None, config=config)
        
        # Register default handlers
        self.register_handler(MessageType.REGISTER_NODE, self._handle_register)
        self.register_handler(MessageType.NODE_HEARTBEAT, self._handle_heartbeat)
        self.register_handler(MessageType.DELTA_SUBMIT, self._handle_delta_submit)
    
    async def _handle_register(self, message: FederatedMessage) -> None:
        """Handle node registration."""
        payload = message.payload
        node_info = NodeInfo(
            node_id=payload.get("node_id", message.sender_id),
            endpoint=payload.get("endpoint", ""),
            public_key=payload.get("public_key"),
            capabilities=payload.get("capabilities", {}),
            last_heartbeat=datetime.utcnow().isoformat(),
        )
        self.register_node(node_info)
    
    async def _handle_heartbeat(self, message: FederatedMessage) -> None:
        """Handle node heartbeat."""
        node_id = message.payload.get("node_id", message.sender_id)
        if node_id in self._known_nodes:
            self._known_nodes[node_id].last_heartbeat = datetime.utcnow().isoformat()
            self._known_nodes[node_id].is_online = True
    
    async def _handle_delta_submit(self, message: FederatedMessage) -> None:
        """Handle delta submission."""
        # This will be handled by the aggregator
        logger.info(f"Received delta from {message.sender_id}")
    
    async def broadcast_model(
        self,
        model_version: str,
        model_url: str,
        round_number: int,
    ) -> int:
        """Broadcast new model to all nodes."""
        return await self.broadcast_to_nodes(
            MessageType.MODEL_BROADCAST,
            {
                "model_version": model_version,
                "model_url": model_url,
                "round_number": round_number,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    async def notify_round_start(
        self,
        round_number: int,
        min_participants: int,
        timeout_seconds: int,
    ) -> int:
        """Notify all nodes of new round."""
        return await self.broadcast_to_nodes(
            MessageType.ROUND_START,
            {
                "round_number": round_number,
                "min_participants": min_participants,
                "timeout_seconds": timeout_seconds,
            }
        )