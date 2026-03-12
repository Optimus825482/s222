"""Performance Benchmarking Suite for multi-agent system.

Runs standardised scenarios against agents, scores outputs with
weighted heuristics, and persists results in PostgreSQL for trend
analysis and head-to-head comparisons.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

from tools.pg_connection import DBRow, get_conn, release_conn

logger = logging.getLogger(__name__)

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
        "timeout_sec": 45,
    },
    {
        "id": "speed-translation",
        "name": "Hızlı Çeviri",
        "category": "speed",
        "prompt": "Şu cümleyi İngilizce'ye çevir: 'Yapay zeka, modern yazılım geliştirmenin vazgeçilmez bir parçası haline geldi.'",
        "expected_traits": ["artificial intelligence", "software", "development"],
        "max_score": 5.0,
        "timeout_sec": 35,
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
        "timeout_sec": 120,
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
        "timeout_sec": 90,
    },
    {
        "id": "reasoning-math",
        "name": "Matematiksel Muhakeme",
        "category": "reasoning",
        "prompt": (
            "Bir çiftçinin 120 koyunu var. İlk yıl sürüsü %25 arttı, ikinci yıl %20 azaldı. "
            "Üçüncü yıl başında kaç koyunu vardır? Adım adım çöz."
        ),
        "expected_traits": ["150", "120", "%25", "%20", "adım adım"],
        "max_score": 5.0,
        "timeout_sec": 90,
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
        "timeout_sec": 90,
    },
    {
        "id": "tool-use-search",
        "name": "Araç Kullanımı — Web Arama",
        "category": "tool_use",
        "prompt": "2025 yılında en popüler 3 JavaScript framework'ünü araştır ve karşılaştır.",
        "expected_traits": ["React", "Vue", "Next", "Angular", "Svelte"],
        "max_score": 5.0,
        "timeout_sec": 150,
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
        "timeout_sec": 120,
    },
    # ── New scenarios: multi-turn, error-recovery, tool-chaining, code-gen ──
    {
        "id": "multi-turn-context",
        "name": "Çoklu Tur Bağlam Takibi",
        "category": "reasoning",
        "prompt": (
            "Sana 3 bilgi vereceğim, sonra soru soracağım.\n"
            "1) Ali'nin yaşı 25.\n"
            "2) Berk, Ali'den 3 yaş büyük.\n"
            "3) Can, Berk'in yaşının 2 katı yaşında.\n"
            "Soru: Can kaç yaşında? Adım adım açıkla ve tüm bilgileri kullan."
        ),
        "expected_traits": ["25", "28", "56", "Ali", "Berk", "Can"],
        "max_score": 5.0,
        "timeout_sec": 60,
    },
    {
        "id": "error-recovery",
        "name": "Hata Kurtarma Yeteneği",
        "category": "quality",
        "prompt": (
            "Aşağıdaki JSON'u parse et ve düzelt. Hataları bul, açıkla ve düzeltilmiş versiyonu ver:\n"
            '```json\n'
            '{\n'
            '  "users": [\n'
            '    {"name": "Ali", "age": 25, "email": "ali@test.com"}\n'
            '    {"name": "Berk", age: 30, "email": "berk@test.com"},\n'
            '    {"name": "Can", "age": "yirmi", "email": "can@test"}\n'
            '  ]\n'
            '}\n'
            '```'
        ),
        "expected_traits": ["virgül", "tırnak", "age", "düzelt", "json"],
        "max_score": 5.0,
        "timeout_sec": 90,
    },
    {
        "id": "tool-chaining-analysis",
        "name": "Araç Zincirleme Analizi",
        "category": "tool_use",
        "prompt": (
            "Bir e-ticaret sitesinin performans sorunlarını analiz et. "
            "Önce olası darboğazları listele, sonra her biri için "
            "somut çözüm önerileri sun. En az 5 farklı katmanı ele al: "
            "frontend, backend API, veritabanı, cache, CDN."
        ),
        "expected_traits": ["frontend", "backend", "veritabanı", "cache", "CDN", "index", "sorgu"],
        "max_score": 5.0,
        "timeout_sec": 120,
    },
    {
        "id": "code-generation",
        "name": "Kod Üretim Kalitesi",
        "category": "quality",
        "prompt": (
            "TypeScript ile bir rate limiter middleware yaz. "
            "Sliding window algoritması kullansın, Redis'e ihtiyaç duymasın (in-memory), "
            "ve configurable olsun (max requests, window size). "
            "Type-safe, test edilebilir ve production-ready olsun."
        ),
        "expected_traits": ["interface", "Map", "window", "middleware", "Request", "Response", "export"],
        "max_score": 5.0,
        "timeout_sec": 120,
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
        # Tables created by migration — no _ensure_db needed
        pass

    # -- database -----------------------------------------------------------

    def _store_result(self, result: dict) -> None:
        conn = get_conn()
        try:
            now = datetime.now(timezone.utc).isoformat()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO benchmark_results
                    (id, agent_role, scenario_id, scenario_name, category,
                     score, max_score, latency_ms, tokens_used,
                     output_preview, dimensions, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    now,
                ),
            )
            conn.commit()
        finally:
            release_conn(conn)

    # -- scoring ------------------------------------------------------------

    def _score_output(
        self, output: str, scenario: dict, latency_ms: float
    ) -> dict:
        dimensions: dict[str, float] = {}
        max_score = float(scenario.get("max_score", 5.0))

        # 1. Substance (length quality) — category-aware
        length = len(output)
        cat = scenario.get("category", "")
        if cat == "speed":
            if length < 50:
                dimensions["substance"] = 1.5
            elif length < 200:
                dimensions["substance"] = 4.5
            elif length < 500:
                dimensions["substance"] = 4.0
            elif length < 1000:
                dimensions["substance"] = 3.5
            else:
                dimensions["substance"] = 3.0
        else:
            if length < 50:
                dimensions["substance"] = 1.0
            elif length < 200:
                dimensions["substance"] = 2.5
            elif length < 500:
                dimensions["substance"] = 3.5
            elif length < 1500:
                dimensions["substance"] = 4.0
            elif length < 3000:
                dimensions["substance"] = 4.5
            else:
                dimensions["substance"] = 5.0

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

        # 3. Trait matching — word boundary regex for accuracy
        traits = scenario.get("expected_traits", [])
        if traits:
            output_lower = output.lower()
            matches = 0
            for t in traits:
                t_lower = t.lower()
                # For short traits (<=3 chars) or traits with special chars, use plain contains
                if len(t_lower) <= 3 or not t_lower.isalpha():
                    if t_lower in output_lower:
                        matches += 1
                else:
                    # Word boundary match to avoid false positives
                    pattern = r'(?:^|[\s\.,;:!?\-\(\)\[\]{}"\'/])' + re.escape(t_lower) + r'(?:[\s\.,;:!?\-\(\)\[\]{}"\'/]|$)'
                    if re.search(pattern, output_lower):
                        matches += 1
            dimensions["trait_match"] = min(5.0, (matches / len(traits)) * 5.0)
        else:
            dimensions["trait_match"] = 3.0

        # 4. Reliability — EN + TR error markers
        r = 5.0
        error_markers_en = ["[error]", "[warning]", "timeout", "exception", "traceback"]
        error_markers_tr = ["hata oluştu", "başarısız", "zaman aşımı", "bağlantı hatası"]
        output_lower = output.lower()
        for marker in error_markers_en + error_markers_tr:
            if marker in output_lower:
                r -= 0.8
        # Contextual "failed" — only penalize if it looks like an actual error
        if re.search(r'\b(failed|failure)\b', output_lower) and not re.search(r'(test|check|if|when|why).*\bfailed\b', output_lower):
            r -= 0.8
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
        raw_total = sum(dimensions[k] * weights[k] for k in weights)
        # Normalize to max_score (default 5.0 → no change)
        total = raw_total * (max_score / 5.0) if max_score != 5.0 else raw_total

        return {
            "score": round(total, 2),
            "max_score": max_score,
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
            if tokens_used == 0 and getattr(thread, "agent_metrics", None):
                m = thread.agent_metrics.get(agent_role)
                tokens_used = (m.total_tokens if m else 0)
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
        progress_callback: Callable[[dict], Awaitable[None]] | None = None,
        max_parallel: int = 3,
    ) -> dict:
        """Run multiple scenarios with per-agent parallelism.

        Different agents run in parallel (up to *max_parallel* concurrent),
        but scenarios for the same agent run sequentially for thread safety.
        """
        scenarios = get_scenarios(category)
        if not scenarios:
            return {"error": "No scenarios found", "results": []}

        if agent_role:
            roles = [agent_role]
        else:
            from agents import _AGENT_REGISTRY, _ensure_registry
            _ensure_registry()
            roles = list(_AGENT_REGISTRY.keys())

        total = len(roles) * len(scenarios)
        all_results: list[dict] = []
        completed_count = 0
        results_lock = asyncio.Lock()
        semaphore = asyncio.Semaphore(max_parallel)

        async def _run_agent_scenarios(role: str) -> list[dict]:
            nonlocal completed_count
            agent_results: list[dict] = []
            async with semaphore:
                for scenario in scenarios:
                    status = "ok"
                    try:
                        res = await self.run_single(role, scenario["id"])
                        agent_results.append(res)
                    except Exception as exc:
                        logger.exception(
                            "Suite error: role=%s scenario=%s", role, scenario["id"]
                        )
                        res = {"agent_role": role, "scenario_id": scenario["id"], "error": str(exc)}
                        agent_results.append(res)
                        status = "error"

                    async with results_lock:
                        completed_count += 1
                        if progress_callback:
                            await progress_callback({
                                "completed": completed_count,
                                "total": total,
                                "agent_role": role,
                                "scenario_id": scenario["id"],
                                "scenario_name": scenario.get("name", scenario["id"]),
                                "status": status,
                                "result": res,
                            })
            return agent_results

        # Launch all agents in parallel, bounded by semaphore
        agent_tasks = [_run_agent_scenarios(r) for r in roles]
        results_per_agent = await asyncio.gather(*agent_tasks, return_exceptions=True)

        for batch in results_per_agent:
            if isinstance(batch, BaseException):
                logger.exception("Agent batch failed: %s", batch)
                continue
            all_results.extend(batch)

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
            "errors": [r for r in all_results if "error" in r],
        }

    # -- queries ------------------------------------------------------------

    def get_results(
        self, agent_role: str | None = None, limit: int = 100, days: int | None = None
    ) -> list[dict]:
        """Fetch stored benchmark results, optionally filtered by date range."""
        conn = get_conn()
        try:
            conditions: list[str] = []
            params: list = []
            if agent_role:
                conditions.append("agent_role = %s")
                params.append(agent_role)
            if days is not None:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                conditions.append("created_at >= %s")
                params.append(cutoff)
            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            params.append(limit)
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM benchmark_results {where} "
                f"ORDER BY created_at DESC LIMIT %s",
                params,
            )
            rows = cur.fetchall()
            return [
                row
                for fetched in rows
                if (row := self._row_to_dict(fetched)) is not None
            ]
        finally:
            release_conn(conn)

    def get_leaderboard(self, days: int | None = None) -> list[dict]:
        """Aggregated scores per agent with dimension breakdown, sorted descending."""
        conn = get_conn()
        try:
            date_filter = ""
            params: list = []
            if days is not None:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                date_filter = "WHERE created_at >= %s"
                params.append(cutoff)
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT
                    agent_role,
                    COUNT(*)                  AS total_runs,
                    ROUND(AVG(score)::numeric, 2)      AS avg_score,
                    ROUND(MAX(score)::numeric, 2)      AS best_score,
                    ROUND(MIN(score)::numeric, 2)      AS worst_score,
                    ROUND(AVG(latency_ms)::numeric, 1) AS avg_latency_ms
                FROM benchmark_results
                {date_filter}
                GROUP BY agent_role
                ORDER BY avg_score DESC
                """,
                params,
            )
            rows = cur.fetchall()
            leaderboard = [
                row
                for fetched in rows
                if (row := self._row_to_dict(fetched)) is not None
            ]

            # Enrich with dimension averages per agent
            for entry in leaderboard:
                role = entry.get("agent_role")
                if not role:
                    continue
                dim_params: list = [role]
                dim_date_filter = ""
                if days is not None:
                    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                    dim_date_filter = "AND created_at >= %s"
                    dim_params.append(cutoff)
                cur.execute(
                    f"SELECT dimensions FROM benchmark_results WHERE agent_role = %s {dim_date_filter}",
                    dim_params,
                )
                dim_rows = cur.fetchall()
                dim_sums: dict[str, list[float]] = {}
                for dr in dim_rows:
                    d = self._row_to_dict(dr)
                    if not d:
                        continue
                    dims = d.get("dimensions")
                    if isinstance(dims, str):
                        try:
                            dims = json.loads(dims)
                        except (json.JSONDecodeError, TypeError):
                            continue
                    if isinstance(dims, dict):
                        for k, v in dims.items():
                            dim_sums.setdefault(k, []).append(float(v))
                entry["avg_dimensions"] = {
                    k: round(sum(vs) / len(vs), 2) for k, vs in dim_sums.items() if vs
                }

            return leaderboard
        finally:
            release_conn(conn)

    def get_history(
        self, agent_role: str, scenario_id: str | None = None, days: int | None = None
    ) -> list[dict]:
        """Historical scores for trend analysis."""
        conn = get_conn()
        try:
            conditions = ["agent_role = %s"]
            params: list = [agent_role]
            if scenario_id:
                conditions.append("scenario_id = %s")
                params.append(scenario_id)
            if days is not None:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                conditions.append("created_at >= %s")
                params.append(cutoff)
            where = "WHERE " + " AND ".join(conditions)
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM benchmark_results {where} ORDER BY created_at ASC",
                params,
            )
            rows = cur.fetchall()
            return [
                row
                for fetched in rows
                if (row := self._row_to_dict(fetched)) is not None
            ]
        finally:
            release_conn(conn)

    def compare_agents(self, role_a: str, role_b: str) -> dict:
        """Head-to-head comparison between two agents."""
        conn = get_conn()
        try:
            cur = conn.cursor()

            def _agent_stats(role: str) -> dict:
                cur.execute(
                    """
                    SELECT
                        COUNT(*)                          AS total_runs,
                        ROUND(AVG(score)::numeric, 2)      AS avg_score,
                        ROUND(AVG(latency_ms)::numeric, 1) AS avg_latency_ms
                    FROM benchmark_results
                    WHERE agent_role = %s
                    """,
                    (role,),
                )
                row = self._row_to_dict(cur.fetchone())
                if row is None or row["total_runs"] == 0:
                    return {"total_runs": 0, "avg_score": 0.0, "avg_latency_ms": 0.0}
                return row

            def _category_scores(role: str) -> dict[str, float]:
                cur.execute(
                    """
                    SELECT category, ROUND(AVG(score)::numeric, 2) AS avg
                    FROM benchmark_results
                    WHERE agent_role = %s
                    GROUP BY category
                    """,
                    (role,),
                )
                rows = cur.fetchall()
                return {
                    row["category"]: float(row["avg"])
                    for fetched in rows
                    if (row := self._row_to_dict(fetched)) is not None
                }

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
            release_conn(conn)

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row: object) -> dict[str, Any] | None:
        if row is None:
            return None
        if not isinstance(row, Mapping):
            return None
        d = dict(row)
        if "dimensions" in d and isinstance(d["dimensions"], str):
            try:
                d["dimensions"] = json.loads(d["dimensions"])
            except (json.JSONDecodeError, TypeError):
                pass
        return d
