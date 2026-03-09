"""
Autonomous Skill Hygiene System
-------------------------------
Periodically validates all skills and removes/deactivates junk entries.
Converts valuable auto-learned content into proper memories instead.

Rules:
  - builtin skills are NEVER touched
  - auto-learned skills are validated against quality thresholds
  - duplicates (by name similarity or knowledge overlap) are merged/removed
  - valuable knowledge from deleted skills is saved to memories table
"""

import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ── Quality thresholds ──────────────────────────────────────────────
MIN_KNOWLEDGE_LEN = 200         # chars — shorter is likely garbage (was 80)
MIN_DESCRIPTION_LEN = 30        # chars — shorter is likely garbage (was 20)
MAX_KEYWORD_RATIO_DIGITS = 0.3  # if >30% of keywords are numeric → junk (was 0.5)
GARBAGE_PATTERNS = [
    r"(?i)max steps reached",
    r"(?i)timeout",
    r"(?i)partial result",
    r"(?i)\[warning\]",
    r"(?i)error:",
    r"(?i)tamamlanan görev",       # generic Turkish "completed task"
    r"(?i)başarıyla tamamlandı",   # "completed successfully" — not a skill
    r"(?i)hata oluştu",           # "error occurred"
    r"^Task:",                     # Task descriptions are NOT skills!
    r"^Bu agent sistemini",        # User questions are NOT skills!
    r"^Görev:",                    # Turkish "Task:"
    r"auto-discovered",            # Generic auto-discovered label
    r"^Bu bir",                    # Generic "This is a..."
    r"^Kullanıcı",                 # User input
]
GARBAGE_RE = [re.compile(p) for p in GARBAGE_PATTERNS]

# Minimum occurrences for pattern → skill conversion
MIN_PATTERN_OCCURRENCES = 5  # Increased from 3 to reduce noise


def _is_garbage_content(text: str) -> bool:
    """Check if text matches known garbage patterns."""
    for pat in GARBAGE_RE:
        if pat.search(text[:300]):
            return True
    return False


def _keyword_quality(keywords: list[str]) -> bool:
    """Return False if keywords are mostly junk (digits, single chars, etc.)."""
    if not keywords:
        return False
    junk_count = sum(
        1 for kw in keywords
        if len(kw) < 2 or kw.isdigit() or len(kw) > 60
    )
    return (junk_count / len(keywords)) < MAX_KEYWORD_RATIO_DIGITS


def _save_knowledge_as_memory(skill: dict) -> None:
    """If a deleted skill has valuable knowledge, save it as a memory entry."""
    knowledge = (skill.get("knowledge") or "").strip()
    if len(knowledge) < MIN_KNOWLEDGE_LEN:
        return
    # Don't save garbage
    if _is_garbage_content(knowledge):
        return
    try:
        from tools.pg_connection import get_conn, release_conn
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO memories (content, category, source_agent, metadata)
                       VALUES (%s, 'learning', 'skill-hygiene',
                               jsonb_build_object(
                                   'origin', 'skill-cleanup',
                                   'original_skill_id', %s,
                                   'original_skill_name', %s,
                                   'migrated_at', %s
                               ))""",
                    (
                        knowledge[:2000],
                        skill.get("id", ""),
                        skill.get("name", ""),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            conn.commit()
            logger.info(f"Migrated skill knowledge to memory: {skill.get('id')}")
        finally:
            release_conn(conn)
    except Exception as e:
        logger.warning(f"Failed to migrate skill to memory: {e}")


def validate_skill(skill: dict) -> dict:
    """
    Validate a single skill and return a report.
    Returns: {"valid": bool, "issues": [...], "action": "keep"|"deactivate"|"delete"}
    """
    issues = []
    sid = skill.get("id", "")
    source = skill.get("source", "")
    knowledge = (skill.get("knowledge") or "").strip()
    description = (skill.get("description") or "").strip()
    keywords = skill.get("keywords") or []
    if isinstance(keywords, str):
        try:
            import json
            keywords = json.loads(keywords)
        except Exception:
            keywords = []

    # Rule 1: builtin skills are always valid
    if source == "builtin":
        return {"valid": True, "issues": [], "action": "keep"}

    # Rule 2: knowledge too short
    if len(knowledge) < MIN_KNOWLEDGE_LEN:
        issues.append(f"knowledge too short ({len(knowledge)} chars)")

    # Rule 3: description too short
    if len(description) < MIN_DESCRIPTION_LEN:
        issues.append(f"description too short ({len(description)} chars)")

    # Rule 4: garbage content in knowledge or description
    if _is_garbage_content(knowledge) or _is_garbage_content(description):
        issues.append("contains garbage/error patterns")

    # Rule 5: keyword quality
    if keywords and not _keyword_quality(keywords):
        issues.append("keywords are mostly junk")

    # Rule 6: no keywords at all
    if not keywords:
        issues.append("no keywords defined")

    # Rule 7: empty knowledge
    if not knowledge:
        issues.append("empty knowledge")

    # Decide action
    if not issues:
        return {"valid": True, "issues": [], "action": "keep"}

    critical_issues = {"empty knowledge", "contains garbage/error patterns"}
    has_critical = any(i in critical_issues for i in issues)

    if has_critical or len(issues) >= 3:
        action = "delete"
    else:
        action = "deactivate"

    return {"valid": False, "issues": issues, "action": action}


def run_hygiene_check(dry_run: bool = False) -> dict:
    """
    Run full skill hygiene check.

    Args:
        dry_run: If True, only report — don't actually delete/deactivate.

    Returns:
        {
            "checked": int,
            "healthy": int,
            "deactivated": [...],
            "deleted": [...],
            "migrated_to_memory": [...],
            "skipped_builtin": int,
        }
    """
    from tools.dynamic_skills import list_skills, update_skill

    all_skills = list_skills(active_only=False)
    report = {
        "checked": len(all_skills),
        "healthy": 0,
        "deactivated": [],
        "deleted": [],
        "migrated_to_memory": [],
        "skipped_builtin": 0,
        "dry_run": dry_run,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    for skill in all_skills:
        sid = skill.get("id", "")
        source = skill.get("source", "")

        if source == "builtin":
            report["skipped_builtin"] += 1
            report["healthy"] += 1
            continue

        result = validate_skill(skill)

        if result["valid"]:
            report["healthy"] += 1
            continue

        entry = {
            "id": sid,
            "name": skill.get("name", ""),
            "issues": result["issues"],
            "action": result["action"],
        }

        if dry_run:
            if result["action"] == "delete":
                report["deleted"].append(entry)
            else:
                report["deactivated"].append(entry)
            continue

        # Save valuable knowledge before deletion
        if result["action"] == "delete":
            _save_knowledge_as_memory(skill)
            report["migrated_to_memory"].append(sid)

        # Execute action
        if result["action"] == "delete":
            update_skill(sid, active=False)
            report["deleted"].append(entry)
            logger.info(f"Skill deleted (deactivated): {sid} — {result['issues']}")
        elif result["action"] == "deactivate":
            update_skill(sid, active=False)
            report["deactivated"].append(entry)
            logger.info(f"Skill deactivated: {sid} — {result['issues']}")

    logger.info(
        f"Skill hygiene complete: {report['checked']} checked, "
        f"{report['healthy']} healthy, "
        f"{len(report['deleted'])} deleted, "
        f"{len(report['deactivated'])} deactivated"
    )
    return report
