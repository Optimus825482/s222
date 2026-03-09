"use client";

import { useState, useEffect, useCallback } from "react";
import { fetcher } from "@/lib/api";
import type { ThresholdData } from "./types";
import { card, xpBtn } from "./shared";

const METRICS = ["latency_ms", "cost_usd", "tokens", "success_rate"];

export function ThresholdsTab() {
  const [metric, setMetric] = useState("latency_ms");
  const [data, setData] = useState<ThresholdData | null>(null);
  const [err, setErr] = useState("");
  const [invalidating, setInvalidating] = useState(false);

  const load = useCallback(() => {
    setErr("");
    fetcher<ThresholdData>(`/api/resilience/thresholds?metric_name=${metric}`)
      .then(setData)
      .catch((e) => setErr(e.message));
  }, [metric]);

  useEffect(() => {
    load();
  }, [load]);

  const invalidate = async () => {
    setInvalidating(true);
    try {
      await fetcher<{ cleared: number }>(
        "/api/resilience/thresholds/invalidate",
        {
          method: "POST",
        },
      );
      load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setInvalidating(false);
    }
  };

  if (err)
    return (
      <div style={{ padding: 20, textAlign: "center" }}>
        <div style={{ color: "#ef4444", fontSize: 12, marginBottom: 8 }}>
          ⚠️ {err}
        </div>
        <button
          onClick={load}
          style={{ ...card, cursor: "pointer", padding: "4px 12px" }}
        >
          Tekrar Dene
        </button>
      </div>
    );

  return (
    <div style={{ padding: 12 }}>
      <div
        style={{ display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" }}
      >
        {METRICS.map((m) => (
          <button
            key={m}
            onClick={() => setMetric(m)}
            style={xpBtn(metric === m)}
          >
            {m}
          </button>
        ))}
        <button
          onClick={invalidate}
          disabled={invalidating}
          style={{
            ...card,
            cursor: "pointer",
            padding: "4px 10px",
            fontSize: 10,
            marginLeft: "auto",
          }}
        >
          {invalidating ? "..." : "🗑️ Cache Temizle"}
        </button>
      </div>

      {!data ? (
        <div
          style={{
            padding: 20,
            textAlign: "center",
            color: "#888",
            fontSize: 12,
          }}
        >
          Yükleniyor...
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: 8,
          }}
        >
          {[
            {
              label: "Alt Eşik",
              value: data.low?.toFixed(2) ?? "—",
              color: "#3b82f6",
            },
            {
              label: "Ortalama",
              value: data.mean?.toFixed(2) ?? "—",
              color: "#8b5cf6",
            },
            {
              label: "Üst Eşik",
              value: data.high?.toFixed(2) ?? "—",
              color: "#ef4444",
            },
            {
              label: "Std Sapma",
              value: data.std?.toFixed(2) ?? "—",
              color: "#f59e0b",
            },
            {
              label: "Örneklem",
              value: String(data.sample_count ?? 0),
              color: "#10b981",
            },
          ].map((item) => (
            <div key={item.label} style={{ ...card, textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "#888", marginBottom: 4 }}>
                {item.label}
              </div>
              <div style={{ fontSize: 18, fontWeight: 700, color: item.color }}>
                {item.value}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
