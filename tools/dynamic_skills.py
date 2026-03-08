"""
Dynamic Skill Registry — PostgreSQL backend + Kiro Skill Format.
Skills are special capabilities (yetenekler) that agents can create,
activate, and delegate at runtime. Each skill is persisted both in
the database AND as a Kiro-compatible SKILL.md folder on disk.

Kiro Skill Format:
  skill-name/
  ├── SKILL.md          # Frontmatter (name, description) + instructions
  ├── scripts/          # Optional executable helpers
  ├── references/       # Optional reference docs
  └── assets/           # Optional templates / data files
"""

from __future__ import annotations

import json
import logging
import re
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
    """Create or replace a skill — saves to DB + writes Kiro SKILL.md to disk."""
    clean_id = skill_id.lower().replace(" ", "-").strip()
    # Remove consecutive hyphens and trim
    clean_id = re.sub(r"-{2,}", "-", clean_id).strip("-")
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
    finally:
        release_conn(conn)

    # Write Kiro-format SKILL.md to disk
    _write_skill_to_disk(clean_id, name, description, knowledge, category, keywords)

    return {"id": clean_id, "name": name, "category": category, "source": source}


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
    limit: int | None = None,
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

    sql = f"SELECT * FROM skills WHERE {' AND '.join(conditions)} ORDER BY use_count DESC, name ASC"
    if limit is not None and limit > 0:
        sql += " LIMIT %s"
        params.append(limit)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
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


# Stopwords to avoid as skill name / keyword (Turkish + English)
_AUTO_SKILL_STOP = frozenset({
    "ve", "veya", "için", "bir", "bu", "şu", "ile", "olarak", "gibi", "kadar",
    "the", "and", "or", "for", "with", "from", "that", "this", "are", "you",
    "bir", "bu", "şu", "ile", "için", "olarak", "gibi", "kadar", "ne", "nasıl",
    "mi", "mı", "mu", "mü", "da", "de", "ta", "te", "ya", "ye",
})


def _skill_name_from_description(desc: str, max_len: int = 55) -> str:
    """Build a readable skill name: first sentence or word-boundary truncation."""
    text = desc.strip()
    if not text:
        return "Öğrenilen görev"
    # First sentence (., !, ?, newline)
    for sep in (".", "!", "?", "\n"):
        idx = text.find(sep)
        if idx != -1 and idx <= max_len + 10:
            candidate = text[:idx].strip()
            if len(candidate) >= 10:
                return (candidate[:max_len] + "…") if len(candidate) > max_len else candidate
    # Word-boundary truncation
    if len(text) <= max_len:
        return text
    cut = text[: max_len + 1].rsplit(maxsplit=1)
    if not cut:
        return text[:max_len].strip()
    return (cut[0].strip() + "…") if cut[0] else text[:max_len].strip()


def _topic_keywords_from_description(desc: str, max_words: int = 4) -> list[str]:
    """Extract a few topic-like keywords from the task description (avoid stopwords)."""
    words = re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]+", desc)
    seen: set[str] = set()
    out: list[str] = []
    for w in words:
        w_lower = w.lower()
        if len(w_lower) < 3 or w_lower in _AUTO_SKILL_STOP or w_lower in seen:
            continue
        seen.add(w_lower)
        out.append(w)
        if len(out) >= max_words:
            break
    return out


def auto_create_skill_from_pattern(
    pattern_description: str,
    knowledge: str,
    category: str = "learned",
    keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Auto-create a skill from a learned agent pattern. Uses readable name and topic keywords."""
    import hashlib
    clean_desc = pattern_description.strip()[:200]
    if not clean_desc:
        clean_desc = "Tamamlanan görev"
    skill_id = "auto-" + hashlib.md5(clean_desc.encode()).hexdigest()[:8]
    name = _skill_name_from_description(clean_desc)
    topic_kw = _topic_keywords_from_description(clean_desc)
    all_keywords = list(dict.fromkeys((keywords or []) + topic_kw))[:12]
    if not all_keywords:
        all_keywords = ["task-completion"]
    return create_skill(
        skill_id=skill_id,
        name=name,
        description=clean_desc,
        knowledge=knowledge,
        category=category,
        keywords=all_keywords,
        source="auto-learned",
    )


# ── Kiro Skill Format — Disk Operations ─────────────────────────

def _write_skill_to_disk(
    skill_id: str,
    name: str,
    description: str,
    knowledge: str,
    category: str = "custom",
    keywords: list[str] | None = None,
) -> Path:
    """Write a skill as Kiro-format SKILL.md folder to data/skills/."""
    skill_dir = SKILLS_DIR / skill_id
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Build SKILL.md with YAML frontmatter + markdown body
    kw_list = keywords or []
    frontmatter = (
        f"---\n"
        f"name: {skill_id}\n"
        f"description: {description}\n"
        f"category: {category}\n"
        f"keywords: {json.dumps(kw_list, ensure_ascii=False)}\n"
        f"---\n\n"
    )
    body = f"# {name}\n\n{knowledge}\n"
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(frontmatter + body, encoding="utf-8")

    # Create optional subdirs if they don't exist
    for sub in ("scripts", "references", "assets"):
        (skill_dir / sub).mkdir(exist_ok=True)

    logger.info(f"Skill written to disk: {skill_dir}")
    return skill_dir


def load_skill_from_disk(skill_id: str) -> dict[str, Any] | None:
    """Load a skill from its Kiro SKILL.md on disk."""
    skill_dir = SKILLS_DIR / skill_id
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None

    content = skill_md.read_text(encoding="utf-8")

    # Parse YAML frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not fm_match:
        return None

    # Simple YAML frontmatter parser (no external dependency)
    meta: dict[str, Any] = {}
    for line in fm_match.group(1).strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                try:
                    meta[key] = json.loads(val)
                except Exception:
                    meta[key] = val
            else:
                meta[key] = val

    body = content[fm_match.end():]

    # List reference files
    refs_dir = skill_dir / "references"
    ref_files = [f.name for f in refs_dir.iterdir() if f.is_file()] if refs_dir.exists() else []

    # List script files
    scripts_dir = skill_dir / "scripts"
    script_files = [f.name for f in scripts_dir.iterdir() if f.is_file()] if scripts_dir.exists() else []

    return {
        "id": meta.get("name", skill_id),
        "name": meta.get("name", skill_id),
        "description": meta.get("description", ""),
        "category": meta.get("category", "custom"),
        "keywords": meta.get("keywords", []),
        "knowledge": body.strip(),
        "references": ref_files,
        "scripts": script_files,
        "path": str(skill_dir),
    }


def get_full_skill_context(skill_id: str) -> str | None:
    """
    Get complete skill context for agent injection.
    Loads SKILL.md knowledge + any reference files content.
    Returns formatted string ready for system prompt injection.
    """
    # Try DB first
    skill = get_skill(skill_id)
    knowledge = skill["knowledge"] if skill else None

    # Enrich with disk references if available
    skill_dir = SKILLS_DIR / skill_id
    refs_dir = skill_dir / "references"
    ref_content = ""
    if refs_dir.exists():
        for ref_file in sorted(refs_dir.iterdir()):
            if ref_file.is_file() and ref_file.suffix in (".md", ".txt", ".json"):
                try:
                    text = ref_file.read_text(encoding="utf-8")[:5000]
                    ref_content += f"\n\n## Reference: {ref_file.name}\n{text}"
                except Exception:
                    pass

    if not knowledge and not ref_content:
        return None

    parts = []
    if knowledge:
        parts.append(knowledge)
    if ref_content:
        parts.append(ref_content)
    return "\n".join(parts)


# ── Kiro Skill Format — Disk-based SKILL.md packages ────────────

def create_skill_package(
    skill_id: str,
    name: str,
    description: str,
    knowledge: str,
    category: str = "capability",
    keywords: list[str] | None = None,
    references: dict[str, str] | None = None,
    scripts: dict[str, str] | None = None,
    source: str = "agent",
) -> dict[str, Any]:
    """
    Create a Kiro-format skill package on disk AND register in DB.

    Produces:
      data/skills/{skill_id}/
        SKILL.md          — frontmatter + instructions
        references/        — optional .md reference files
        scripts/           — optional executable scripts

    Also saves to PostgreSQL for search/listing.
    """
    clean_id = skill_id.lower().replace(" ", "-").strip()
    skill_dir = SKILLS_DIR / clean_id
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Build SKILL.md content
    kw_list = keywords or []
    frontmatter = (
        f"---\n"
        f"name: {clean_id}\n"
        f"description: {description}\n"
        f"---\n\n"
    )
    skill_md = frontmatter + knowledge

    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # Write reference files
    if references:
        ref_dir = skill_dir / "references"
        ref_dir.mkdir(exist_ok=True)
        for filename, content in references.items():
            (ref_dir / filename).write_text(content, encoding="utf-8")

    # Write script files
    if scripts:
        scr_dir = skill_dir / "scripts"
        scr_dir.mkdir(exist_ok=True)
        for filename, content in scripts.items():
            (scr_dir / filename).write_text(content, encoding="utf-8")

    # Register in DB
    db_result = create_skill(
        skill_id=clean_id,
        name=name,
        description=description,
        knowledge=knowledge,
        category=category,
        keywords=kw_list,
        source=source,
    )

    logger.info(f"Skill package created: {skill_dir}")
    return {
        **db_result,
        "path": str(skill_dir),
        "has_references": bool(references),
        "has_scripts": bool(scripts),
    }


def load_skill_package(skill_id: str) -> dict[str, Any] | None:
    """
    Load a Kiro-format skill package from disk.
    Returns full skill with SKILL.md content + reference file list.
    """
    clean_id = skill_id.lower().replace(" ", "-").strip()
    skill_dir = SKILLS_DIR / clean_id
    skill_md_path = skill_dir / "SKILL.md"

    if not skill_md_path.exists():
        # Fallback to DB-only skill
        return get_skill(skill_id)

    content = skill_md_path.read_text(encoding="utf-8")

    # Parse frontmatter
    name = clean_id
    description = ""
    knowledge = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            # Simple YAML parser (no external dependency)
            meta: dict[str, Any] = {}
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip()] = val.strip()
            name = meta.get("name", clean_id)
            description = meta.get("description", "")
            knowledge = parts[2].strip()

    # Collect references
    ref_dir = skill_dir / "references"
    ref_files = []
    if ref_dir.exists():
        ref_files = [f.name for f in ref_dir.iterdir() if f.is_file()]

    # Collect scripts
    scr_dir = skill_dir / "scripts"
    scr_files = []
    if scr_dir.exists():
        scr_files = [f.name for f in scr_dir.iterdir() if f.is_file()]

    return {
        "id": clean_id,
        "name": name,
        "description": description,
        "knowledge": knowledge,
        "path": str(skill_dir),
        "references": ref_files,
        "scripts": scr_files,
        "source": "package",
    }


def load_skill_reference(skill_id: str, ref_filename: str) -> str | None:
    """Load a specific reference file from a skill package."""
    clean_id = skill_id.lower().replace(" ", "-").strip()
    ref_path = SKILLS_DIR / clean_id / "references" / ref_filename
    if ref_path.exists():
        return ref_path.read_text(encoding="utf-8")
    return None


def list_skill_packages() -> list[dict[str, Any]]:
    """List all Kiro-format skill packages on disk."""
    if not SKILLS_DIR.exists():
        return []
    packages = []
    for d in sorted(SKILLS_DIR.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            packages.append({
                "id": d.name,
                "path": str(d),
                "has_references": (d / "references").exists(),
                "has_scripts": (d / "scripts").exists(),
            })
    return packages


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
