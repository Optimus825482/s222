from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)
from deps import get_current_user, _audit
router = APIRouter()

# ── Shared Pydantic Models ───────────────────────────────────────

class MCPServerRequest(BaseModel):
    server_id: str
    url: str
    name: str = ""


class TeachRequest(BaseModel):
    content: str

# ── Skill Creator Endpoints ──────────────────────────────────────

class SkillGradeRequest(BaseModel):
    output_text: str
    expectations: list[str]
    strict: bool = False

class SkillValidateRequest(BaseModel):
    skill_path: str

class SkillBenchmarkRequest(BaseModel):
    workspace_dir: str
    skill_name: str = "unnamed-skill"

class EvalViewerRequest(BaseModel):
    workspace_dir: str
    skill_name: str = "unnamed-skill"
    benchmark_path: str = ""
    output_path: str = ""


@router.post("/api/skill-creator/grade")
async def api_skill_creator_grade(req: SkillGradeRequest):
    """Grade a skill output against expectations."""
    import re as _re
    results = []
    passed_count = 0
    output_lower = req.output_text.lower()

    for exp in req.expectations:
        exp_lower = exp.lower()
        key_terms = [w for w in _re.findall(r'\b\w{3,}\b', exp_lower)]

        if req.strict:
            found = exp_lower in output_lower
            evidence = f"Exact match {'found' if found else 'not found'}"
        else:
            matched_terms = [t for t in key_terms if t in output_lower]
            ratio = len(matched_terms) / max(len(key_terms), 1)
            found = ratio >= 0.6
            if found:
                evidence = f"Matched {len(matched_terms)}/{len(key_terms)} key terms: {', '.join(matched_terms[:5])}"
            else:
                missing = [t for t in key_terms if t not in output_lower]
                evidence = f"Only {len(matched_terms)}/{len(key_terms)} terms found. Missing: {', '.join(missing[:5])}"

        if found:
            passed_count += 1
        results.append({"text": exp, "passed": found, "evidence": evidence})

    total = len(req.expectations)
    return {
        "expectations": results,
        "summary": {
            "passed": passed_count,
            "failed": total - passed_count,
            "total": total,
            "pass_rate": round(passed_count / max(total, 1), 4),
        },
    }


@router.post("/api/skill-creator/validate")
async def api_skill_creator_validate(req: SkillValidateRequest):
    """Validate a SKILL.md file structure and quality."""
    import re as _re
    p = Path(req.skill_path)
    skill_md = p / "SKILL.md" if p.is_dir() else p
    skill_dir = skill_md.parent

    if not skill_md.exists():
        raise HTTPException(404, f"SKILL.md not found at {req.skill_path}")

    content = skill_md.read_text(errors="replace")
    lines = content.split("\n")
    issues, suggestions = [], []
    score = 100

    has_frontmatter = content.startswith("---")
    if not has_frontmatter:
        issues.append("Missing YAML frontmatter")
        score -= 30
    else:
        fm_end = content.find("---", 3)
        if fm_end == -1:
            issues.append("Unclosed YAML frontmatter")
            score -= 20
        else:
            fm = content[3:fm_end].strip()
            if "name:" not in fm:
                issues.append("Missing 'name' in frontmatter")
                score -= 15
            if "description:" not in fm:
                issues.append("Missing 'description' in frontmatter")
                score -= 20
            else:
                desc_match = _re.search(r'description:\s*(.+?)(?:\n[a-z]|\n---)', fm, _re.DOTALL)
                if desc_match:
                    desc = desc_match.group(1).strip().strip('"').strip("'")
                    if len(desc) < 30:
                        issues.append(f"Description too short ({len(desc)} chars)")
                        score -= 10
                    if "use when" not in desc.lower() and "use for" not in desc.lower():
                        suggestions.append("Add 'Use when...' trigger hints to description")

    line_count = len(lines)
    if line_count > 500:
        issues.append(f"SKILL.md is {line_count} lines — max recommended is 500")
        score -= 10

    for subdir, label in [(skill_dir / "references", "references"), (skill_dir / "scripts", "scripts"), (skill_dir / "assets", "assets")]:
        if subdir.exists():
            for f in subdir.iterdir():
                if f.is_file():
                    proper_link = f"(./{label}/{f.name})"
                    if proper_link not in content and f.name not in content:
                        issues.append(f"Bundled file {label}/{f.name} not referenced in SKILL.md")
                        score -= 5

    must_count = len(_re.findall(r'\bMUST\b', content))
    never_count = len(_re.findall(r'\bNEVER\b', content))
    always_count = len(_re.findall(r'\bALWAYS\b', content))
    if must_count + never_count + always_count > 10:
        suggestions.append(f"Found {must_count + never_count + always_count} heavy-handed directives — consider explaining WHY instead")

    score = max(0, min(100, score))
    return {
        "valid": len(issues) == 0,
        "score": score,
        "line_count": line_count,
        "issues": issues,
        "suggestions": suggestions,
        "has_frontmatter": has_frontmatter,
    }


@router.post("/api/skill-creator/benchmark")
async def api_skill_creator_benchmark(req: SkillBenchmarkRequest):
    """Aggregate grading results from workspace into benchmark stats."""
    ws = Path(req.workspace_dir)
    if not ws.is_dir():
        raise HTTPException(404, f"Directory not found: {req.workspace_dir}")

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / ".claude" / "skill-creator" / "skills" / "skill-creator"))
        from scripts.aggregate_benchmark import generate_benchmark
        benchmark = generate_benchmark(ws, req.skill_name)
        return benchmark
    except ImportError:
        raise HTTPException(503, "aggregate_benchmark module not available")
    except Exception as e:
        raise HTTPException(500, f"Benchmark error: {e}")


@router.get("/api/skill-creator/search")
async def api_skill_creator_search(query: str = "", max_results: int = 10):
    """Search existing skills by keyword."""
    if not query:
        return []
    try:
        from tools.dynamic_skills import search_skills
        return search_skills(query, max_results=max_results)
    except Exception as e:
        raise HTTPException(500, f"Search error: {e}")


# ── Workflow Engine Endpoints ────────────────────────────────────

@router.get("/api/workflows/templates")
async def api_workflow_templates():
    """List available workflow templates."""
    try:
        from tools.workflow_engine import get_workflow_templates
        return get_workflow_templates()
    except Exception as e:
        raise HTTPException(503, f"Workflow engine error: {e}")


@router.get("/api/workflows/history")
async def api_workflow_history(limit: int = 20, user: dict = Depends(get_current_user)):
    """List recent workflow execution results."""
    try:
        from tools.workflow_engine import list_workflow_results
        return list_workflow_results(limit=limit)
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(503, f"Workflow engine error: {e}")


class WorkflowRunRequest(BaseModel):
    template: str
    variables: dict = {}
    custom_steps: list[dict] | None = None


@router.post("/api/workflows/run")
async def api_run_workflow(req: WorkflowRunRequest, user: dict = Depends(get_current_user)):
    """Execute a workflow template or custom workflow."""
    try:
        from tools.workflow_engine import (
            WORKFLOW_TEMPLATES, create_workflow, execute_workflow, WorkflowStep, Workflow
        )
        from core.models import Thread as ThreadModel

        # Support both dict key ("research-and-report") and workflow_id ("tpl-research-and-report")
        resolved_key = None
        if req.template != "custom":
            if req.template in WORKFLOW_TEMPLATES:
                resolved_key = req.template
            else:
                # Lookup by workflow_id (e.g. "tpl-research-and-report")
                for k, wf in WORKFLOW_TEMPLATES.items():
                    if wf.workflow_id == req.template:
                        resolved_key = k
                        break

        if resolved_key is not None:
            tpl_workflow = WORKFLOW_TEMPLATES[resolved_key]
            workflow = Workflow(
                workflow_id=f"{resolved_key}-{int(__import__('time').time())}",
                name=tpl_workflow.name,
                description=tpl_workflow.description,
                steps=list(tpl_workflow.steps),
                variables={**tpl_workflow.variables, **(req.variables or {})},
            )
        elif req.template == "custom" and req.custom_steps:
            steps = [WorkflowStep(**s) for s in req.custom_steps]
            workflow = Workflow(
                workflow_id=f"custom-{int(__import__('time').time())}",
                name="Custom Workflow",
                description="User-defined workflow",
                steps=steps,
                variables=req.variables,
            )
        else:
            raise HTTPException(400, f"Unknown template: {req.template}")

        thread = ThreadModel()
        result = await execute_workflow(workflow, thread)
        return {
            "workflow_id": result.workflow_id,
            "status": result.status,
            "step_results": result.step_results,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "variables": result.variables,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Workflow execution error: {e}")


@router.get("/api/workflows/history/{workflow_id}")
async def api_workflow_detail(workflow_id: str, user: dict = Depends(get_current_user)):
    """Get detailed execution result for a specific workflow run."""
    try:
        from tools.workflow_engine import list_workflow_results
        results = list_workflow_results(limit=200)
        match = next((r for r in results if r.get("workflow_id") == workflow_id), None)
        if not match:
            raise HTTPException(404, "Workflow result not found")
        return match
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Error: {e}")


class ScheduleCreateRequest(BaseModel):
    template: str
    cron: str  # crontab expression: "*/30 * * * *"
    variables: dict = {}


@router.get("/api/workflows/schedules")
async def api_list_schedules(user: dict = Depends(get_current_user)):
    """List all scheduled workflows."""
    try:
        from tools.workflow_scheduler import list_schedules
        return list_schedules()
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(503, f"Scheduler module error: {e}")


@router.post("/api/workflows/schedules")
async def api_create_schedule(req: ScheduleCreateRequest, user: dict = Depends(get_current_user)):
    """Create a new cron-scheduled workflow."""
    try:
        from tools.workflow_scheduler import add_schedule
        return add_schedule(
            schedule_id=None,
            template=req.template,
            cron_expr=req.cron,
            variables=req.variables,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(503, f"Schedule error: {e}")


@router.delete("/api/workflows/schedules/{schedule_id}")
async def api_delete_schedule(schedule_id: str, user: dict = Depends(get_current_user)):
    """Delete a scheduled workflow."""
    try:
        from tools.workflow_scheduler import remove_schedule
        ok = remove_schedule(schedule_id)
        if not ok:
            raise HTTPException(404, "Schedule not found")
        return {"status": "deleted", "schedule_id": schedule_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Error: {e}")


@router.post("/api/workflows/schedules/{schedule_id}/toggle")
async def api_toggle_schedule(schedule_id: str, user: dict = Depends(get_current_user)):
    """Toggle a scheduled workflow on/off."""
    try:
        from tools.workflow_scheduler import toggle_schedule
        return toggle_schedule(schedule_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(503, f"Error: {e}")


@router.patch("/api/workflows/schedules/{schedule_id}")
async def api_patch_toggle_schedule(schedule_id: str, user: dict = Depends(get_current_user)):
    """PATCH toggle — frontend compat alias for POST .../toggle."""
    try:
        from tools.workflow_scheduler import toggle_schedule
        return toggle_schedule(schedule_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(503, f"Error: {e}")


# ── Domain Expert Endpoints ──────────────────────────────────────

@router.get("/api/domains")
async def api_list_domains():
    """List available domain expertise modules."""
    try:
        from tools.domain_skills import list_domains
        return list_domains()
    except Exception as e:
        raise HTTPException(503, f"Domain skills error: {e}")


@router.get("/api/domains/{domain_id}/tools")
async def api_domain_tools(domain_id: str):
    """List tools available in a specific domain."""
    try:
        from tools.domain_skills import get_domain_tools
        tools = get_domain_tools(domain_id)
        if tools is None:
            raise HTTPException(404, f"Domain not found: {domain_id}")
        return tools
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Domain skills error: {e}")


class DomainExpertRequest(BaseModel):
    domain: str
    tool_name: str
    arguments: dict = {}


@router.post("/api/domains/execute")
async def api_execute_domain_tool(req: DomainExpertRequest, user: dict = Depends(get_current_user)):
    """Execute a domain-specific tool."""
    try:
        from tools.domain_skills import execute_domain_tool
        result = await execute_domain_tool(req.domain, req.tool_name, req.arguments)
        return result
    except Exception as e:
        raise HTTPException(503, f"Domain execution error: {e}")

# ── Domain Auto-Discovery & Marketplace ──────────────────────────

class DomainDetectRequest(BaseModel):
    query: str
    top_k: int = 3

@router.post("/api/domains/auto-detect")
async def api_auto_detect_domain(req: DomainDetectRequest, user: dict = Depends(get_current_user)):
    """Auto-detect relevant domain(s) from a user query."""
    try:
        from tools.domain_skills import auto_detect_domain
        results = auto_detect_domain(req.query, req.top_k)
        return {"query": req.query, "matches": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(503, f"Domain detection error: {e}")

@router.get("/api/domains/marketplace")
async def api_domain_marketplace():
    """Get all domain skills with marketplace metadata."""
    try:
        from tools.domain_skills import get_marketplace_data
        return get_marketplace_data()
    except Exception as e:
        raise HTTPException(503, f"Marketplace error: {e}")

@router.post("/api/domains/discover")
async def api_discover_domains(user: dict = Depends(get_current_user)):
    """Trigger domain skill auto-discovery scan."""
    try:
        from tools.domain_skills import discover_domain_skills
        return discover_domain_skills()
    except Exception as e:
        raise HTTPException(503, f"Discovery error: {e}")

@router.post("/api/domains/{domain_id}/toggle")
async def api_toggle_domain(domain_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Enable or disable a domain skill."""
    try:
        from tools.domain_skills import toggle_domain_skill
        enabled = body.get("enabled", True)
        return toggle_domain_skill(domain_id, enabled)
    except Exception as e:
        raise HTTPException(503, f"Toggle error: {e}")

@router.get("/api/marketplace/catalog")
async def api_marketplace_catalog(
    category: str | None = None,
    search: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Get unified skill marketplace catalog."""
    try:
        from tools.domain_skills import get_marketplace_catalog
        catalog = get_marketplace_catalog()

        # Filter by category
        if category and category != "all":
            catalog = [item for item in catalog if item.get("category") == category]

        # Search filter
        if search:
            search_lower = search.lower()
            catalog = [
                item for item in catalog
                if search_lower in item.get("name", "").lower()
                or search_lower in item.get("name_tr", "").lower()
                or search_lower in item.get("description", "").lower()
                or any(search_lower in tag.lower() for tag in item.get("tags", []))
            ]

        return {
            "items": catalog,
            "total": len(catalog),
            "categories": list(set(item.get("category", "other") for item in catalog)),
        }
    except Exception as e:
        raise HTTPException(503, f"Marketplace error: {e}")

@router.get("/api/marketplace/stats")
async def api_marketplace_stats(user: dict = Depends(get_current_user)):
    """Get marketplace statistics."""
    try:
        from tools.domain_skills import list_domains, get_marketplace_catalog
        domains = list_domains()
        catalog = get_marketplace_catalog()
        domain_items = [c for c in catalog if c["type"] == "domain"]
        skill_items = [c for c in catalog if c["type"] == "skill"]
        total_tools = sum(d.get("tool_count", 0) for d in domains)
        return {
            "total_items": len(catalog),
            "domain_count": len(domain_items),
            "skill_count": len(skill_items),
            "total_tools": total_tools,
            "categories": list(set(c.get("category", "other") for c in catalog)),
            "installed_count": len([c for c in catalog if c.get("installed")]),
        }
    except Exception as e:
        raise HTTPException(503, f"Marketplace stats error: {e}")



@router.get("/api/mcp/servers")
async def api_mcp_servers():
    try:
        from tools.mcp_client import list_servers
        return list_servers()
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(503, f"MCP module error: {e}")


@router.post("/api/mcp/servers")
async def api_add_mcp_server(req: MCPServerRequest):
    try:
        from tools.mcp_client import register_server
        return register_server(req.server_id, req.url, req.name)
    except Exception as e:
        raise HTTPException(503, f"MCP module error: {e}")


@router.post("/api/mcp/seed")
async def api_mcp_seed(overwrite: bool = False):
    """Re-seed default MCP servers. Use overwrite=true to reset configs."""
    try:
        from tools.mcp_client import seed_default_servers, DEFAULT_MCP_SERVERS
        count = seed_default_servers(overwrite=overwrite)
        return {
            "seeded": count,
            "total_defaults": len(DEFAULT_MCP_SERVERS),
            "message": f"{count} server kaydedildi" if count else "Tüm server'lar zaten kayıtlı",
        }
    except Exception as e:
        raise HTTPException(503, f"MCP seed error: {e}")


@router.get("/api/mcp/servers/{server_id}/tools")
async def api_mcp_tools(server_id: str):
    try:
        from tools.mcp_client import discover_tools
        return await discover_tools(server_id)
    except Exception as e:
        raise HTTPException(503, f"MCP module error: {e}")


@router.get("/api/teachability")
async def api_get_teachings():
    try:
        from tools.teachability import get_all_teachings
        return get_all_teachings()
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(503, f"Teachability module error: {e}")


@router.post("/api/teachability")
async def api_add_teaching(req: TeachRequest):
    try:
        from tools.teachability import save_teaching
        return save_teaching(req.content)
    except Exception as e:
        raise HTTPException(503, f"Teachability module error: {e}")


@router.get("/api/eval/stats")
async def api_eval_stats():
    """Per-agent evaluation stats (task count, avg score)."""
    try:
        from tools.agent_eval import get_agent_stats
        return get_agent_stats()
    except ImportError:
        return []
    except Exception as e:
        raise HTTPException(503, f"Eval module error: {e}")


@router.get("/api/eval/baseline")
async def api_eval_baseline(agent_role: str | None = None):
    """
    Performance baseline report (agent-orchestration-improve-agent skill).
    Returns: task_success_rate_pct, user_satisfaction_score, avg_latency_ms,
    token_efficiency_ratio, total_tasks, success_count.
    """
    try:
        from tools.agent_eval import get_performance_baseline
        return get_performance_baseline(agent_role)
    except Exception as e:
        raise HTTPException(503, "Baseline unavailable") from e