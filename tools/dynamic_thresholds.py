"""
Dynamic Threshold System — Auto-adjusting thresholds based on KPI trends.

Uses k-means clustering (2 clusters: normal/anomaly) on rolling 7-day KPIs
to dynamically update alert thresholds. Replaces static hardcoded values.

Usage:
    from tools.dynamic_thresholds import threshold_engine
    thresholds = threshold_engine.compute("latency_p95", agent_role="researcher")
    # {"lower": 1.2, "upper": 5.8, "mean": 3.1, "method": "kmeans"}
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("dynamic_thresholds")


class DynamicThresholdEngine:
    """Computes adaptive thresholds from recent metric history."""

    DEFAULT_WINDOW_DAYS = 7
    MIN_SAMPLES = 10

    def __init__(self):
        self._cache: dict[str, dict] = {}
        self._cache_ttl = 300  # 5 min
        self._cache_ts: dict[str, float] = {}

    def _get_conn(self):
        from tools.pg_connection import get_conn
        return get_conn()

    def _release(self, conn):
        from tools.pg_connection import release_conn
        release_conn(conn)

    def compute(
        self,
        metric_name: str,
        agent_role: str = "",
        window_days: int | None = None,
    ) -> dict[str, Any]:
        """
        Compute dynamic thresholds for a metric using k-means (k=2).
        Returns: {lower, upper, mean, std, method, samples}
        """
        import time as _time
        cache_key = f"{metric_name}:{agent_role}"
        now = _time.time()

        # Check cache
        if cache_key in self._cache and (now - self._cache_ts.get(cache_key, 0)) < self._cache_ttl:
            return self._cache[cache_key]

        days = window_days or self.DEFAULT_WINDOW_DAYS
        values = self._fetch_metric_values(metric_name, agent_role, days)

        if len(values) < self.MIN_SAMPLES:
            result = self._static_fallback(metric_name)
        else:
            result = self._kmeans_thresholds(values)

        result["metric"] = metric_name
        result["agent_role"] = agent_role
        result["window_days"] = days

        self._cache[cache_key] = result
        self._cache_ts[cache_key] = now
        return result

    def _fetch_metric_values(self, metric_name: str, agent_role: str, days: int) -> list[float]:
        """Fetch metric values from agent_metrics_log or execution_traces."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        values = []

        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                # Try agent_metrics_log first
                if metric_name in ("latency_ms", "latency_p95", "response_time"):
                    query = "SELECT latency_ms FROM execution_traces WHERE created_at >= %s"
                    params: list[Any] = [cutoff]
                    if agent_role:
                        query += " AND agent_role = %s"
                        params.append(agent_role)
                    cur.execute(query, params)
                    values = [float(r[0]) for r in cur.fetchall() if r[0] is not None]

                elif metric_name in ("cost_usd", "cost"):
                    query = "SELECT cost_usd FROM execution_traces WHERE created_at >= %s"
                    params = [cutoff]
                    if agent_role:
                        query += " AND agent_role = %s"
                        params.append(agent_role)
                    cur.execute(query, params)
                    values = [float(r[0]) for r in cur.fetchall() if r[0] and float(r[0]) > 0]

                elif metric_name in ("tokens", "token_usage"):
                    query = "SELECT tokens FROM execution_traces WHERE created_at >= %s"
                    params = [cutoff]
                    if agent_role:
                        query += " AND agent_role = %s"
                        params.append(agent_role)
                    cur.execute(query, params)
                    values = [float(r[0]) for r in cur.fetchall() if r[0] and int(r[0]) > 0]

                elif metric_name == "score":
                    try:
                        query = "SELECT overall_score FROM agent_evaluations WHERE created_at >= %s"
                        params = [cutoff]
                        if agent_role:
                            query += " AND agent_role = %s"
                            params.append(agent_role)
                        cur.execute(query, params)
                        values = [float(r[0]) for r in cur.fetchall() if r[0] is not None]
                    except Exception:
                        pass

            self._release(conn)
        except Exception as e:
            logger.debug(f"Metric fetch failed for {metric_name}: {e}")

        return values

    def _kmeans_thresholds(self, values: list[float]) -> dict[str, Any]:
        """
        Simple k-means (k=2) to separate normal vs anomaly clusters.
        Lower threshold = max of normal cluster.
        Upper threshold = min of anomaly cluster.
        """
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mean_val = sum(sorted_vals) / n
        std_val = math.sqrt(sum((x - mean_val) ** 2 for x in sorted_vals) / n) if n > 1 else 0

        # Initialize centroids: 25th and 75th percentile
        c1 = sorted_vals[n // 4]
        c2 = sorted_vals[3 * n // 4]

        # Run k-means for 20 iterations
        for _ in range(20):
            cluster1, cluster2 = [], []
            for v in sorted_vals:
                if abs(v - c1) <= abs(v - c2):
                    cluster1.append(v)
                else:
                    cluster2.append(v)

            if not cluster1 or not cluster2:
                break

            new_c1 = sum(cluster1) / len(cluster1)
            new_c2 = sum(cluster2) / len(cluster2)

            if abs(new_c1 - c1) < 0.001 and abs(new_c2 - c2) < 0.001:
                break
            c1, c2 = new_c1, new_c2

        # Normal cluster = lower centroid, anomaly = higher
        normal = cluster1 if c1 < c2 else cluster2
        anomaly = cluster2 if c1 < c2 else cluster1

        return {
            "lower": max(normal) if normal else mean_val - std_val,
            "upper": min(anomaly) if anomaly else mean_val + 2 * std_val,
            "mean": round(mean_val, 4),
            "std": round(std_val, 4),
            "method": "kmeans",
            "samples": n,
            "normal_cluster_size": len(normal),
            "anomaly_cluster_size": len(anomaly),
        }

    def _static_fallback(self, metric_name: str) -> dict[str, Any]:
        """Fallback static thresholds when insufficient data."""
        defaults = {
            "latency_ms": {"lower": 500, "upper": 5000},
            "latency_p95": {"lower": 1000, "upper": 10000},
            "cost_usd": {"lower": 0.01, "upper": 0.50},
            "tokens": {"lower": 100, "upper": 10000},
            "score": {"lower": 2.0, "upper": 4.5},
        }
        d = defaults.get(metric_name, {"lower": 0, "upper": 100})
        d["method"] = "static_fallback"
        d["mean"] = (d["lower"] + d["upper"]) / 2
        d["std"] = 0
        d["samples"] = 0
        return d

    def invalidate_cache(self, metric_name: str = "", agent_role: str = "") -> int:
        """Clear cached thresholds. Returns count of cleared entries."""
        if not metric_name:
            count = len(self._cache)
            self._cache.clear()
            self._cache_ts.clear()
            return count
        key = f"{metric_name}:{agent_role}"
        if key in self._cache:
            del self._cache[key]
            self._cache_ts.pop(key, None)
            return 1
        return 0


# ── Singleton ────────────────────────────────────────────────────

_engine: DynamicThresholdEngine | None = None


def get_threshold_engine() -> DynamicThresholdEngine:
    global _engine
    if _engine is None:
        _engine = DynamicThresholdEngine()
    return _engine


threshold_engine = get_threshold_engine()
