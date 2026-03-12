"""
Teachability — Agents learn from user corrections and preferences.
PostgreSQL backend. Same public API as SQLite version.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Mapping

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)

TEACHING_PATTERNS = re.compile(
    r"(böyle yapma|şöyle yap|bunu değiştir|her zaman|asla|unutma|"
    r"don'?t do|always|never|remember|instead of|yerine|"
    r"tercihim|prefer|benim için|for me|"
    r"bundan sonra|from now on|artık|"
    r"düzelt|correct|yanlış|wrong|hatalı)",
    re.IGNORECASE,
)


# ── Detection ────────────────────────────────────────────────────

def is_teaching_message(text: str) -> bool:
    """Detect if user message contains a teaching/correction."""
    return bool(TEACHING_PATTERNS.search(text))


# ── CRUD ─────────────────────────────────────────────────────────

def save_teaching(
    instruction: str,
    trigger_text: str = "",
    category: str = "preference",
    context: str | None = None,
) -> dict[str, Any]:
    """Save a user teaching/preference."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO teachings (category, trigger_text, instruction, context)
                   VALUES (%s, %s, %s, %s)
                   RETURNING id, created_at""",
                (category, trigger_text[:500], instruction[:2000], context),
            )
            row = cur.fetchone()
        conn.commit()
        row_dict = _as_row_dict(row)
        logger.info(f"Teaching saved: [{category}] {instruction[:60]}")
        return {
            "id": row_dict.get("id"),
            "instruction": instruction,
            "category": category,
            "created_at": str(row_dict.get("created_at")),
        }
    finally:
        release_conn(conn)


def get_relevant_teachings(
    query: str,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Find teachings relevant to current query via keyword matching."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            query_words = set(w for w in query.lower().split() if len(w) > 2)
            if not query_words:
                cur.execute(
                    """SELECT * FROM teachings WHERE active = TRUE
                       ORDER BY use_count DESC, created_at DESC LIMIT %s""",
                    (max_results,),
                )
                rows = cur.fetchall()
                return [_row_to_dict(_as_row_dict(r)) for r in rows]

            cur.execute(
                "SELECT * FROM teachings WHERE active = TRUE ORDER BY created_at DESC LIMIT 100"
            )
            rows = cur.fetchall()

        # Build query bigrams for phrase matching
        query_bigrams = set()
        qw_list = query.lower().split()
        for i in range(len(qw_list) - 1):
            query_bigrams.add(f"{qw_list[i]} {qw_list[i+1]}")

        scored = []
        for row in rows:
            d = _as_row_dict(row)
            instruction = str(d.get("instruction", "")).lower()
            trigger = str(d.get("trigger_text", "")).lower()
            text = instruction + " " + trigger
            text_words = set(w for w in text.split() if len(w) > 2)

            # Word overlap score
            overlap = query_words & text_words
            score = len(overlap) * 1.5

            # Bigram match bonus (phrase-level matching)
            for bg in query_bigrams:
                if bg in text:
                    score += 3.0

            # Partial substring match for compound words
            for qw in query_words:
                if any(qw in tw or tw in qw for tw in text_words if len(tw) > 3):
                    score += 0.5

            # Category boost: corrections > preferences
            cat = d.get("category", "")
            if cat == "correction":
                score *= 1.3
            elif cat == "rule":
                score *= 1.2

            # Usage popularity
            score += float(d.get("use_count", 0)) * 0.1

            # Recency boost (newer teachings slightly preferred)
            created = str(d.get("created_at", ""))
            if "2026" in created:
                score += 0.3
            elif "2025" in created:
                score += 0.1

            if score > 0:
                scored.append((score, d))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [_row_to_dict(d) for _, d in scored[:max_results]]

        if results:
            ids = [r["id"] for r in results]
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE teachings SET use_count = use_count + 1 WHERE id = ANY(%s)",
                    (ids,),
                )
            conn.commit()

        return results
    finally:
        release_conn(conn)


def get_all_teachings(active_only: bool = True) -> list[dict[str, Any]]:
    """List all teachings."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if active_only:
                cur.execute(
                    """SELECT * FROM teachings WHERE active = TRUE
                       ORDER BY use_count DESC, created_at DESC"""
                )
            else:
                cur.execute("SELECT * FROM teachings ORDER BY created_at DESC")
            return [_row_to_dict(_as_row_dict(r)) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def deactivate_teaching(teaching_id: int) -> bool:
    """Soft-delete a teaching."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE teachings SET active = FALSE, updated_at = now() WHERE id = %s",
                (teaching_id,),
            )
            updated = cur.rowcount > 0
        conn.commit()
        return updated
    finally:
        release_conn(conn)


def format_teachings_for_context(teachings: list[dict]) -> str:
    """Format teachings for injection into agent system prompt."""
    if not teachings:
        return ""
    lines = ["--- USER PREFERENCES & TEACHINGS ---"]
    for t in teachings:
        lines.append(f"• [{t['category']}] {t['instruction']}")
    lines.append("--- END TEACHINGS ---")
    return "\n".join(lines)


# ── Helper ───────────────────────────────────────────────────────

def _as_row_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    if isinstance(row, Mapping):
        return dict(row)
    return {}


def _row_to_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "category": row.get("category", "preference"),
        "trigger_text": row.get("trigger_text", ""),
        "instruction": row.get("instruction", ""),
        "use_count": row.get("use_count", 0),
        "active": bool(row.get("active", True)),
        "created_at": str(row.get("created_at", "")),
    }
