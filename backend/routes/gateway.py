"""
Pi-AI Gateway Management Routes.
Proxy endpoints for managing the LLM gateway service.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

_parent = str(Path(__file__).parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from deps import get_current_user, _audit
from config import PI_GATEWAY_URL, PI_GATEWAY_ENABLED, PI_GATEWAY_FALLBACK_ENABLED, PI_GATEWAY_FALLBACK_MAX_RETRIES, GATEWAY_MODELS, DATA_DIR

logger = logging.getLogger(__name__)

router = APIRouter(tags=["gateway"])

# ── Helpers ──────────────────────────────────────────────────────

MAPPING_FILE = DATA_DIR / "gateway_model_mapping.json"
HTTP_TIMEOUT = 10.0


def _gateway_base_url() -> str:
    """Strip /v1 suffix to get the gateway root URL."""
    url = PI_GATEWAY_URL.rstrip("/")
    if url.endswith("/v1"):
        return url[:-3]
    return url


def _ensure_gateway():
    """Raise 503 if gateway is not enabled."""
    if not PI_GATEWAY_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Pi-AI Gateway is not enabled. Set PI_GATEWAY_ENABLED=true.",
        )


def _load_overrides() -> dict[str, Any]:
    """Load runtime model mapping overrides from JSON file."""
    if MAPPING_FILE.exists():
        try:
            return json.loads(MAPPING_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to read gateway model mapping file, using defaults")
    return {}


def _save_overrides(overrides: dict[str, Any]):
    """Persist model mapping overrides to JSON file."""
    MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
    MAPPING_FILE.write_text(
        json.dumps(overrides, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _build_mapping() -> dict[str, Any]:
    """Build the full role → model mapping with overrides applied."""
    overrides = _load_overrides()
    result = {}
    for role, cfg in GATEWAY_MODELS.items():
        primary = cfg.get("primary", {})
        alternatives = cfg.get("alternatives", [])
        if role in overrides:
            ov = overrides[role]
            result[role] = {
                "current_model": ov.get("model_id", primary.get("id")),
                "provider": ov.get("provider", primary.get("provider")),
                "alternatives": alternatives,
                "is_override": True,
            }
        else:
            result[role] = {
                "current_model": primary.get("id"),
                "provider": primary.get("provider"),
                "alternatives": alternatives,
                "is_override": False,
            }
    return result


# ── Request Models ───────────────────────────────────────────────

class ModelMappingUpdate(BaseModel):
    role: str
    model_id: str
    provider: str


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/api/gateway/health")
async def gateway_health(user: dict = Depends(get_current_user)):
    """Check gateway health status."""
    _ensure_gateway()
    base = _gateway_base_url()
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(f"{base}/health")
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": "connected",
                "url": PI_GATEWAY_URL,
                "uptime": data.get("uptime", 0),
                "total_requests": data.get("total_requests", 0),
                "avg_latency_ms": data.get("avg_latency_ms", 0),
            }
    except Exception as e:
        logger.warning(f"Gateway health check failed: {e}")
        return {
            "status": "disconnected",
            "url": PI_GATEWAY_URL,
            "uptime": 0,
            "total_requests": 0,
            "avg_latency_ms": 0,
        }


@router.get("/api/gateway/providers")
async def gateway_providers(user: dict = Depends(get_current_user)):
    """List all providers and their status."""
    _ensure_gateway()
    base = _gateway_base_url()
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(f"{base}/api/providers")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Gateway providers fetch failed: {e}")
        raise HTTPException(status_code=502, detail=f"Gateway unreachable: {e}")


@router.get("/api/gateway/models")
async def gateway_models(user: dict = Depends(get_current_user)):
    """List all available models (OpenAI-compatible)."""
    _ensure_gateway()
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(f"{PI_GATEWAY_URL}/models")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Gateway models fetch failed: {e}")
        raise HTTPException(status_code=502, detail=f"Gateway unreachable: {e}")


@router.get("/api/gateway/model-mapping")
async def get_model_mapping(user: dict = Depends(get_current_user)):
    """Get current agent-model mapping with overrides applied."""
    _ensure_gateway()
    return _build_mapping()


@router.post("/api/gateway/model-mapping")
async def update_model_mapping(
    body: ModelMappingUpdate,
    user: dict = Depends(get_current_user),
):
    """Update agent-model mapping for a specific role."""
    _ensure_gateway()
    if body.role not in GATEWAY_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown role: {body.role}. Valid roles: {list(GATEWAY_MODELS.keys())}",
        )
    _audit("gateway_model_mapping_update", user["user_id"], detail=f"{body.role} → {body.model_id}")
    overrides = _load_overrides()
    overrides[body.role] = {"model_id": body.model_id, "provider": body.provider}
    _save_overrides(overrides)
    return _build_mapping()


@router.delete("/api/gateway/model-mapping/{role}")
async def reset_model_mapping(role: str, user: dict = Depends(get_current_user)):
    """Reset a role's model mapping back to default."""
    _ensure_gateway()
    if role not in GATEWAY_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown role: {role}. Valid roles: {list(GATEWAY_MODELS.keys())}",
        )
    _audit("gateway_model_mapping_reset", user["user_id"], detail=role)
    overrides = _load_overrides()
    overrides.pop(role, None)
    _save_overrides(overrides)
    # Return the default mapping for this role
    primary = GATEWAY_MODELS[role].get("primary", {})
    return {
        "role": role,
        "current_model": primary.get("id"),
        "provider": primary.get("provider"),
        "alternatives": GATEWAY_MODELS[role].get("alternatives", []),
        "is_override": False,
    }


@router.get("/api/gateway/fallback-config")
async def get_fallback_config(user: dict = Depends(get_current_user)):
    """Get provider fallback configuration and per-role fallback chains."""
    _ensure_gateway()
    chains = {}
    for role, cfg in GATEWAY_MODELS.items():
        primary = cfg.get("primary", {})
        alternatives = cfg.get("alternatives", [])
        chains[role] = {
            "primary": f"{primary.get('provider', '?')}/{primary.get('id', '?')}",
            "fallbacks": [
                f"{alt.get('provider', '?')}/{alt.get('id', '?')}"
                for alt in alternatives
            ],
            "total_providers": 1 + len(alternatives),
        }
    return {
        "enabled": PI_GATEWAY_FALLBACK_ENABLED,
        "max_retries": PI_GATEWAY_FALLBACK_MAX_RETRIES,
        "chains": chains,
    }


# ── Tool Schema Registry (Faz 14.3) ─────────────────────────────

@router.get("/api/gateway/tool-schemas")
async def list_tool_schemas(user: dict = Depends(get_current_user)):
    """List all registered tool schemas with summary info."""
    from tools.tool_schema_registry import get_all_schemas_summary
    return {"schemas": get_all_schemas_summary()}


@router.get("/api/gateway/tool-validation-stats")
async def tool_validation_stats(user: dict = Depends(get_current_user)):
    """Get tool validation statistics from both local and gateway."""
    from tools.tool_schema_registry import get_local_stats, get_gateway_stats
    local = get_local_stats()
    gateway = await get_gateway_stats()
    return {"local": local, "gateway": gateway}


@router.post("/api/gateway/tool-schemas/sync")
async def sync_tool_schemas(user: dict = Depends(get_current_user)):
    """Register all tool schemas with the gateway."""
    _ensure_gateway()
    _audit("gateway_tool_schema_sync", user["user_id"])
    from tools.tool_schema_registry import register_with_gateway
    result = await register_with_gateway()
    return result


@router.post("/api/gateway/tool-validate")
async def validate_tool(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """Validate tool arguments against schema (local validation)."""
    tool_name = body.get("tool_name")
    args = body.get("arguments", {})
    if not tool_name:
        raise HTTPException(status_code=400, detail="tool_name required")
    from tools.tool_schema_registry import validate_tool_args
    return validate_tool_args(tool_name, args)
