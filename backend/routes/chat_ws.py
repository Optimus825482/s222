"""WebSocket chat endpoints — real-time agent execution streaming."""

import asyncio
import json
import logging
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Coroutine, Union

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi import Request, Depends
from fastapi.responses import StreamingResponse

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import _get_user_from_token
from config import MODELS, RUNTIME_EVENT_SCHEMA_VERSION, get_feature_flags
from core.models import Thread, PipelineType
from core.state import save_thread, load_thread
from shared_state import _AGENT_ROLES, _mask_user_id, _utcnow

router = APIRouter()
logger = logging.getLogger(__name__)


class WSLiveMonitor:
    """WebSocket-based live monitor replacing Streamlit's LiveMonitor."""

    def __init__(self, ws: WebSocket, events_list: list | None = None):
        self.ws = ws
        self._stop = False
        self._closed = False
        self._events_list = events_list or []
        self._pending_tasks: set[asyncio.Task] = set()
        self._run_id = uuid.uuid4().hex
        self._sequence = 0
        # Faz 14.6: Steering queue for injecting user messages into running agent
        from agents.agentic_loop import SteeringQueue
        self._steering_queue = SteeringQueue()

    def _next_envelope(self, *, event: str, phase: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._sequence += 1
        return {
            "schema_version": RUNTIME_EVENT_SCHEMA_VERSION,
            "event": event,
            "phase": phase,
            "run_id": self._run_id,
            "sequence": self._sequence,
            "ts": time.time(),
            "feature_flags": get_feature_flags(),
            "payload": payload,
        }

    def envelope(self, *, event: str, phase: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Public wrapper so callers can advance sequence safely."""
        return self._next_envelope(event=event, phase=phase, payload=payload)

    def should_stop(self) -> bool:
        return self._stop

    def request_stop(self):
        self._stop = True

    async def _send(self, data: dict):
        if self._closed:
            return
        try:
            await self.ws.send_json(data)
        except (RuntimeError, WebSocketDisconnect):
            # WebSocket already closed — suppress silently
            self._closed = True

    async def close(self):
        """Mark closed and cancel all pending background sends."""
        self._closed = True
        for task in list(self._pending_tasks):
            task.cancel()
        self._pending_tasks.clear()

    def _track_task(
        self, coroutine: Union[asyncio.Future[Any], Coroutine[Any, Any, Any]]
    ) -> None:
        if self._closed:
            # Must close unawaited coroutine to avoid ResourceWarning
            if asyncio.iscoroutine(coroutine):
                coroutine.close()
            return

        task = asyncio.ensure_future(coroutine)
        try:
            task.set_name("ws-send")
        except AttributeError:
            pass
        self._pending_tasks.add(task)

        def _on_done(done_task: asyncio.Task) -> None:
            self._pending_tasks.discard(done_task)
            if done_task.cancelled():
                return
            exc = done_task.exception()
            if exc is None:
                return
            # WS-closed errors already handled in _send — suppress
            if isinstance(exc, (RuntimeError, WebSocketDisconnect)):
                self._closed = True
                return
            logger.error("WSLiveMonitor background send failed: %s", exc, exc_info=True)

        task.add_done_callback(_on_done)

    def start(self, task_description: str):
        self._track_task(
            self._send(
                {
                    "type": "monitor_start",
                    "description": task_description,
                    **self._next_envelope(
                        event="monitor.started",
                        phase="start",
                        payload={"description": task_description},
                    ),
                }
            )
        )

    def emit(self, event_type: str, agent: str, content: str, **extra):
        payload = {
            "type": "live_event",
            "event_type": event_type,
            "agent": agent,
            "content": content,
            "extra": extra,
            "timestamp": time.time(),
        }
        payload.update(
            self._next_envelope(
                event=f"live.{event_type}",
                phase="progress",
                payload={
                    "agent": agent,
                    "content": content,
                    "extra": extra,
                },
            )
        )
        self._events_list.append(payload)
        self._track_task(self._send(payload))

    def complete(self, summary: str = ""):
        self._track_task(
            self._send(
                {
                    "type": "monitor_complete",
                    "summary": summary,
                    **self._next_envelope(
                        event="monitor.completed",
                        phase="complete",
                        payload={"summary": summary},
                    ),
                }
            )
        )

    def error(self, message: str):
        self._track_task(
            self._send(
                {
                    "type": "monitor_error",
                    "message": message,
                    **self._next_envelope(
                        event="monitor.error",
                        phase="error",
                        payload={"message": message},
                    ),
                }
            )
        )

    def emit_stream_event(self, event_type: str, agent: str, delta: str = "", **extra):
        """Emit granular streaming events (thinking_delta, text_delta, toolcall_*)."""
        payload = {
            "type": "stream_event",
            "event_type": event_type,
            "agent": agent,
            "delta": delta,
            "extra": extra,
            "timestamp": time.time(),
        }
        payload.update(
            self._next_envelope(
                event=f"stream.{event_type}",
                phase="stream",
                payload={
                    "agent": agent,
                    "delta": delta,
                    "extra": extra,
                },
            )
        )
        self._events_list.append(payload)
        self._track_task(self._send(payload))


# Import post-task meeting generator + WS delivery event id helper from messaging module
try:
    from routes.messaging import _build_ws_delivery_event_id, _generate_post_task_meeting
except ImportError:

    def _generate_post_task_meeting(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}

    def _build_ws_delivery_event_id(run_id: str, event_type: str) -> str:
        safe_run_id = (run_id or "unknown_run").strip() or "unknown_run"
        safe_event_type = (event_type or "unknown_event").strip() or "unknown_event"
        return f"{safe_run_id}:{safe_event_type}"


# Rate limiter from deps
try:
    from deps import rate_limiter as _rate_limiter
except ImportError:
    from deps import _RateLimiter

    _rate_limiter = _RateLimiter(max_requests=120, window_seconds=60)


@router.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    """
    WebSocket endpoint for real-time agent execution.
    Auth: pass token via query ?token=... or in first message {"token": "..."}.
    Client sends: {"message": "...", "thread_id": "...", "pipeline_type": "auto"}
    Server streams: live events, then final result.
    """
    token = (ws.query_params.get("token") or "").strip()
    user_id: str | None = None
    if token:
        user = _get_user_from_token(token)
        if user:
            user_id = user["user_id"]

    await ws.accept()
    ws.state.run_task = None
    ws.state.live_events = []
    ws.state.ws_send_failures = 0
    ws.state.sent_event_ids = set()

    async def _safe_ws_send(
        data: dict,
        *,
        event_context: dict[str, Any] | None = None,
        retry_attempts: int = 1,
        retry_backoff_seconds: float = 0.2,
        idempotency_key: str | None = None,
    ) -> bool:
        """Reliably send WS payload with structured logging, retry/backoff, and idempotency."""
        ctx = {
            "type": data.get("type"),
            "event": data.get("event"),
            **(event_context or {}),
        }

        if idempotency_key:
            sent_event_ids = getattr(ws.state, "sent_event_ids", set())
            if idempotency_key in sent_event_ids:
                logger.info(
                    "ws.send.skipped_duplicate",
                    extra={
                        "event": "ws.send.skipped_duplicate",
                        "idempotency_key": idempotency_key,
                        "context": ctx,
                    },
                )
                return True

        attempts = max(1, retry_attempts)
        for attempt in range(1, attempts + 1):
            try:
                await ws.send_json(data)
                if idempotency_key:
                    sent_event_ids = getattr(ws.state, "sent_event_ids", set())
                    sent_event_ids.add(idempotency_key)
                    ws.state.sent_event_ids = sent_event_ids
                return True
            except Exception as exc:
                ws.state.ws_send_failures = int(getattr(ws.state, "ws_send_failures", 0)) + 1
                log_payload = {
                    "event": "ws.send.failed",
                    "attempt": attempt,
                    "attempts_total": attempts,
                    "ws_send_failures_total": ws.state.ws_send_failures,
                    "idempotency_key": idempotency_key,
                    "context": ctx,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
                if attempt < attempts:
                    logger.warning("ws.send.failed.retrying", extra=log_payload)
                    backoff = retry_backoff_seconds * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff)
                    continue

                logger.error("ws.send.failed.exhausted", extra=log_payload, exc_info=True)
                return False

        return False

    def _collect_token_usage(thread: Thread | None) -> dict[str, int]:
        if not thread or not thread.tasks:
            return {
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }

        total_tokens = sum(getattr(task, "total_tokens", 0) or 0 for task in thread.tasks)
        prompt_tokens = 0
        completion_tokens = 0
        has_prompt_completion = False

        for task in thread.tasks:
            for sub_task in getattr(task, "sub_tasks", []):
                meta = getattr(sub_task, "metadata", {}) or {}
                if not isinstance(meta, dict):
                    continue
                p_tok = meta.get("prompt_tokens")
                c_tok = meta.get("completion_tokens")
                if isinstance(p_tok, int):
                    prompt_tokens += p_tok
                    has_prompt_completion = True
                if isinstance(c_tok, int):
                    completion_tokens += c_tok
                    has_prompt_completion = True

        return {
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens if has_prompt_completion else 0,
            "completion_tokens": completion_tokens if has_prompt_completion else 0,
        }

    def _resolve_pipeline_type(thread: Thread | None, fallback: str | None = None) -> str:
        if thread and thread.tasks:
            last_task = thread.tasks[-1]
            task_pipeline = getattr(last_task, "pipeline_type", None)
            if isinstance(task_pipeline, PipelineType):
                return task_pipeline.value
            if task_pipeline:
                return str(task_pipeline)
        return fallback or PipelineType.AUTO.value

    def _log_run_telemetry(
        *,
        event: str,
        phase: str,
        monitor: WSLiveMonitor | None,
        correlation_id: str,
        effective_user_id: str | None,
        thread: Thread | None,
        started_at: float,
        status: str,
        pipeline_type: str,
        agent: str,
        error: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "event": event,
            "phase": phase,
            "run_id": getattr(monitor, "_run_id", None),
            "thread_id": getattr(thread, "id", None),
            "user_id_masked": _mask_user_id(effective_user_id),
            "sequence": getattr(monitor, "_sequence", 0),
            "pipeline_type": pipeline_type,
            "agent": agent,
            "status": status,
            "latency_ms": round(max((time.time() - started_at) * 1000.0, 0.0), 2),
            "token_usage": _collect_token_usage(thread),
            "correlation_id": correlation_id,
            "ts": _utcnow().isoformat(),
        }
        if error:
            payload["error"] = error
        logger.info("ws.run.telemetry %s", json.dumps(payload, ensure_ascii=False, default=str))

    async def _execute_run(
        message: str,
        thread: Thread,
        monitor: WSLiveMonitor,
        pipeline_str: str,
        effective_user_id: str | None,
        correlation_id: str,
        started_at: float,
    ):
        try:
            _log_run_telemetry(
                event="run.progress",
                phase="progress",
                monitor=monitor,
                correlation_id=correlation_id,
                effective_user_id=effective_user_id,
                thread=thread,
                started_at=started_at,
                status="running",
                pipeline_type=_resolve_pipeline_type(thread, pipeline_str),
                agent="orchestrator",
            )
            from agents.orchestrator import OrchestratorAgent

            orchestrator = OrchestratorAgent()
            forced_pipe = None
            if pipeline_str != "auto":
                try:
                    forced_pipe = PipelineType(pipeline_str)
                except ValueError:
                    pass

            result = await orchestrator.route_and_execute(
                message,
                thread,
                live_monitor=monitor,
                forced_pipeline=forced_pipe,
                user_id=effective_user_id,
            )
            save_thread(thread, user_id=effective_user_id)

            # Pattern detection: record execution for 3+ tekrar → skill (Faz 11.3)
            try:
                from tools.pattern_skill import observe_thread

                observe_thread(thread, user_id=effective_user_id)
            except Exception:
                pass

            try:
                from tools.pii_masker import mask_pii_in_response

                result = mask_pii_in_response(result)
            except Exception:
                pass

            if monitor.should_stop():
                monitor.error("Kullanıcı tarafından durduruldu")
            else:
                monitor.complete(result[:80] if result else "")
                # Emit final_report with retry/backoff and idempotency
                if result:
                    final_report_event = {
                        "type": "live_event",
                        "event_type": "final_report",
                        "agent": "orchestrator",
                        "content": result[:20000],
                        "extra": {},
                        "timestamp": time.time(),
                    }
                    final_report_event.update(
                        monitor.envelope(
                            event="live.final_report",
                            phase="complete",
                            payload={
                                "agent": "orchestrator",
                                "content_preview": result[:500],
                            },
                        )
                    )
                    final_report_event_id = _build_ws_delivery_event_id(
                        monitor._run_id,
                        "final_report",
                    )
                    final_report_event["event_id"] = final_report_event_id
                    ws.state.live_events.append(final_report_event)
                    final_report_sent = await _safe_ws_send(
                        final_report_event,
                        event_context={
                            "event": "live.final_report",
                            "type": "live_event",
                            "thread_id": thread.id,
                            "run_id": monitor._run_id,
                        },
                        retry_attempts=3,
                        retry_backoff_seconds=0.2,
                        idempotency_key=final_report_event_id,
                    )
                    if not final_report_sent:
                        logger.error(
                            "run.final_report.delivery_failed",
                            extra={
                                "event": "run.final_report.delivery_failed",
                                "thread_id": thread.id,
                                "run_id": monitor._run_id,
                                "idempotency_key": final_report_event_id,
                            },
                        )
                    _log_run_telemetry(
                        event="run.final_report",
                        phase="complete",
                        monitor=monitor,
                        correlation_id=correlation_id,
                        effective_user_id=effective_user_id,
                        thread=thread,
                        started_at=started_at,
                        status=(
                            "final_report_delivered"
                            if final_report_sent
                            else "final_report_delivery_failed"
                        ),
                        pipeline_type=_resolve_pipeline_type(thread, pipeline_str),
                        agent="orchestrator",
                    )
                else:
                    _log_run_telemetry(
                        event="run.final_report",
                        phase="complete",
                        monitor=monitor,
                        correlation_id=correlation_id,
                        effective_user_id=effective_user_id,
                        thread=thread,
                        started_at=started_at,
                        status="final_report_skipped_empty_result",
                        pipeline_type=_resolve_pipeline_type(thread, pipeline_str),
                        agent="orchestrator",
                    )

            result_sent = await _safe_ws_send(
                {
                    "type": "result",
                    "thread_id": thread.id,
                    "result": result,
                    "thread": thread.model_dump(mode="json"),
                    **monitor.envelope(
                        event="run.result",
                        phase="complete",
                        payload={"thread_id": thread.id, "has_result": bool(result)},
                    ),
                }
            )
            _log_run_telemetry(
                event="run.result",
                phase="complete",
                monitor=monitor,
                correlation_id=correlation_id,
                effective_user_id=effective_user_id,
                thread=thread,
                started_at=started_at,
                status="completed" if result_sent else "result_delivery_failed",
                pipeline_type=_resolve_pipeline_type(thread, pipeline_str),
                agent="orchestrator",
            )

            # Auto-trigger post-task retrospective meeting
            try:
                task_agents = list(
                    set(
                        e.agent_role
                        for t in thread.tasks
                        for e in thread.events
                        if e.agent_role
                        and e.event_type in ("agent_start", "agent_response")
                    )
                )
                if not task_agents:
                    task_agents = ["orchestrator", "thinker"]
                total_tok = sum((t.total_tokens or 0) for t in thread.tasks)
                total_lat = sum(t.total_latency_ms for t in thread.tasks)
                last_task = thread.tasks[-1] if thread.tasks else None
                summary = last_task.user_input[:120] if last_task else message[:120]
                status = last_task.status if last_task else "completed"
                meeting = _generate_post_task_meeting(
                    task_summary=summary,
                    participating_agents=task_agents,
                    task_status=status,
                    task_duration_ms=total_lat,
                    total_tokens=total_tok,
                )
                post_task_event_id = _build_ws_delivery_event_id(
                    monitor._run_id,
                    "post_task_meeting",
                )
                post_task_sent = await _safe_ws_send(
                    {
                        "type": "post_task_meeting",
                        "meeting": meeting,
                        "event_id": post_task_event_id,
                        **monitor.envelope(
                            event="run.post_task_meeting",
                            phase="complete",
                            payload={
                                "thread_id": thread.id,
                                "participating_agents": task_agents,
                            },
                        ),
                    },
                    event_context={
                        "event": "run.post_task_meeting",
                        "type": "post_task_meeting",
                        "thread_id": thread.id,
                        "run_id": monitor._run_id,
                    },
                    retry_attempts=3,
                    retry_backoff_seconds=0.2,
                    idempotency_key=post_task_event_id,
                )
                if not post_task_sent:
                    logger.error(
                        "run.post_task_meeting.delivery_failed",
                        extra={
                            "event": "run.post_task_meeting.delivery_failed",
                            "thread_id": thread.id,
                            "run_id": monitor._run_id,
                            "idempotency_key": post_task_event_id,
                        },
                    )
                _log_run_telemetry(
                    event="run.post_task_meeting",
                    phase="complete",
                    monitor=monitor,
                    correlation_id=correlation_id,
                    effective_user_id=effective_user_id,
                    thread=thread,
                    started_at=started_at,
                    status=(
                        "post_task_meeting_delivered"
                        if post_task_sent
                        else "post_task_meeting_delivery_failed"
                    ),
                    pipeline_type=_resolve_pipeline_type(thread, pipeline_str),
                    agent="orchestrator",
                )
            except Exception as exc:
                logger.warning(
                    "run.post_task_meeting.generation_failed",
                    extra={
                        "event": "run.post_task_meeting.generation_failed",
                        "thread_id": thread.id,
                        "run_id": monitor._run_id,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                    exc_info=True,
                )
                _log_run_telemetry(
                    event="run.post_task_meeting",
                    phase="error",
                    monitor=monitor,
                    correlation_id=correlation_id,
                    effective_user_id=effective_user_id,
                    thread=thread,
                    started_at=started_at,
                    status="post_task_meeting_generation_failed",
                    pipeline_type=_resolve_pipeline_type(thread, pipeline_str),
                    agent="orchestrator",
                    error=f"{type(exc).__name__}: {exc}",
                )
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            monitor.error(err)
            await _safe_ws_send(
                {
                    "type": "error",
                    "message": err,
                    "traceback": traceback.format_exc(),
                    "thread_id": thread.id,
                    **monitor.envelope(
                        event="run.error",
                        phase="error",
                        payload={"thread_id": thread.id, "message": err},
                    ),
                }
            )
            _log_run_telemetry(
                event="run.error",
                phase="error",
                monitor=monitor,
                correlation_id=correlation_id,
                effective_user_id=effective_user_id,
                thread=thread,
                started_at=started_at,
                status="failed",
                pipeline_type=_resolve_pipeline_type(thread, pipeline_str),
                agent="orchestrator",
                error=err,
            )
        finally:
            ws.state.run_task = None

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)

            msg_type = data.get("type", "chat")

            if user_id is None and "token" in data:
                token = (data.get("token") or "").strip()
                user = _get_user_from_token(token) if token else None
                if user:
                    user_id = user["user_id"]
                else:
                    await ws.close(code=4001)
                    return

            if msg_type == "chat" and user_id is None:
                await ws.close(code=4001)
                return

            if msg_type == "stop":
                monitor_obj = getattr(ws.state, "monitor", None)
                if monitor_obj:
                    monitor_obj.request_stop()
                continue

            if msg_type == "ping":
                await _safe_ws_send({"type": "pong"})
                continue

            # ── Retry via WebSocket (live monitoring support) ──
            if msg_type == "retry":
                retry_thread_id = data.get("thread_id", "")
                retry_task_id = data.get("task_id", "")
                if not retry_thread_id or not retry_task_id:
                    await _safe_ws_send({"type": "error", "message": "retry requires thread_id and task_id"})
                    continue

                active_task = getattr(ws.state, "run_task", None)
                if active_task is not None and not active_task.done():
                    await _safe_ws_send({"type": "error", "message": "Bir görev zaten çalışıyor."})
                    continue

                retry_thread = load_thread(retry_thread_id, user_id=user_id or None)
                if not retry_thread:
                    await _safe_ws_send({"type": "error", "message": "Thread not found"})
                    continue

                # Find the target task
                target_task = None
                for t in retry_thread.tasks:
                    if t.id == retry_task_id:
                        target_task = t
                        break

                if not target_task:
                    await _safe_ws_send({"type": "error", "message": "Task not found"})
                    continue

                from core.models import TaskStatus as _TS
                if target_task.status not in (
                    _TS.COMPLETED, _TS.FAILED, _TS.STOPPED,
                    "completed", "failed", "stopped", "error",
                ):
                    await _safe_ws_send({"type": "error", "message": f"Task status '{target_task.status}' is not retryable"})
                    continue

                original_input = target_task.user_input
                retry_pipeline_str = (
                    target_task.pipeline_type.value
                    if hasattr(target_task.pipeline_type, "value")
                    else str(target_task.pipeline_type)
                )

                ws.state.live_events = []
                monitor = WSLiveMonitor(ws, ws.state.live_events)
                ws.state.monitor = monitor
                correlation_id = data.get("correlation_id") or monitor._run_id
                started_at = time.time()
                monitor.start(f"[Retry] {original_input[:100]}")

                ws.state.run_task = asyncio.create_task(
                    _execute_run(
                        original_input,
                        retry_thread,
                        monitor,
                        retry_pipeline_str,
                        user_id,
                        correlation_id,
                        started_at,
                    ),
                )
                continue

            if msg_type == "orchestrator_chat":
                user_msg = (data.get("message") or "").strip()
                run_task = getattr(ws.state, "run_task", None)
                events = getattr(ws.state, "live_events", [])
                if run_task and not run_task.done():
                    # Faz 14.6: Steering — inject user message into running agent's queue
                    monitor_obj = getattr(ws.state, "monitor", None)
                    if user_msg and monitor_obj and hasattr(monitor_obj, '_steering_queue'):
                        # Status queries don't get injected as steering
                        is_status_query = user_msg.lower() in (
                            "durum", "status", "nerede", "ne oldu", "?",
                        )
                        if not is_status_query:
                            monitor_obj._steering_queue.push(user_msg)

                    step_count = len(events)
                    last_agents = list(
                        dict.fromkeys(
                            e.get("agent", "") for e in events[-20:] if e.get("agent")
                        )
                    )
                    status_lines = [
                        f"Görev devam ediyor. Toplam {step_count} adım.",
                        f"Son etkileşimler: {', '.join(last_agents[-5:]) or '—'}.",
                    ]
                    is_status_query = user_msg.lower() in (
                        "durum", "status", "nerede", "ne oldu", "?",
                    )
                    if is_status_query:
                        reply = "\n".join(status_lines)
                    else:
                        reply = (
                            "\n".join(status_lines)
                            + "\n\n✅ Talimatınız agent'a iletildi — bir sonraki adımda dikkate alınacak."
                        )
                    await _safe_ws_send(
                        {
                            "type": "orchestrator_chat_reply",
                            "content": reply,
                            "is_status": is_status_query,
                            "schema_version": RUNTIME_EVENT_SCHEMA_VERSION,
                            "event": "steering.reply",
                            "phase": "progress",
                            "run_id": getattr(monitor_obj, "_run_id", None),
                            "sequence": getattr(monitor_obj, "_sequence", 0) + 1,
                            "ts": time.time(),
                        }
                    )
                else:
                    await _safe_ws_send(
                        {
                            "type": "orchestrator_chat_reply",
                            "content": "Şu an aktif görev yok. Yeni görev için ana alandan mesaj gönderin.",
                            "is_status": False,
                        }
                    )
                continue

            message = data.get("message", "")
            thread_id = data.get("thread_id")
            pipeline_str = data.get("pipeline_type", "auto")
            effective_user_id = user_id or data.get("user_id", "") or None

            if effective_user_id and not _rate_limiter.is_allowed(
                f"ws:{effective_user_id}"
            ):
                await _safe_ws_send(
                    {
                        "type": "error",
                        "message": "İstek limiti aşıldı. Lütfen biraz bekleyin.",
                    }
                )
                continue

            if not message:
                await _safe_ws_send({"type": "error", "message": "Empty message"})
                continue

            active_task = getattr(ws.state, "run_task", None)
            if active_task is not None and not active_task.done():
                await _safe_ws_send(
                    {
                        "type": "error",
                        "message": "Bir görev zaten çalışıyor. Durdurmak için Durdur'a basın veya Orkestratör sohbetinden durum sorun.",
                    }
                )
                continue

            thread = (
                load_thread(thread_id, user_id=user_id or None) if thread_id else None
            )
            if not thread:
                thread = Thread()

            ws.state.live_events = []
            monitor = WSLiveMonitor(ws, ws.state.live_events)
            ws.state.monitor = monitor
            correlation_id = data.get("correlation_id") or monitor._run_id
            started_at = time.time()
            monitor.start(message)
            _log_run_telemetry(
                event="run.start",
                phase="start",
                monitor=monitor,
                correlation_id=correlation_id,
                effective_user_id=effective_user_id,
                thread=thread,
                started_at=started_at,
                status="started",
                pipeline_type=_resolve_pipeline_type(thread, pipeline_str),
                agent="orchestrator",
            )

            ws.state.run_task = asyncio.create_task(
                _execute_run(
                    message,
                    thread,
                    monitor,
                    pipeline_str,
                    effective_user_id,
                    correlation_id,
                    started_at,
                ),
            )

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        # Do not cancel active run on client disconnect.
        # Otherwise long pipelines can be interrupted mid-flight and never reach
        # a terminal task state (completed/failed/stopped).
        run_task = getattr(ws.state, "run_task", None)
        if run_task and not run_task.done():
            logger.info(
                "ws.chat.disconnected_run_continues",
                extra={
                    "event": "ws.chat.disconnected_run_continues",
                    "run_task": str(run_task),
                },
            )
        monitor_obj = getattr(ws.state, "monitor", None)
        if monitor_obj:
            await monitor_obj.close()


@router.websocket("/api/ws/chat")
async def ws_chat_api_alias(ws: WebSocket):
    """Alias route for deployments where only /api/* is routed to backend."""
    await ws_chat(ws)


@router.post("/api/stream")
async def stream_chat(request: Request):
    """SSE endpoint for granular LLM streaming.

    Accepts JSON body: {"message": str, "thread_id": str | None, "pipeline_type": str}
    Requires Authorization: Bearer <token> header.
    Returns text/event-stream with SSE events.
    """
    # Auth check
    auth_header = request.headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""
    if not token:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Missing authorization token"}, status_code=401)

    user = _get_user_from_token(token)
    if not user:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Invalid token"}, status_code=401)

    user_id = user["user_id"]

    # Rate limit
    if not _rate_limiter.is_allowed(f"sse:{user_id}"):
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)

    body = await request.json()
    message = (body.get("message") or "").strip()
    thread_id = body.get("thread_id")
    pipeline_str = body.get("pipeline_type", "auto")

    if not message:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Empty message"}, status_code=400)

    async def _sse_generator():
        """Async generator that yields SSE-formatted events."""
        try:
            from agents.orchestrator import OrchestratorAgent

            thread = load_thread(thread_id, user_id=user_id) if thread_id else None
            if not thread:
                thread = Thread()

            orchestrator = OrchestratorAgent()
            forced_pipe = None
            if pipeline_str != "auto":
                try:
                    forced_pipe = PipelineType(pipeline_str)
                except ValueError:
                    pass

            # Build context and stream from orchestrator's LLM
            messages = await orchestrator.build_context(thread, message)
            tools = orchestrator.get_tools()

            async for event in orchestrator.call_llm_stream(messages, tools):
                sse_data = json.dumps(event, ensure_ascii=False)
                if "schema_version" not in event:
                    event["schema_version"] = RUNTIME_EVENT_SCHEMA_VERSION
                    event["event"] = f"stream.{event.get('type', 'unknown')}"
                    event["phase"] = "stream"
                    event["ts"] = time.time()
                sse_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {sse_data}\n\n"

                # On done event, save thread and send final result
                if event.get("type") == "done":
                    # Save the result to thread
                    content = event.get("content", "")
                    if content:
                        from core.models import EventType
                        thread.add_event(
                            EventType.AGENT_RESPONSE,
                            content,
                            agent_role=orchestrator.role,
                        )
                    save_thread(thread, user_id=user_id)

                    # Yield thread info as final SSE event
                    final_event = json.dumps({
                        "type": "stream_end",
                        "thread_id": thread.id,
                        "schema_version": RUNTIME_EVENT_SCHEMA_VERSION,
                        "event": "stream.end",
                        "phase": "complete",
                        "ts": time.time(),
                    }, ensure_ascii=False)
                    yield f"data: {final_event}\n\n"

        except Exception as e:
            error_event = json.dumps({
                "type": "error",
                "message": f"{type(e).__name__}: {e}",
                "agent": "orchestrator",
                "schema_version": RUNTIME_EVENT_SCHEMA_VERSION,
                "event": "stream.error",
                "phase": "error",
                "ts": time.time(),
            }, ensure_ascii=False)
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Task Retry Endpoint ──────────────────────────────────────────

@router.post("/api/threads/{thread_id}/tasks/{task_id}/retry")
async def retry_task(thread_id: str, task_id: str, request: Request):
    """Re-execute a completed or failed task on the same thread."""
    from fastapi.responses import JSONResponse
    from core.models import EventType, TaskStatus as TS

    try:
        auth_header = request.headers.get("authorization", "")
        token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""
        if not token:
            return JSONResponse({"error": "Missing authorization token"}, status_code=401)

        user = _get_user_from_token(token)
        if not user:
            return JSONResponse({"error": "Invalid token"}, status_code=401)

        user_id = user["user_id"]

        thread = load_thread(thread_id, user_id=user_id)
        if not thread:
            return JSONResponse({"error": "Thread not found"}, status_code=404)

        # Find the task
        target_task = None
        for t in thread.tasks:
            if t.id == task_id:
                target_task = t
                break

        if not target_task:
            return JSONResponse({"error": "Task not found"}, status_code=404)

        if target_task.status not in (
            TS.COMPLETED, TS.FAILED, TS.STOPPED,
            "completed", "failed", "stopped", "error",
        ):
            return JSONResponse(
                {"error": f"Task status '{target_task.status}' is not retryable"},
                status_code=400,
            )

        original_input = target_task.user_input
        pipeline_str = (
            target_task.pipeline_type.value
            if hasattr(target_task.pipeline_type, "value")
            else str(target_task.pipeline_type)
        )

        # Create a background execution
        async def _run_retry():
            try:
                from agents.orchestrator import OrchestratorAgent

                orchestrator = OrchestratorAgent()
                forced_pipe = None
                if pipeline_str != "auto":
                    try:
                        forced_pipe = PipelineType(pipeline_str)
                    except ValueError:
                        pass

                result = await orchestrator.route_and_execute(
                    original_input,
                    thread,
                    forced_pipeline=forced_pipe,
                    user_id=user_id,
                )
                save_thread(thread, user_id=user_id)
            except Exception as exc:
                logger.error("retry_task.failed", extra={
                    "thread_id": thread_id,
                    "task_id": task_id,
                    "error": str(exc),
                })

        asyncio.create_task(_run_retry())

        new_task_id = thread.tasks[-1].id if thread.tasks else task_id
        return JSONResponse({
            "status": "retry_started",
            "thread_id": thread_id,
            "new_task_id": new_task_id,
        })

    except Exception as exc:
        logger.error("retry_task.unhandled", extra={
            "thread_id": thread_id,
            "task_id": task_id,
            "error": str(exc),
        })
        return JSONResponse(
            {"error": "Internal server error during retry"},
            status_code=500,
        )


@router.get("/api/threads/{thread_id}/tasks/{task_id}/checkpoints")
async def get_task_checkpoints(thread_id: str, task_id: str, request: Request):
    """Return checkpoints for a specific task."""
    from fastapi.responses import JSONResponse

    auth_header = request.headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""
    if not token:
        return JSONResponse({"error": "Missing authorization token"}, status_code=401)

    user = _get_user_from_token(token)
    if not user:
        return JSONResponse({"error": "Invalid token"}, status_code=401)

    thread = load_thread(thread_id, user_id=user["user_id"])
    if not thread:
        return JSONResponse({"error": "Thread not found"}, status_code=404)

    for t in thread.tasks:
        if t.id == task_id:
            checkpoints = [cp.model_dump(mode="json") for cp in getattr(t, "checkpoints", [])]
            return JSONResponse({"checkpoints": checkpoints})

    return JSONResponse({"error": "Task not found"}, status_code=404)
