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

SEARXNG_URL = os.getenv(
    "SEARXNG_URL",
    "http://searxng-pwcsc8ow08oks0ggokwoo8ww.77.42.68.4.sslip.io",
)

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
        "max_tokens": 16384,
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
