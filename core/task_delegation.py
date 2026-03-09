"""
Async Task Delegation — Agent'lar arası asenkron görev atama.

Bir agent başka bir agent'a görev atar, sonucu beklemeden devam edebilir
veya Future pattern ile sonucu asenkron olarak alır.

Özellikler:
- Fire-and-forget delegation (sonucu bekleme)
- Await delegation (sonucu bekle, timeout ile)
- Task queue with priority
- Parallel delegation (birden fazla agent'a aynı anda)
- Fan-out/fan-in pattern
- Progress tracking
- Cancellation support
"""

from __future__ import annotations

import asyncio
import heapq
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .event_bus import EventBus, get_event_bus
from .protocols import (
    ChannelType,
    DelegatedTask,
    DeliveryGuarantee,
    MessageEnvelope,
    MessagePriority,
    MessageType,
)

logger = logging.getLogger("task_delegation")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TaskDelegationManager:
    """
    Asenkron görev delegasyonu koordinatörü.

    Kullanım:
        mgr = TaskDelegationManager(bus)

        # Fire-and-forget
        task_id = await mgr.delegate(
            delegator="orchestrator",
            delegate="researcher",
            description="Web'de X konusunu araştır",
        )

        # Await result
        result = await mgr.delegate_and_wait(
            delegator="orchestrator",
            delegate="researcher",
            description="Web'de X konusunu araştır",
            timeout=60.0,
        )

        # Fan-out: birden fazla agent'a paralel görev
        results = await mgr.fan_out(
            delegator="orchestrator",
            tasks=[
                ("researcher", "Veri topla"),
                ("thinker", "Analiz yap"),
                ("reasoner", "Sonuç çıkar"),
            ],
            timeout=90.0,
        )
    """

    def __init__(self, bus: EventBus | None = None):
        self._bus = bus or get_event_bus()
        # Active tasks: task_id → DelegatedTask
        self._tasks: dict[str, DelegatedTask] = {}
        # Completion futures: task_id → Future
        self._futures: dict[str, asyncio.Future] = {}
        # Agent task queues: agent_role → [task_ids]
        self._agent_queues: dict[str, list[str]] = defaultdict(list)
        # Agent executors: agent_role → executor callback
        self._executors: dict[str, Any] = {}
        # Progress callbacks: task_id → callback
        self._progress_callbacks: dict[str, Any] = {}
        # Priority queue: (priority, timestamp, task_id)
        self._priority_queue: list[tuple[int, float, str]] = []

    def register_executor(
        self,
        agent_role: str,
        executor: Any,  # async def executor(task: DelegatedTask) -> str
    ) -> None:
        """Agent'ın görev yürütücüsünü kaydet."""
        self._executors[agent_role] = executor
        # Subscribe to task channel
        self._bus.subscribe(
            agent_role=agent_role,
            channel=f"tasks:{agent_role}",
            handler=self._on_task_message,
            filter_types={MessageType.TASK_REQUEST, MessageType.CANCEL},
        )
        logger.info(f"Task executor registered: {agent_role}")

    async def delegate(
        self,
        delegator: str,
        delegate: str,
        description: str,
        input_data: dict[str, Any] | None = None,
        priority: int = 3,
        timeout_seconds: float | None = None,
    ) -> str:
        """
        Fire-and-forget görev delegasyonu.
        Returns task_id — sonucu sonra sorgulayabilirsin.

        priority: 1=highest, 5=lowest (default 3)
        timeout_seconds: per-task timeout, None = no timeout
        """
        task = DelegatedTask(
            delegator=delegator,
            delegate=delegate,
            description=description,
            input_data=input_data or {},
            priority=MessagePriority.NORMAL,
            timeout_seconds=int(timeout_seconds) if timeout_seconds else 120,
            queued_at=_now(),
        )

        self._tasks[task.id] = task
        self._agent_queues[delegate].append(task.id)

        # Push to priority queue
        heapq.heappush(self._priority_queue, (priority, time.time(), task.id))

        # Send via event bus
        envelope = MessageEnvelope(
            source_agent=delegator,
            target_agent=delegate,
            channel=f"tasks:{delegate}",
            channel_type=ChannelType.UNICAST,
            message_type=MessageType.TASK_REQUEST,
            payload={
                "task_id": task.id,
                "description": description,
                "input_data": input_data or {},
                "timeout_seconds": task.timeout_seconds,
            },
            priority=MessagePriority.NORMAL,
            delivery=DeliveryGuarantee.AT_LEAST_ONCE,
            correlation_id=task.id,
        )

        await self._bus.publish(envelope)
        logger.info(f"Task delegated: {task.id} ({delegator} → {delegate}) priority={priority}")
        return task.id

    async def delegate_and_wait(
        self,
        delegator: str,
        delegate: str,
        description: str,
        input_data: dict[str, Any] | None = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        timeout: float = 120.0,
    ) -> str | None:
        """
        Görev delegasyonu + sonucu bekle.
        Timeout olursa None döner.
        """
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()

        task_id = await self.delegate(
            delegator=delegator,
            delegate=delegate,
            description=description,
            input_data=input_data,
            priority=priority,
            timeout_seconds=int(timeout),
        )

        self._futures[task_id] = future

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Task delegation timeout: {task_id}")
            task = self._tasks.get(task_id)
            if task:
                task.status = "failed"
                task.error = "timeout"
            return None
        finally:
            self._futures.pop(task_id, None)

    async def fan_out(
        self,
        delegator: str,
        tasks: list[tuple[str, str]],  # [(delegate, description), ...]
        input_data: dict[str, Any] | None = None,
        timeout: float = 120.0,
        allow_partial: bool = True,
        context: dict[str, Any] | None = None,
    ) -> dict[str, str | None]:
        """
        Fan-out pattern: birden fazla agent'a paralel görev at, hepsini bekle.

        allow_partial=True (default): başarısız görevleri logla, başarılıları döndür.
        allow_partial=False: herhangi biri başarısız olursa exception fırlat.
        context: delegator bağlamı, her görevin input_data'sına eklenir.

        Returns: {delegate_role: result_or_none}
        """
        coros = []
        delegates = []

        # Merge context into input_data
        merged_input = dict(input_data or {})
        if context:
            merged_input["_delegator_context"] = context

        for delegate, description in tasks:
            delegates.append(delegate)
            coros.append(
                self.delegate_and_wait(
                    delegator=delegator,
                    delegate=delegate,
                    description=description,
                    input_data=merged_input,
                    timeout=timeout,
                )
            )

        results = await asyncio.gather(*coros, return_exceptions=True)

        output: dict[str, str | None] = {}
        failed: list[str] = []

        for delegate, r in zip(delegates, results):
            if isinstance(r, Exception):
                logger.error(f"Fan-out task failed for {delegate}: {r}")
                failed.append(delegate)
                output[delegate] = None
            else:
                output[delegate] = str(r) if r is not None else None

        if not allow_partial and failed:
            raise RuntimeError(
                f"Fan-out failed for agents: {', '.join(failed)}. "
                f"Partial results not allowed."
            )

        return output

    async def _on_task_message(self, msg: MessageEnvelope) -> None:
        """EventBus'tan gelen görev mesajlarını işle."""
        if msg.message_type == MessageType.CANCEL:
            await self._handle_cancel(msg)
            return

        task_id = msg.payload.get("task_id", "")
        target = msg.target_agent

        if target not in self._executors:
            logger.warning(f"No executor for {target}, task {task_id}")
            return

        task = self._tasks.get(task_id)
        if not task:
            return

        # Execute
        task.status = "running"
        task.started_at = _now()
        task.assigned_at = _now()

        try:
            executor = self._executors[target]

            # Wrap with timeout if set
            if task.timeout_seconds:
                result = await asyncio.wait_for(
                    executor(task), timeout=float(task.timeout_seconds)
                )
            else:
                result = await executor(task)

            task.status = "completed"
            task.result = result
            task.completed_at = _now()

            # Send result back
            await self._bus.send_to_agent(
                source=target,
                target=task.delegator,
                msg_type=MessageType.TASK_RESULT,
                payload={
                    "task_id": task_id,
                    "result": result,
                    "status": "completed",
                },
                correlation_id=task_id,
            )

            # Resolve future
            future = self._futures.get(task_id)
            if future and not future.done():
                future.set_result(result)

            logger.info(f"Task completed: {task_id} by {target}")

        except asyncio.TimeoutError:
            task.retry_count += 1
            task.completed_at = _now()

            if task.retry_count < task.max_retries:
                # Re-queue for retry
                task.status = "pending"
                task.started_at = None
                task.assigned_at = None
                task.completed_at = None
                self._agent_queues[target].append(task.id)
                heapq.heappush(self._priority_queue, (3, time.time(), task.id))

                # Re-publish task message
                envelope = MessageEnvelope(
                    source_agent=task.delegator,
                    target_agent=target,
                    channel=f"tasks:{target}",
                    channel_type=ChannelType.UNICAST,
                    message_type=MessageType.TASK_REQUEST,
                    payload={
                        "task_id": task_id,
                        "description": task.description,
                        "input_data": task.input_data,
                        "timeout_seconds": task.timeout_seconds,
                    },
                    priority=MessagePriority.NORMAL,
                    delivery=DeliveryGuarantee.AT_LEAST_ONCE,
                    correlation_id=task_id,
                )
                await self._bus.publish(envelope)
                logger.warning(
                    f"Task timed out, retrying ({task.retry_count}/{task.max_retries}): {task_id}"
                )
            else:
                task.status = "timed_out"
                task.error = f"Timed out after {task.retry_count} retries"

                await self._bus.send_to_agent(
                    source=target,
                    target=task.delegator,
                    msg_type=MessageType.ERROR,
                    payload={
                        "task_id": task_id,
                        "error": task.error,
                        "status": "timed_out",
                    },
                    correlation_id=task_id,
                )

                future = self._futures.get(task_id)
                if future and not future.done():
                    future.set_exception(
                        TimeoutError(f"Task {task_id} timed out after {task.retry_count} retries")
                    )

                logger.error(f"Task timed out permanently: {task_id}")

        except asyncio.CancelledError:
            task.status = "cancelled"
            task.completed_at = _now()

            # Publish cancel event
            await self._bus.publish(MessageEnvelope(
                source_agent=target,
                target_agent=task.delegator,
                channel="task.cancelled",
                channel_type=ChannelType.BROADCAST,
                message_type=MessageType.CANCEL,
                payload={"task_id": task_id, "status": "cancelled"},
                correlation_id=task_id,
            ))

            future = self._futures.get(task_id)
            if future and not future.done():
                future.cancel()

            logger.info(f"Task cancelled: {task_id}")

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = _now()

            await self._bus.send_to_agent(
                source=target,
                target=task.delegator,
                msg_type=MessageType.ERROR,
                payload={
                    "task_id": task_id,
                    "error": str(e),
                    "status": "failed",
                },
                correlation_id=task_id,
            )

            future = self._futures.get(task_id)
            if future and not future.done():
                future.set_exception(e)

            logger.error(f"Task failed: {task_id} by {target}: {e}")

        finally:
            # Remove from agent queue
            queue = self._agent_queues.get(target, [])
            if task_id in queue:
                queue.remove(task_id)

    async def _handle_cancel(self, msg: MessageEnvelope) -> None:
        """Görev iptal mesajını işle."""
        task_id = msg.payload.get("task_id", "")
        task = self._tasks.get(task_id)
        if task and task.status in ("pending", "running"):
            task.status = "cancelled"
            task.completed_at = _now()
            future = self._futures.get(task_id)
            if future and not future.done():
                future.cancel()
            logger.info(f"Task cancelled: {task_id}")

    async def cancel_task(self, task_id: str, by_agent: str) -> bool:
        """Bir görevi iptal et."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        await self._bus.send_to_agent(
            source=by_agent,
            target=task.delegate,
            msg_type=MessageType.CANCEL,
            payload={"task_id": task_id},
            priority=MessagePriority.HIGH,
        )
        return True

    def report_progress(self, task_id: str, progress: float, detail: str = "") -> None:
        """Görev ilerleme bildirimi (0.0 - 1.0)."""
        task = self._tasks.get(task_id)
        if task:
            # Fire-and-forget progress event
            asyncio.ensure_future(
                self._bus.send_to_agent(
                    source=task.delegate,
                    target=task.delegator,
                    msg_type=MessageType.TASK_PROGRESS,
                    payload={
                        "task_id": task_id,
                        "progress": progress,
                        "detail": detail,
                    },
                )
            )

    # ── Query ────────────────────────────────────────────────────

    def get_task(self, task_id: str) -> DelegatedTask | None:
        return self._tasks.get(task_id)

    def get_agent_queue(self, agent_role: str) -> list[dict[str, Any]]:
        """Agent'ın görev kuyruğunu döndür."""
        task_ids = self._agent_queues.get(agent_role, [])
        return [
            {
                "id": tid,
                "description": self._tasks[tid].description[:80] if tid in self._tasks else "?",
                "status": self._tasks[tid].status if tid in self._tasks else "unknown",
                "priority": self._tasks[tid].priority.value if tid in self._tasks else 0,
            }
            for tid in task_ids
        ]

    def get_stats(self) -> dict[str, Any]:
        status_counts: dict[str, int] = defaultdict(int)
        wait_times: list[float] = []
        completion_times: list[float] = []
        active_count = 0

        for t in self._tasks.values():
            status_counts[t.status] += 1

            if t.status in ("running", "pending"):
                active_count += 1

            # avg_wait_time: queued_at → started_at for completed tasks
            if t.started_at and t.queued_at:
                wait_times.append((t.started_at - t.queued_at).total_seconds())

            # avg_completion_time: started_at → completed_at
            if t.completed_at and t.started_at:
                completion_times.append((t.completed_at - t.started_at).total_seconds())

        return {
            "total_tasks": len(self._tasks),
            "active_tasks": active_count,
            "by_status": dict(status_counts),
            "registered_executors": list(self._executors.keys()),
            "agent_queue_sizes": {
                role: len(ids) for role, ids in self._agent_queues.items()
            },
            "pending_futures": len(self._futures),
            "priority_queue_size": len(self._priority_queue),
            "avg_wait_time": (
                sum(wait_times) / len(wait_times) if wait_times else 0.0
            ),
            "avg_completion_time": (
                sum(completion_times) / len(completion_times) if completion_times else 0.0
            ),
        }


# ── Singleton ────────────────────────────────────────────────────

_delegation_instance: TaskDelegationManager | None = None


def get_task_delegation_manager() -> TaskDelegationManager:
    global _delegation_instance
    if _delegation_instance is None:
        _delegation_instance = TaskDelegationManager()
    return _delegation_instance
