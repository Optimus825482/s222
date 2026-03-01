"""
Dynamic Skill Registry — PostgreSQL backend.
Same public API as SQLite version.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
SKILLS_DIR = DATA_DIR / "skills"


# ── Seed ─────────────────────────────────────────────────────────

def seed_builtin_skills() -> int:
    """Import hardcoded skills from skill_finder.py into DB (idempotent)."""
    from tools.skill_finder import SKILL_REGISTRY

    conn = get_conn()
    try:
        count = 0
        with conn.cursor() as cur:
            for skill in SKILL_REGISTRY:
                cur.execute(
                    """INSERT INTO skills
                       (id, name, category, description, keywords, knowledge, source)
                       VALUES (%s, %s, %s, %s, %s, %s, 'builtin')
                       ON CONFLICT (id) DO NOTHING""",
                    (
                        skill["id"],
                        skill["name"],
                        skill["category"],
                        skill["description"],
                        json.dumps(skill["keywords"]),
                        skill["knowledge"],
                    ),
                )
                count += cur.rowcount
        conn.commit()
        if count:
            logger.info(f"Seeded {count} builtin skills into dynamic registry")
        return count
    finally:
        release_conn(conn)


# ── CRUD ─────────────────────────────────────────────────────────

def create_skill(
    skill_id: str,
    name: str,
    description: str,
    knowledge: str,
    category: str = "custom",
    keywords: list[str] | None = None,
    source: str = "user",
) -> dict[str, Any]:
    """Create or replace a custom skill."""
    clean_id = skill_id.lower().replace(" ", "-").strip()
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO skills (id, name, category, description, keywords, knowledge, source)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET
                       name = EXCLUDED.name,
                       category = EXCLUDED.category,
                       description = EXCLUDED.description,
                       keywords = EXCLUDED.keywords,
                       knowledge = EXCLUDED.knowledge,
                       source = EXCLUDED.source,
                       updated_at = now()""",
                (clean_id, name, category, description,
                 json.dumps(keywords or []), knowledge, source),
            )
        conn.commit()
        logger.info(f"Skill created: [{clean_id}] {name}")
        return {"id": clean_id, "name": name, "category": category, "source": source}
    finally:
        release_conn(conn)


def update_skill(skill_id: str, **updates) -> bool:
    """Update skill fields."""
    allowed = {"name", "category", "description", "keywords", "knowledge", "active"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return False

    if "keywords" in fields and isinstance(fields["keywords"], list):
        fields["keywords"] = json.dumps(fields["keywords"])

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    set_clause += ", updated_at = now()"
    values = list(fields.values()) + [skill_id]

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE skills SET {set_clause} WHERE id = %s", values)
            updated = cur.rowcount > 0
        conn.commit()
        return updated
    finally:
        release_conn(conn)


def delete_skill(skill_id: str) -> bool:
    """Soft-delete a skill."""
    return update_skill(skill_id, active=False)


def get_skill(skill_id: str) -> dict[str, Any] | None:
    """Get a single skill by ID."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM skills WHERE id = %s AND active = TRUE", (skill_id,)
            )
            row = cur.fetchone()
        return _row_to_dict(dict(row)) if row else None
    finally:
        release_conn(conn)


def list_skills(
    category: str | None = None,
    source: str | None = None,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """List skills with optional filters."""
    conditions = ["1=1"]
    params: list[Any] = []

    if active_only:
        conditions.append("active = TRUE")
    if category:
        conditions.append("category = %s")
        params.append(category)
    if source:
        conditions.append("source = %s")
        params.append(source)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM skills WHERE {' AND '.join(conditions)} ORDER BY use_count DESC, name ASC",
                params,
            )
            return [_row_to_dict(dict(r)) for r in cur.fetchall()]
    finally:
        release_conn(conn)


def search_skills(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    """Search skills by keyword matching."""
    seed_builtin_skills()

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM skills WHERE active = TRUE")
            rows = cur.fetchall()
    finally:
        release_conn(conn)

    query_lower = query.lower()
    query_words = set(query_lower.split())

    scored: list[tuple[float, dict]] = []
    for row in rows:
        skill = _row_to_dict(dict(row))
        score = 0.0

        for kw in skill["keywords"]:
            kw_lower = kw.lower()
            if kw_lower in query_lower:
                score += 3.0
            elif any(w in kw_lower for w in query_words):
                score += 1.5

        if any(w in skill["name"].lower() for w in query_words):
            score += 2.0
        if any(w in skill["description"].lower() for w in query_words):
            score += 1.0
        score += skill["use_count"] * 0.05

        if score > 0:
            scored.append((score, skill))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [
        {
            "id": s["id"],
            "name": s["name"],
            "category": s["category"],
            "description": s["description"],
            "source": s["source"],
            "relevance_score": round(sc, 1),
        }
        for sc, s in scored[:max_results]
    ]

    if results:
        ids = [r["id"] for r in results]
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE skills SET use_count = use_count + 1 WHERE id = ANY(%s)",
                    (ids,),
                )
            conn.commit()
        finally:
            release_conn(conn)

    return results


def get_skill_knowledge(skill_id: str) -> str | None:
    skill = get_skill(skill_id)
    return skill["knowledge"] if skill else None


def auto_create_skill_from_pattern(
    pattern_description: str,
    knowledge: str,
    category: str = "learned",
    keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Auto-create a skill from a learned agent pattern."""
    import hashlib
    skill_id = "auto-" + hashlib.md5(pattern_description.encode()).hexdigest()[:8]
    return create_skill(
        skill_id=skill_id,
        name=pattern_description[:60],
        description=pattern_description,
        knowledge=knowledge,
        category=category,
        keywords=keywords or [],
        source="auto-learned",
    )


def import_skills_from_file(file_path: str | Path) -> int:
    """Import skills from a JSON file."""
    path = Path(file_path)
    if not path.exists():
        return 0

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    skills = data if isinstance(data, list) else data.get("skills", [])
    count = 0
    for s in skills:
        if not all(k in s for k in ("id", "name", "description", "knowledge")):
            continue
        create_skill(
            skill_id=s["id"],
            name=s["name"],
            description=s["description"],
            knowledge=s["knowledge"],
            category=s.get("category", "imported"),
            keywords=s.get("keywords", []),
            source=f"file:{path.name}",
        )
        count += 1

    logger.info(f"Imported {count} skills from {path.name}")
    return count


def export_skills_to_file(file_path: str | Path, source: str | None = None) -> int:
    """Export skills to a JSON file."""
    skills = list_skills(source=source, active_only=True)
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"skills": skills, "exported_at": datetime.now(timezone.utc).isoformat()},
            f, indent=2, ensure_ascii=False,
        )
    return len(skills)


# ── Helper ───────────────────────────────────────────────────────

def _row_to_dict(row: dict) -> dict[str, Any]:
    kw = row.get("keywords", "[]")
    if isinstance(kw, str):
        try:
            kw = json.loads(kw)
        except (json.JSONDecodeError, TypeError):
            kw = []
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "description": row["description"],
        "keywords": kw,
        "knowledge": row["knowledge"],
        "source": row["source"],
        "use_count": row["use_count"],
        "avg_score": row["avg_score"],
        "active": bool(row["active"]),
        "created_at": str(row["created_at"]),
    }
