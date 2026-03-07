#!/usr/bin/env python3
"""
Skill Creator MCP Server — FastMCP-based server providing 5 tools
for skill evaluation, benchmarking, validation, and search.

Tools:
  - grade_skill_output: Grade output text against expectations
  - aggregate_benchmark: Aggregate grading results into benchmark stats
  - generate_eval_viewer: Generate standalone HTML eval viewer
  - validate_skill: Validate SKILL.md structure and quality
  - search_skills: Search existing skills by keyword

Requires: Python 3.11+, mcp[cli] (pip install "mcp[cli]")
"""

import json
import math
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# ── Server Setup ─────────────────────────────────────────────────

mcp = FastMCP(
    "skill-creator-server",
    version="1.0.0",
    description="Skill evaluation, benchmarking, validation, and search tools",
)


# ── Tool 1: grade_skill_output ───────────────────────────────────

@mcp.tool()
def grade_skill_output(
    output_text: str,
    expectations: list[str],
    strict: bool = False,
) -> dict[str, Any]:
    """Grade a skill's output against a list of expectations.

    Args:
        output_text: The actual output text produced by the skill
        expectations: List of expectation strings to check against
        strict: If True, requires exact substring match; if False, uses fuzzy matching

    Returns:
        Dict with expectations results (text, passed, evidence), summary stats
    """
    results = []
    passed_count = 0
    output_lower = output_text.lower()

    for exp in expectations:
        exp_lower = exp.lower()
        # Extract key terms (3+ char words)
        key_terms = [w for w in re.findall(r'\b\w{3,}\b', exp_lower)]

        if strict:
            found = exp_lower in output_lower
            evidence = f"Exact match {'found' if found else 'not found'}"
        else:
            # Fuzzy: check what fraction of key terms appear
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

        results.append({
            "text": exp,
            "passed": found,
            "evidence": evidence,
        })

    total = len(expectations)
    return {
        "expectations": results,
        "summary": {
            "passed": passed_count,
            "failed": total - passed_count,
            "total": total,
            "pass_rate": round(passed_count / max(total, 1), 4),
        },
    }


# ── Tool 2: aggregate_benchmark ──────────────────────────────────

def _calc_stats(values: list[float]) -> dict:
    """Calculate mean, stddev, min, max."""
    if not values:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}
    n = len(values)
    mean = sum(values) / n
    stddev = math.sqrt(sum((x - mean) ** 2 for x in values) / (n - 1)) if n > 1 else 0.0
    return {
        "mean": round(mean, 4),
        "stddev": round(stddev, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


@mcp.tool()
def aggregate_benchmark(
    workspace_dir: str,
    skill_name: str = "unnamed-skill",
) -> dict[str, Any]:
    """Aggregate grading results from a workspace directory into benchmark statistics.

    Args:
        workspace_dir: Path to the iteration workspace (e.g., ./my-skill-workspace/iteration-1)
        skill_name: Name of the skill being benchmarked

    Returns:
        Dict with metadata, runs array, run_summary with mean/stddev/delta
    """
    ws = Path(workspace_dir)
    if not ws.is_dir():
        return {"error": f"Directory not found: {workspace_dir}"}

    results: dict[str, list] = {}

    # Discover eval directories
    search_dir = ws / "runs" if (ws / "runs").exists() else ws
    for eval_dir in sorted(search_dir.glob("eval-*")):
        # Read eval metadata
        meta_path = eval_dir / "eval_metadata.json"
        eval_id = 0
        if meta_path.exists():
            try:
                eval_id = json.loads(meta_path.read_text()).get("eval_id", 0)
            except (json.JSONDecodeError, OSError):
                pass

        for config_dir in sorted(eval_dir.iterdir()):
            if not config_dir.is_dir() or not list(config_dir.glob("run-*")):
                continue
            config = config_dir.name
            if config not in results:
                results[config] = []

            for run_dir in sorted(config_dir.glob("run-*")):
                grading_file = run_dir / "grading.json"
                if not grading_file.exists():
                    continue
                try:
                    grading = json.loads(grading_file.read_text())
                except (json.JSONDecodeError, OSError):
                    continue

                run_number = int(run_dir.name.split("-")[1]) if "-" in run_dir.name else 1
                summary = grading.get("summary", {})

                entry = {
                    "eval_id": eval_id,
                    "run_number": run_number,
                    "pass_rate": summary.get("pass_rate", 0.0),
                    "passed": summary.get("passed", 0),
                    "failed": summary.get("failed", 0),
                    "total": summary.get("total", 0),
                    "time_seconds": 0.0,
                    "tokens": 0,
                }

                # Timing from timing.json
                timing_file = run_dir / "timing.json"
                if timing_file.exists():
                    try:
                        td = json.loads(timing_file.read_text())
                        entry["time_seconds"] = td.get("total_duration_seconds", 0.0)
                        entry["tokens"] = td.get("total_tokens", 0)
                    except (json.JSONDecodeError, OSError):
                        pass

                entry["expectations"] = grading.get("expectations", [])
                results[config].append(entry)

    if not results:
        return {"error": "No grading results found", "workspace": workspace_dir}

    # Aggregate
    configs = list(results.keys())
    run_summary = {}
    for config in configs:
        runs = results[config]
        run_summary[config] = {
            "pass_rate": _calc_stats([r["pass_rate"] for r in runs]),
            "time_seconds": _calc_stats([r["time_seconds"] for r in runs]),
            "tokens": _calc_stats([r.get("tokens", 0) for r in runs]),
        }

    # Delta between first two configs
    if len(configs) >= 2:
        a, b = run_summary[configs[0]], run_summary[configs[1]]
        run_summary["delta"] = {
            "pass_rate": f"{a['pass_rate']['mean'] - b['pass_rate']['mean']:+.2f}",
            "time_seconds": f"{a['time_seconds']['mean'] - b['time_seconds']['mean']:+.1f}",
            "tokens": f"{a['tokens']['mean'] - b['tokens']['mean']:+.0f}",
        }

    # Build runs array
    all_runs = []
    for config in configs:
        for r in results[config]:
            all_runs.append({
                "eval_id": r["eval_id"],
                "configuration": config,
                "run_number": r["run_number"],
                "result": {
                    "pass_rate": r["pass_rate"],
                    "passed": r["passed"],
                    "failed": r["failed"],
                    "total": r["total"],
                    "time_seconds": r["time_seconds"],
                    "tokens": r["tokens"],
                },
                "expectations": r["expectations"],
            })

    benchmark = {
        "metadata": {
            "skill_name": skill_name,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "runs": all_runs,
        "run_summary": run_summary,
    }

    # Write to workspace
    out_path = ws / "benchmark.json"
    out_path.write_text(json.dumps(benchmark, indent=2))

    return benchmark


# ── Tool 3: generate_eval_viewer ─────────────────────────────────

@mcp.tool()
def generate_eval_viewer(
    workspace_dir: str,
    skill_name: str = "unnamed-skill",
    benchmark_path: str = "",
    output_path: str = "",
) -> dict[str, Any]:
    """Generate a standalone HTML eval viewer from a workspace directory.

    Args:
        workspace_dir: Path to the iteration workspace with eval results
        skill_name: Name of the skill for the viewer header
        benchmark_path: Optional path to benchmark.json for the Benchmark tab
        output_path: Where to write the HTML file (default: workspace/eval_viewer.html)

    Returns:
        Dict with status, output_path, and run count
    """
    ws = Path(workspace_dir)
    if not ws.is_dir():
        return {"error": f"Directory not found: {workspace_dir}"}

    # Try to use the original generate_review.py if available
    script_candidates = [
        Path(__file__).parent.parent.parent.parent / ".claude" / "skill-creator" / "skills" / "skill-creator" / "eval-viewer" / "generate_review.py",
        Path(__file__).parent / "generate_review.py",
    ]

    generate_script = None
    for candidate in script_candidates:
        if candidate.exists():
            generate_script = candidate
            break

    out = Path(output_path) if output_path else ws / "eval_viewer.html"

    if generate_script:
        # Use the original script in --static mode
        import subprocess
        cmd = [
            sys.executable, str(generate_script),
            str(ws),
            "--skill-name", skill_name,
            "--static", str(out),
        ]
        if benchmark_path and Path(benchmark_path).exists():
            cmd.extend(["--benchmark", benchmark_path])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return {
                "status": "ok",
                "output_path": str(out),
                "method": "generate_review.py --static",
            }
        else:
            return {
                "status": "error",
                "error": result.stderr[:500],
                "method": "generate_review.py --static",
            }
    else:
        # Fallback: generate minimal HTML viewer
        runs = _discover_runs(ws)
        benchmark = None
        if benchmark_path and Path(benchmark_path).exists():
            try:
                benchmark = json.loads(Path(benchmark_path).read_text())
            except (json.JSONDecodeError, OSError):
                pass

        html = _generate_minimal_viewer(runs, skill_name, benchmark)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html)
        return {
            "status": "ok",
            "output_path": str(out),
            "runs_found": len(runs),
            "method": "minimal_fallback",
        }


def _discover_runs(ws: Path) -> list[dict]:
    """Discover eval runs in workspace."""
    runs = []
    search_dir = ws / "runs" if (ws / "runs").exists() else ws
    for eval_dir in sorted(search_dir.glob("eval-*")):
        for config_dir in sorted(eval_dir.iterdir()):
            if not config_dir.is_dir():
                continue
            outputs_dir = config_dir / "outputs"
            if not outputs_dir.is_dir():
                # Check run subdirs
                for run_dir in sorted(config_dir.glob("run-*")):
                    od = run_dir / "outputs"
                    if od.is_dir():
                        runs.append({
                            "id": f"{eval_dir.name}-{config_dir.name}-{run_dir.name}",
                            "prompt": _read_prompt(eval_dir),
                            "config": config_dir.name,
                            "files": [f.name for f in od.iterdir() if f.is_file()],
                        })
            else:
                runs.append({
                    "id": f"{eval_dir.name}-{config_dir.name}",
                    "prompt": _read_prompt(eval_dir),
                    "config": config_dir.name,
                    "files": [f.name for f in outputs_dir.iterdir() if f.is_file()],
                })
    return runs


def _read_prompt(eval_dir: Path) -> str:
    meta = eval_dir / "eval_metadata.json"
    if meta.exists():
        try:
            return json.loads(meta.read_text()).get("prompt", "(no prompt)")
        except (json.JSONDecodeError, OSError):
            pass
    return "(no prompt)"


def _generate_minimal_viewer(runs: list[dict], skill_name: str, benchmark: dict | None) -> str:
    """Generate a minimal standalone HTML viewer."""
    data = json.dumps({"skill_name": skill_name, "runs": runs, "benchmark": benchmark})
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Eval Viewer — {skill_name}</title>
<style>
body{{font-family:system-ui;max-width:900px;margin:2rem auto;padding:0 1rem;background:#1a1a2e;color:#e0e0e0}}
h1{{color:#00e5ff}}table{{width:100%;border-collapse:collapse;margin:1rem 0}}
th,td{{border:1px solid #333;padding:8px;text-align:left}}th{{background:#2a2a4a}}
.pass{{color:#10b981}}.fail{{color:#ef4444}}pre{{background:#2a2a4a;padding:1rem;overflow-x:auto;border-radius:4px}}
</style></head>
<body>
<h1>Eval Viewer — {skill_name}</h1>
<p>{len(runs)} runs found</p>
<div id="content"></div>
<script>
const D={data};
const el=document.getElementById('content');
let h='';
D.runs.forEach(r=>{{
  h+=`<h2>${{r.id}}</h2><p><b>Config:</b> ${{r.config}}</p><p><b>Prompt:</b> ${{r.prompt}}</p>`;
  h+=`<p><b>Files:</b> ${{r.files.join(', ')||'none'}}</p><hr>`;
}});
if(D.benchmark){{
  h+='<h2>Benchmark</h2><pre>'+JSON.stringify(D.benchmark.run_summary,null,2)+'</pre>';
}}
el.innerHTML=h;
</script></body></html>"""


# ── Tool 4: validate_skill ───────────────────────────────────────

@mcp.tool()
def validate_skill(skill_path: str) -> dict[str, Any]:
    """Validate a SKILL.md file structure and quality.

    Args:
        skill_path: Path to the skill directory or SKILL.md file

    Returns:
        Dict with validation results: valid, score, issues, suggestions
    """
    p = Path(skill_path)
    skill_md = p / "SKILL.md" if p.is_dir() else p
    skill_dir = skill_md.parent

    if not skill_md.exists():
        return {"valid": False, "score": 0, "issues": [f"SKILL.md not found at {skill_path}"]}

    content = skill_md.read_text(errors="replace")
    lines = content.split("\n")
    issues: list[str] = []
    suggestions: list[str] = []
    score = 100

    # 1. Check YAML frontmatter
    has_frontmatter = content.startswith("---")
    if not has_frontmatter:
        issues.append("Missing YAML frontmatter (must start with ---)")
        score -= 30
    else:
        # Extract frontmatter
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
                # Check description quality
                desc_match = re.search(r'description:\s*(.+?)(?:\n[a-z]|\n---)', fm, re.DOTALL)
                if desc_match:
                    desc = desc_match.group(1).strip().strip('"').strip("'")
                    if len(desc) < 30:
                        issues.append(f"Description too short ({len(desc)} chars) — aim for 50+ chars")
                        score -= 10
                    if "use when" not in desc.lower() and "use for" not in desc.lower():
                        suggestions.append("Add 'Use when...' trigger hints to description for better activation")

    # 2. Check line count
    line_count = len(lines)
    if line_count > 500:
        issues.append(f"SKILL.md is {line_count} lines — recommended max is 500. Use references/ for overflow")
        score -= 10
    elif line_count > 400:
        suggestions.append(f"SKILL.md is {line_count} lines — approaching 500 line limit")

    # 3. Check for reference links
    refs_dir = skill_dir / "references"
    scripts_dir = skill_dir / "scripts"
    assets_dir = skill_dir / "assets"

    for subdir, label in [(refs_dir, "references"), (scripts_dir, "scripts"), (assets_dir, "assets")]:
        if subdir.exists():
            for f in subdir.iterdir():
                if f.is_file():
                    # Check if properly linked with markdown link syntax
                    proper_link = f"(./{label}/{f.name})"
                    backtick_ref = f"`{label}/{f.name}`"
                    if proper_link not in content and f.name not in content:
                        issues.append(f"Bundled file {label}/{f.name} not referenced in SKILL.md")
                        score -= 5
                    elif backtick_ref in content and proper_link not in content:
                        issues.append(f"Use markdown link for {label}/{f.name}: [{f.name}](./{label}/{f.name})")
                        score -= 3

    # 4. Check writing style
    must_count = len(re.findall(r'\bMUST\b', content))
    never_count = len(re.findall(r'\bNEVER\b', content))
    always_count = len(re.findall(r'\bALWAYS\b', content))
    heavy_handed = must_count + never_count + always_count
    if heavy_handed > 10:
        suggestions.append(f"Found {heavy_handed} heavy-handed directives (MUST/NEVER/ALWAYS) — consider explaining WHY instead")

    # 5. Check for examples
    if "example" not in content.lower() and "```" not in content:
        suggestions.append("No examples found — adding examples improves skill effectiveness")

    score = max(0, min(100, score))

    return {
        "valid": len(issues) == 0,
        "score": score,
        "line_count": line_count,
        "issues": issues,
        "suggestions": suggestions,
        "has_frontmatter": has_frontmatter,
        "has_references": refs_dir.exists(),
        "has_scripts": scripts_dir.exists(),
        "has_assets": assets_dir.exists(),
    }


# ── Tool 5: search_skills ───────────────────────────────────────

@mcp.tool()
def search_skills(
    query: str,
    search_paths: list[str] | None = None,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Search existing skills by keyword to find similar or related skills.

    Args:
        query: Search query (keywords, phrases)
        search_paths: List of directories to search for skills (default: common locations)
        max_results: Maximum number of results to return

    Returns:
        List of matching skills with name, description, path, and relevance score
    """
    if not search_paths:
        # Default search locations relative to workspace
        cwd = Path.cwd()
        search_paths = [
            str(cwd / "skills"),
            str(cwd / "data" / "skills"),
            str(cwd / ".claude" / "skill-creator" / "skills"),
            str(cwd / ".cursor" / "skills"),
        ]

    query_terms = set(query.lower().split())
    found: list[dict] = []

    for sp in search_paths:
        sp_path = Path(sp)
        if not sp_path.exists():
            continue

        for skill_md in sp_path.rglob("SKILL.md"):
            try:
                content = skill_md.read_text(errors="replace")
            except OSError:
                continue

            # Extract name and description from frontmatter
            name = skill_md.parent.name
            description = ""
            if content.startswith("---"):
                fm_end = content.find("---", 3)
                if fm_end != -1:
                    fm = content[3:fm_end]
                    name_match = re.search(r'name:\s*(.+)', fm)
                    desc_match = re.search(r'description:\s*(.+?)(?:\n[a-z]|\n---)', fm, re.DOTALL)
                    if name_match:
                        name = name_match.group(1).strip().strip('"').strip("'")
                    if desc_match:
                        description = desc_match.group(1).strip().strip('"').strip("'")

            # Score relevance
            text = f"{name} {description} {content[:500]}".lower()
            matched = sum(1 for t in query_terms if t in text)
            if matched == 0:
                continue

            relevance = round(matched / max(len(query_terms), 1), 2)

            found.append({
                "name": name,
                "description": description[:200],
                "path": str(skill_md.parent),
                "relevance": relevance,
                "line_count": len(content.split("\n")),
            })

    # Sort by relevance descending
    found.sort(key=lambda x: x["relevance"], reverse=True)
    return found[:max_results]


# ── Server Entry Point ───────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
