from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
import sys, hashlib
from pathlib import Path

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)
import bcrypt
from deps import (
    get_current_user,
    _audit,
    _issue_signed_token,
    _active_tokens,
    _revoked_tokens,
    USERS,
    _extract_bearer_token,
    _get_user_from_token,
    _utcnow,
)
from config import MODELS
from core.models import Thread, PipelineType, EventType, AgentRole
from core.state import (
    save_thread,
    load_thread,
    list_threads,
    delete_thread,
    delete_all_threads,
)

router = APIRouter()

_TOOL_USAGE = []
_USER_BEHAVIORS = []


# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str


class RAGIngestRequest(BaseModel):
    content: str
    title: str
    source: str


class RAGQueryRequest(BaseModel):
    query: str
    max_results: int = 10


class SkillCreateRequest(BaseModel):
    skill_id: str
    name: str
    description: str
    knowledge: str
    category: str = "general"
    keywords: list[str] = []


# ── Auth Endpoints ────────────────────────────────────────────────


@router.post("/api/auth/login")
async def api_login(req: LoginRequest):
    user = USERS.get(req.username.lower())
    if not user:
        raise HTTPException(401, "Kullanıcı bulunamadı")
    stored = user["password_hash"]
    if stored.startswith("$2b$") or stored.startswith("$2a$"):
        ok = bcrypt.checkpw(req.password.encode(), stored.encode())
    else:
        import hashlib

        ok = hashlib.sha256(req.password.encode()).hexdigest() == stored
    if not ok:
        raise HTTPException(401, "Şifre hatalı")
    token = _issue_signed_token(user["user_id"])
    # Keep compatibility with old lookup path (also supports explicit logout revocation workflows).
    _active_tokens[token] = user["user_id"]
    return {
        "token": token,
        "user_id": user["user_id"],
        "full_name": user["full_name"],
    }


@router.post("/api/auth/logout")
async def api_logout(authorization: str | None = Header(None, alias="Authorization")):
    token = _extract_bearer_token(authorization)
    _active_tokens.pop(token, None)
    if token:
        _revoked_tokens.add(token)
    return {"ok": True}


@router.get("/api/auth/me")
async def api_me(authorization: str | None = Header(None, alias="Authorization")):
    token = _extract_bearer_token(authorization)
    user = _get_user_from_token(token)
    if not user:
        raise HTTPException(401, "Geçersiz token")
    return {"user_id": user["user_id"], "full_name": user["full_name"]}


# ── REST Endpoints: Models & Config ──────────────────────────────


@router.get("/api/models")
async def get_models():
    """Return all model configurations for the agent fleet."""
    return MODELS


@router.get("/api/pipelines")
async def get_pipelines():
    """Return available pipeline types."""
    return [
        {"id": p.value, "label": p.value.replace("_", " ").title()}
        for p in PipelineType
    ]


# ── REST Endpoints: Threads ──────────────────────────────────────


@router.get("/api/threads")
async def api_list_threads(user: dict = Depends(get_current_user), limit: int = 20):
    return list_threads(limit=limit, user_id=user["user_id"])


@router.post("/api/threads")
async def api_create_thread(user: dict = Depends(get_current_user)):
    thread = Thread()
    save_thread(thread, user_id=user["user_id"])
    return {"id": thread.id}


@router.get("/api/threads/{thread_id}")
async def api_get_thread(thread_id: str, user: dict = Depends(get_current_user)):
    thread = load_thread(thread_id, user_id=user["user_id"])
    if not thread:
        raise HTTPException(404, "Thread not found")
    return thread.model_dump(mode="json")


@router.delete("/api/threads/{thread_id}")
async def api_delete_thread(thread_id: str, user: dict = Depends(get_current_user)):
    ok = delete_thread(thread_id, user_id=user["user_id"])
    if not ok:
        raise HTTPException(404, "Thread not found")
    return {"deleted": True}


@router.delete("/api/threads")
async def api_delete_all_threads(user: dict = Depends(get_current_user)):
    count = delete_all_threads(user_id=user["user_id"])
    return {"deleted": count}


# ── REST Endpoints: Tools (RAG, Skills, MCP, Teachability, Eval) ─


@router.post("/api/rag/ingest")
async def api_rag_ingest(req: RAGIngestRequest, user: dict = Depends(get_current_user)):
    from tools.rag import ingest_document

    result = await ingest_document(
        req.content, req.title, req.source, user_id=user["user_id"]
    )
    return result


@router.post("/api/rag/query")
async def api_rag_query(req: RAGQueryRequest, user: dict = Depends(get_current_user)):
    from tools.rag import query_documents

    results = await query_documents(req.query, req.max_results, user_id=user["user_id"])
    return results


@router.get("/api/rag/documents")
async def api_rag_documents(user: dict = Depends(get_current_user)):
    try:
        from tools.rag import list_documents

        return list_documents(user_id=user["user_id"])
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(503, f"RAG module error: {e}")


@router.get("/api/skills")
async def api_list_skills():
    try:
        from tools.dynamic_skills import list_skills

        return list_skills()
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(503, f"Skills module error: {e}")


@router.get("/api/skills/auto")
async def api_list_auto_skills():
    """List auto-generated skills."""
    try:
        from tools.dynamic_skills import list_skills

        return list_skills(source="auto-learned")
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(503, f"Skills module error: {e}")


@router.post("/api/skills/migrate")
async def api_migrate_skills():
    """Trigger SQLite → PostgreSQL migration."""
    try:
        from tools.pg_connection import migrate_from_sqlite

        result = migrate_from_sqlite()
        return {"status": "ok", "migrated": result}
    except Exception as e:
        raise HTTPException(503, f"Migration error: {e}")


@router.post("/api/skills")
async def api_create_skill(req: SkillCreateRequest):
    try:
        from tools.dynamic_skills import create_skill

        return create_skill(
            skill_id=req.skill_id,
            name=req.name,
            description=req.description,
            knowledge=req.knowledge,
            category=req.category,
            keywords=req.keywords,
        )
    except Exception as e:
        raise HTTPException(503, f"Skills module error: {e}")


@router.get("/api/skills/recommendations")
async def get_skill_recommendations(
    query: str = "",
    user: dict = Depends(get_current_user),
):
    """Recommend skills based on query context."""
    _audit("skill_recommendation", user["user_id"], detail=query[:100])
    try:
        from tools.dynamic_skills import search_skills
        from tools.agent_eval import get_best_agent_for_task, detect_task_type

        skills = search_skills(query, max_results=5) if query else []

        best_agent = None
        task_type = None
        if query:
            task_type = detect_task_type(query)
            best_agent = get_best_agent_for_task(task_type)

        # Inject recommended_agent into each skill
        for skill in skills:
            if "recommended_agent" not in skill or not skill["recommended_agent"]:
                skill["recommended_agent"] = best_agent

        return skills

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill recommendation failed: {e}")


@router.post("/api/skills/hygiene")
async def api_skill_hygiene(
    dry_run: bool = False,
    user: dict = Depends(get_current_user),
):
    """Run autonomous skill hygiene check — validates and cleans junk skills. Manual trigger from Yetenek Merkezi."""
    _audit("skill_hygiene", user["user_id"], f"dry_run={dry_run}")
    try:
        from tools.skill_hygiene import run_hygiene_check

        return run_hygiene_check(dry_run=dry_run)
    except Exception as e:
        raise HTTPException(503, f"Skill hygiene error: {e}")


# ── Gelişmiş pattern detection (3+ tekrar → skill) ─────────────────


@router.get("/api/self-skills/patterns")
async def api_self_skills_patterns(
    min_occurrences: int = 3,
    user: dict = Depends(get_current_user),
):
    """Detect repeating execution patterns (same tool sequence 3+ times)."""
    _audit("self_skills_patterns", user["user_id"])
    try:
        from tools.pattern_skill import detect_patterns

        return {
            "patterns": detect_patterns(
                min_occurrences=max(2, min(min_occurrences, 10))
            )
        }
    except Exception as e:
        raise HTTPException(503, f"Pattern detection error: {e}")


@router.post("/api/self-skills/generate")
async def api_self_skills_generate(
    signature: str,
    user: dict = Depends(get_current_user),
):
    """Generate an auto-learned skill from a detected pattern (signature from GET /api/self-skills/patterns)."""
    _audit("self_skills_generate", user["user_id"], detail=signature[:20])
    if not signature or len(signature) > 32:
        raise HTTPException(400, "Invalid signature")
    try:
        from tools.pattern_skill import generate_skill_from_pattern

        result = generate_skill_from_pattern(signature)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "Generation failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Skill generation error: {e}")


@router.get("/api/skills/proactive-suggestions")
async def api_proactive_skill_suggestions(user: dict = Depends(get_current_user)):
    """Analyze usage patterns, behaviors, teachings, and threads to proactively suggest skills."""
    try:
        _audit("proactive_skill_suggestions", user["user_id"])
        uid = user["user_id"]
        suggestions: list[dict] = []
        tools_analyzed = 0
        behaviors_analyzed = 0
        teachings_count = 0
        threads_scanned = 0

        # ── 1. Tool usage analysis: most-used & failing tools ────────
        try:
            user_tools = [t for t in _TOOL_USAGE if t.get("user_id") == uid]
            tools_analyzed = len(user_tools)

            if user_tools:
                # Most-used tools
                tool_freq: dict[str, int] = {}
                tool_failures: dict[str, int] = {}
                for t in user_tools:
                    name = t.get("tool_name", "unknown")
                    tool_freq[name] = tool_freq.get(name, 0) + 1
                    if not t.get("success", True):
                        tool_failures[name] = tool_failures.get(name, 0) + 1

                top_tools = sorted(tool_freq.items(), key=lambda x: x[1], reverse=True)[
                    :5
                ]
                for tool_name, count in top_tools:
                    try:
                        from tools.dynamic_skills import search_skills

                        matches = search_skills(tool_name, max_results=1)
                        if matches:
                            suggestions.append(
                                {
                                    "id": f"up-{tool_name}",
                                    "skill_name": matches[0]["name"],
                                    "reason": f"'{tool_name}' aracını {count} kez kullandın — bu skill iş akışını hızlandırabilir.",
                                    "category": "usage_pattern",
                                    "confidence": round(
                                        min(0.5 + count * 0.05, 0.95), 2
                                    ),
                                    "source_data": f"tool_usage: {tool_name} ({count}x)",
                                    "suggested_action": "activate",
                                    "icon": "🔧",
                                }
                            )
                    except Exception:
                        pass

                # Failing tools
                top_failures = sorted(
                    tool_failures.items(), key=lambda x: x[1], reverse=True
                )[:3]
                for tool_name, fail_count in top_failures:
                    try:
                        from tools.dynamic_skills import search_skills

                        matches = search_skills(f"{tool_name} error fix", max_results=1)
                        if matches:
                            suggestions.append(
                                {
                                    "id": f"er-{tool_name}",
                                    "skill_name": matches[0]["name"],
                                    "reason": f"'{tool_name}' aracı {fail_count} kez hata verdi — bu skill hata kurtarma sağlayabilir.",
                                    "category": "error_recovery",
                                    "confidence": round(
                                        min(0.6 + fail_count * 0.08, 0.95), 2
                                    ),
                                    "source_data": f"tool_failures: {tool_name} ({fail_count} failures)",
                                    "suggested_action": "install",
                                    "icon": "🛠️",
                                }
                            )
                    except Exception:
                        pass
        except Exception:
            pass

        # ── 2. User behavior analysis ────────────────────────────────
        try:
            user_behaviors = [b for b in _USER_BEHAVIORS if b.get("user_id") == uid]
            behaviors_analyzed = len(user_behaviors)

            if user_behaviors:
                action_freq: dict[str, int] = {}
                for b in user_behaviors:
                    action = b.get("action", "unknown")
                    action_freq[action] = action_freq.get(action, 0) + 1

                top_actions = sorted(
                    action_freq.items(), key=lambda x: x[1], reverse=True
                )[:3]
                for action, count in top_actions:
                    try:
                        from tools.dynamic_skills import search_skills

                        matches = search_skills(action, max_results=1)
                        if matches:
                            suggestions.append(
                                {
                                    "id": f"bi-{action}",
                                    "skill_name": matches[0]["name"],
                                    "reason": f"'{action}' eylemini sık kullanıyorsun ({count}x) — bu skill bu alışkanlığı destekleyebilir.",
                                    "category": "behavior_insight",
                                    "confidence": round(
                                        min(0.4 + count * 0.06, 0.90), 2
                                    ),
                                    "source_data": f"behavior: {action} ({count}x)",
                                    "suggested_action": "learn",
                                    "icon": "🧠",
                                }
                            )
                    except Exception:
                        pass
        except Exception:
            pass

        # ── 3. Teachings analysis ────────────────────────────────────
        try:
            from tools.teachability import get_all_teachings

            teachings = get_all_teachings()
            if isinstance(teachings, list):
                teachings_count = len(teachings)
            elif isinstance(teachings, dict):
                teachings_count = len(
                    teachings.get("teachings", teachings.get("items", []))
                )
                teachings = teachings.get("teachings", teachings.get("items", []))
            else:
                teachings = []

            for teaching in teachings[:5]:
                content = (
                    teaching.get("content", "")
                    if isinstance(teaching, dict)
                    else str(teaching)
                )
                if not content:
                    continue
                keywords = " ".join(content.split()[:6])
                try:
                    from tools.dynamic_skills import search_skills

                    matches = search_skills(keywords, max_results=1)
                    if matches:
                        snippet = content[:60] + ("..." if len(content) > 60 else "")
                        suggestions.append(
                            {
                                "id": f"tb-{hashlib.md5(content[:50].encode()).hexdigest()[:8]}",
                                "skill_name": matches[0]["name"],
                                "reason": f"Öğretmen notun '{snippet}' ile ilgili — bu skill faydalı olabilir.",
                                "category": "teaching_based",
                                "confidence": round(
                                    min(0.55 + teachings_count * 0.02, 0.85), 2
                                ),
                                "source_data": f"teaching: {snippet}",
                                "suggested_action": "learn",
                                "icon": "📚",
                            }
                        )
                except Exception:
                    pass
        except Exception:
            pass

        # ── 4. Recent threads analysis (trending topics) ─────────────
        try:
            all_threads = list_threads()
            recent_threads = sorted(
                all_threads,
                key=lambda t: t.get("updated_at", t.get("created_at", "")),
                reverse=True,
            )[:10]
            threads_scanned = len(recent_threads)

            topic_freq: dict[str, int] = {}
            for t_meta in recent_threads:
                thread_id = t_meta.get("thread_id", t_meta.get("id", ""))
                if not thread_id:
                    continue
                try:
                    thread = load_thread(thread_id)
                    title = ""
                    if isinstance(thread, dict):
                        title = thread.get("title", thread.get("name", ""))
                    elif hasattr(thread, "title"):
                        title = thread.title or ""
                    if title:
                        for word in title.lower().split():
                            if len(word) > 3:
                                topic_freq[word] = topic_freq.get(word, 0) + 1
                except Exception:
                    pass

            top_topics = sorted(topic_freq.items(), key=lambda x: x[1], reverse=True)[
                :3
            ]
            for topic, count in top_topics:
                if count < 2:
                    continue
                try:
                    from tools.dynamic_skills import search_skills

                    matches = search_skills(topic, max_results=1)
                    if matches:
                        suggestions.append(
                            {
                                "id": f"tr-{topic}",
                                "skill_name": matches[0]["name"],
                                "reason": f"Son görevlerinde '{topic}' konusu {count} kez geçiyor — trend skill önerisi.",
                                "category": "trending",
                                "confidence": round(min(0.45 + count * 0.1, 0.90), 2),
                                "source_data": f"thread_topic: {topic} ({count}x)",
                                "suggested_action": "activate",
                                "icon": "🔥",
                            }
                        )
                except Exception:
                    pass
        except Exception:
            pass

        # ── Deduplicate by skill_name, keep highest confidence ───────
        seen: dict[str, dict] = {}
        for s in suggestions:
            name = s["skill_name"]
            if name not in seen or s["confidence"] > seen[name]["confidence"]:
                seen[name] = s
        suggestions = list(seen.values())

        # ── Sort by confidence desc, limit to 12 ────────────────────
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        suggestions = suggestions[:12]

        return {
            "suggestions": suggestions,
            "analysis_summary": {
                "tools_analyzed": tools_analyzed,
                "behaviors_analyzed": behaviors_analyzed,
                "teachings_count": teachings_count,
                "threads_scanned": threads_scanned,
            },
            "generated_at": _utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Proactive suggestion error: {e}")


@router.get("/api/skills/hygiene/validate/{skill_id}")
async def api_validate_skill(skill_id: str):
    """Validate a single skill and return quality report."""
    try:
        from tools.dynamic_skills import get_skill
        from tools.skill_hygiene import validate_skill

        skill = get_skill(skill_id)
        if not skill:
            raise HTTPException(404, "Skill not found")
        return validate_skill(skill)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Validation error: {e}")


@router.get("/api/skills/{skill_id}")
async def api_get_skill(skill_id: str):
    try:
        from tools.dynamic_skills import get_skill

        skill = get_skill(skill_id)
        if not skill:
            raise HTTPException(404, "Skill not found")
        return skill
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Skills module error: {e}")


@router.delete("/api/skills/{skill_id}")
async def api_delete_skill(skill_id: str):
    try:
        from tools.dynamic_skills import delete_skill

        return delete_skill(skill_id)
    except Exception as e:
        raise HTTPException(503, f"Skills module error: {e}")


# ── Skill Auto-Discovery ─────────────────────────────────────────


@router.post("/api/skills/auto-discover")
async def auto_discover_skills(user: dict = Depends(get_current_user)):
    """Analyze recent tasks and auto-create skills from successful patterns."""
    _audit("skill_auto_discover", user["user_id"])
    try:
        from datetime import timedelta
        from tools.dynamic_skills import auto_create_skill_from_pattern

        discovered: list[dict] = []
        seen_descriptions: set[str] = set()

        user_threads = list_threads(limit=50, user_id=user["user_id"])
        cutoff = (_utcnow() - timedelta(days=7)).isoformat()

        for t_info in user_threads:
            created = t_info.get("created_at", "")
            if created and created < cutoff:
                continue

            thread = load_thread(t_info["id"], user_id=user["user_id"])
            if not thread:
                continue

            for task in thread.tasks:
                if task.status.value != "completed" or not task.final_result:
                    continue

                desc = task.user_input[:200].strip()
                if not desc or desc in seen_descriptions:
                    continue
                seen_descriptions.add(desc)

                knowledge_parts = [f"Task: {desc}"]
                tool_sequence: list[str] = []
                for sub in task.sub_tasks:
                    if sub.result:
                        knowledge_parts.append(
                            f"Agent {sub.assigned_agent.value}: {sub.result[:200]}"
                        )
                    if sub.skills:
                        tool_sequence.extend(sub.skills)

                knowledge = "\n".join(knowledge_parts[:5])
                keywords = list(set(tool_sequence))[:6] or ["auto-discovered"]

                try:
                    skill = auto_create_skill_from_pattern(
                        pattern_description=desc,
                        knowledge=knowledge,
                        category="auto-discovered",
                        keywords=keywords,
                    )
                    discovered.append(
                        {
                            "skill_id": skill.get("id", ""),
                            "name": skill.get("name", ""),
                            "description": desc,
                        }
                    )
                except Exception:
                    continue

            if len(discovered) >= 10:
                break

        return {
            "discovered_count": len(discovered),
            "skills": discovered,
            "scanned_threads": len(user_threads),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skill discovery failed: {e}")
