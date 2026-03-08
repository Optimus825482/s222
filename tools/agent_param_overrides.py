"""
Agent parameter overrides — Faz 12.1.
Persisted per-role overrides (temperature, max_tokens, top_p) applied on top of config.MODELS.
Apply-learning writes here; agents read via get_effective_config().
"""

from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
OVERRIDES_PATH = DATA_DIR / "agent_param_overrides.json"

ALLOWED_OVERRIDE_KEYS = frozenset({"temperature", "max_tokens", "top_p"})


def _load_raw() -> dict[str, dict]:
    if not OVERRIDES_PATH.exists():
        return {}
    try:
        with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("agent_param_overrides: load failed: %s", e)
        return {}


def _save_raw(data: dict[str, dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OVERRIDES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_overrides(role: str | None = None) -> dict:
    """Return overrides for one role or all roles. Only allowed keys are included."""
    raw = _load_raw()
    if role is not None:
        per_role = raw.get(role) or {}
        return {k: v for k, v in per_role.items() if k in ALLOWED_OVERRIDE_KEYS}
    return {r: {k: v for k, v in (raw.get(r) or {}).items() if k in ALLOWED_OVERRIDE_KEYS} for r in raw}


def set_overrides(role: str, overrides: dict) -> None:
    """Set overrides for a role. Only temperature, max_tokens, top_p are persisted."""
    filtered = {k: v for k, v in overrides.items() if k in ALLOWED_OVERRIDE_KEYS}
    if not filtered:
        return
    raw = _load_raw()
    current = raw.get(role) or {}
    current.update(filtered)
    raw[role] = current
    _save_raw(raw)
    logger.info("agent_param_overrides: updated %s: %s", role, list(filtered.keys()))


def clear_overrides(role: str | None = None) -> None:
    """Clear overrides for one role or all roles."""
    if role is None:
        _save_raw({})
        logger.info("agent_param_overrides: cleared all")
        return
    raw = _load_raw()
    if role in raw:
        del raw[role]
        _save_raw(raw)
        logger.info("agent_param_overrides: cleared %s", role)


def get_effective_config(role: str) -> dict:
    """
    Return merged config for role: config.MODELS[role] + persisted overrides.
    Use this in agents when building LLM request (temperature, max_tokens, top_p, etc.).
    """
    from config import MODELS

    base = dict(MODELS.get(role, {}))
    overrides = get_overrides(role)
    if overrides:
        base.update(overrides)
    return base
