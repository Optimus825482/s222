"""
Human-in-the-Loop — Approval gates for critical agent decisions.
Inspired by Autogen's async human input patterns.

Uses Streamlit session state for approval flow:
Agent requests approval → UI shows dialog → User approves/rejects → Agent continues.
"""

from __future__ import annotations

import time
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from core.models import EventType, Thread

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    MODIFIED = "modified"  # User approved with modifications


class ApprovalRequest:
    """Represents a pending human approval request."""

    def __init__(
        self,
        request_id: str,
        action: str,
        description: str,
        details: dict[str, Any] | None = None,
        agent_role: str = "orchestrator",
        timeout_seconds: int = 300,
    ):
        self.request_id = request_id
        self.action = action
        self.description = description
        self.details = details or {}
        self.agent_role = agent_role
        self.timeout_seconds = timeout_seconds
        self.status = ApprovalStatus.PENDING
        self.user_message: str | None = None
        self.created_at = datetime.now(timezone.utc)

    @property
    def is_expired(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return elapsed > self.timeout_seconds

    def approve(self, message: str | None = None) -> None:
        self.status = ApprovalStatus.APPROVED
        self.user_message = message

    def reject(self, message: str | None = None) -> None:
        self.status = ApprovalStatus.REJECTED
        self.user_message = message

    def modify(self, message: str) -> None:
        self.status = ApprovalStatus.MODIFIED
        self.user_message = message

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "action": self.action,
            "description": self.description,
            "details": self.details,
            "agent_role": self.agent_role,
            "status": self.status.value,
            "user_message": self.user_message,
            "created_at": self.created_at.isoformat(),
        }


# ── Actions that require approval ────────────────────────────────

APPROVAL_REQUIRED_ACTIONS = {
    "code_execute": "Kod çalıştırma",
    "file_write": "Dosya yazma",
    "file_delete": "Dosya silme",
    "api_call": "Dış API çağrısı",
    "data_modify": "Veri değişikliği",
    "deploy": "Deployment",
    "send_message": "Mesaj gönderme",
    "payment": "Ödeme işlemi",
    "project_scaffold": "Proje oluşturma",
}


def needs_approval(action: str) -> bool:
    """Check if an action requires human approval."""
    return action in APPROVAL_REQUIRED_ACTIONS


def create_approval_request(
    action: str,
    description: str,
    details: dict[str, Any] | None = None,
    agent_role: str = "orchestrator",
    thread: Thread | None = None,
) -> ApprovalRequest:
    """Create a new approval request and log it to thread."""
    import uuid
    request_id = f"approval_{uuid.uuid4().hex[:8]}"

    request = ApprovalRequest(
        request_id=request_id,
        action=action,
        description=description,
        details=details,
        agent_role=agent_role,
    )

    if thread:
        thread.add_event(
            EventType.HUMAN_REQUEST,
            f"[{APPROVAL_REQUIRED_ACTIONS.get(action, action)}] {description}",
            metadata={"request_id": request_id, "action": action},
        )

    logger.info(f"Approval requested: {action} — {description}")
    return request


def format_approval_for_agent(request: ApprovalRequest) -> str:
    """Format approval result for agent context."""
    if request.status == ApprovalStatus.APPROVED:
        msg = f"✅ APPROVED: {request.description}"
        if request.user_message:
            msg += f"\nUser note: {request.user_message}"
        return msg

    if request.status == ApprovalStatus.REJECTED:
        msg = f"❌ REJECTED: {request.description}"
        if request.user_message:
            msg += f"\nUser reason: {request.user_message}"
        return msg

    if request.status == ApprovalStatus.MODIFIED:
        return (
            f"✏️ MODIFIED: {request.description}\n"
            f"User modification: {request.user_message}"
        )

    if request.status == ApprovalStatus.TIMEOUT:
        return f"⏰ TIMEOUT: {request.description} — no response within {request.timeout_seconds}s"

    return f"⏳ PENDING: {request.description}"
