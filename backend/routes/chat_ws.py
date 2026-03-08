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

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import _get_user_from_token
from config import MODELS
from core.models import Thread, PipelineType
from core.state import save_thread, load_thread
from shared_state import _AGENT_ROLES, _utcnow

router = APIRouter()
logger = logging.getLogger(__name__)


class WSLiveMonitor:
    """WebSocket-based live monitor replacing Streamlit's LiveMonitor."""

    def __init__(self, ws: WebSocket, events_list: list | None = None):
        self.ws = ws
        self._stop = False
        self._events_list = events_list or []
        self._pending_tasks: set[asyncio.Task] = set()

    def should_stop(self) -> bool:
        return self._stop

    def request_stop(self):
        self._stop = True

    async def _send(self, data: dict):
        await self.ws.send_json(data)

    def _track_task(self, coroutine: Union[asyncio.Future, Coroutine[Any, Any, Any]]) -> None:
        task = asyncio.create_task(coroutine, name="ws-send")
        self._pending_tasks.add(task)

        def _on_done(done_task: asyncio.Task) -> None:
            self._pending_tasks.discard(done_task)
            try:
                done_task.result()
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.error("WSLiveMonitor background send failed: %s", exc, exc_info=True)

        task.add_done_callback(_on_done)

    def start(self, task_description: str):
        self._track_task(
            self._send(
                {
                    "type": "monitor_start",
                    "description": task_description,
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
        self._events_list.append(payload)
        self._track_task(self._send(payload))

    def complete(self, summary: str = ""):
        self._track_task(
            self._send(
                {
                    "type": "monitor_complete",
                    "summary": summary,
                }
            )
        )

    def error(self, message: str):
        self._track_task(
            self._send(
                {
                    "type": "monitor_error",
                    "message": message,
                }
            )
        )


# Import _generate_post_task_meeting from messaging module
try:
    from routes.messaging import _generate_post_task_meeting
except ImportError:

    def _generate_post_task_meeting(**kwargs):
        return {}


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

    async def _safe_ws_send(data: dict):
        try:
            await ws.send_json(data)
        except Exception:
            pass

    async def _execute_run(
        message: str,
        thread: Thread,
        monitor: WSLiveMonitor,
        pipeline_str: str,
        effective_user_id: str | None,
    ):
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

            await _safe_ws_send(
                {
                    "type": "result",
                    "thread_id": thread.id,
                    "result": result,
                    "thread": thread.model_dump(mode="json"),
                }
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
                total_tok = sum(t.total_tokens for t in thread.tasks)
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
                await _safe_ws_send(
                    {
                        "type": "post_task_meeting",
                        "meeting": meeting,
                    }
                )
            except Exception:
                pass
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            monitor.error(err)
            await _safe_ws_send(
                {
                    "type": "error",
                    "message": err,
                    "traceback": traceback.format_exc(),
                    "thread_id": thread.id,
                }
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

            if msg_type == "orchestrator_chat":
                user_msg = (data.get("message") or "").strip()
                run_task = getattr(ws.state, "run_task", None)
                events = getattr(ws.state, "live_events", [])
                if run_task and not run_task.done():
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
                    if user_msg.lower() in (
                        "durum",
                        "status",
                        "nerede",
                        "ne oldu",
                        "?",
                    ):
                        reply = "\n".join(status_lines)
                    else:
                        reply = (
                            "\n".join(status_lines)
                            + "\n\nEk talimatınız kaydedildi; mevcut görev bittikten sonra yeni bir mesaj olarak gönderebilirsiniz."
                        )
                    await _safe_ws_send(
                        {
                            "type": "orchestrator_chat_reply",
                            "content": reply,
                            "is_status": True,
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
            monitor.start(message)

            ws.state.run_task = asyncio.create_task(
                _execute_run(message, thread, monitor, pipeline_str, effective_user_id),
            )

    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@router.websocket("/api/ws/chat")
async def ws_chat_api_alias(ws: WebSocket):
    """Alias route for deployments where only /api/* is routed to backend."""
    await ws_chat(ws)
