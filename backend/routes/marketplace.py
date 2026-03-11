"""
Skill Marketplace API Routes — Faz 16.
Skill discovery, ratings, templates, export/import/fork.
"""

from __future__ import annotations

import json
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("marketplace")
router = APIRouter(tags=["marketplace"])


def _row_dict(row: object) -> dict[str, object]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    try:
        return dict(row)  # type: ignore[arg-type]
    except Exception:
        return {}


# ── Request Models ───────────────────────────────────────────────

class RatingRequest(BaseModel):
    score: int = Field(..., ge=1, le=5)
    review_text: str = ""
    reviewer: str = "anonymous"
    reviewer_type: str = "user"


class FromTemplateRequest(BaseModel):
    template_id: str
    skill_id: str
    name: str
    description: str = ""
    knowledge_override: str = ""


class ImportRequest(BaseModel):
    skills: list[dict]


class ForkRequest(BaseModel):
    new_id: str
    new_name: str = ""


# ── Helper ───────────────────────────────────────────────────────

def _get_conn():
    from tools.pg_connection import get_conn
    return get_conn()


def _release(conn):
    from tools.pg_connection import release_conn
    release_conn(conn)


def _ensure_ratings_table():
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS skill_ratings (
                    id SERIAL PRIMARY KEY,
                    skill_id VARCHAR(64) NOT NULL,
                    score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
                    review_text TEXT DEFAULT '',
                    reviewer VARCHAR(64) NOT NULL,
                    reviewer_type VARCHAR(16) DEFAULT 'user',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_skill_ratings_skill ON skill_ratings(skill_id)")
        conn.commit()
        _release(conn)
    except Exception as e:
        logger.warning(f"skill_ratings table init failed: {e}")


def _ensure_templates_table():
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS skill_templates (
                    id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(128) NOT NULL,
                    description TEXT DEFAULT '',
                    category VARCHAR(64) NOT NULL,
                    knowledge_template TEXT NOT NULL,
                    frontmatter_template JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
        conn.commit()
        _release(conn)
    except Exception as e:
        logger.warning(f"skill_templates table init failed: {e}")


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/api/skills")
def list_skills_endpoint(
    category: str | None = None,
    source: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Paginated skill list with category/source filters."""
    from tools.dynamic_skills import list_skills
    all_skills = list_skills(category=category, source=source, active_only=True)
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "skills": all_skills[start:end],
        "total": len(all_skills),
        "page": page,
        "per_page": per_page,
    }


def _rating_to_dict(row: dict) -> dict:
    if "created_at" in row and hasattr(row["created_at"], "isoformat"):
        row["created_at"] = row["created_at"].isoformat()
    return row


@router.get("/api/skills/search")
def search_skills_endpoint(q: str = Query("", min_length=1)):
    from tools.dynamic_skills import search_skills
    results = search_skills(q, max_results=20)
    return {"results": results, "query": q}


@router.get("/api/skills/{skill_id}")
def get_skill_detail(skill_id: str):
    from tools.dynamic_skills import get_skill
    skill = get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    # Enrich with performance stats
    try:
        from tools.performance_collector import get_performance_collector

        collector = get_performance_collector()
        get_skill_stats = getattr(collector, "get_skill_stats", None)
        stats = get_skill_stats(skill_id) if callable(get_skill_stats) else {}
        skill["performance"] = stats
    except Exception:
        pass
    return skill


@router.post("/api/skills/{skill_id}/ratings")
def submit_rating(skill_id: str, req: RatingRequest):
    _ensure_ratings_table()
    from tools.dynamic_skills import get_skill
    if not get_skill(skill_id):
        raise HTTPException(status_code=404, detail="Skill not found")
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO skill_ratings (skill_id, score, review_text, reviewer, reviewer_type) VALUES (%s, %s, %s, %s, %s) RETURNING id, created_at",
                (skill_id, req.score, req.review_text, req.reviewer, req.reviewer_type),
            )
            row = _row_dict(cur.fetchone())
            # Update skills.avg_score
            cur.execute(
                "UPDATE skills SET avg_score = (SELECT AVG(score) FROM skill_ratings WHERE skill_id = %s) WHERE id = %s",
                (skill_id, skill_id),
            )
        conn.commit()
        return {
            "id": row.get("id"),
            "skill_id": skill_id,
            "score": req.score,
            "created_at": str(row.get("created_at", "")),
        }
    finally:
        _release(conn)


@router.get("/api/skills/{skill_id}/ratings")
def list_ratings(skill_id: str, page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100)):
    _ensure_ratings_table()
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as total FROM skill_ratings WHERE skill_id = %s", (skill_id,))
            total = _row_dict(cur.fetchone()).get("total", 0)
            offset = (page - 1) * per_page
            cur.execute(
                "SELECT * FROM skill_ratings WHERE skill_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (skill_id, per_page, offset),
            )
            rows = cur.fetchall()
        normalized_rows = [_rating_to_dict(_row_dict(r)) for r in rows]
        return {
            "ratings": normalized_rows,
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    finally:
        _release(conn)


@router.get("/api/skill-templates")
def list_templates():
    _ensure_templates_table()
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM skill_templates ORDER BY category, name")
            rows = cur.fetchall()
        return {"templates": [_row_dict(r) for r in rows]}
    finally:
        _release(conn)


@router.post("/api/skills/from-template")
def create_from_template(req: FromTemplateRequest):
    _ensure_templates_table()
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM skill_templates WHERE id = %s", (req.template_id,))
            tmpl = _row_dict(cur.fetchone())
        if not tmpl:
            raise HTTPException(status_code=404, detail="Template not found")
    finally:
        _release(conn)
    knowledge = req.knowledge_override or str(tmpl.get("knowledge_template", ""))
    description = req.description or str(tmpl.get("description", ""))
    from tools.dynamic_skills import create_skill
    result = create_skill(
        skill_id=req.skill_id,
        name=req.name,
        description=description,
        knowledge=knowledge,
        category=str(tmpl.get("category", "template")),
        source="template",
    )
    return result


@router.post("/api/skills/{skill_id}/export")
def export_skill(skill_id: str):
    from tools.dynamic_skills import get_skill
    skill = get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"package": skill, "format": "json", "version": "1.0"}


@router.post("/api/skills/import")
def import_skills(req: ImportRequest):
    from tools.dynamic_skills import create_skill
    imported = 0
    skipped = 0
    for s in req.skills:
        if not all(k in s for k in ("id", "name", "description", "knowledge")):
            skipped += 1
            continue
        try:
            create_skill(
                skill_id=s["id"],
                name=s["name"],
                description=s["description"],
                knowledge=s["knowledge"],
                category=s.get("category", "imported"),
                keywords=s.get("keywords", []),
                source="import",
            )
            imported += 1
        except Exception:
            skipped += 1
    return {"imported": imported, "skipped": skipped}


@router.post("/api/skills/{skill_id}/fork")
def fork_skill(skill_id: str, req: ForkRequest):
    from tools.dynamic_skills import get_skill, create_skill
    original = get_skill(skill_id)
    if not original:
        raise HTTPException(status_code=404, detail="Skill not found")
    result = create_skill(
        skill_id=req.new_id,
        name=req.new_name or f"Fork of {original['name']}",
        description=original["description"],
        knowledge=original["knowledge"],
        category=original["category"],
        keywords=original.get("keywords", []),
        source=f"fork:{skill_id}",
    )
    return result
