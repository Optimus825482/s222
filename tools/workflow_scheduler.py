"""
Workflow Scheduler — APScheduler + PostgreSQL ile cron tabanlı workflow zamanlama.

Her schedule bir cron expression ile tanımlanır ve tetiklendiğinde
workflow_engine.execute_workflow() çağrılır.
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)

# Module-level scheduler instance
_scheduler: AsyncIOScheduler | None = None


# ── Job execution callback ───────────────────────────────────────

async def _run_scheduled_workflow(schedule_id: str) -> None:
    """Scheduler tarafından tetiklenen job — workflow'u ayrı thread'de çalıştırır."""
    logger.info("[Scheduler] Firing schedule '%s'", schedule_id)

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM schedules WHERE id = %s", (schedule_id,))
        row = cur.fetchone()
        if not row:
            logger.warning("[Scheduler] Schedule '%s' not found, skipping", schedule_id)
            return
        if not row["enabled"]:
            logger.info("[Scheduler] Schedule '%s' disabled, skipping", schedule_id)
            return

        template_name = row["template"]
        variables = json.loads(row["variables"])
    finally:
        release_conn(conn)

    try:
        from tools.workflow_engine import get_template, execute_workflow
        from core.models import Thread as ThreadModel

        workflow = get_template(template_name, variables)
        thread = ThreadModel()

        result = await execute_workflow(workflow, thread)

        status = result.status
        logger.info(
            "[Scheduler] Schedule '%s' completed — status=%s, duration=%dms",
            schedule_id, status, result.duration_ms,
        )
    except Exception as e:
        status = f"error: {e}"
        logger.error("[Scheduler] Schedule '%s' failed: %s", schedule_id, e, exc_info=True)

    # last_run ve status güncelle
    conn = get_conn()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()
        cur.execute(
            "UPDATE schedules SET last_run = %s, last_status = %s WHERE id = %s",
            (now, status, schedule_id),
        )
        conn.commit()
    finally:
        release_conn(conn)


# ── Scheduler lifecycle ──────────────────────────────────────────

def _add_job_to_scheduler(schedule_id: str, cron_expr: str) -> None:
    """APScheduler'a cron job ekle."""
    global _scheduler
    if _scheduler is None:
        return
    try:
        trigger = CronTrigger.from_crontab(cron_expr)
        _scheduler.add_job(
            _run_scheduled_workflow,
            trigger=trigger,
            args=[schedule_id],
            id=schedule_id,
            replace_existing=True,
            misfire_grace_time=60,
        )
    except Exception as e:
        logger.error("[Scheduler] Failed to add job '%s': %s", schedule_id, e)


def _remove_job_from_scheduler(schedule_id: str) -> None:
    """APScheduler'dan job kaldır."""
    global _scheduler
    if _scheduler is None:
        return
    try:
        _scheduler.remove_job(schedule_id)
    except Exception:
        pass  # job zaten yoksa sorun değil


async def init_scheduler() -> None:
    """Scheduler'ı başlat ve DB'deki aktif schedule'ları yükle."""
    global _scheduler

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.start()
    logger.info("[Scheduler] APScheduler started")

    # DB'deki enabled schedule'ları yükle
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, cron_expr FROM schedules WHERE enabled = TRUE")
        rows = cur.fetchall()
        for row in rows:
            _add_job_to_scheduler(row["id"], row["cron_expr"])
        logger.info("[Scheduler] Loaded %d active schedule(s)", len(rows))
    finally:
        release_conn(conn)


# ── CRUD operations ──────────────────────────────────────────────

def add_schedule(
    schedule_id: str | None,
    template: str,
    cron_expr: str,
    variables: dict[str, Any] | None = None,
) -> dict:
    """Yeni schedule oluştur ve scheduler'a ekle."""
    # Cron expression'ı validate et
    try:
        CronTrigger.from_crontab(cron_expr)
    except Exception as e:
        raise ValueError(f"Invalid cron expression '{cron_expr}': {e}")

    # Template'in var olduğunu kontrol et
    from tools.workflow_engine import WORKFLOW_TEMPLATES
    if template not in WORKFLOW_TEMPLATES:
        available = ", ".join(WORKFLOW_TEMPLATES.keys())
        raise ValueError(f"Unknown template '{template}'. Available: {available}")

    sid = schedule_id or f"sched-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    vars_json = json.dumps(variables or {}, ensure_ascii=False)

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO schedules (id, template, cron_expr, variables, enabled, created_at)
               VALUES (%s, %s, %s, %s, TRUE, %s)""",
            (sid, template, cron_expr, vars_json, now),
        )
        conn.commit()
    finally:
        release_conn(conn)

    _add_job_to_scheduler(sid, cron_expr)
    logger.info("[Scheduler] Added schedule '%s' — template=%s, cron=%s", sid, template, cron_expr)

    return get_schedule(sid)


def remove_schedule(schedule_id: str) -> bool:
    """Schedule'ı sil."""
    _remove_job_from_scheduler(schedule_id)

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM schedules WHERE id = %s", (schedule_id,))
        conn.commit()
        deleted = cur.rowcount > 0
    finally:
        release_conn(conn)

    if deleted:
        logger.info("[Scheduler] Removed schedule '%s'", schedule_id)
    return deleted


def toggle_schedule(schedule_id: str, enabled: bool | None = None) -> dict:
    """Schedule'ı aç/kapat. enabled=None ise toggle yapar."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM schedules WHERE id = %s", (schedule_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Schedule '{schedule_id}' not found")

        new_enabled = (not row["enabled"]) if enabled is None else enabled

        cur.execute(
            "UPDATE schedules SET enabled = %s WHERE id = %s",
            (new_enabled, schedule_id),
        )
        conn.commit()
    finally:
        release_conn(conn)

    if new_enabled:
        _add_job_to_scheduler(schedule_id, row["cron_expr"])
    else:
        _remove_job_from_scheduler(schedule_id)

    logger.info("[Scheduler] Schedule '%s' %s", schedule_id, "enabled" if new_enabled else "disabled")
    return get_schedule(schedule_id)


def list_schedules() -> list[dict]:
    """Tüm schedule'ları listele."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM schedules ORDER BY created_at DESC")
        rows = cur.fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        release_conn(conn)


def get_schedule(schedule_id: str) -> dict:
    """Tek bir schedule getir."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM schedules WHERE id = %s", (schedule_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Schedule '{schedule_id}' not found")
        return _row_to_dict(row)
    finally:
        release_conn(conn)


def _row_to_dict(row: dict) -> dict:
    """PG Row (dict) → dict dönüşümü, next_run'ı scheduler'dan al."""
    global _scheduler
    d = dict(row)
    d["variables"] = json.loads(d["variables"])
    d["enabled"] = bool(d["enabled"])

    # APScheduler'dan next_run bilgisini al
    if _scheduler and d["enabled"]:
        try:
            job = _scheduler.get_job(d["id"])
            if job and job.next_run_time:
                d["next_run"] = job.next_run_time.isoformat()
        except Exception:
            pass

    return d
