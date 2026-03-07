"""Performance Benchmarking Suite for multi-agent system.

Runs standardised scenarios against agents, scores outputs with
weighted heuristics, and persists results in SQLite for trend
analysis and head-to-head comparisons.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
BENCH_DB_PATH = DATA_DIR / "benchmarks.db"

# ---------------------------------------------------------------------------
# Predefined benchmark scenarios
# ---------------------------------------------------------------------------

BENCHMARK_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "speed-simple-qa",
        "name": "Basit Soru-Cevap Hızı",
        "category": "speed",
        "prompt": "Python'da bir listenin elemanlarını ters çevirmek için 3 farklı yöntem göster. Kısa ve öz cevap ver.",
        "expected_traits": ["reverse", "[::-1]", "reversed"],
        "max_score": 5.0,
        "timeout_sec": 30,
    },
    {
        "id": "speed-translation",
        "name": "Hızlı Çeviri",
        "category": "speed",
        "prompt": "Şu cümleyi İngilizce'ye çevir: 'Yapay zeka, modern yazılım geliştirmenin vazgeçilmez bir parçası haline geldi.'",
        "expected_traits": ["artificial intelligence", "software", "development"],
        "max_score": 5.0,
        "timeout_sec": 20,
    },
    {
        "id": "quality-report",
        "name": "Detaylı Rapor Kalitesi",
        "category": "quality",
        "prompt": (
            "Mikroservis mimarisinin monolitik mimariye göre avantaj ve dezavantajlarını "
            "detaylı bir rapor olarak yaz. Başlıklar, maddeler ve örnekler kullan."
        ),
        "expected_traits": ["mikroservis", "monolitik", "avantaj", "dezavantaj", "ölçeklen"],
        "max_score": 5.0,
        "timeout_sec": 60,
    },
    {
        "id": "quality-code-review",
        "name": "Kod İnceleme Kalitesi",
        "category": "quality",
        "prompt": (
            "Şu Python kodunu incele ve iyileştirme önerileri sun:\n"
            "```python\n"
            "def calc(x,y,op):\n"
            "  if op=='+':\n"
            "    return x+y\n"
            "  if op=='-':\n"
            "    return x-y\n"
            "  if op=='*':\n"
            "    return x*y\n"
            "  if op=='/':\n"
            "    return x/y\n"
            "```"
        ),
        "expected_traits": ["ZeroDivisionError", "type hint", "elif", "docstring"],
        "max_score": 5.0,
        "timeout_sec": 45,
    },
    {
        "id": "reasoning-math",
        "name": "Matematiksel Muhakeme",
        "category": "reasoning",
        "prompt": (
            "Bir çiftçinin 120 koyunu var. İlk yıl sürüsü %25 arttı, ikinci yıl %20 azaldı. "
            "Üçüncü yıl başında kaç koyunu vardır? Adım adım çöz."
        ),
        "expected_traits": ["150", "120", "adım", "sonuç"],
        "max_score": 5.0,
        "timeout_sec": 45,
    },
    {
        "id": "reasoning-logic",
        "name": "Mantık Problemi",
        "category": "reasoning",
        "prompt": (
            "Ali, Berk ve Can yan yana oturuyor. Ali en solda değil. "
            "Berk, Can'ın yanında oturmuyor. Oturma düzenini bul ve açıkla."
        ),
        "expected_traits": ["Can", "Ali", "Berk", "sol", "sağ", "orta"],
        "max_score": 5.0,
        "timeout_sec": 45,
    },
    {
        "id": "tool-use-search",
        "name": "Araç Kullanımı — Web Arama",
        "category": "tool_use",
        "prompt": "2025 yılında en popüler 3 JavaScript framework'ünü araştır ve karşılaştır.",
        "expected_traits": ["React", "Vue", "Next", "Angular", "Svelte"],
        "max_score": 5.0,
        "timeout_sec": 90,
    },
    {
        "id": "creativity-story",
        "name": "Yaratıcı İçerik Üretimi",
        "category": "creativity",
        "prompt": (
            "Bir yapay zeka asistanının kendi bilincine vardığı anı anlatan "
            "200 kelimelik kısa bir hikaye yaz. Duygusal ve etkileyici olsun."
        ),
        "expected_traits": ["bilinç", "farkında", "düşün", "hisset", "yapay"],
        "max_score": 5.0,
        "timeout_sec": 60,
    },
]


def get_scenarios(category: str | None = None) -> list[dict]:
    """Return benchmark scenarios, optionally filtered by *category*."""
    if category is None:
        return list(BENCHMARK_SCENARIOS)
    return [s for s in BENCHMARK_SCENARIOS if s["category"] == category]


# ---------------------------------------------------------------------------
# BenchmarkRunner
# ---------------------------------------------------------------------------

class BenchmarkRunner:
    """Execute benchmark scenarios against agents and persist scored results."""

    def __init__(self) -> None:
        self._ensure_db()

    # -- database -----------------------------------------------------------

    def _ensure_db(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(BENCH_DB_PATH))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS benchmark_results (
                    id            TEXT PRIMARY KEY,
                    agent_role    TEXT NOT NULL,
                    scenario_id   TEXT NOT NULL,
                    scenario_name TEXT NOT NULL,
                    category      TEXT NOT NULL,
                    score         REAL NOT NULL,
                    max_score     REAL NOT NULL,
                    latency_ms    REAL NOT NULL,
                    tokens_used   INTEGER NOT NULL DEFAULT 0,
                    output_preview TEXT,
                    dimensions    TEXT,
                    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_br_agent ON benchmark_results(agent_role)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_br_scenario ON benchmark_results(scenario_id)"
            )
            conn.commit()
        finally:
            conn.close()

    def _store_result(self, result: dict) -> None:
        conn = sqlite3.connect(str(BENCH_DB_PATH))
        try:
            conn.execute(
                """
                INSERT INTO benchmark_results
                    (id, agent_role, scenario_id, scenario_name, category,
                     score, max_score, latency_ms, tokens_used,
                     output_preview, dimensions, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    result["id"],
                    result["agent_role"],
                    result["scenario_id"],
                    result["scenario_name"],
                    result["category"],
                    result["score"],
                    result["max_score"],
                    result["latency_ms"],
                    result["tokens_used"],
                    result["output_preview"],
                    json.dumps(result["dimensions"], ensure_ascii=False),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    # -- scoring ------------------------------------------------------------

    def _score_output(
        self, output: str, scenario: dict, latency_ms: float
    ) -> dict:
        dimensions: dict[str, float] = {}

        # 1. Substance (length quality)
        length = len(output)
        if length < 50:
            dimensions["substance"] = 1.0
        elif length < 200:
            dimensions["substance"] = 2.5
        elif length < 1000:
            dimensions["substance"] = 4.0
        elif length < 3000:
            dimensions["substance"] = 4.5
        else:
            dimensions["substance"] = 3.5

        # 2. Structure
        s = 2.0
        if "\n" in output:
            s += 0.5
        if any(m in output for m in ["- ", "* ", "1.", "•"]):
            s += 0.5
        if any(m in output for m in ["##", "**", "###"]):
            s += 0.5
        if "```" in output:
            s += 0.5
        dimensions["structure"] = min(s, 5.0)

        # 3. Trait matching (key differentiator)
        traits = scenario["expected_traits"]
        if traits:
            matches = sum(1 for t in traits if t.lower() in output.lower())
            dimensions["trait_match"] = min(5.0, (matches / len(traits)) * 5.0)
        else:
            dimensions["trait_match"] = 3.0

        # 4. Reliability (no errors)
        r = 5.0
        for marker in ["[Error]", "[Warning]", "failed", "timeout", "exception"]:
            if marker.lower() in output.lower():
                r -= 1.0
        dimensions["reliability"] = max(r, 1.0)

        # 5. Speed (relative to timeout)
        timeout_ms = scenario["timeout_sec"] * 1000
        ratio = latency_ms / timeout_ms if timeout_ms else 1
        if ratio < 0.3:
            dimensions["speed"] = 5.0
        elif ratio < 0.5:
            dimensions["speed"] = 4.0
        elif ratio < 0.7:
            dimensions["speed"] = 3.0
        elif ratio < 1.0:
            dimensions["speed"] = 2.0
        else:
            dimensions["speed"] = 1.0

        weights = {
            "substance": 0.25,
            "structure": 0.15,
            "trait_match": 0.30,
            "reliability": 0.15,
            "speed": 0.15,
        }
        total = sum(dimensions[k] * weights[k] for k in weights)

        return {
            "score": round(total, 2),
            "dimensions": {k: round(v, 1) for k, v in dimensions.items()},
        }

    # -- run ----------------------------------------------------------------

    async def run_single(self, agent_role: str, scenario_id: str) -> dict:
        """Run one scenario against one agent and return the scored result."""
        from agents import create_agent
        from core.state import Thread

        scenario = next(
            (s for s in BENCHMARK_SCENARIOS if s["id"] == scenario_id), None
        )
        if scenario is None:
            raise ValueError(f"Unknown scenario: {scenario_id}")

        agent = create_agent(agent_role)
        thread = Thread()

        output = ""
        tokens_used = 0
        start = time.perf_counter()
        try:
            result_raw = await asyncio.wait_for(
                agent.execute(scenario["prompt"], thread),
                timeout=scenario["timeout_sec"],
            )
            latency_ms = (time.perf_counter() - start) * 1000

            if isinstance(result_raw, dict):
                output = result_raw.get("output", str(result_raw))
                tokens_used = result_raw.get("tokens_used", 0)
            else:
                output = str(result_raw)
        except asyncio.TimeoutError:
            latency_ms = scenario["timeout_sec"] * 1000
            output = "[Error] Timeout: agent did not respond in time."
            logger.warning(
                "Timeout for agent=%s scenario=%s", agent_role, scenario_id
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            output = f"[Error] {type(exc).__name__}: {exc}"
            logger.exception(
                "Error running scenario %s for agent %s", scenario_id, agent_role
            )

        scoring = self._score_output(output, scenario, latency_ms)

        result: dict[str, Any] = {
            "id": uuid.uuid4().hex,
            "agent_role": agent_role,
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "category": scenario["category"],
            "score": scoring["score"],
            "max_score": scenario["max_score"],
            "latency_ms": round(latency_ms, 1),
            "tokens_used": tokens_used,
            "output_preview": output[:500],
            "dimensions": scoring["dimensions"],
        }

        self._store_result(result)
        logger.info(
            "Benchmark %s | %s | score=%.2f | latency=%.0fms",
            agent_role,
            scenario_id,
            result["score"],
            latency_ms,
        )
        return result

    async def run_suite(
        self,
        agent_role: str | None = None,
        category: str | None = None,
    ) -> dict:
        """Run multiple scenarios and return an aggregated summary."""
        from agents import create_agent

        scenarios = get_scenarios(category)
        if not scenarios:
            return {"error": "No scenarios found", "results": []}

        # Determine which agents to benchmark
        if agent_role:
            roles = [agent_role]
        else:
            # Fallback: run for a default set (caller should specify)
            roles = ["assistant"]

        all_results: list[dict] = []
        for role in roles:
            for scenario in scenarios:
                try:
                    res = await self.run_single(role, scenario["id"])
                    all_results.append(res)
                except Exception as exc:
                    logger.exception(
                        "Suite error: role=%s scenario=%s", role, scenario["id"]
                    )
                    all_results.append(
                        {
                            "agent_role": role,
                            "scenario_id": scenario["id"],
                            "error": str(exc),
                        }
                    )

        scored = [r for r in all_results if "score" in r]
        avg_score = (
            round(sum(r["score"] for r in scored) / len(scored), 2)
            if scored
            else 0.0
        )
        avg_latency = (
            round(sum(r["latency_ms"] for r in scored) / len(scored), 1)
            if scored
            else 0.0
        )

        return {
            "total_runs": len(all_results),
            "successful": len(scored),
            "failed": len(all_results) - len(scored),
            "avg_score": avg_score,
            "avg_latency_ms": avg_latency,
            "results": all_results,
        }

    # -- queries ------------------------------------------------------------

    def get_results(
        self, agent_role: str | None = None, limit: int = 100
    ) -> list[dict]:
        """Fetch stored benchmark results."""
        conn = sqlite3.connect(str(BENCH_DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            if agent_role:
                rows = conn.execute(
                    "SELECT * FROM benchmark_results WHERE agent_role = ? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (agent_role, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM benchmark_results ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def get_leaderboard(self) -> list[dict]:
        """Aggregated scores per agent, sorted descending."""
        conn = sqlite3.connect(str(BENCH_DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT
                    agent_role,
                    COUNT(*)          AS total_runs,
                    ROUND(AVG(score), 2)      AS avg_score,
                    ROUND(MAX(score), 2)      AS best_score,
                    ROUND(MIN(score), 2)      AS worst_score,
                    ROUND(AVG(latency_ms), 1) AS avg_latency_ms
                FROM benchmark_results
                GROUP BY agent_role
                ORDER BY avg_score DESC
                """
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_history(
        self, agent_role: str, scenario_id: str | None = None
    ) -> list[dict]:
        """Historical scores for trend analysis."""
        conn = sqlite3.connect(str(BENCH_DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            if scenario_id:
                rows = conn.execute(
                    "SELECT * FROM benchmark_results "
                    "WHERE agent_role = ? AND scenario_id = ? "
                    "ORDER BY created_at ASC",
                    (agent_role, scenario_id),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM benchmark_results "
                    "WHERE agent_role = ? ORDER BY created_at ASC",
                    (agent_role,),
                ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def compare_agents(self, role_a: str, role_b: str) -> dict:
        """Head-to-head comparison between two agents."""
        conn = sqlite3.connect(str(BENCH_DB_PATH))
        conn.row_factory = sqlite3.Row
        try:
            def _agent_stats(role: str) -> dict:
                row = conn.execute(
                    """
                    SELECT
                        COUNT(*)                  AS total_runs,
                        ROUND(AVG(score), 2)      AS avg_score,
                        ROUND(AVG(latency_ms), 1) AS avg_latency_ms
                    FROM benchmark_results
                    WHERE agent_role = ?
                    """,
                    (role,),
                ).fetchone()
                if row is None or row["total_runs"] == 0:
                    return {"total_runs": 0, "avg_score": 0.0, "avg_latency_ms": 0.0}
                return dict(row)

            def _category_scores(role: str) -> dict[str, float]:
                rows = conn.execute(
                    """
                    SELECT category, ROUND(AVG(score), 2) AS avg
                    FROM benchmark_results
                    WHERE agent_role = ?
                    GROUP BY category
                    """,
                    (role,),
                ).fetchall()
                return {r["category"]: r["avg"] for r in rows}

            stats_a = _agent_stats(role_a)
            stats_b = _agent_stats(role_b)
            cats_a = _category_scores(role_a)
            cats_b = _category_scores(role_b)

            all_cats = sorted(set(cats_a) | set(cats_b))
            category_comparison = {}
            for cat in all_cats:
                sa = cats_a.get(cat, 0.0)
                sb = cats_b.get(cat, 0.0)
                category_comparison[cat] = {
                    role_a: sa,
                    role_b: sb,
                    "winner": role_a if sa > sb else (role_b if sb > sa else "tie"),
                }

            overall_winner = "tie"
            if stats_a["avg_score"] > stats_b["avg_score"]:
                overall_winner = role_a
            elif stats_b["avg_score"] > stats_a["avg_score"]:
                overall_winner = role_b

            return {
                role_a: stats_a,
                role_b: stats_b,
                "category_comparison": category_comparison,
                "overall_winner": overall_winner,
            }
        finally:
            conn.close()

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        if "dimensions" in d and isinstance(d["dimensions"], str):
            try:
                d["dimensions"] = json.loads(d["dimensions"])
            except (json.JSONDecodeError, TypeError):
                pass
        return d
