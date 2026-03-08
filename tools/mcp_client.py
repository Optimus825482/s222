"""
MCP Client — Model Context Protocol integration.
Connects agents to external services (GitHub, Slack, databases, etc.)
via the MCP protocol. Generic wrapper that discovers and calls MCP tools.

Supports:
- Server discovery from config
- Tool listing per server
- Tool execution with JSON-RPC
- Connection pooling and retry
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
MCP_CONFIG_PATH = DATA_DIR / "mcp_servers.json"
MCP_DB_PATH = DATA_DIR / "mcp_history.db"

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(MCP_DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _init_schema(_conn)
    return _conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS mcp_servers (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            command     TEXT NOT NULL,
            args        TEXT NOT NULL DEFAULT '[]',
            env         TEXT NOT NULL DEFAULT '{}',
            description TEXT,
            active      INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mcp_tools (
            id          TEXT PRIMARY KEY,
            server_id   TEXT NOT NULL,
            name        TEXT NOT NULL,
            description TEXT,
            parameters  TEXT NOT NULL DEFAULT '{}',
            discovered_at TEXT NOT NULL,
            FOREIGN KEY (server_id) REFERENCES mcp_servers(id)
        );

        CREATE TABLE IF NOT EXISTS mcp_call_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id   TEXT NOT NULL,
            tool_name   TEXT NOT NULL,
            arguments   TEXT,
            result      TEXT,
            success     INTEGER NOT NULL DEFAULT 1,
            latency_ms  REAL,
            called_at   TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_mcp_tools_server ON mcp_tools(server_id);
        CREATE INDEX IF NOT EXISTS idx_mcp_history_server ON mcp_call_history(server_id);
    """)


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
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """INSERT OR REPLACE INTO mcp_servers (id, name, command, args, env, description, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            server_id,
            name,
            command,
            json.dumps(args or []),
            json.dumps(env or {}),
            description,
            now,
        ),
    )
    conn.commit()
    logger.info(f"MCP server registered: {server_id} ({name})")
    return {"id": server_id, "name": name, "command": command}


def list_servers(active_only: bool = True) -> list[dict[str, Any]]:
    """List registered MCP servers with discovered tool counts."""
    conn = _get_conn()
    query = "SELECT * FROM mcp_servers"
    if active_only:
        query += " WHERE active = 1"
    rows = conn.execute(query).fetchall()

    # Get tool counts per server in one query
    tool_counts: dict[str, int] = {}
    try:
        tc_rows = conn.execute(
            "SELECT server_id, COUNT(*) as cnt FROM mcp_tools GROUP BY server_id"
        ).fetchall()
        tool_counts = {r["server_id"]: r["cnt"] for r in tc_rows}
    except Exception:
        pass

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "command": r["command"],
            "args": json.loads(r["args"]),
            "description": r["description"],
            "active": bool(r["active"]),
            "tool_count": tool_counts.get(r["id"], 0),
        }
        for r in rows
    ]


def remove_server(server_id: str) -> bool:
    """Deactivate an MCP server."""
    conn = _get_conn()
    cur = conn.execute(
        "UPDATE mcp_servers SET active = 0 WHERE id = ?", (server_id,)
    )
    conn.commit()
    return cur.rowcount > 0


# ── Load from config file ────────────────────────────────────────

def load_servers_from_config(config_path: str | Path | None = None) -> int:
    """Load MCP server definitions from a JSON config file."""
    path = Path(config_path) if config_path else MCP_CONFIG_PATH
    if not path.exists():
        return 0

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    servers = data.get("mcpServers", data.get("servers", {}))
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

    logger.info(f"Loaded {count} MCP servers from {path.name}")
    return count


# ── Tool Discovery ───────────────────────────────────────────────

async def discover_tools(server_id: str) -> list[dict[str, Any]]:
    """
    Discover available tools from an MCP server via JSON-RPC.
    Starts the server process, sends tools/list, parses response.
    """
    conn = _get_conn()
    server = conn.execute(
        "SELECT * FROM mcp_servers WHERE id = ? AND active = 1", (server_id,)
    ).fetchone()

    if not server:
        return []

    command = server["command"]
    args = json.loads(server["args"])
    env_vars = json.loads(server["env"])

    try:
        import os
        env = {**os.environ, **env_vars}

        # JSON-RPC request for tools/list
        request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }) + "\n"

        proc = await asyncio.create_subprocess_exec(
            command, *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=request.encode()),
            timeout=15.0,
        )

        response = json.loads(stdout.decode().strip().split("\n")[-1])
        tools = response.get("result", {}).get("tools", [])

        # Save discovered tools to DB
        now = datetime.now(timezone.utc).isoformat()
        for tool in tools:
            tool_id = f"{server_id}:{tool['name']}"
            conn.execute(
                """INSERT OR REPLACE INTO mcp_tools (id, server_id, name, description, parameters, discovered_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    tool_id,
                    server_id,
                    tool["name"],
                    tool.get("description", ""),
                    json.dumps(tool.get("inputSchema", {})),
                    now,
                ),
            )
        conn.commit()

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
    conn = _get_conn()
    if server_id:
        rows = conn.execute(
            "SELECT * FROM mcp_tools WHERE server_id = ?", (server_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM mcp_tools").fetchall()

    return [
        {
            "id": r["id"],
            "server_id": r["server_id"],
            "name": r["name"],
            "description": r["description"],
            "parameters": json.loads(r["parameters"]),
        }
        for r in rows
    ]


# ── Tool Execution ───────────────────────────────────────────────

async def call_mcp_tool(
    server_id: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """
    Execute a tool on an MCP server via JSON-RPC.
    Returns result dict with success status, output, and latency.
    """
    import time
    conn = _get_conn()

    server = conn.execute(
        "SELECT * FROM mcp_servers WHERE id = ? AND active = 1", (server_id,)
    ).fetchone()

    if not server:
        return {"success": False, "error": f"Server '{server_id}' not found or inactive"}

    command = server["command"]
    args = json.loads(server["args"])
    env_vars = json.loads(server["env"])

    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {},
        },
    }) + "\n"

    t0 = time.monotonic()
    try:
        import os
        env = {**os.environ, **env_vars}

        proc = await asyncio.create_subprocess_exec(
            command, *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=request.encode()),
            timeout=timeout,
        )

        latency_ms = (time.monotonic() - t0) * 1000
        output = stdout.decode().strip()

        # Parse last JSON line (skip any logging output)
        json_lines = [l for l in output.split("\n") if l.strip().startswith("{")]
        if json_lines:
            response = json.loads(json_lines[-1])
            result_data = response.get("result", {})
            content = result_data.get("content", [])
            text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
            result_text = "\n".join(text_parts) if text_parts else json.dumps(result_data)
        else:
            result_text = output
            response = {}

        success = "error" not in response
        _log_call(server_id, tool_name, arguments, result_text, success, latency_ms)

        return {
            "success": success,
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
        conn = _get_conn()
        conn.execute(
            """INSERT INTO mcp_call_history (server_id, tool_name, arguments, result, success, latency_ms, called_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                server_id,
                tool_name,
                json.dumps(arguments) if arguments else None,
                result[:5000],
                int(success),
                latency_ms,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    except Exception:
        pass


# ── Call History ─────────────────────────────────────────────────

def get_call_history(server_id: str | None = None, limit: int = 20) -> list[dict]:
    """Get recent MCP tool call history."""
    conn = _get_conn()
    if server_id:
        rows = conn.execute(
            "SELECT * FROM mcp_call_history WHERE server_id = ? ORDER BY called_at DESC LIMIT ?",
            (server_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM mcp_call_history ORDER BY called_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    return [
        {
            "server_id": r["server_id"],
            "tool_name": r["tool_name"],
            "success": bool(r["success"]),
            "latency_ms": r["latency_ms"],
            "called_at": r["called_at"],
        }
        for r in rows
    ]


# ── Default Server Seeding ───────────────────────────────────────

DEFAULT_MCP_SERVERS: list[dict] = [
    # ── Arama & İçerik ───────────────────────────────────────────
    {
        "id": "brave-search",
        "name": "Brave Search",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "env": {"BRAVE_API_KEY": ""},
        "description": "Brave Search API — Whoogle'a ek olarak ikinci web arama motoru",
    },
    {
        "id": "fetch",
        "name": "Web Fetch",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {},
        "description": "URL içerik çekme — JS gerektirmeyen sayfalar, API yanıtları, ham HTML",
    },
    {
        "id": "puppeteer",
        "name": "Puppeteer (Browser)",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "env": {},
        "description": "Headless browser — JS gerektiren sayfalar, SPA'lar, screenshot, form doldurma",
    },
    # ── Akademik & Bilgi ─────────────────────────────────────────
    {
        "id": "arxiv",
        "name": "arXiv Research",
        "command": "uvx",
        "args": ["mcp-server-arxiv"],
        "env": {},
        "description": "arXiv akademik makale arama — AI/ML/CS araştırmaları için thinker/researcher agent'a kritik",
    },
    {
        "id": "wikipedia",
        "name": "Wikipedia",
        "command": "uvx",
        "args": ["mcp-server-wikipedia-search"],
        "env": {},
        "description": "Wikipedia arama ve içerik çekme — genel bilgi, tanımlar, tarihsel veriler",
    },
    # ── Veri & Finans ────────────────────────────────────────────
    {
        "id": "yahoo-finance",
        "name": "Yahoo Finance",
        "command": "uvx",
        "args": ["mcp-yahoo-finance"],
        "env": {},
        "description": "Hisse senedi fiyatları, finansal veriler, piyasa haberleri — finans analizleri için",
    },
    {
        "id": "time-mcp",
        "name": "Time & Timezone",
        "command": "uvx",
        "args": ["mcp-server-time"],
        "env": {},
        "description": "Gerçek zamanlı saat ve timezone dönüşümleri — agent'ların tarih/saat hesaplamaları için",
    },
    # ── Dosya & Veri İşleme ──────────────────────────────────────
    {
        "id": "filesystem",
        "name": "Filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data"],
        "env": {},
        "description": "Yerel dosya sistemi okuma/yazma — data/ dizinine erişim, proje dosyaları",
    },
    {
        "id": "sequential-thinking",
        "name": "Sequential Thinking",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "env": {},
        "description": "Adım adım düşünme zinciri — karmaşık problem çözme, reasoner agent için ideal",
    },
    # ── Veritabanı ───────────────────────────────────────────────
    {
        "id": "postgres",
        "name": "PostgreSQL",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"],
        "env": {"POSTGRES_CONNECTION_STRING": ""},
        "description": "Direkt PostgreSQL sorguları — veritabanı analizi, şema keşfi, veri sorgulama",
    },
    {
        "id": "sqlite",
        "name": "SQLite",
        "command": "uvx",
        "args": ["mcp-server-sqlite", "--db-path", "./data/memory.db"],
        "env": {},
        "description": "SQLite veritabanı sorguları — yerel DB analizi, data/ klasöründeki DB'lere erişim",
    },
]


def seed_default_servers(overwrite: bool = False) -> int:
    """
    Register default MCP servers for orchestration on first startup.
    Skips servers already registered unless overwrite=True.
    Returns count of newly registered servers.
    """
    conn = _get_conn()
    count = 0
    for srv in DEFAULT_MCP_SERVERS:
        existing = conn.execute(
            "SELECT id FROM mcp_servers WHERE id = ?", (srv["id"],)
        ).fetchone()
        if existing and not overwrite:
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
