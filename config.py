"""
Multi-Agent Dashboard Configuration.
5 NVIDIA models — Qwen orchestrator + 4 specialists.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# .env dosyasını bul — birden fazla olası konum
_config_dir = Path(__file__).parent
for _env_path in [
    _config_dir / ".env",              # multi-agent-dashboard/.env
    _config_dir.parent / ".env",       # workspace root/.env
]:
    if _env_path.exists():
        load_dotenv(_env_path)
        break
else:
    load_dotenv()  # fallback: default .env search

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# ── PI AI Gateway ────────────────────────────────────────────────
PI_GATEWAY_URL = os.getenv("PI_GATEWAY_URL", "http://localhost:3100")
PI_GATEWAY_ENABLED = os.getenv("PI_GATEWAY_ENABLED", "false").lower() == "true"
PI_GATEWAY_FALLBACK_ENABLED = os.getenv("PI_GATEWAY_FALLBACK_ENABLED", "true").lower() == "true"
PI_GATEWAY_FALLBACK_MAX_RETRIES = int(os.getenv("PI_GATEWAY_FALLBACK_MAX_RETRIES", "2"))

# Streaming configuration (Faz 14.2)
PI_GATEWAY_STREAMING_ENABLED = os.getenv("PI_GATEWAY_STREAMING_ENABLED", "true").lower() == "true"

# Whoogle — self-hosted Google proxy (format=json API, needs session cookie)
_WHOOGLE_RAW = os.getenv(
    "WHOOGLE_URL",
    "http://whoogle-e4s8oc4kkc8sokcsco808ccw.77.42.68.4.sslip.io",
)
WHOOGLE_URL = _WHOOGLE_RAW.rstrip("/") if _WHOOGLE_RAW else ""

# ── Model Definitions ────────────────────────────────────────────

MODELS = {
    "orchestrator": {
        "id": "deepseek-chat",
        "name": "DeepSeek Chat",
        "role": "orchestrator",
        "description": "Orchestrator — intent analysis, pipeline selection, task routing, synthesis",
        "max_tokens": 4096,
        "temperature": 0.5,
        "top_p": 0.9,
        "has_thinking": False,
        "extra_body": None,
        "color": "#ec4899",
        "icon": "🧠",
        "base_url": "deepseek",
    },
    "thinker": {
        "id": "minimaxai/minimax-m2.1",
        "name": "MiniMax M2.1",
        "role": "thinker",
        "description": "Deep Thinker — complex reasoning, analysis, planning",
        "max_tokens": 8192,
        "temperature": 0.7,
        "top_p": 0.95,
        "has_thinking": True,
        "extra_body": None,
        "color": "#00e5ff",
        "icon": "🔬",
    },
    "speed": {
        "id": "stepfun-ai/step-3.5-flash",
        "name": "Step 3.5 Flash",
        "role": "speed",
        "description": "Speed Agent — quick responses, code generation, formatting",
        "max_tokens": 16384,
        "temperature": 1.0,
        "top_p": 0.9,
        "has_thinking": False,
        "extra_body": None,
        "color": "#a78bfa",
        "icon": "⚡",
    },
    "researcher": {
        "id": "z-ai/glm4.7",
        "name": "GLM 4.7",
        "role": "researcher",
        "description": "Research Agent — web search, data gathering, summarization",
        "max_tokens": 4096,
        "temperature": 1.0,
        "top_p": 1.0,
        "has_thinking": False,
        "extra_body": {
            "chat_template_kwargs": {"enable_thinking": False, "clear_thinking": True}
        },
        "color": "#f59e0b",
        "icon": "🔍",
    },
    "reasoner": {
        "id": "nvidia/nemotron-3-nano-30b-a3b",
        "name": "Nemotron 3 Nano",
        "role": "reasoner",
        "description": "Reasoner — chain-of-thought, math, logic, verification",
        "max_tokens": 16384,
        "temperature": 1.0,
        "top_p": 1.0,
        "has_thinking": True,
        "extra_body": {
            "reasoning_budget": 8192,
            "chat_template_kwargs": {"enable_thinking": True},
        },
        "color": "#10b981",
        "icon": "🌊",
    },
    "critic": {
        "id": "qwen/qwen3-next-80b-a3b-instruct",
        "name": "Qwen3 Next 80B",
        "role": "critic",
        "description": "Critic + Skill Creator — quality review, fact-checking, skill generation, improvement suggestions",
        "max_tokens": 8192,
        "temperature": 0.6,
        "top_p": 0.7,
        "has_thinking": False,
        "extra_body": None,
        "color": "#06b6d4",
        "icon": "🎯",
    },
}

MODEL_KEYS = list(MODELS.keys())

# ── Gateway Multi-Provider Model Definitions ─────────────────────

GATEWAY_MODELS = {
    "orchestrator": {
        "primary": {"id": "deepseek-chat", "provider": "deepseek"},
        "alternatives": [
            {"id": "qwen/qwen3-next-80b-a3b-instruct", "provider": "nvidia"},
            {"id": "claude-sonnet-4-20250514", "provider": "anthropic"},
        ],
    },
    "thinker": {
        "primary": {"id": "minimaxai/minimax-m2.1", "provider": "nvidia"},
        "alternatives": [
            {"id": "claude-sonnet-4-20250514", "provider": "anthropic"},
            {"id": "gemini-2.5-pro-preview-06-05", "provider": "google"},
        ],
    },
    "speed": {
        "primary": {"id": "stepfun-ai/step-3.5-flash", "provider": "nvidia"},
        "alternatives": [
            {"id": "llama-3.3-70b-versatile", "provider": "groq"},
            {"id": "gpt-4o-mini", "provider": "openai"},
        ],
    },
    "researcher": {
        "primary": {"id": "z-ai/glm4.7", "provider": "nvidia"},
        "alternatives": [
            {"id": "gemini-2.5-flash-preview-05-20", "provider": "google"},
            {"id": "mistral-large-latest", "provider": "mistral"},
        ],
    },
    "reasoner": {
        "primary": {"id": "nvidia/nemotron-3-nano-30b-a3b", "provider": "nvidia"},
        "alternatives": [
            {"id": "claude-sonnet-4-20250514", "provider": "anthropic"},
            {"id": "o4-mini", "provider": "openai"},
        ],
    },
    "critic": {
        "primary": {"id": "qwen/qwen3-next-80b-a3b-instruct", "provider": "nvidia"},
        "alternatives": [
            {"id": "deepseek-chat", "provider": "deepseek"},
            {"id": "claude-sonnet-4-20250514", "provider": "anthropic"},
        ],
    },
}

# ── Agent Role → Model Key Mapping ───────────────────────────────

ROLE_TO_MODEL = {cfg["role"]: key for key, cfg in MODELS.items()}

# ── Runtime Standardization / Rollout Flags (Faz 15.3-15.5) ─────

RUNTIME_EVENT_SCHEMA_VERSION = os.getenv("RUNTIME_EVENT_SCHEMA_VERSION", "2")


def _env_flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default).lower()).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


FEATURE_FLAGS = {
    "runtime_event_v2": _env_flag("FEATURE_RUNTIME_EVENT_V2", True),
    "steering_queue_v2": _env_flag("FEATURE_STEERING_QUEUE_V2", True),
    "provider_registry_v2": _env_flag("FEATURE_PROVIDER_REGISTRY_V2", True),
    "sandbox_executor_v1": _env_flag("FEATURE_SANDBOX_EXECUTOR_V1", True),
    "session_queueing_v1": _env_flag("FEATURE_SESSION_QUEUEING_V1", True),
    "scheduled_events_v1": _env_flag("FEATURE_SCHEDULED_EVENTS_V1", True),
    "telemetry_runtime_v1": _env_flag("FEATURE_TELEMETRY_RUNTIME_V1", True),
}


def _resolve_model_key(model_key_or_role: str) -> str:
    return ROLE_TO_MODEL.get(model_key_or_role, model_key_or_role)


def _get_gateway_config(model_key_or_role: str) -> dict | None:
    model_key = _resolve_model_key(model_key_or_role)
    return GATEWAY_MODELS.get(model_key)


def _get_primary_provider(model_key_or_role: str) -> str:
    model_key = _resolve_model_key(model_key_or_role)
    gateway_cfg = _get_gateway_config(model_key)
    if gateway_cfg and gateway_cfg.get("primary", {}).get("provider"):
        return str(gateway_cfg["primary"]["provider"])
    return str(MODELS[model_key].get("base_url", "nvidia"))


def _get_primary_model_id(model_key_or_role: str) -> str:
    model_key = _resolve_model_key(model_key_or_role)
    gateway_cfg = _get_gateway_config(model_key)
    if gateway_cfg and gateway_cfg.get("primary", {}).get("id"):
        return str(gateway_cfg["primary"]["id"])
    return str(MODELS[model_key]["id"])


MODEL_CAPABILITIES = {
    model_key: {
        "reasoning": bool(cfg.get("has_thinking")),
        "thinking": bool(cfg.get("has_thinking")),
        "streaming": bool(PI_GATEWAY_STREAMING_ENABLED),
        "tool_calls": True,
        "steering": True,
        "follow_up": True,
        "gateway_routing": model_key in GATEWAY_MODELS,
        "fallback": bool(PI_GATEWAY_FALLBACK_ENABLED and model_key in GATEWAY_MODELS),
        "vision": False,
    }
    for model_key, cfg in MODELS.items()
}


PROVIDER_REGISTRY = {
    model_key: {
        "role": cfg["role"],
        "primary_provider": _get_primary_provider(model_key),
        "primary_model": _get_primary_model_id(model_key),
        "alternatives": list((_get_gateway_config(model_key) or {}).get("alternatives", [])),
        "gateway_enabled": bool(PI_GATEWAY_ENABLED and model_key in GATEWAY_MODELS),
        "gateway_url": PI_GATEWAY_URL if PI_GATEWAY_ENABLED else None,
        "fallback_enabled": bool(PI_GATEWAY_FALLBACK_ENABLED and model_key in GATEWAY_MODELS),
    }
    for model_key, cfg in MODELS.items()
}


def get_feature_flags() -> dict[str, bool]:
    return dict(FEATURE_FLAGS)


def is_feature_enabled(flag_name: str, default: bool = False) -> bool:
    return bool(FEATURE_FLAGS.get(flag_name, default))


def get_model_capabilities(model_key_or_role: str) -> dict[str, bool | str]:
    model_key = _resolve_model_key(model_key_or_role)
    capabilities: dict[str, bool | str] = {
        key: value for key, value in MODEL_CAPABILITIES.get(model_key, {}).items()
    }
    capabilities["model_key"] = model_key
    capabilities["role"] = MODELS[model_key]["role"]
    return capabilities


def get_provider_registry_entry(model_key_or_role: str) -> dict[str, object]:
    model_key = _resolve_model_key(model_key_or_role)
    entry = dict(PROVIDER_REGISTRY.get(model_key, {}))
    entry["model_key"] = model_key
    return entry


def get_provider_registry_summary() -> dict[str, object]:
    return {
        "gateway_enabled": PI_GATEWAY_ENABLED,
        "fallback_enabled": PI_GATEWAY_FALLBACK_ENABLED,
        "streaming_enabled": PI_GATEWAY_STREAMING_ENABLED,
        "runtime_schema_version": RUNTIME_EVENT_SCHEMA_VERSION,
        "roles": {
            model_key: {
                "primary_provider": entry["primary_provider"],
                "primary_model": entry["primary_model"],
                "alternative_count": len(entry.get("alternatives", [])),
                "gateway_enabled": entry["gateway_enabled"],
                "fallback_enabled": entry["fallback_enabled"],
            }
            for model_key, entry in PROVIDER_REGISTRY.items()
        },
    }

# ── Paths ────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data"
THREADS_DIR = DATA_DIR / "threads"

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:518518Erkan@localhost:5432/multiagent")


# ── Iterative Eval Runtime Config ───────────────────────────────

ITERATIVE_EVAL_MODE = os.getenv("ITERATIVE_EVAL_MODE", "auto").strip().lower()
ITERATIVE_EVAL_DEFAULT_MAX_ROUNDS = int(
    os.getenv("ITERATIVE_EVAL_DEFAULT_MAX_ROUNDS", "3")
)
ITERATIVE_EVAL_FAST_MAX_ROUNDS = int(os.getenv("ITERATIVE_EVAL_FAST_MAX_ROUNDS", "1"))
ITERATIVE_EVAL_FULL_SCORE_THRESHOLD = float(
    os.getenv("ITERATIVE_EVAL_FULL_SCORE_THRESHOLD", "0.8")
)
ITERATIVE_EVAL_FAST_SCORE_THRESHOLD = float(
    os.getenv("ITERATIVE_EVAL_FAST_SCORE_THRESHOLD", "0.65")
)
ITERATIVE_EVAL_MIN_IMPROVEMENT_DELTA = float(
    os.getenv("ITERATIVE_EVAL_MIN_IMPROVEMENT_DELTA", "0.05")
)


def _safe_int(value: str, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: str, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _normalize_iterative_mode(raw: str) -> str:
    mode = (raw or "").strip().lower()
    return mode if mode in {"auto", "fast", "full"} else "auto"


def get_iterative_eval_runtime_config() -> dict[str, float | int | str]:
    """
    Resolve iterative-eval settings from process env at call time.
    Allows runtime toggling via env updates without code changes.
    """
    mode = _normalize_iterative_mode(
        os.getenv("ITERATIVE_EVAL_MODE", ITERATIVE_EVAL_MODE)
    )
    default_rounds = max(
        1,
        _safe_int(
            os.getenv(
                "ITERATIVE_EVAL_DEFAULT_MAX_ROUNDS",
                str(ITERATIVE_EVAL_DEFAULT_MAX_ROUNDS),
            ),
            ITERATIVE_EVAL_DEFAULT_MAX_ROUNDS,
        ),
    )
    fast_rounds = max(
        1,
        _safe_int(
            os.getenv(
                "ITERATIVE_EVAL_FAST_MAX_ROUNDS", str(ITERATIVE_EVAL_FAST_MAX_ROUNDS)
            ),
            ITERATIVE_EVAL_FAST_MAX_ROUNDS,
        ),
    )
    full_threshold = max(
        0.0,
        min(
            1.0,
            _safe_float(
                os.getenv(
                    "ITERATIVE_EVAL_FULL_SCORE_THRESHOLD",
                    str(ITERATIVE_EVAL_FULL_SCORE_THRESHOLD),
                ),
                ITERATIVE_EVAL_FULL_SCORE_THRESHOLD,
            ),
        ),
    )
    fast_threshold = max(
        0.0,
        min(
            1.0,
            _safe_float(
                os.getenv(
                    "ITERATIVE_EVAL_FAST_SCORE_THRESHOLD",
                    str(ITERATIVE_EVAL_FAST_SCORE_THRESHOLD),
                ),
                ITERATIVE_EVAL_FAST_SCORE_THRESHOLD,
            ),
        ),
    )
    min_delta = max(
        0.0,
        _safe_float(
            os.getenv(
                "ITERATIVE_EVAL_MIN_IMPROVEMENT_DELTA",
                str(ITERATIVE_EVAL_MIN_IMPROVEMENT_DELTA),
            ),
            ITERATIVE_EVAL_MIN_IMPROVEMENT_DELTA,
        ),
    )

    return {
        "mode": mode,
        "default_max_rounds": default_rounds,
        "fast_max_rounds": fast_rounds,
        "full_score_threshold": full_threshold,
        "fast_score_threshold": fast_threshold,
        "min_improvement_delta": min_delta,
    }


# ── Reflexion / Self-Evaluation Settings ───────────────────────────────

# ── YouTube Proxy (cloud IP ban workaround) ──────────────────────
# Generic HTTP/HTTPS proxy for YouTube transcript fetching
# Format: http://user:pass@host:port or http://host:port
YOUTUBE_PROXY_URL = os.getenv("YOUTUBE_PROXY_URL", "")

# Webshare residential proxy (recommended for youtube_transcript_api)
WEBSHARE_PROXY_USERNAME = os.getenv("WEBSHARE_PROXY_USERNAME", "")
WEBSHARE_PROXY_PASSWORD = os.getenv("WEBSHARE_PROXY_PASSWORD", "")

# Cookie-based auth (last resort — YouTube may ban the account)
YOUTUBE_COOKIES_PATH = os.getenv("YOUTUBE_COOKIES_PATH", "")

# Enable automatic self-evaluation after each agent response
REFLEXION_ENABLED = os.getenv("REFLEXION_ENABLED", "true").lower() == "true"

# Minimum score threshold for improvement (1-5 scale)
REFLEXION_SCORE_THRESHOLD = float(os.getenv("REFLEXION_SCORE_THRESHOLD", "3.5"))

# Which agents should use reflexion (comma-separated, empty = all)
REFLEXION_AGENTS = os.getenv("REFLEXION_AGENTS", "").split(",") if os.getenv("REFLEXION_AGENTS") else []

# Auto-improve if score below threshold
REFLEXION_AUTO_IMPROVE = os.getenv("REFLEXION_AUTO_IMPROVE", "true").lower() == "true"

# Max improvement iterations per response
REFLEXION_MAX_ITERATIONS = int(os.getenv("REFLEXION_MAX_ITERATIONS", "1"))
