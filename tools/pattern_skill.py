"""
Gelişmiş pattern detection — 3+ tekrar → otomatik skill çıkarma (Faz 11.3).
Thread event'lerinden araç sıralarını çıkarır, tekrarlayan kalıpları tespit eder,
skill_hygiene ve dynamic_skills ile uyumlu otomatik skill oluşturur.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
_PG_TABLE_INITIALIZED = False

DATA_DIR = Path(__file__).parent.parent / "data"
PATTERN_STORE = DATA_DIR / "pattern_executions.json"
_MAX_RECORDS = 200
_MIN_OCCURRENCES = 5  # Increased from 3 - patterns must repeat more to become skills


def _ensure_pg_table() -> None:
    """Ensure pattern_executions table exists in PostgreSQL."""
    global _PG_TABLE_INITIALIZED
    if _PG_TABLE_INITIALIZED:
        return
    try:
        from tools.pg_connection import get_conn, release_conn
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS pattern_executions (
                        id SERIAL PRIMARY KEY,
                        thread_id VARCHAR(128),
                        signature VARCHAR(24) NOT NULL,
                        tools_used JSONB NOT NULL,
                        user_input_snippet TEXT DEFAULT '',
                        status VARCHAR(32) DEFAULT 'completed',
                        user_id VARCHAR(128) DEFAULT '',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_pe_signature ON pattern_executions(signature)")
            conn.commit()
            _PG_TABLE_INITIALIZED = True
        finally:
            release_conn(conn)
    except Exception as e:
        logger.warning(f"pattern_executions table init failed: {e}")


def _cleanup_old_records() -> None:
    """Keep only the last _MAX_RECORDS entries."""
    try:
        from tools.pg_connection import get_conn, release_conn
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """DELETE FROM pattern_executions
                       WHERE id NOT IN (
                           SELECT id FROM pattern_executions
                           ORDER BY created_at DESC LIMIT %s
                       )""",
                    (_MAX_RECORDS,),
                )
            conn.commit()
        finally:
            release_conn(conn)
    except Exception:
        pass


def _load_json_store() -> list[dict]:
    """Load execution records from JSON file (fallback)."""
    if not PATTERN_STORE.exists():
        return []
    try:
        data = json.loads(PATTERN_STORE.read_text(encoding="utf-8"))
        return data.get("executions", [])
    except (json.JSONDecodeError, TypeError):
        return []


def _save_json_store(executions: list[dict]) -> None:
    """Persist execution records to JSON (fallback)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PATTERN_STORE.write_text(
        json.dumps({"executions": executions[-_MAX_RECORDS:]}, ensure_ascii=False, indent=0),
        encoding="utf-8",
    )


def _tool_sequence_from_thread(thread: Any) -> list[str]:
    """Extract ordered list of tool names from thread events (TOOL_CALL)."""
    tools: list[str] = []
    for ev in getattr(thread, "events", []) or []:
        et = getattr(ev, "event_type", None) or ev.get("event_type") if isinstance(ev, dict) else None
        if et != "tool_call" and str(et) != "tool_call":
            continue
        content = getattr(ev, "content", None) or (ev.get("content", "") if isinstance(ev, dict) else "")
        if not content or "(" not in content:
            continue
        name = content.split("(")[0].strip()
        if name and name not in ("decompose_task", "direct_response", "synthesize_results"):
            tools.append(name)
    return tools


def _user_input_snippet(thread: Any) -> str:
    """First user message or first task input, truncated."""
    for ev in getattr(thread, "events", []) or []:
        et = getattr(ev, "event_type", None) or (ev.get("event_type") if isinstance(ev, dict) else None)
        if et == "user_message" or str(et) == "user_message":
            c = getattr(ev, "content", None) or (ev.get("content", "") if isinstance(ev, dict) else "")
            return (c or "")[:150].strip()
    tasks = getattr(thread, "tasks", []) or []
    if tasks:
        t = tasks[0]
        ui = getattr(t, "user_input", None) or (t.get("user_input", "") if isinstance(t, dict) else "")
        return (ui or "")[:150].strip()
    return ""


def _thread_status(thread: Any) -> str:
    """Overall thread/task status."""
    tasks = getattr(thread, "tasks", []) or []
    if not tasks:
        return "completed"
    last = tasks[-1]
    st = getattr(last, "status", None) or (last.get("status", "") if isinstance(last, dict) else "")
    return st or "completed"


def observe_thread(thread: Any, user_id: str | None = None) -> dict[str, Any] | None:
    """
    Record one thread execution for pattern detection.
    Call after save_thread (e.g. from chat_ws). Returns record if stored, else None.
    """
    tools = _tool_sequence_from_thread(thread)
    if not tools:
        return None
    signature = hashlib.md5(json.dumps(tools, sort_keys=True).encode()).hexdigest()[:12]
    snippet = _user_input_snippet(thread)
    status = _thread_status(thread)
    thread_id = getattr(thread, "id", None) or (thread.get("id") if isinstance(thread, dict) else "")
    record = {
        "thread_id": thread_id,
        "signature": signature,
        "tools_used": tools,
        "user_input_snippet": snippet,
        "status": status,
        "user_id": user_id or "",
    }

    _ensure_pg_table()
    try:
        from tools.pg_connection import get_conn, release_conn
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO pattern_executions (thread_id, signature, tools_used, user_input_snippet, status, user_id)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (thread_id, signature, json.dumps(tools), snippet[:500], status, user_id or ""),
                )
            conn.commit()
        finally:
            release_conn(conn)
        logger.debug("Pattern observed: signature=%s tools=%s", signature, tools)
        return record
    except Exception as e:
        logger.warning(f"observe_thread PG insert failed, falling back to JSON: {e}")
        # Fallback to JSON file
        executions = _load_json_store()
        executions.append(record)
        _save_json_store(executions)
        return record


def detect_patterns(min_occurrences: int = _MIN_OCCURRENCES) -> list[dict[str, Any]]:
    """
    Find repeating execution patterns (same tool sequence seen >= min_occurrences).
    Returns list of { signature, count, tools_used, examples }.
    """
    _ensure_pg_table()
    try:
        from tools.pg_connection import get_conn, release_conn
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT signature, COUNT(*) as cnt,
                              (array_agg(tools_used ORDER BY created_at DESC))[1] as tools_used
                       FROM pattern_executions
                       GROUP BY signature
                       HAVING COUNT(*) >= %s
                       ORDER BY cnt DESC""",
                    (min_occurrences,),
                )
                groups = cur.fetchall()

                out = []
                for g in groups:
                    gd = dict(g) if hasattr(g, 'keys') else {}
                    sig = gd.get("signature", "")
                    cnt = int(gd.get("cnt", 0))
                    tools_raw = gd.get("tools_used", [])
                    tools_used = json.loads(tools_raw) if isinstance(tools_raw, str) else (tools_raw or [])

                    # Get examples
                    cur.execute(
                        """SELECT user_input_snippet, status, thread_id
                           FROM pattern_executions
                           WHERE signature = %s
                           ORDER BY created_at DESC LIMIT 5""",
                        (sig,),
                    )
                    examples = [
                        {
                            "user_input_snippet": dict(r).get("user_input_snippet", ""),
                            "status": dict(r).get("status", ""),
                            "thread_id": dict(r).get("thread_id", ""),
                        }
                        for r in cur.fetchall()
                    ]
                    out.append({
                        "signature": sig,
                        "count": cnt,
                        "tools_used": tools_used,
                        "examples": examples,
                    })
            return out
        finally:
            release_conn(conn)
    except Exception as e:
        logger.warning(f"detect_patterns PG failed, falling back to JSON: {e}")
        # Fallback to JSON-based detection
        executions = _load_json_store()
        by_sig: dict[str, list[dict]] = defaultdict(list)
        for rec in executions:
            sig = rec.get("signature", "")
            if sig:
                by_sig[sig].append(rec)
        out = []
        for sig, group in by_sig.items():
            if len(group) < min_occurrences:
                continue
            tools_used = group[0].get("tools_used", [])
            examples = [
                {
                    "user_input_snippet": r.get("user_input_snippet", ""),
                    "status": r.get("status", ""),
                    "thread_id": r.get("thread_id", ""),
                }
                for r in group[:5]
            ]
            out.append({
                "signature": sig,
                "count": len(group),
                "tools_used": tools_used,
                "examples": examples,
            })
        out.sort(key=lambda x: -x["count"])
        return out


def generate_skill_from_pattern(
    signature: str,
    min_occurrences: int = _MIN_OCCURRENCES,
) -> dict[str, Any]:
    """
    Create an auto-learned skill from a detected pattern.
    Uses dynamic_skills.auto_create_skill_from_pattern. Skips if duplicate (same tools).
    Returns created skill info or error dict.
    """
    patterns = detect_patterns(min_occurrences=min_occurrences)
    match = next((p for p in patterns if p["signature"] == signature), None)
    if not match:
        return {"ok": False, "error": "pattern_not_found_or_below_threshold", "signature": signature}

    tools_used = match["tools_used"]
    examples = match.get("examples", [])
    snippet = examples[0].get("user_input_snippet", "") if examples else ""
    description = f"Tekrarlayan görev kalıbı: araç sırası {', '.join(tools_used)}. Örnek: {snippet[:80]}..." if snippet else f"Tekrarlayan araç sırası: {', '.join(tools_used)}"
    knowledge = (
        "## Ne zaman kullanılır\n"
        "Bu kalıp, benzer kullanıcı isteklerinde aynı araç sırasıyla yanıt verildiğinde tespit edildi.\n\n"
        "## Adımlar (araç sırası)\n"
        + "\n".join(f"{i+1}. {t}" for i, t in enumerate(tools_used))
        + "\n\n## Örnek kullanıcı girişleri\n"
        + "\n".join(f"- {ex.get('user_input_snippet', '')[:100]}" for ex in examples[:3])
    )

    try:
        from tools.dynamic_skills import auto_create_skill_from_pattern, list_skills
        existing = list_skills(active_only=False)
        for s in existing:
            desc = (s.get("description") or "").lower()
            if "tekrarlayan" in desc and all(t in desc for t in tools_used[:3]):
                return {"ok": False, "error": "duplicate_skill", "existing_id": s.get("id"), "signature": signature}
        result = auto_create_skill_from_pattern(
            pattern_description=description,
            knowledge=knowledge,
            category="learned",
            keywords=tools_used[:8],
        )
        return {"ok": True, "skill": result, "signature": signature, "count": match["count"]}
    except Exception as e:
        logger.exception("generate_skill_from_pattern failed")
        return {"ok": False, "error": str(e), "signature": signature}
