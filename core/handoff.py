"""
Agent Handoff Protocol — Bir agent'ın işi başka bir agent'a devretmesi.

Senaryo: Researcher veri topladı ama analiz yapamıyor → Thinker'a handoff.
Veya: Speed hızlı yanıt verdi ama derinlik yetersiz → Reasoner'a handoff.

Handoff akışı:
1. Agent A → HandoffManager.initiate() → HandoffContext oluştur
2. HandoffManager → EventBus üzerinden HANDOFF_REQUEST gönder
3. Agent B handler → accept/reject
4. Accept → Agent B işi devralır, context ile çalışır
5. Complete → HANDOFF_COMPLETE event, sonuç orijinal akışa döner

Özellikler:
- Context preservation (ne yapıldı, ne kaldı)
- Graceful degradation (reject durumunda fallback)
- Handoff chain tracking (A→B→C zinciri)
- Timeout handling
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

from .event_bus import EventBus, get_event_bus
from .protocols import (
    ChannelType,
    DeliveryGuarantee,
    HandoffContext,
    MessageEnvelope,
    MessagePriority,
    MessageType,
)

logger = logging.getLogger("handoff")


class HandoffManager:
    """
    Agent handoff koordinatörü.

    Kullanım:
        manager = HandoffManager(bus)

        # Agent A: işi devret
        ctx = await manager.initiate(
            from_agent="researcher",
            to_agent="thinker",
            reason="Analiz derinliği gerekiyor",
            task_description="Pazar analizi yap",
            work_completed="Veri toplandı: 15 kaynak",
            work_remaining="Trend analizi ve sonuç çıkarımı",
        )

        # Agent B: otomatik olarak handler çağrılır
        # (subscribe sırasında register edilen handler)
    """

    def __init__(self, bus: EventBus | None = None):
        self._bus = bus or get_event_bus()
        # Active handoffs: handoff_id → HandoffContext
        self._active: dict[str, HandoffContext] = {}
        # Handoff chain: original_task → [handoff_ids]
        self._chains: dict[str, list[str]] = defaultdict(list)
        # Agent handlers: agent_role → accept callback
        self._handlers: dict[str, Any] = {}
        # Completion futures: handoff_id → Future
        self._completion_futures: dict[str, asyncio.Future] = {}

    def register_handler(
        self,
        agent_role: str,
        handler: Any,  # async def handler(ctx: HandoffContext) -> str
    ) -> None:
        """Agent'ın handoff kabul handler'ını kaydet."""
        self._handlers[agent_role] = handler
        # Auto-subscribe to handoff channel
        self._bus.subscribe(
            agent_role=agent_role,
            channel=f"handoff:{agent_role}",
            handler=self._on_handoff_message,
            filter_types={MessageType.HANDOFF_REQUEST},
        )
        logger.info(f"Handoff handler registered: {agent_role}")

    async def initiate(
        self,
        from_agent: str,
        to_agent: str,
        reason: str,
        task_description: str,
        work_completed: str = "",
        work_remaining: str = "",
        partial_result: str = "",
        context_data: dict[str, Any] | None = None,
        thread_id: str | None = None,
        timeout: float = 60.0,
    ) -> HandoffContext:
        """
        Handoff başlat — Agent A'dan Agent B'ye iş devri.
        Timeout süresi içinde yanıt gelmezse reject sayılır.
        """
        ctx = HandoffContext(
            from_agent=from_agent,
            to_agent=to_agent,
            reason=reason,
            task_description=task_description,
            work_completed=work_completed,
            work_remaining=work_remaining,
            partial_result=partial_result,
            context_data=context_data or {},
            thread_id=thread_id,
        )

        self._active[ctx.id] = ctx
        self._chains[task_description[:80]].append(ctx.id)

        # Create completion future
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._completion_futures[ctx.id] = future

        # Send handoff request via event bus
        envelope = MessageEnvelope(
            source_agent=from_agent,
            target_agent=to_agent,
            channel=f"handoff:{to_agent}",
            channel_type=ChannelType.UNICAST,
            message_type=MessageType.HANDOFF_REQUEST,
            payload={
                "handoff_id": ctx.id,
                "reason": reason,
                "task_description": task_description,
                "work_completed": work_completed,
                "work_remaining": work_remaining,
                "partial_result": partial_result,
                "context_data": context_data or {},
            },
            priority=MessagePriority.HIGH,
            delivery=DeliveryGuarantee.AT_LEAST_ONCE,
            correlation_id=ctx.id,
        )

        delivered = await self._bus.publish(envelope)

        if not delivered:
            ctx.accepted = False
            self._cleanup_handoff(ctx.id)
            logger.warning(f"Handoff failed: no handler for {to_agent}")
            return ctx

        # Wait for completion
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            ctx.completed = True
            return ctx
        except asyncio.TimeoutError:
            logger.warning(f"Handoff timeout: {ctx.id} ({from_agent} → {to_agent})")
            ctx.accepted = False
            self._cleanup_handoff(ctx.id)
            return ctx

    async def _on_handoff_message(self, msg: MessageEnvelope) -> None:
        """EventBus'tan gelen handoff mesajlarını işle."""
        handoff_id = msg.payload.get("handoff_id", "")
        target = msg.target_agent

        if target not in self._handlers:
            # Reject — handler yok
            await self._send_reject(msg.source_agent, handoff_id, "no_handler_registered")
            return

        ctx = self._active.get(handoff_id)
        if not ctx:
            return

        # Accept and execute
        ctx.accepted = True
        logger.info(f"Handoff accepted: {ctx.from_agent} → {ctx.to_agent} ({ctx.reason})")

        # Send accept notification
        await self._bus.send_to_agent(
            source=target,
            target=msg.source_agent,
            msg_type=MessageType.HANDOFF_ACCEPT,
            payload={"handoff_id": handoff_id},
        )

        # Execute handler
        try:
            handler = self._handlers[target]
            result = await handler(ctx)
            ctx.completed = True

            # Send completion
            await self._bus.publish_to_channel(
                source=target,
                channel=f"handoff:{msg.source_agent}",
                msg_type=MessageType.HANDOFF_COMPLETE,
                payload={
                    "handoff_id": handoff_id,
                    "result": result,
                    "from_agent": ctx.from_agent,
                    "to_agent": ctx.to_agent,
                },
            )

            # Resolve future
            future = self._completion_futures.get(handoff_id)
            if future and not future.done():
                future.set_result(result)

        except Exception as e:
            logger.error(f"Handoff execution failed: {handoff_id}: {e}")
            await self._send_reject(msg.source_agent, handoff_id, str(e))
            future = self._completion_futures.get(handoff_id)
            if future and not future.done():
                future.set_exception(e)
        finally:
            self._cleanup_handoff(handoff_id)

    async def _send_reject(self, target: str, handoff_id: str, reason: str) -> None:
        """Handoff reject mesajı gönder."""
        await self._bus.send_to_agent(
            source="handoff_manager",
            target=target,
            msg_type=MessageType.HANDOFF_REJECT,
            payload={"handoff_id": handoff_id, "reason": reason},
        )

    def _cleanup_handoff(self, handoff_id: str) -> None:
        """Tamamlanan/başarısız handoff'u temizle."""
        self._active.pop(handoff_id, None)
        self._completion_futures.pop(handoff_id, None)

    # ── Query ────────────────────────────────────────────────────

    def get_active_handoffs(self) -> list[dict[str, Any]]:
        """Aktif handoff'ları listele."""
        return [
            {
                "id": ctx.id,
                "from": ctx.from_agent,
                "to": ctx.to_agent,
                "reason": ctx.reason,
                "accepted": ctx.accepted,
                "task": ctx.task_description[:80],
                "timestamp": ctx.timestamp.isoformat(),
            }
            for ctx in self._active.values()
        ]

    def get_handoff_chain(self, task_key: str) -> list[str]:
        """Bir görev için handoff zincirini döndür."""
        return self._chains.get(task_key[:80], [])

    def get_stats(self) -> dict[str, Any]:
        return {
            "active_handoffs": len(self._active),
            "registered_handlers": list(self._handlers.keys()),
            "total_chains": len(self._chains),
        }


# ── Singleton ────────────────────────────────────────────────────

_manager_instance: HandoffManager | None = None


def get_handoff_manager() -> HandoffManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = HandoffManager()
    return _manager_instance
