"""MCP Server health checking and management routes."""

import sys
import time
import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit
from tools.mcp_client import list_servers, discover_tools, call_mcp_tool
from tools.pg_connection import get_conn, release_conn

router = APIRouter(prefix="/api/mcp", tags=["mcp"])

# ── In-memory health cache ───────────────────────────────────────

_health_cache: dict[str, dict[str, Any]] = {}


def _row_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return {}


def _set_health(server_id: str, healthy: bool, tool_count: int = 0, error: str = ""):
    _health_cache[server_id] = {
        "healthy": healthy,
        "tool_count": tool_count,
        "error": error,
        "checked_at": time.time(),
        "checked_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


async def _check_one(server_id: str) -> dict[str, Any]:
    """Run discover_tools on a single server and cache the result."""
    try:
        tools = await asyncio.wait_for(discover_tools(server_id), timeout=20.0)
        _set_health(server_id, healthy=True, tool_count=len(tools))
        return {"server_id": server_id, "healthy": True, "tool_count": len(tools)}
    except asyncio.TimeoutError:
        _set_health(server_id, healthy=False, error="timeout")
        return {"server_id": server_id, "healthy": False, "error": "timeout"}
    except Exception as e:
        msg = str(e)[:200]
        _set_health(server_id, healthy=False, error=msg)
        return {"server_id": server_id, "healthy": False, "error": msg}


# ── Endpoints ────────────────────────────────────────────────────


@router.post("/health-check")
async def mcp_health_check(
    server_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Test connectivity of all or a specific MCP server."""
    servers = list_servers(active_only=True)

    if server_id:
        if not any(s["id"] == server_id for s in servers):
            raise HTTPException(404, f"Server '{server_id}' not found or inactive")
        results = [await _check_one(server_id)]
    else:
        # Check all servers concurrently
        results = await asyncio.gather(
            *[_check_one(s["id"]) for s in servers],
            return_exceptions=False,
        )

    healthy = sum(1 for r in results if r["healthy"])
    _audit("mcp_health_check", user["user_id"], f"{healthy}/{len(results)} healthy")
    return {"results": results, "healthy": healthy, "total": len(results)}


@router.get("/servers")
async def mcp_list_servers(user: dict = Depends(get_current_user)):
    """List all registered servers with cached health status."""
    servers = list_servers(active_only=False)
    enriched = []
    for s in servers:
        health = _health_cache.get(s["id"])
        enriched.append({
            **s,
            "health": health if health else None,
        })
    return {"servers": enriched}


@router.post("/servers/{server_id}/test")
async def mcp_test_server(
    server_id: str,
    user: dict = Depends(get_current_user),
):
    """Test a specific server by discovering its tools."""
    servers = list_servers(active_only=False)
    if not any(s["id"] == server_id for s in servers):
        raise HTTPException(404, f"Server '{server_id}' not found")

    result = await _check_one(server_id)
    _audit("mcp_server_test", user["user_id"], f"{server_id}: {'ok' if result['healthy'] else result.get('error', 'fail')}")
    return result


@router.get("/servers/{server_id}/tools")
async def mcp_server_tools(
    server_id: str,
    user: dict = Depends(get_current_user),
):
    """Discover tools on a specific server (live call)."""
    servers = list_servers(active_only=False)
    if not any(s["id"] == server_id for s in servers):
        raise HTTPException(404, f"Server '{server_id}' not found")

    try:
        tools = await asyncio.wait_for(discover_tools(server_id), timeout=20.0)
        _set_health(server_id, healthy=True, tool_count=len(tools))
        return {"server_id": server_id, "tools": tools, "count": len(tools)}
    except asyncio.TimeoutError:
        _set_health(server_id, healthy=False, error="timeout")
        raise HTTPException(504, f"Server '{server_id}' timed out")
    except Exception as e:
        _set_health(server_id, healthy=False, error=str(e)[:200])
        raise HTTPException(502, f"Server '{server_id}' error: {str(e)[:200]}")


@router.post("/servers/{server_id}/toggle")
async def mcp_toggle_server(
    server_id: str,
    user: dict = Depends(get_current_user),
):
    """Enable/disable a server (toggle active flag in PostgreSQL)."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, active FROM mcp_servers WHERE id = %s", (server_id,))
            row_data = _row_dict(cur.fetchone())
            if not row_data:
                raise HTTPException(404, f"Server '{server_id}' not found")

            new_active = not bool(row_data.get("active", False))
            cur.execute("UPDATE mcp_servers SET active = %s WHERE id = %s", (new_active, server_id))
        conn.commit()
    finally:
        release_conn(conn)

    state = "enabled" if new_active else "disabled"
    _audit("mcp_server_toggle", user["user_id"], f"{server_id} → {state}")
    return {"server_id": server_id, "active": new_active, "state": state}


@router.get("/status")
async def mcp_status(user: dict = Depends(get_current_user)):
    """Dashboard summary: total servers, healthy count, last check time."""
    servers = list_servers(active_only=False)
    active_servers = [s for s in servers if s["active"]]

    healthy_count = 0
    last_check: float | None = None

    for s in active_servers:
        h = _health_cache.get(s["id"])
        if h:
            if h["healthy"]:
                healthy_count += 1
            ts = h["checked_at"]
            if last_check is None or ts > last_check:
                last_check = ts

    return {
        "total_servers": len(servers),
        "active_servers": len(active_servers),
        "healthy": healthy_count,
        "unhealthy": len(active_servers) - healthy_count,
        "unchecked": len(active_servers) - len([s for s in active_servers if s["id"] in _health_cache]),
        "last_check_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(last_check)) if last_check else None,
    }


# ── MCP Usage Statistics ─────────────────────────────────────────


@router.get("/usage-stats")
async def mcp_usage_stats(user: dict = Depends(get_current_user)):
    """Get MCP server usage statistics from tool_usage table.
    Returns per-server call counts, per-model breakdown, and daily timeline.
    Never 500 so CORS headers are always sent."""
    empty = {
        "server_stats": [],
        "all_tools": [],
        "model_breakdown": {},
        "timeline": {},
    }

    uid = user["user_id"]
    try:
        conn = get_conn()
    except Exception:
        return empty

    try:
        with conn.cursor() as cur:
            # Get all known MCP server names
            try:
                servers = list_servers(active_only=False)
            except Exception:
                servers = []

            # Per-server usage counts
            server_stats = []
            for s in servers:
                sid = s["id"]
                sname = s.get("name") or sid
                try:
                    cur.execute(
                        """SELECT COUNT(*) as cnt,
                                  SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as ok,
                                  SUM(latency_ms) as lat,
                                  SUM(tokens_used) as tok
                           FROM tool_usage
                           WHERE user_id IN (%s, 'system')
                             AND (tool_name ILIKE %s OR tool_name ILIKE %s)""",
                        (uid, f"%{sid}%", f"%{sname}%"),
                    )
                    row_data = _row_dict(cur.fetchone())
                    cnt = int(row_data.get("cnt", 0) or 0)
                    if cnt > 0:
                        server_stats.append(
                            {
                                "server_id": sid,
                                "server_name": sname,
                                "call_count": cnt,
                                "success_count": int(row_data.get("ok", 0) or 0),
                                "total_latency_ms": round(
                                    float(row_data.get("lat", 0) or 0), 1
                                ),
                                "total_tokens": int(row_data.get("tok", 0) or 0),
                            }
                        )
                except Exception:
                    pass

            # All tools grouped by tool_name
            all_tools = []
            try:
                cur.execute(
                    """SELECT tool_name, COUNT(*) as cnt,
                              SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as ok,
                              SUM(latency_ms) as lat,
                              SUM(tokens_used) as tok
                       FROM tool_usage WHERE user_id IN (%s, 'system')
                       GROUP BY tool_name ORDER BY cnt DESC LIMIT 50""",
                    (uid,),
                )
                for row in cur.fetchall():
                    all_tools.append({
                        "tool_name": row[0],
                        "call_count": row[1],
                        "success_count": row[2] or 0,
                        "total_latency_ms": round(row[3] or 0, 1),
                        "total_tokens": row[4] or 0,
                    })
            except Exception:
                pass

            # Per-model (agent_role) breakdown
            model_breakdown: dict = {}
            try:
                cur.execute(
                    """SELECT agent_role, tool_name, COUNT(*) as cnt
                       FROM tool_usage WHERE user_id IN (%s, 'system')
                       GROUP BY agent_role, tool_name
                       ORDER BY cnt DESC LIMIT 200""",
                    (uid,),
                )
                for row in cur.fetchall():
                    role = row[0]
                    tool = row[1]
                    cnt = row[2]
                    if tool not in model_breakdown:
                        model_breakdown[tool] = {}
                    model_breakdown[tool][role] = cnt
            except Exception:
                pass

            # Daily timeline (last 30 days)
            timeline: dict = {}
            try:
                cur.execute(
                    """SELECT DATE(timestamp) as day, tool_name, COUNT(*) as cnt
                       FROM tool_usage
                       WHERE user_id IN (%s, 'system')
                         AND timestamp >= NOW() - INTERVAL '30 days'
                       GROUP BY DATE(timestamp), tool_name
                       ORDER BY day ASC""",
                    (uid,),
                )
                for row in cur.fetchall():
                    day = str(row[0])
                    tool = row[1]
                    if day not in timeline:
                        timeline[day] = {}
                    timeline[day][tool] = row[2]
            except Exception:
                pass

    except Exception:
        return empty
    finally:
        try:
            release_conn(conn)
        except Exception:
            pass

    return {
        "server_stats": server_stats,
        "all_tools": all_tools,
        "model_breakdown": model_breakdown,
        "timeline": timeline,
    }
