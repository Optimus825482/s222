"""
Inter-Agent Communication System.
Enables direct messaging, collaboration requests, and shared memory between agents.

Features:
- Direct messaging: Agent A → Agent B
- Collaboration requests: Ask another agent for help
- Shared memory: Common knowledge base for all agents
- Event broadcasting: Notify other agents of important findings
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of inter-agent messages."""
    DIRECT = "direct"                    # Direct message to specific agent
    BROADCAST = "broadcast"              # Broadcast to all agents
    COLLABORATION_REQUEST = "collab_request"  # Ask for help
    COLLABORATION_RESPONSE = "collab_response"  # Response to help request
    SHARED_KNOWLEDGE = "shared_knowledge"      # Share information
    TASK_DELEGATION = "task_delegation"        # Delegate a subtask
    TASK_RESULT = "task_result"                # Return delegated task result
    ALERT = "alert"                            # Important notification


@dataclass
class AgentMessage:
    """A message between agents."""
    id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    from_agent: str = ""
    to_agent: str = ""  # "broadcast" for broadcast messages
    message_type: MessageType = MessageType.DIRECT
    content: str = ""
    metadata: dict = field(default_factory=dict)
    thread_id: str = ""
    task_id: str = ""
    priority: int = 0  # Higher = more important
    requires_response: bool = False
    response_to: str = ""  # Original message ID if this is a response
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = ""  # Optional expiration
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "thread_id": self.thread_id,
            "task_id": self.task_id,
            "priority": self.priority,
            "requires_response": self.requires_response,
            "response_to": self.response_to,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentMessage":
        return cls(
            id=data.get("id", f"msg_{uuid.uuid4().hex[:8]}"),
            from_agent=data.get("from_agent", ""),
            to_agent=data.get("to_agent", ""),
            message_type=MessageType(data.get("message_type", "direct")),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            thread_id=data.get("thread_id", ""),
            task_id=data.get("task_id", ""),
            priority=data.get("priority", 0),
            requires_response=data.get("requires_response", False),
            response_to=data.get("response_to", ""),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            expires_at=data.get("expires_at", ""),
        )


@dataclass
class SharedKnowledge:
    """A piece of knowledge shared between agents."""
    id: str = field(default_factory=lambda: f"know_{uuid.uuid4().hex[:8]}")
    key: str = ""  # e.g., "user_preference_theme"
    value: Any = None
    source_agent: str = ""
    confidence: float = 1.0
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ttl_seconds: int = 3600  # Time to live
    
    def is_expired(self) -> bool:
        if self.ttl_seconds <= 0:
            return False
        created = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - created).total_seconds()
        return elapsed > self.ttl_seconds


# ── Message Bus ─────────────────────────────────────────────────────────────

class AgentMessageBus:
    """
    Central message bus for inter-agent communication.
    Implements publish-subscribe pattern with message queuing.
    """
    
    def __init__(self):
        # Message queues per agent
        self._queues: dict[str, asyncio.Queue] = {}
        # Pre-register known agent roles to avoid "unknown recipient" warnings
        # before target agents are lazily instantiated.
        for role in (
            "orchestrator",
            "thinker",
            "researcher",
            "speed",
            "reasoner",
            "critic",
        ):
            self._queues[role] = asyncio.Queue()
        # Shared knowledge store
        self._shared_knowledge: dict[str, SharedKnowledge] = {}
        # Message handlers per agent
        self._handlers: dict[str, Callable] = {}
        # Message history for debugging
        self._history: list[AgentMessage] = []
        self._max_history = 1000
    
    def register_agent(self, agent_role: str, handler: Optional[Callable] = None) -> None:
        """Register an agent with the message bus."""
        if agent_role not in self._queues:
            self._queues[agent_role] = asyncio.Queue()
        if handler:
            self._handlers[agent_role] = handler
        logger.info(f"Agent registered: {agent_role}")
    
    def unregister_agent(self, agent_role: str) -> None:
        """Unregister an agent from the message bus."""
        self._queues.pop(agent_role, None)
        self._handlers.pop(agent_role, None)
        logger.info(f"Agent unregistered: {agent_role}")
    
    async def send(self, message: AgentMessage) -> bool:
        """Send a message to one or more agents."""
        # Normalize recipient to keep role matching resilient against casing/whitespace.
        message.to_agent = (message.to_agent or "").strip().lower()

        # Add to history
        self._history.append(message)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        
        if message.message_type == MessageType.BROADCAST or message.to_agent == "broadcast":
            # Broadcast to all agents except sender
            tasks = []
            for agent_role, queue in self._queues.items():
                if agent_role != message.from_agent:
                    tasks.append(self._deliver(agent_role, message))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            logger.debug(f"Broadcast from {message.from_agent} to {len(tasks)} agents")
            return True
        
        elif message.to_agent in self._queues:
            # Direct message
            await self._deliver(message.to_agent, message)
            logger.debug(f"Message from {message.from_agent} to {message.to_agent}")
            return True
        
        else:
            logger.warning(f"Unknown recipient: {message.to_agent}")
            return False
    
    async def _deliver(self, agent_role: str, message: AgentMessage) -> None:
        """Deliver a message to an agent's queue."""
        queue = self._queues.get(agent_role)
        if queue:
            await queue.put(message)
            # Trigger handler if registered
            handler = self._handlers.get(agent_role)
            if handler and asyncio.iscoroutinefunction(handler):
                asyncio.create_task(handler(message))
    
    async def receive(self, agent_role: str, timeout: float = 0.1) -> Optional[AgentMessage]:
        """Receive a message for an agent (non-blocking with timeout)."""
        queue = self._queues.get(agent_role)
        if not queue:
            return None
        
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    def get_pending_count(self, agent_role: str) -> int:
        """Get number of pending messages for an agent."""
        queue = self._queues.get(agent_role)
        return queue.qsize() if queue else 0
    
    # ── Shared Knowledge ─────────────────────────────────────────────
    
    def share_knowledge(self, knowledge: SharedKnowledge) -> None:
        """Store shared knowledge for all agents to access."""
        self._shared_knowledge[knowledge.key] = knowledge
        logger.debug(f"Knowledge shared: {knowledge.key} by {knowledge.source_agent}")
    
    def get_knowledge(self, key: str) -> Optional[Any]:
        """Get shared knowledge by key."""
        knowledge = self._shared_knowledge.get(key)
        if knowledge and not knowledge.is_expired():
            return knowledge.value
        elif knowledge:
            # Remove expired
            del self._shared_knowledge[key]
        return None
    
    def get_all_knowledge(self, tags: Optional[list[str]] = None) -> dict[str, Any]:
        """Get all shared knowledge, optionally filtered by tags."""
        result = {}
        expired_keys = []
        
        for key, knowledge in self._shared_knowledge.items():
            if knowledge.is_expired():
                expired_keys.append(key)
                continue
            if tags and not any(t in knowledge.tags for t in tags):
                continue
            result[key] = knowledge.value
        
        # Clean up expired
        for key in expired_keys:
            del self._shared_knowledge[key]
        
        return result

    def clear_knowledge(self, key: Optional[str] = None) -> None:
        """Clear shared knowledge."""
        if key:
            self._shared_knowledge.pop(key, None)
        else:
            self._shared_knowledge.clear()
    
    # ── History & Debugging ─────────────────────────────────────────

    def get_history(
        self, agent_role: Optional[str] = None, limit: int = 50
    ) -> list[dict]:
        """Get message history for debugging."""
        messages = self._history[-limit:]
        if agent_role:
            messages = [m for m in messages 
                       if m.from_agent == agent_role or m.to_agent == agent_role]
        return [m.to_dict() for m in messages]


# Global message bus instance
_message_bus: Optional[AgentMessageBus] = None


def get_message_bus() -> AgentMessageBus:
    """Get the global message bus instance."""
    global _message_bus
    if _message_bus is None:
        _message_bus = AgentMessageBus()
    return _message_bus


# ── Convenience Functions ───────────────────────────────────────────────────

async def send_direct_message(
    from_agent: str,
    to_agent: str,
    content: str,
    metadata: Optional[dict[str, Any]] = None,
    requires_response: bool = False,
    priority: int = 0,
) -> str:
    """Send a direct message to another agent."""
    bus = get_message_bus()
    message = AgentMessage(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=MessageType.DIRECT,
        content=content,
        metadata=metadata or {},
        requires_response=requires_response,
        priority=priority,
    )
    await bus.send(message)
    return message.id


async def send_collaboration_request(
    from_agent: str,
    to_agent: str,
    task_description: str,
    context: Optional[dict[str, Any]] = None,
    thread_id: str = "",
) -> str:
    """Request collaboration from another agent."""
    bus = get_message_bus()
    message = AgentMessage(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=MessageType.COLLABORATION_REQUEST,
        content=task_description,
        metadata={"context": context or {}},
        thread_id=thread_id,
        requires_response=True,
        priority=5,
    )
    await bus.send(message)
    return message.id


async def send_task_delegation(
    from_agent: str,
    to_agent: str,
    task: str,
    task_id: str = "",
    thread_id: str = "",
) -> str:
    """Delegate a task to another agent."""
    bus = get_message_bus()
    message = AgentMessage(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=MessageType.TASK_DELEGATION,
        content=task,
        task_id=task_id,
        thread_id=thread_id,
        requires_response=True,
        priority=8,
    )
    await bus.send(message)
    return message.id


async def broadcast_alert(
    from_agent: str,
    alert_content: str,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Broadcast an alert to all agents."""
    bus = get_message_bus()
    message = AgentMessage(
        from_agent=from_agent,
        to_agent="broadcast",
        message_type=MessageType.ALERT,
        content=alert_content,
        metadata=metadata or {},
        priority=10,
    )
    await bus.send(message)


def share_knowledge(
    key: str,
    value: Any,
    source_agent: str,
    confidence: float = 1.0,
    tags: Optional[list[str]] = None,
) -> None:
    """Share knowledge with all agents."""
    bus = get_message_bus()
    knowledge = SharedKnowledge(
        key=key,
        value=value,
        source_agent=source_agent,
        confidence=confidence,
        tags=tags or [],
    )
    bus.share_knowledge(knowledge)


def get_shared_knowledge(key: str) -> Optional[Any]:
    """Get shared knowledge by key."""
    bus = get_message_bus()
    return bus.get_knowledge(key)


# ── Agent Integration Helpers ───────────────────────────────────────────────

# Agent capabilities registry
_AGENT_CAPABILITIES: dict[str, list[str]] = {
    "orchestrator": ["routing", "synthesis", "planning", "coordination"],
    "thinker": ["analysis", "planning", "reasoning", "strategy"],
    "researcher": ["web_search", "data_gathering", "summarization", "mcp"],
    "speed": ["quick_response", "code_generation", "formatting"],
    "reasoner": ["math", "logic", "verification", "chain_of_thought"],
    "critic": ["review", "quality_check", "feedback", "security"],
}


def get_agent_capabilities(agent_role: str) -> list[str]:
    """Get capabilities of an agent."""
    return _AGENT_CAPABILITIES.get(agent_role, [])


def find_agent_for_capability(capability: str) -> Optional[str]:
    """Find an agent that has a specific capability."""
    for agent, capabilities in _AGENT_CAPABILITIES.items():
        if capability in capabilities:
            return agent
    return None


def suggest_collaborator(current_agent: str, task_type: str) -> Optional[str]:
    """Suggest a collaborator agent based on task type."""
    # Map task types to capabilities
    task_capability_map = {
        "research": "web_search",
        "analysis": "analysis",
        "code": "code_generation",
        "math": "math",
        "review": "review",
        "planning": "planning",
        "verification": "verification",
    }
    
    capability = task_capability_map.get(task_type.lower())
    if not capability:
        return None
    
    # Find agent with this capability (excluding current)
    for agent, caps in _AGENT_CAPABILITIES.items():
        if agent != current_agent and capability in caps:
            return agent
    
    return None