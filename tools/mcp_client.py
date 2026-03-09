"""
MCP Client — Model Context Protocol integration.
Connects agents to external services (GitHub, Slack, databases, etc.)
via the MCP protocol. Generic wrapper that discovers and calls MCP tools.

Supports:
- Server discovery from config
- Tool listing per server
- Tool execution with JSON-RPC
- Connection pooling and retry
- Proper MCP lifecycle handshake (initialize → initialized → tools/list)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.pg_connection import get_conn, release_conn

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
MCP_CONFIG_PATH = DATA_DIR / "mcp_servers.json"


def _ensure_tables() -> None:
    """Create MCP tables in PostgreSQL if they don't exist."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mcp_servers (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    command     TEXT NOT NULL,
                    args        TEXT NOT NULL DEFAULT '[]',
                    env         TEXT NOT NULL DEFAULT '{}',
                    description TEXT,
                    active      BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS mcp_tools (
                    id          TEXT PRIMARY KEY,
                    server_id   TEXT NOT NULL REFERENCES mcp_servers(id),
                    name        TEXT NOT NULL,
                    description TEXT,
                    parameters  TEXT NOT NULL DEFAULT '{}',
                    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS mcp_call_history (
                    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    server_id   TEXT NOT NULL,
                    tool_name   TEXT NOT NULL,
                    arguments   TEXT,
                    result      TEXT,
                    success     BOOLEAN NOT NULL DEFAULT TRUE,
                    latency_ms  DOUBLE PRECISION,
                    called_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_mcp_tools_server ON mcp_tools(server_id);
                CREATE INDEX IF NOT EXISTS idx_mcp_history_server ON mcp_call_history(server_id);
                CREATE INDEX IF NOT EXISTS idx_mcp_history_called ON mcp_call_history(called_at DESC);
            """)
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        release_conn(conn)


# Run on import
_ensure_tables()


# ── MCP Protocol Handshake ───────────────────────────────────────

MCP_PROTOCOL_VERSION = "2024-11-05"

def _build_initialize_request() -> str:
    """Build JSON-RPC initialize request per MCP spec."""
    return json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {
                "name": "pi-mcp-client",
                "version": "2.0.0",
            },
        },
    }) + "\n"


def _build_initialized_notification() -> str:
    """Build JSON-RPC initialized notification per MCP spec."""
    return json.dumps({
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
    }) + "\n"


def _build_tools_list_request() -> str:
    """Build JSON-RPC tools/list request."""
    return json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }) + "\n"


def _build_tool_call_request(tool_name: str, arguments: dict | None = None) -> str:
    """Build JSON-RPC tools/call request."""
    return json.dumps({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {},
        },
    }) + "\n"


async def _read_json_response(
    stdout: asyncio.StreamReader,
    timeout: float = 15.0,
) -> dict | None:
    """Read a single JSON-RPC response line from stdout."""
    try:
        line = await asyncio.wait_for(stdout.readline(), timeout=timeout)
        if not line:
            return None
        text = line.decode().strip()
        if text.startswith("{"):
            return json.loads(text)
    except (asyncio.TimeoutError, json.JSONDecodeError):
        pass
    return None


async def _mcp_handshake(
    proc: asyncio.subprocess.Process,
    stdout: asyncio.StreamReader,
) -> bool:
    """Perform MCP initialize → initialized handshake. Returns True on success."""
    # Step 1: Send initialize request
    proc.stdin.write(_build_initialize_request().encode())
    await proc.stdin.drain()

    # Step 2: Read initialize response
    response = await _read_json_response(stdout, timeout=10.0)
    if not response or "result" not in response:
        return False

    # Step 3: Send initialized notification
    proc.stdin.write(_build_initialized_notification().encode())
    await proc.stdin.drain()

    # Small delay to let server process the notification
    await asyncio.sleep(0.1)
    return True


# ── Server Management ────────────────────────────────────────────

def register_server(
    server_id: str,
    name: str,
    command: str,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    description: str = "",
) -> dict[str, Any]:
    """Register an MCP server configuration."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO mcp_servers (id, name, command, args, env, description)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET
                       name = EXCLUDED.name,
                       command = EXCLUDED.command,
                       args = EXCLUDED.args,
                       env = EXCLUDED.env,
                       description = EXCLUDED.description""",
                (
                    server_id,
                    name,
                    command,
                    json.dumps(args or []),
                    json.dumps(env or {}),
                    description,
                ),
            )
        conn.commit()
    finally:
        release_conn(conn)
    logger.info(f"MCP server registered: {server_id} ({name})")
    return {"id": server_id, "name": name, "command": command}


def list_servers(active_only: bool = True) -> list[dict[str, Any]]:
    """List registered MCP servers with discovered tool counts."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT s.*, COALESCE(tc.cnt, 0) as tool_count
                FROM mcp_servers s
                LEFT JOIN (
                    SELECT server_id, COUNT(*) as cnt FROM mcp_tools GROUP BY server_id
                ) tc ON tc.server_id = s.id
            """
            if active_only:
                query += " WHERE s.active = TRUE"
            cur.execute(query)
            rows = cur.fetchall()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "command": r["command"],
                    "args": json.loads(r["args"]) if isinstance(r["args"], str) else r["args"],
                    "description": r["description"],
                    "active": r["active"],
                    "tool_count": r["tool_count"],
                }
                for r in rows
            ]
    finally:
        release_conn(conn)


def remove_server(server_id: str) -> bool:
    """Deactivate an MCP server."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE mcp_servers SET active = FALSE WHERE id = %s", (server_id,)
            )
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    finally:
        release_conn(conn)


# ── Load from config file ────────────────────────────────────────

def load_servers_from_config(config_path: str | Path | None = None) -> int:
    """Load MCP server definitions from a JSON config file.
    
    Also deactivates servers that exist in DB but are no longer in the config,
    ensuring removed servers (like brave-search) don't persist.
    """
    path = Path(config_path) if config_path else MCP_CONFIG_PATH
    if not path.exists():
        return 0

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw = data.get("mcpServers", data.get("servers", {}))

    # Support both dict format {"id": {...config}} and list format [{...config}]
    if isinstance(raw, list):
        servers = {s["id"]: s for s in raw if "id" in s}
    else:
        servers = raw

    count = 0
    for sid, cfg in servers.items():
        register_server(
            server_id=sid,
            name=cfg.get("name", sid),
            command=cfg.get("command", ""),
            args=cfg.get("args", []),
            env=cfg.get("env", {}),
            description=cfg.get("description", ""),
        )
        count += 1

    # Deactivate servers not present in config file
    config_ids = set(servers.keys())
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM mcp_servers WHERE active = TRUE")
            db_ids = {r["id"] for r in cur.fetchall()}
            stale_ids = db_ids - config_ids
            if stale_ids:
                cur.execute(
                    "UPDATE mcp_servers SET active = FALSE WHERE id = ANY(%s)",
                    (list(stale_ids),),
                )
                logger.info(f"Deactivated {len(stale_ids)} stale MCP servers: {stale_ids}")
        conn.commit()
    finally:
        release_conn(conn)

    logger.info(f"Loaded {count} MCP servers from {path.name}")
    return count


# ── Tool Discovery (with proper MCP handshake) ──────────────────

async def discover_tools(server_id: str) -> list[dict[str, Any]]:
    """
    Discover available tools from an MCP server via JSON-RPC.
    Performs proper MCP lifecycle: initialize → initialized → tools/list.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM mcp_servers WHERE id = %s AND active = TRUE",
                (server_id,),
            )
            server = cur.fetchone()
    finally:
        release_conn(conn)

    if not server:
        return []

    command = server["command"]
    args = json.loads(server["args"]) if isinstance(server["args"], str) else server["args"]
    env_vars = json.loads(server["env"]) if isinstance(server["env"], str) else server["env"]

    try:
        env = {**os.environ, **{k: v for k, v in env_vars.items() if v}}

        proc = await asyncio.create_subprocess_exec(
            command, *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        # Perform MCP handshake
        handshake_ok = await _mcp_handshake(proc, proc.stdout)
        if not handshake_ok:
            logger.warning(f"MCP handshake failed for {server_id}, trying direct tools/list")
            # Fallback: some older servers might not need handshake
            # Kill and restart for clean state
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            proc = await asyncio.create_subprocess_exec(
                command, *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            # Try direct tools/list (legacy fallback)
            proc.stdin.write(_build_tools_list_request().encode())
            await proc.stdin.drain()
            response = await _read_json_response(proc.stdout, timeout=10.0)
        else:
            # Send tools/list after successful handshake
            proc.stdin.write(_build_tools_list_request().encode())
            await proc.stdin.drain()
            response = await _read_json_response(proc.stdout, timeout=10.0)

        # Clean up process
        try:
            proc.stdin.close()
            proc.kill()
            await proc.wait()
        except Exception:
            pass

        if not response or "result" not in response:
            logger.warning(f"No tools response from MCP server: {server_id}")
            return []

        tools = response.get("result", {}).get("tools", [])

        # Save discovered tools to DB
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                for tool in tools:
                    tool_id = f"{server_id}:{tool['name']}"
                    cur.execute(
                        """INSERT INTO mcp_tools (id, server_id, name, description, parameters)
                           VALUES (%s, %s, %s, %s, %s)
                           ON CONFLICT (id) DO UPDATE SET
                               description = EXCLUDED.description,
                               parameters = EXCLUDED.parameters,
                               discovered_at = NOW()""",
                        (
                            tool_id,
                            server_id,
                            tool["name"],
                            tool.get("description", ""),
                            json.dumps(tool.get("inputSchema", {})),
                        ),
                    )
            conn.commit()
        finally:
            release_conn(conn)

        logger.info(f"Discovered {len(tools)} tools from MCP server: {server_id}")
        return [
            {
                "id": f"{server_id}:{t['name']}",
                "name": t["name"],
                "description": t.get("description", ""),
                "server": server_id,
            }
            for t in tools
        ]

    except asyncio.TimeoutError:
        logger.warning(f"MCP server {server_id} timed out during tool discovery")
        return []
    except Exception as e:
        logger.error(f"MCP tool discovery failed for {server_id}: {e}")
        return []


def list_discovered_tools(server_id: str | None = None) -> list[dict[str, Any]]:
    """List previously discovered tools from DB."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if server_id:
                cur.execute("SELECT * FROM mcp_tools WHERE server_id = %s", (server_id,))
            else:
                cur.execute("SELECT * FROM mcp_tools")
            rows = cur.fetchall()
            return [
                {
                    "id": r["id"],
                    "server_id": r["server_id"],
                    "name": r["name"],
                    "description": r["description"],
                    "parameters": json.loads(r["parameters"]) if isinstance(r["parameters"], str) else r["parameters"],
                }
                for r in rows
            ]
    finally:
        release_conn(conn)


# ── Tool Execution (with proper MCP handshake) ──────────────────

async def call_mcp_tool(
    server_id: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    Execute a tool on an MCP server via JSON-RPC.
    Performs proper MCP lifecycle: initialize → initialized → tools/call.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM mcp_servers WHERE id = %s AND active = TRUE",
                (server_id,),
            )
            server = cur.fetchone()
    finally:
        release_conn(conn)

    if not server:
        return {"success": False, "error": f"Server '{server_id}' not found or inactive"}

    command = server["command"]
    args = json.loads(server["args"]) if isinstance(server["args"], str) else server["args"]
    env_vars = json.loads(server["env"]) if isinstance(server["env"], str) else server["env"]

    t0 = time.monotonic()
    try:
        env = {**os.environ, **{k: v for k, v in env_vars.items() if v}}

        proc = await asyncio.create_subprocess_exec(
            command, *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        # Perform MCP handshake
        handshake_ok = await _mcp_handshake(proc, proc.stdout)
        if not handshake_ok:
            logger.warning(f"MCP handshake failed for {server_id}, trying direct call")

        # Send tool call
        proc.stdin.write(_build_tool_call_request(tool_name, arguments).encode())
        await proc.stdin.drain()

        response = await _read_json_response(proc.stdout, timeout=timeout)

        # Clean up
        try:
            proc.stdin.close()
            proc.kill()
            await proc.wait()
        except Exception:
            pass

        latency_ms = (time.monotonic() - t0) * 1000

        if not response:
            _log_call(server_id, tool_name, arguments, "NO_RESPONSE", False, latency_ms)
            return {"success": False, "error": "No response from server", "server": server_id}

        if "error" in response:
            error_msg = json.dumps(response["error"])
            _log_call(server_id, tool_name, arguments, error_msg, False, latency_ms)
            return {"success": False, "error": error_msg, "server": server_id}

        result_data = response.get("result", {})
        content = result_data.get("content", [])
        text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
        result_text = "\n".join(text_parts) if text_parts else json.dumps(result_data)

        _log_call(server_id, tool_name, arguments, result_text, True, latency_ms)

        return {
            "success": True,
            "output": result_text,
            "latency_ms": round(latency_ms, 1),
            "server": server_id,
            "tool": tool_name,
        }

    except asyncio.TimeoutError:
        latency_ms = (time.monotonic() - t0) * 1000
        _log_call(server_id, tool_name, arguments, "TIMEOUT", False, latency_ms)
        return {"success": False, "error": f"Timeout after {timeout}s", "server": server_id}

    except Exception as e:
        latency_ms = (time.monotonic() - t0) * 1000
        _log_call(server_id, tool_name, arguments, str(e), False, latency_ms)
        return {"success": False, "error": str(e), "server": server_id}


def _log_call(
    server_id: str,
    tool_name: str,
    arguments: dict | None,
    result: str,
    success: bool,
    latency_ms: float,
) -> None:
    """Log MCP tool call to history."""
    try:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO mcp_call_history
                       (server_id, tool_name, arguments, result, success, latency_ms)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (
                        server_id,
                        tool_name,
                        json.dumps(arguments) if arguments else None,
                        result[:5000],
                        success,
                        latency_ms,
                    ),
                )
            conn.commit()
        finally:
            release_conn(conn)
    except Exception:
        pass


# ── Call History ─────────────────────────────────────────────────

def get_call_history(server_id: str | None = None, limit: int = 20) -> list[dict]:
    """Get recent MCP tool call history."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if server_id:
                cur.execute(
                    """SELECT server_id, tool_name, success, latency_ms, called_at
                       FROM mcp_call_history WHERE server_id = %s
                       ORDER BY called_at DESC LIMIT %s""",
                    (server_id, limit),
                )
            else:
                cur.execute(
                    """SELECT server_id, tool_name, success, latency_ms, called_at
                       FROM mcp_call_history ORDER BY called_at DESC LIMIT %s""",
                    (limit,),
                )
            rows = cur.fetchall()
            return [
                {
                    "server_id": r["server_id"],
                    "tool_name": r["tool_name"],
                    "success": r["success"],
                    "latency_ms": r["latency_ms"],
                    "called_at": str(r["called_at"]),
                }
                for r in rows
            ]
    finally:
        release_conn(conn)


# ── Default Server Seeding ───────────────────────────────────────

DEFAULT_MCP_SERVERS: list[dict] = [
    {
        "id": "fetch",
        "name": "Web Fetch",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {},
        "description": "URL content fetching",
    },
    {
        "id": "puppeteer",
        "name": "Puppeteer (Browser)",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "env": {},
        "description": "Headless browser for JS-rendered pages",
    },
    {
        "id": "arxiv",
        "name": "arXiv Research",
        "command": "uvx",
        "args": ["arxiv-mcp-server"],
        "env": {},
        "description": "Academic paper search",
    },
    {
        "id": "wikipedia",
        "name": "Wikipedia",
        "command": "npx",
        "args": ["-y", "wikipedia-mcp"],
        "env": {},
        "description": "Wikipedia search and content",
    },
    {
        "id": "yahoo-finance",
        "name": "Yahoo Finance",
        "command": "uvx",
        "args": ["mcp-yahoo-finance"],
        "env": {},
        "description": "Stock prices and financial data",
    },
    {
        "id": "time-mcp",
        "name": "Time & Timezone",
        "command": "uvx",
        "args": ["mcp-server-time"],
        "env": {},
        "description": "Real-time clock and timezone conversions",
    },
    {
        "id": "filesystem",
        "name": "Filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data"],
        "env": {},
        "description": "Local filesystem read/write for data/ directory",
    },
    {
        "id": "sequential-thinking",
        "name": "Sequential Thinking",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "env": {},
        "description": "Step-by-step reasoning chain",
    },
    {
        "id": "postgres",
        "name": "PostgreSQL",
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-postgres",
            "postgresql://agent:agent_secret_2024@postgres:5432/multiagent",
        ],
        "env": {},
        "description": "Direct PostgreSQL queries",
    },
    {
        "id": "sqlite",
        "name": "SQLite",
        "command": "uvx",
        "args": ["mcp-server-sqlite", "--db-path", "./data/memory.db"],
        "env": {},
        "description": "SQLite database queries",
    },
]


def seed_default_servers(overwrite: bool = False) -> int:
    """Register default MCP servers on first startup."""
    conn = get_conn()
    count = 0
    try:
        with conn.cursor() as cur:
            for srv in DEFAULT_MCP_SERVERS:
                if not overwrite:
                    cur.execute("SELECT id FROM mcp_servers WHERE id = %s", (srv["id"],))
                    if cur.fetchone():
                        continue
                register_server(
                    server_id=srv["id"],
                    name=srv["name"],
                    command=srv["command"],
                    args=srv["args"],
                    env=srv["env"],
                    description=srv["description"],
                )
                count += 1
    finally:
        release_conn(conn)
    if count:
        logger.info(f"Seeded {count} default MCP servers")
    return count


# ── Format for Agent Context ─────────────────────────────────────

def format_mcp_tools_for_agent(server_id: str | None = None) -> str:
    """Format discovered MCP tools for injection into agent context."""
    tools = list_discovered_tools(server_id)
    if not tools:
        return ""

    lines = ["--- AVAILABLE MCP TOOLS ---"]
    by_server: dict[str, list] = {}
    for t in tools:
        by_server.setdefault(t["server_id"], []).append(t)

    for sid, server_tools in by_server.items():
        lines.append(f"\n[{sid}]")
        for t in server_tools:
            lines.append(f"  • {t['name']}: {t['description'][:100]}")

    lines.append("--- END MCP TOOLS ---")
    return "\n".join(lines)
