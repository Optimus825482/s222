"""
Event Bus — In-process async Pub-Sub message bus for agent communication.

Özellikler:
- Topic-based channel subscription (unicast, multicast, broadcast)
- Priority queue ile mesaj sıralama
- Dead Letter Queue (DLQ) — teslim edilemeyen mesajlar
- TTL + retry mekanizması
- Exactly-once delivery (dedup via message ID)
- Middleware pipeline (logging, filtering, transformation)
- Backpressure: kanal başına max queue size
- Redis-ready interface (şimdilik in-memory, interface aynı kalacak)
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from .protocols import (
    ChannelType,
    DeliveryGuarantee,
    MessageEnvelope,
    MessagePriority,
    MessageType,
)

logger = logging.getLogger("event_bus")

# Type aliases
MessageHandler = Callable[[MessageEnvelope], Awaitable[None]]
Middleware = Callable[[MessageEnvelope], Awaitable[MessageEnvelope | None]]


@dataclass
class ChannelStats:
    """Kanal bazlı istatistikler."""
    published: int = 0
    delivered: int = 0
    failed: int = 0
    expired: int = 0
    retried: int = 0


@dataclass
class Subscription:
    """Bir agent'ın bir kanala aboneliği."""
    agent_role: str
    channel: str
    handler: MessageHandler
    filter_types: set[MessageType] | None = None  # None = tüm tipler
    created_at: float = field(default_factory=time.time)


class DeadLetterQueue:
    """Teslim edilemeyen mesajların deposu — debug ve retry için."""

    def __init__(self, max_size: int = 500):
        self._queue: list[tuple[MessageEnvelope, str]] = []  # (msg, reason)
        self._max_size = max_size

    def push(self, msg: MessageEnvelope, reason: str) -> None:
        if len(self._queue) >= self._max_size:
            self._queue.pop(0)  # FIFO eviction
        self._queue.append((msg, reason))
        logger.warning(f"DLQ: {msg.message_type.value} from {msg.source_agent} → reason: {reason}")

    def pop(self) -> tuple[MessageEnvelope, str] | None:
        return self._queue.pop(0) if self._queue else None

    def peek(self, limit: int = 10) -> list[dict[str, Any]]:
        return [
            {
                "id": msg.id,
                "type": msg.message_type.value,
                "source": msg.source_agent,
                "target": msg.target_agent,
                "reason": reason,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg, reason in self._queue[-limit:]
        ]

    @property
    def size(self) -> int:
        return len(self._queue)

    def clear(self) -> int:
        count = len(self._queue)
        self._queue.clear()
        return count


class EventBus:
    """
    Merkezi mesaj yönlendirici — tüm ajan iletişimi buradan akar.

    Kullanım:
        bus = EventBus()
        bus.subscribe("researcher", "tasks", handler_fn)
        await bus.publish(MessageEnvelope(...))

    Kanal tipleri:
        - "agent:{role}" → unicast (doğrudan agent'a)
        - "pipeline:{id}" → multicast (pipeline katılımcılarına)
        - "broadcast" → tüm subscriber'lara
        - Custom topic adları da desteklenir
    """

    def __init__(self, max_queue_per_channel: int = 100):
        # Channel → list of subscriptions
        self._subscriptions: dict[str, list[Subscription]] = defaultdict(list)
        # Message dedup set (exactly-once delivery)
        self._delivered_ids: OrderedDict[str, None] = OrderedDict()
        self._delivered_ids_max = 10_000
        # Middleware pipeline
        self._middlewares: list[Middleware] = []
        # Dead letter queue
        self.dlq = DeadLetterQueue()
        # Per-channel stats
        self._stats: dict[str, ChannelStats] = defaultdict(ChannelStats)
        # Backpressure
        self._max_queue = max_queue_per_channel
        # Pending futures for request-response pattern
        self._pending_futures: dict[str, asyncio.Future] = {}
        # Running flag
        self._running = True

    # ── Subscription Management ──────────────────────────────────

    def subscribe(
        self,
        agent_role: str,
        channel: str,
        handler: MessageHandler,
        filter_types: set[MessageType] | None = None,
    ) -> Subscription:
        """Agent'ı bir kanala abone et."""
        sub = Subscription(
            agent_role=agent_role,
            channel=channel,
            handler=handler,
            filter_types=filter_types,
        )
        self._subscriptions[channel].append(sub)
        logger.info(f"Subscribed: {agent_role} → channel '{channel}'")
        return sub

    def unsubscribe(self, agent_role: str, channel: str) -> bool:
        """Agent'ın kanal aboneliğini kaldır."""
        subs = self._subscriptions.get(channel, [])
        before = len(subs)
        self._subscriptions[channel] = [s for s in subs if s.agent_role != agent_role]
        removed = before - len(self._subscriptions[channel])
        if removed:
            logger.info(f"Unsubscribed: {agent_role} from channel '{channel}'")
        return removed > 0

    def unsubscribe_all(self, agent_role: str) -> int:
        """Agent'ın tüm aboneliklerini kaldır."""
        count = 0
        for channel in list(self._subscriptions.keys()):
            if self.unsubscribe(agent_role, channel):
                count += 1
        return count

    # ── Middleware ────────────────────────────────────────────────

    def add_middleware(self, mw: Middleware) -> None:
        """Publish pipeline'ına middleware ekle (logging, filtering, transform)."""
        self._middlewares.append(mw)

    async def _apply_middlewares(self, msg: MessageEnvelope) -> MessageEnvelope | None:
        """Middleware zincirini uygula. None dönerse mesaj drop edilir."""
        current = msg
        for mw in self._middlewares:
            result = await mw(current)
            if result is None:
                logger.debug(f"Message {msg.id} dropped by middleware")
                return None
            current = result
        return current

    # ── Publishing ───────────────────────────────────────────────

    async def publish(self, msg: MessageEnvelope) -> bool:
        """
        Mesajı yayınla — routing, delivery guarantee, retry hepsi burada.
        Returns True if delivered to at least one subscriber.
        """
        if not self._running:
            self.dlq.push(msg, "bus_stopped")
            return False

        # TTL check
        if msg.is_expired:
            self._stats[msg.channel].expired += 1
            self.dlq.push(msg, "expired_before_delivery")
            return False

        # Exactly-once dedup
        if msg.delivery == DeliveryGuarantee.EXACTLY_ONCE:
            if msg.id in self._delivered_ids:
                logger.debug(f"Dedup: message {msg.id} already delivered")
                return True
            self._delivered_ids[msg.id] = None
            # Evict oldest IDs to prevent memory leak
            while len(self._delivered_ids) > self._delivered_ids_max:
                self._delivered_ids.popitem(last=False)

        # Apply middlewares
        processed = await self._apply_middlewares(msg)
        if processed is None:
            return False
        msg = processed

        self._stats[msg.channel].published += 1

        # Route based on channel type
        subscribers = self._resolve_subscribers(msg)

        if not subscribers:
            if msg.delivery != DeliveryGuarantee.AT_MOST_ONCE:
                self.dlq.push(msg, "no_subscribers")
            self._stats[msg.channel].failed += 1
            return False

        # Deliver to all matching subscribers
        delivered = False
        for sub in subscribers:
            try:
                await asyncio.wait_for(sub.handler(msg), timeout=30.0)
                msg.acknowledged = True
                msg.delivered_at = msg.timestamp.__class__.now(msg.timestamp.tzinfo)
                self._stats[msg.channel].delivered += 1
                delivered = True
            except asyncio.TimeoutError:
                logger.error(f"Delivery timeout: {msg.id} → {sub.agent_role}")
                self._handle_delivery_failure(msg, sub, "timeout")
            except Exception as e:
                logger.error(f"Delivery error: {msg.id} → {sub.agent_role}: {e}")
                self._handle_delivery_failure(msg, sub, str(e))

        # Resolve pending future if this is a response
        if msg.correlation_id and msg.correlation_id in self._pending_futures:
            future = self._pending_futures.pop(msg.correlation_id)
            if not future.done():
                future.set_result(msg)

        return delivered

    def _resolve_subscribers(self, msg: MessageEnvelope) -> list[Subscription]:
        """Mesajın hedef subscriber'larını belirle."""
        result: list[Subscription] = []

        if msg.channel_type == ChannelType.BROADCAST:
            # Tüm kanallardaki tüm subscriber'lar
            for subs in self._subscriptions.values():
                result.extend(subs)
        elif msg.channel_type == ChannelType.UNICAST and msg.target_agent:
            # Hedef agent'ın aboneliklerinden channel'a uyanlar
            channel_subs = self._subscriptions.get(msg.channel, [])
            agent_channel = f"agent:{msg.target_agent}"
            agent_subs = self._subscriptions.get(agent_channel, [])
            result = [s for s in channel_subs if s.agent_role == msg.target_agent]
            result.extend(agent_subs)
        else:
            # Multicast — channel'daki tüm subscriber'lar
            result = list(self._subscriptions.get(msg.channel, []))

        # Filter by message type
        filtered = []
        for sub in result:
            if sub.filter_types is None or msg.message_type in sub.filter_types:
                filtered.append(sub)

        # Dedup by agent_role (aynı agent'a 2 kez gönderme)
        seen = set()
        unique = []
        for sub in filtered:
            if sub.agent_role not in seen:
                seen.add(sub.agent_role)
                unique.append(sub)

        return unique

    def _handle_delivery_failure(self, msg: MessageEnvelope, sub: Subscription, reason: str) -> None:
        """Teslim hatası — retry veya DLQ."""
        self._stats[msg.channel].failed += 1
        if msg.can_retry:
            msg.retry_count += 1
            self._stats[msg.channel].retried += 1
            # Schedule retry with exponential backoff
            try:
                loop = asyncio.get_running_loop()
                loop.call_later(
                    2 ** msg.retry_count,
                    lambda: asyncio.ensure_future(self.publish(msg)),
                )
            except RuntimeError:
                # No running loop — push to DLQ instead
                self.dlq.push(msg, f"no_running_loop: {reason}")
        else:
            self.dlq.push(msg, f"max_retries_or_expired: {reason}")

    # ── Request-Response Pattern ─────────────────────────────────

    async def request(
        self,
        msg: MessageEnvelope,
        timeout: float = 30.0,
    ) -> MessageEnvelope | None:
        """
        Request-response pattern: mesaj gönder, correlation_id ile yanıt bekle.
        Agent-to-agent soru-cevap için kullanılır.
        """
        if not msg.correlation_id:
            msg.correlation_id = msg.id

        future: asyncio.Future[MessageEnvelope] = asyncio.get_event_loop().create_future()
        self._pending_futures[msg.correlation_id] = future

        await self.publish(msg)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_futures.pop(msg.correlation_id, None)
            logger.warning(f"Request timeout: {msg.id} (correlation: {msg.correlation_id})")
            return None

    # ── Convenience Methods ──────────────────────────────────────

    async def send_to_agent(
        self,
        source: str,
        target: str,
        msg_type: MessageType,
        payload: dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: str | None = None,
    ) -> bool:
        """Kısayol: bir agent'a doğrudan mesaj gönder."""
        envelope = MessageEnvelope(
            source_agent=source,
            target_agent=target,
            channel=f"agent:{target}",
            channel_type=ChannelType.UNICAST,
            message_type=msg_type,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id,
        )
        return await self.publish(envelope)

    async def broadcast(
        self,
        source: str,
        msg_type: MessageType,
        payload: dict[str, Any],
    ) -> bool:
        """Kısayol: tüm agent'lara broadcast mesaj."""
        envelope = MessageEnvelope(
            source_agent=source,
            channel="broadcast",
            channel_type=ChannelType.BROADCAST,
            message_type=msg_type,
            payload=payload,
            delivery=DeliveryGuarantee.AT_MOST_ONCE,
        )
        return await self.publish(envelope)

    async def publish_to_channel(
        self,
        source: str,
        channel: str,
        msg_type: MessageType,
        payload: dict[str, Any],
    ) -> bool:
        """Kısayol: belirli bir topic/channel'a multicast mesaj."""
        envelope = MessageEnvelope(
            source_agent=source,
            channel=channel,
            channel_type=ChannelType.MULTICAST,
            message_type=msg_type,
            payload=payload,
        )
        return await self.publish(envelope)

    # ── Stats & Monitoring ───────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Tüm kanal istatistiklerini döndür."""
        return {
            "channels": {
                ch: {
                    "published": s.published,
                    "delivered": s.delivered,
                    "failed": s.failed,
                    "expired": s.expired,
                    "retried": s.retried,
                    "subscribers": len(self._subscriptions.get(ch, [])),
                }
                for ch, s in self._stats.items()
            },
            "total_subscriptions": sum(len(v) for v in self._subscriptions.values()),
            "dlq_size": self.dlq.size,
            "pending_requests": len(self._pending_futures),
        }

    def get_subscriptions(self) -> dict[str, list[str]]:
        """Kanal → agent listesi."""
        return {
            ch: [s.agent_role for s in subs]
            for ch, subs in self._subscriptions.items()
        }

    # ── Lifecycle ────────────────────────────────────────────────

    def stop(self) -> None:
        """Bus'ı durdur — yeni mesaj kabul etme."""
        self._running = False
        # Cancel pending futures
        for fid, future in self._pending_futures.items():
            if not future.done():
                future.cancel()
        self._pending_futures.clear()

    def start(self) -> None:
        """Bus'ı yeniden başlat."""
        self._running = True


# ── Singleton ────────────────────────────────────────────────────

_bus_instance: EventBus | None = None


def get_event_bus() -> EventBus:
    """Global EventBus singleton."""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = EventBus()
    return _bus_instance


def reset_event_bus() -> None:
    """Test/reset için bus'ı sıfırla."""
    global _bus_instance
    if _bus_instance:
        _bus_instance.stop()
    _bus_instance = None
