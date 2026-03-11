"""
Code Executor — Sandboxed code execution for agents.
Inspired by Autogen's code generation + execution + debug loop.

Supports Python execution in a subprocess sandbox.
Captures stdout, stderr, and return values.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Safety limits
MAX_EXECUTION_TIME = 30  # seconds
MAX_OUTPUT_SIZE = 50_000  # characters
ALLOWED_LANGUAGES = {"python", "javascript", "bash"}

# Dangerous patterns to block
_DANGEROUS_PATTERNS = [
    "os.system",
    "subprocess.call",
    "subprocess.run",
    "subprocess.Popen",
    "__import__('os')",
    "shutil.rmtree",
    "os.remove",
    "os.unlink",
    "open('/etc",
    "open('C:\\\\",
    "eval(",
    "exec(",
    "importlib",
    "ctypes",
    "socket.connect",
    "requests.delete",
    "httpx.delete",
]


def get_executor_capabilities() -> dict[str, Any]:
    """Describe the current execution backend and safety envelope."""
    return {
        "mode": "host_subprocess",
        "isolation_level": "basic",
        "workspace_isolation": False,
        "docker_backed": False,
        "allowed_languages": sorted(ALLOWED_LANGUAGES),
        "max_execution_time_seconds": MAX_EXECUTION_TIME,
        "max_output_size": MAX_OUTPUT_SIZE,
        "blocked_pattern_count": len(_DANGEROUS_PATTERNS),
    }


def _check_safety(code: str) -> tuple[bool, str]:
    """Check code for dangerous patterns. Returns (is_safe, reason)."""
    for pattern in _DANGEROUS_PATTERNS:
        if pattern in code:
            return False, f"Blocked dangerous pattern: {pattern}"
    return True, "OK"


async def execute_code(
    code: str,
    language: str = "python",
    timeout: int = MAX_EXECUTION_TIME,
) -> dict[str, Any]:
    """
    Execute code in a sandboxed subprocess.
    Returns dict with stdout, stderr, return_code, execution_time.
    """
    language = language.lower()
    if language not in ALLOWED_LANGUAGES:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Unsupported language: {language}. Allowed: {', '.join(ALLOWED_LANGUAGES)}",
            "return_code": -1,
            "execution_time_ms": 0,
        }

    # Safety check
    is_safe, reason = _check_safety(code)
    if not is_safe:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Security check failed: {reason}",
            "return_code": -1,
            "execution_time_ms": 0,
        }

    # Write code to temp file
    suffix_map = {"python": ".py", "javascript": ".js", "bash": ".sh"}
    suffix = suffix_map.get(language, ".py")

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            temp_path = f.name

        # Build command
        cmd_map = {
            "python": ["python", "-u", temp_path],
            "javascript": ["node", temp_path],
            "bash": ["bash", temp_path],
        }
        cmd = cmd_map[language]

        # Execute
        t0 = time.monotonic()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir(),
                env={"PATH": "/usr/bin:/usr/local/bin", "HOME": tempfile.gettempdir()},
            )
            execution_time = (time.monotonic() - t0) * 1000

            stdout = result.stdout[:MAX_OUTPUT_SIZE]
            stderr = result.stderr[:MAX_OUTPUT_SIZE]

            return {
                "success": result.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": result.returncode,
                "execution_time_ms": round(execution_time, 1),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout}s",
                "return_code": -1,
                "execution_time_ms": timeout * 1000,
            }

    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution error: {type(e).__name__}: {e}",
            "return_code": -1,
            "execution_time_ms": 0,
        }
    finally:
        # Cleanup temp file
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass


def format_execution_result(result: dict[str, Any]) -> str:
    """Format execution result for LLM context."""
    status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
    parts = [f"Code Execution {status} ({result['execution_time_ms']:.0f}ms)"]

    if result["stdout"]:
        parts.append(f"\n--- STDOUT ---\n{result['stdout']}")
    if result["stderr"]:
        parts.append(f"\n--- STDERR ---\n{result['stderr']}")
    if not result["stdout"] and not result["stderr"]:
        parts.append("\n(no output)")

    return "\n".join(parts)
