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

# Base URL without trailing slash (app appends /search)
_SEARXNG_RAW = os.getenv(
    "SEARXNG_URL",
    "http://searxng-pwcsc8ow08oks0ggokwoo8ww.77.42.68.4.sslip.io",
)
SEARXNG_URL = _SEARXNG_RAW.rstrip("/") if _SEARXNG_RAW else ""

# ── Model Definitions ────────────────────────────────────────────

MODELS = {
    "orchestrator": {
        "id": "qwen/qwen3-next-80b-a3b-instruct",
        "name": "Qwen3 Next 80B",
        "role": "orchestrator",
        "description": "Orchestrator — task analysis, decomposition, routing, synthesis",
        "max_tokens": 4096,
        "temperature": 0.6,
        "top_p": 0.7,
        "has_thinking": False,
        "extra_body": None,
        "color": "#ec4899",
        "icon": "🧠",
    },
    "thinker": {
        "id": "minimaxai/minimax-m2.1",
        "name": "MiniMax M2.1",
        "role": "thinker",
        "description": "Deep Thinker — complex reasoning, analysis, planning",
        "max_tokens": 4096,
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
}

MODEL_KEYS = list(MODELS.keys())

# ── Agent Role → Model Key Mapping ───────────────────────────────

ROLE_TO_MODEL = {cfg["role"]: key for key, cfg in MODELS.items()}

# ── Paths ────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data"
THREADS_DIR = DATA_DIR / "threads"

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agent:agent_secret_2024@localhost:5432/multiagent")


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
