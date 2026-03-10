"""
Webhook System — Webhook receiver, sender, and event subscription management.

Features:
- Webhook receiver with HMAC-SHA256 signature verification
- Webhook sender with retry logic and timeout handling
- Event subscription system with PostgreSQL persistence
- Delivery logging and status tracking
- Support for multiple event types and filters
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import httpx

from tools.pg_connection import get_conn, release_conn, db_conn

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────

WEBHOOK_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAYS = [1, 5, 15]  # exponential backoff in seconds

# ── Enums ──────────────────────────────────────────────────────────


class WebhookStatus(str, Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class EventType(str, Enum):
    """Built-in event types for webhook subscriptions."""
    # Agent events
    AGENT_MESSAGE = "agent.message"
    AGENT_TASK_START = "agent.task.start"
    AGENT_TASK_COMPLETE = "agent.task.complete"
    AGENT_TASK_FAILED = "agent.task.failed"
    
    # Memory events
    MEMORY_SAVED = "memory.saved"
    MEMORY_RECALLED = "memory.recalled"
    
    # Workflow events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    
    # Skill events
    SKILL_CREATED = "skill.created"
    SKILL_USED = "skill.used"
    
    # System events
    SYSTEM_ALERT = "system.alert"
    SYSTEM_ERROR = "system.error"
    
    # Custom events
    CUSTOM = "custom"


# ── Data Classes ───────────────────────────────────────────────────

@dataclass
class WebhookSubscription:
    """Webhook subscription configuration."""
    id: str
    name: str
    url: str
    secret: str  # For HMAC signature
    events: list[str]  # Event types to subscribe to
    filters: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    created_at: str = ""
    updated_at: str = ""
    last_triggered: str | None = None
    delivery_count: int = 0
    failure_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "secret": "***",  # Don't expose secret
            "events": self.events,
            "filters": self.filters,
            "headers": self.headers,
            "status": self.status.value if isinstance(self.status, SubscriptionStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_triggered": self.last_triggered,
            "delivery_count": self.delivery_count,
            "failure_count": self.failure_count,
        }


@dataclass
class WebhookDelivery:
    """Webhook delivery record."""
    id: str
    subscription_id: str
    event_type: str
    payload: dict[str, Any]
    status: WebhookStatus
    response_code: int | None = None
    response_body: str | None = None
    error_message: str | None = None
    attempt_count: int = 1
    delivered_at: str | None = None
    created_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "status": self.status.value if isinstance(self.status, WebhookStatus) else self.status,
            "response_code": self.response_code,
            "response_body": self.response_body,
            "error_message": self.error_message,
            "attempt_count": self.attempt_count,
            "delivered_at": self.delivered_at,
            "created_at": self.created_at,
        }


# ── Database Schema ────────────────────────────────────────────────

WEBHOOK_SCHEMA_SQL = """
-- Webhook subscriptions
CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    url           TEXT NOT NULL,
    secret        TEXT NOT NULL,
    events        TEXT NOT NULL DEFAULT '[]',
    filters       TEXT NOT NULL DEFAULT '{}',
    headers       TEXT NOT NULL DEFAULT '{}',
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_triggered TIMESTAMPTZ,
    delivery_count INTEGER NOT NULL DEFAULT 0,
    failure_count  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_webhook_sub_status ON webhook_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_webhook_sub_events ON webhook_subscriptions USING GIN(events::jsonb);

-- Webhook delivery log
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id              TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL REFERENCES webhook_subscriptions(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    payload         TEXT NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'pending',
    response_code   INTEGER,
    response_body   TEXT,
    error_message   TEXT,
    attempt_count   INTEGER NOT NULL DEFAULT 1,
    delivered_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_webhook_del_sub ON webhook_deliveries(subscription_id);
CREATE INDEX IF NOT EXISTS idx_webhook_del_status ON webhook_deliveries(status);
CREATE INDEX IF NOT EXISTS idx_webhook_del_created ON webhook_deliveries(created_at DESC);

-- Incoming webhook log
CREATE TABLE IF NOT EXISTS webhook_incoming (
    id            TEXT PRIMARY KEY,
    source        TEXT,
    event_type    TEXT,
    payload       TEXT NOT NULL DEFAULT '{}',
    headers       TEXT NOT NULL DEFAULT '{}',
    signature     TEXT,
    verified      BOOLEAN NOT NULL DEFAULT FALSE,
    processed     BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_webhook_in_created ON webhook_incoming(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_webhook_in_source ON webhook_incoming(source);
"""


def init_webhook_tables() -> None:
    """Initialize webhook database tables. Safe to call multiple times."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(WEBHOOK_SCHEMA_SQL)
        conn.commit()
    logger.info("Webhook tables initialized")


# ── Signature Verification ──────────────────────────────────────────

def compute_signature(payload: str | bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for a payload."""
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()


def verify_signature(payload: str | bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature. Supports multiple signature formats."""
    if not signature or not secret:
        return False
    
    # Compute expected signature
    expected = compute_signature(payload, secret)
    
    # Handle different signature formats
    # Format 1: raw hex
    if hmac.compare_digest(signature, expected):
        return True
    
    # Format 2: sha256=hex (GitHub style)
    if signature.startswith("sha256="):
        return hmac.compare_digest(signature[7:], expected)
    
    # Format 3: sha256:hex (alternative)
    if signature.startswith("sha256:"):
        return hmac.compare_digest(signature[7:], expected)
    
    return False


# ── Webhook Sender ──────────────────────────────────────────────────

async def send_webhook(
    url: str,
    payload: dict[str, Any],
    secret: str,
    headers: dict[str, str] | None = None,
    timeout: float = WEBHOOK_TIMEOUT,
    max_retries: int = MAX_RETRIES,
) -> dict[str, Any]:
    """
    Send a webhook POST request with signature verification header.
    
    Args:
        url: Target webhook URL
        payload: JSON payload to send
        secret: Secret for HMAC signature
        headers: Additional headers
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
    
    Returns:
        Dict with success status, response code, and delivery info
    """
    payload_str = json.dumps(payload, ensure_ascii=False)
    signature = compute_signature(payload_str, secret)
    
    request_headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Webhook-Timestamp": datetime.now(timezone.utc).isoformat(),
        "User-Agent": "AGENTIX-Webhook/1.0",
    }
    if headers:
        request_headers.update(headers)
    
    last_error: str | None = None
    response_code: int | None = None
    response_body: str | None = None
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    content=payload_str,
                    headers=request_headers,
                )
                response_code = response.status_code
                response_body = response.text[:1000]  # Truncate for storage
                
                if 200 <= response_code < 300:
                    return {
                        "success": True,
                        "status": WebhookStatus.DELIVERED.value,
                        "response_code": response_code,
                        "response_body": response_body,
                        "attempts": attempt + 1,
                    }
                
                # Non-2xx response
                last_error = f"HTTP {response_code}: {response.text[:200]}"
                
        except httpx.TimeoutException:
            last_error = "Request timed out"
        except httpx.ConnectError as e:
            last_error = f"Connection failed: {str(e)}"
        except Exception as e:
            last_error = f"Request failed: {str(e)}"
        
        # Retry with exponential backoff (except last attempt)
        if attempt < max_retries - 1:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            logger.warning(
                "Webhook delivery attempt %d/%d failed: %s. Retrying in %ds",
                attempt + 1, max_retries, last_error, delay
            )
            await asyncio.sleep(delay)
    
    return {
        "success": False,
        "status": WebhookStatus.FAILED.value,
        "response_code": response_code,
        "response_body": response_body,
        "error_message": last_error,
        "attempts": max_retries,
    }


# Need asyncio for async sleep
import asyncio


# ── Webhook Receiver ────────────────────────────────────────────────

def receive_webhook(
    source: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    signature: str | None = None,
    expected_secret: str | None = None,
    event_type: str | None = None,
) -> dict[str, Any]:
    """
    Receive and log an incoming webhook.
    
    Args:
        source: Source identifier (e.g., 'github', 'stripe', 'custom')
        payload: Webhook payload
        headers: Request headers
        signature: Signature from the sender
        expected_secret: Secret to verify signature (if required)
        event_type: Event type extracted from payload
    
    Returns:
        Dict with received status and verification result
    """
    webhook_id = f"wh-in-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
    # Verify signature if provided
    verified = False
    if signature and expected_secret:
        payload_str = json.dumps(payload, ensure_ascii=False)
        verified = verify_signature(payload_str, signature, expected_secret)
    
    # Log incoming webhook
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO webhook_incoming
                       (id, source, event_type, payload, headers, signature, verified, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        webhook_id,
                        source,
                        event_type,
                        json.dumps(payload, ensure_ascii=False),
                        json.dumps(headers, ensure_ascii=False),
                        signature,
                        verified,
                        now,
                    ),
                )
            conn.commit()
    except Exception as e:
        logger.error("Failed to log incoming webhook: %s", e)
    
    return {
        "webhook_id": webhook_id,
        "received": True,
        "verified": verified,
        "source": source,
        "event_type": event_type,
    }


def get_incoming_webhooks(
    source: str | None = None,
    verified_only: bool = False,
    unprocessed_only: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get list of incoming webhooks with optional filters."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            conditions = []
            params: list = []
            
            if source:
                conditions.append("source = %s")
                params.append(source)
            if verified_only:
                conditions.append("verified = TRUE")
            if unprocessed_only:
                conditions.append("processed = FALSE")
            
            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f"""
                SELECT * FROM webhook_incoming
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
            """
            params.append(limit)
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            return [_row_to_incoming_dict(r) for r in rows]


def mark_incoming_processed(webhook_id: str, error_message: str | None = None) -> bool:
    """Mark an incoming webhook as processed."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE webhook_incoming
                   SET processed = TRUE, error_message = %s
                   WHERE id = %s""",
                (error_message, webhook_id),
            )
            conn.commit()
            return cur.rowcount > 0


def _row_to_incoming_dict(row: dict) -> dict[str, Any]:
    """Convert database row to dict."""
    return {
        "id": row["id"],
        "source": row["source"],
        "event_type": row["event_type"],
        "payload": json.loads(row["payload"]) if row["payload"] else {},
        "headers": json.loads(row["headers"]) if row["headers"] else {},
        "signature": row["signature"],
        "verified": row["verified"],
        "processed": row["processed"],
        "error_message": row["error_message"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


# ── Subscription Management ─────────────────────────────────────────

def create_subscription(
    name: str,
    url: str,
    events: list[str],
    secret: str | None = None,
    filters: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> WebhookSubscription:
    """
    Create a new webhook subscription.
    
    Args:
        name: Subscription name
        url: Target URL for webhooks
        events: List of event types to subscribe to
        secret: HMAC secret (auto-generated if not provided)
        filters: Optional filters for event matching
        headers: Additional headers to send with webhooks
    
    Returns:
        WebhookSubscription object
    """
    sub_id = f"sub-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    
    # Auto-generate secret if not provided
    if not secret:
        secret = uuid.uuid4().hex
    
    subscription = WebhookSubscription(
        id=sub_id,
        name=name,
        url=url,
        secret=secret,
        events=events,
        filters=filters or {},
        headers=headers or {},
        status=SubscriptionStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO webhook_subscriptions
                   (id, name, url, secret, events, filters, headers, status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    sub_id,
                    name,
                    url,
                    secret,
                    json.dumps(events, ensure_ascii=False),
                    json.dumps(filters or {}, ensure_ascii=False),
                    json.dumps(headers or {}, ensure_ascii=False),
                    SubscriptionStatus.ACTIVE.value,
                    now,
                    now,
                ),
            )
        conn.commit()
    
    logger.info("Created webhook subscription '%s' (id=%s) for events: %s", name, sub_id, events)
    return subscription


def get_subscription(subscription_id: str) -> WebhookSubscription | None:
    """Get a subscription by ID."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM webhook_subscriptions WHERE id = %s", (subscription_id,))
            row = cur.fetchone()
            if not row:
                return None
            return _row_to_subscription(row)


def list_subscriptions(
    status: SubscriptionStatus | None = None,
    event_type: str | None = None,
) -> list[WebhookSubscription]:
    """List all subscriptions with optional filters."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            conditions = []
            params: list = []
            
            if status:
                conditions.append("status = %s")
                params.append(status.value)
            if event_type:
                conditions.append("events::jsonb ? %s")
                params.append(event_type)
            
            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f"SELECT * FROM webhook_subscriptions WHERE {where_clause} ORDER BY created_at DESC"
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            return [_row_to_subscription(r) for r in rows]


def update_subscription(
    subscription_id: str,
    name: str | None = None,
    url: str | None = None,
    events: list[str] | None = None,
    secret: str | None = None,
    filters: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    status: SubscriptionStatus | None = None,
) -> WebhookSubscription | None:
    """Update a subscription."""
    updates = []
    params: list = []
    
    if name is not None:
        updates.append("name = %s")
        params.append(name)
    if url is not None:
        updates.append("url = %s")
        params.append(url)
    if events is not None:
        updates.append("events = %s")
        params.append(json.dumps(events, ensure_ascii=False))
    if secret is not None:
        updates.append("secret = %s")
        params.append(secret)
    if filters is not None:
        updates.append("filters = %s")
        params.append(json.dumps(filters, ensure_ascii=False))
    if headers is not None:
        updates.append("headers = %s")
        params.append(json.dumps(headers, ensure_ascii=False))
    if status is not None:
        updates.append("status = %s")
        params.append(status.value)
    
    if not updates:
        return get_subscription(subscription_id)
    
    updates.append("updated_at = %s")
    params.append(datetime.now(timezone.utc).isoformat())
    params.append(subscription_id)
    
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE webhook_subscriptions SET {', '.join(updates)} WHERE id = %s",
                params,
            )
            conn.commit()
    
    return get_subscription(subscription_id)


def delete_subscription(subscription_id: str) -> bool:
    """Delete a subscription."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM webhook_subscriptions WHERE id = %s", (subscription_id,))
            conn.commit()
            deleted = cur.rowcount > 0
    
    if deleted:
        logger.info("Deleted webhook subscription %s", subscription_id)
    return deleted


def pause_subscription(subscription_id: str) -> WebhookSubscription | None:
    """Pause a subscription (stop sending webhooks)."""
    return update_subscription(subscription_id, status=SubscriptionStatus.PAUSED)


def resume_subscription(subscription_id: str) -> WebhookSubscription | None:
    """Resume a paused subscription."""
    return update_subscription(subscription_id, status=SubscriptionStatus.ACTIVE)


def _row_to_subscription(row: dict) -> WebhookSubscription:
    """Convert database row to WebhookSubscription."""
    return WebhookSubscription(
        id=row["id"],
        name=row["name"],
        url=row["url"],
        secret=row["secret"],
        events=json.loads(row["events"]) if row["events"] else [],
        filters=json.loads(row["filters"]) if row["filters"] else {},
        headers=json.loads(row["headers"]) if row["headers"] else {},
        status=SubscriptionStatus(row["status"]) if row["status"] else SubscriptionStatus.ACTIVE,
        created_at=row["created_at"].isoformat() if row["created_at"] else "",
        updated_at=row["updated_at"].isoformat() if row["updated_at"] else "",
        last_triggered=row["last_triggered"].isoformat() if row["last_triggered"] else None,
        delivery_count=row["delivery_count"] or 0,
        failure_count=row["failure_count"] or 0,
    )


# ── Event Dispatch ─────────────────────────────────────────────────

async def dispatch_event(
    event_type: str,
    payload: dict[str, Any],
    source: str = "system",
) -> list[dict[str, Any]]:
    """
    Dispatch an event to all matching subscriptions.
    
    Args:
        event_type: Event type (e.g., 'agent.task.complete')
        payload: Event payload
        source: Source identifier
    
    Returns:
        List of delivery results for each subscription
    """
    # Find matching subscriptions
    subscriptions = list_subscriptions(status=SubscriptionStatus.ACTIVE)
    matching = [s for s in subscriptions if event_type in s.events or "*" in s.events]
    
    if not matching:
        logger.debug("No subscriptions match event type: %s", event_type)
        return []
    
    results = []
    now = datetime.now(timezone.utc).isoformat()
    
    for sub in matching:
        # Apply filters if any
        if not _matches_filters(payload, sub.filters):
            continue
        
        # Create delivery record
        delivery_id = f"del-{uuid.uuid4().hex[:12]}"
        delivery = WebhookDelivery(
            id=delivery_id,
            subscription_id=sub.id,
            event_type=event_type,
            payload=payload,
            status=WebhookStatus.PENDING,
            created_at=now,
        )
        
        # Store delivery record
        _store_delivery(delivery)
        
        # Send webhook
        result = await send_webhook(
            url=sub.url,
            payload={
                "id": delivery_id,
                "event": event_type,
                "source": source,
                "timestamp": now,
                "data": payload,
            },
            secret=sub.secret,
            headers=sub.headers,
        )
        
        # Update delivery status
        delivery.status = WebhookStatus.DELIVERED if result["success"] else WebhookStatus.FAILED
        delivery.response_code = result.get("response_code")
        delivery.response_body = result.get("response_body")
        delivery.error_message = result.get("error_message")
        delivery.attempt_count = result.get("attempts", 1)
        delivery.delivered_at = now if result["success"] else None
        
        _update_delivery(delivery)
        _update_subscription_stats(sub.id, result["success"])
        
        results.append({
            "subscription_id": sub.id,
            "delivery_id": delivery_id,
            "success": result["success"],
            "status": delivery.status.value,
            "response_code": delivery.response_code,
            "error": delivery.error_message,
        })
    
    logger.info("Dispatched event %s to %d subscription(s)", event_type, len(results))
    return results


def _matches_filters(payload: dict[str, Any], filters: dict[str, Any]) -> bool:
    """Check if payload matches subscription filters."""
    if not filters:
        return True
    
    for key, expected in filters.items():
        actual = payload.get(key)
        if actual is None:
            return False
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    
    return True


def _store_delivery(delivery: WebhookDelivery) -> None:
    """Store a delivery record in the database."""
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO webhook_deliveries
                       (id, subscription_id, event_type, payload, status, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (
                        delivery.id,
                        delivery.subscription_id,
                        delivery.event_type,
                        json.dumps(delivery.payload, ensure_ascii=False),
                        delivery.status.value,
                        delivery.created_at,
                    ),
                )
            conn.commit()
    except Exception as e:
        logger.error("Failed to store delivery: %s", e)


def _update_delivery(delivery: WebhookDelivery) -> None:
    """Update delivery status in the database."""
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE webhook_deliveries
                       SET status = %s, response_code = %s, response_body = %s,
                           error_message = %s, attempt_count = %s, delivered_at = %s
                       WHERE id = %s""",
                    (
                        delivery.status.value,
                        delivery.response_code,
                        delivery.response_body,
                        delivery.error_message,
                        delivery.attempt_count,
                        delivery.delivered_at,
                        delivery.id,
                    ),
                )
            conn.commit()
    except Exception as e:
        logger.error("Failed to update delivery: %s", e)


def _update_subscription_stats(subscription_id: str, success: bool) -> None:
    """Update subscription statistics."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        with db_conn() as conn:
            with conn.cursor() as cur:
                if success:
                    cur.execute(
                        """UPDATE webhook_subscriptions
                           SET delivery_count = delivery_count + 1,
                               last_triggered = %s,
                               updated_at = %s
                           WHERE id = %s""",
                        (now, now, subscription_id),
                    )
                else:
                    cur.execute(
                        """UPDATE webhook_subscriptions
                           SET failure_count = failure_count + 1,
                               updated_at = %s
                           WHERE id = %s""",
                        (now, subscription_id),
                    )
            conn.commit()
    except Exception as e:
        logger.error("Failed to update subscription stats: %s", e)


# ── Delivery History ───────────────────────────────────────────────

def get_delivery_history(
    subscription_id: str | None = None,
    status: WebhookStatus | None = None,
    event_type: str | None = None,
    limit: int = 50,
) -> list[WebhookDelivery]:
    """Get webhook delivery history with filters."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            conditions = []
            params: list = []
            
            if subscription_id:
                conditions.append("subscription_id = %s")
                params.append(subscription_id)
            if status:
                conditions.append("status = %s")
                params.append(status.value)
            if event_type:
                conditions.append("event_type = %s")
                params.append(event_type)
            
            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f"""
                SELECT * FROM webhook_deliveries
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
            """
            params.append(limit)
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            return [_row_to_delivery(r) for r in rows]


def get_delivery(delivery_id: str) -> WebhookDelivery | None:
    """Get a single delivery by ID."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM webhook_deliveries WHERE id = %s", (delivery_id,))
            row = cur.fetchone()
            if not row:
                return None
            return _row_to_delivery(row)


def retry_delivery(delivery_id: str) -> dict[str, Any]:
    """Retry a failed webhook delivery."""
    delivery = get_delivery(delivery_id)
    if not delivery:
        return {"success": False, "error": "Delivery not found"}
    
    if delivery.status == WebhookStatus.DELIVERED:
        return {"success": False, "error": "Already delivered"}
    
    subscription = get_subscription(delivery.subscription_id)
    if not subscription:
        return {"success": False, "error": "Subscription not found"}
    
    if subscription.status != SubscriptionStatus.ACTIVE:
        return {"success": False, "error": "Subscription is not active"}
    
    # Retry send
    import asyncio
    result = asyncio.run(send_webhook(
        url=subscription.url,
        payload={
            "id": delivery.id,
            "event": delivery.event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": delivery.payload,
            "retry": True,
        },
        secret=subscription.secret,
        headers=subscription.headers,
    ))
    
    # Update delivery
    delivery.status = WebhookStatus.DELIVERED if result["success"] else WebhookStatus.FAILED
    delivery.response_code = result.get("response_code")
    delivery.response_body = result.get("response_body")
    delivery.error_message = result.get("error_message")
    delivery.attempt_count += 1
    if result["success"]:
        delivery.delivered_at = datetime.now(timezone.utc).isoformat()
    
    _update_delivery(delivery)
    _update_subscription_stats(subscription.id, result["success"])
    
    return {
        "success": result["success"],
        "delivery_id": delivery_id,
        "status": delivery.status.value,
        "attempts": delivery.attempt_count,
        "error": delivery.error_message,
    }


def _row_to_delivery(row: dict) -> WebhookDelivery:
    """Convert database row to WebhookDelivery."""
    return WebhookDelivery(
        id=row["id"],
        subscription_id=row["subscription_id"],
        event_type=row["event_type"],
        payload=json.loads(row["payload"]) if row["payload"] else {},
        status=WebhookStatus(row["status"]) if row["status"] else WebhookStatus.PENDING,
        response_code=row["response_code"],
        response_body=row["response_body"],
        error_message=row["error_message"],
        attempt_count=row["attempt_count"] or 1,
        delivered_at=row["delivered_at"].isoformat() if row["delivered_at"] else None,
        created_at=row["created_at"].isoformat() if row["created_at"] else "",
    )


# ── Statistics ─────────────────────────────────────────────────────

def get_webhook_stats() -> dict[str, Any]:
    """Get webhook system statistics."""
    with db_conn() as conn:
        with conn.cursor() as cur:
            # Subscription stats
            cur.execute("SELECT COUNT(*) as total FROM webhook_subscriptions")
            total_subs = cur.fetchone()["total"]
            
            cur.execute("SELECT COUNT(*) as active FROM webhook_subscriptions WHERE status = 'active'")
            active_subs = cur.fetchone()["active"]
            
            # Delivery stats
            cur.execute("SELECT COUNT(*) as total FROM webhook_deliveries")
            total_deliveries = cur.fetchone()["total"]
            
            cur.execute("SELECT COUNT(*) as delivered FROM webhook_deliveries WHERE status = 'delivered'")
            delivered = cur.fetchone()["delivered"]
            
            cur.execute("SELECT COUNT(*) as failed FROM webhook_deliveries WHERE status = 'failed'")
            failed = cur.fetchone()["failed"]
            
            cur.execute("SELECT COUNT(*) as pending FROM webhook_deliveries WHERE status = 'pending'")
            pending = cur.fetchone()["pending"]
            
            # Incoming webhook stats
            cur.execute("SELECT COUNT(*) as total FROM webhook_incoming")
            total_incoming = cur.fetchone()["total"]
            
            cur.execute("SELECT COUNT(*) as verified FROM webhook_incoming WHERE verified = TRUE")
            verified = cur.fetchone()["verified"]
            
            cur.execute("SELECT COUNT(*) as unprocessed FROM webhook_incoming WHERE processed = FALSE")
            unprocessed = cur.fetchone()["unprocessed"]
            
            return {
                "subscriptions": {
                    "total": total_subs,
                    "active": active_subs,
                    "paused": total_subs - active_subs,
                },
                "deliveries": {
                    "total": total_deliveries,
                    "delivered": delivered,
                    "failed": failed,
                    "pending": pending,
                    "success_rate": round(delivered / total_deliveries * 100, 2) if total_deliveries > 0 else 0,
                },
                "incoming": {
                    "total": total_incoming,
                    "verified": verified,
                    "unprocessed": unprocessed,
                },
            }


# ── Convenience Functions for Tool Integration ─────────────────────

async def trigger_webhook(
    event_type: str,
    data: dict[str, Any],
    source: str = "agent",
) -> dict[str, Any]:
    """
    Convenience function for agents to trigger webhooks.
    
    Args:
        event_type: Event type (e.g., 'agent.task.complete')
        data: Event data payload
        source: Source identifier
    
    Returns:
        Dict with dispatch results
    """
    results = await dispatch_event(event_type, data, source)
    
    return {
        "event_type": event_type,
        "source": source,
        "dispatched": len(results),
        "results": results,
    }


def create_simple_subscription(
    name: str,
    url: str,
    events: list[str],
) -> dict[str, Any]:
    """
    Create a simple subscription with auto-generated secret.
    
    Args:
        name: Subscription name
        url: Webhook URL
        events: Event types to subscribe to
    
    Returns:
        Subscription info including the secret (only shown once!)
    """
    sub = create_subscription(name=name, url=url, events=events)
    
    return {
        "id": sub.id,
        "name": sub.name,
        "url": sub.url,
        "secret": sub.secret,  # Only returned on creation!
        "events": sub.events,
        "status": sub.status.value,
        "created_at": sub.created_at,
    }


def verify_webhook_request(
    payload: str | bytes,
    signature: str,
    subscription_id: str,
) -> dict[str, Any]:
    """
    Verify an incoming webhook request against a subscription's secret.
    
    Args:
        payload: Raw request body
        signature: Signature header value
        subscription_id: Subscription ID to look up secret
    
    Returns:
        Dict with verification result
    """
    sub = get_subscription(subscription_id)
    if not sub:
        return {"valid": False, "error": "Subscription not found"}
    
    verified = verify_signature(payload, signature, sub.secret)
    
    return {
        "valid": verified,
        "subscription_id": subscription_id,
        "subscription_name": sub.name,
    }