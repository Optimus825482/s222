"use client";

import { useState, useEffect, useCallback } from "react";
import { fetcher } from "@/lib/api";
import type { ChaosReport } from "./types";
import { CHAOS_SCENARIOS } from "./types";
import { card, badge } from "./shared";

export function ChaosTab() {
  const [report, setReport] = useState<ChaosReport | null>(null);
  const [err, setErr] = useState("");
  const [scenario, setScenario] = useState<string>(CHAOS_SCENARIOS[0].value);
  const [target, setTarget] = useState("");
  const [duration, setDuration] = useState(5);
  const [intensity, setIntensity] = useState(0.5);
  const [injecting, setInjecting] = useState(false);
  const [lastResult, setLastResult] = useState("");

  const load = useCallback(() => {
    setErr("");
    fetcher<ChaosReport>("/api/chaos/report")
      .then(setReport)
      .catch((e) => setErr(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = async (enabled: boolean) => {
    try {
      await fetcher<{ enabled: boolean }>("/api/chaos/toggle", {
        method: "POST",
        body: JSON.stringify({ enabled }),
      });
      load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };

  const inject = async () => {
    setInjecting(true);
    setLastResult("");
    try {
      const res = await fetcher<{
        success: boolean;
        detail: string;
        recovery_ms: number;
      }>("/api/chaos/inject", {
        method: "POST",
        body: JSON.stringify({
          scenario,
          target: target || scenario,
          duration_s: duration,
          intensity,
        }),
      });
      setLastResult(
        `${res.success ? "✅" : "❌"} ${res.detail} (${res.recovery_ms.toFixed(0)}ms)`,
      );
      load();
    } catch (e: unknown) {
      setLastResult(`❌ ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setInjecting(false);
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
  if (!report)
    return (
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
    );

  return (
    <div style={{ padding: 12 }}>
      {/* Toggle */}
      <div
        style={{
          ...card,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <span style={{ fontWeight: 600 }}>Chaos Engine</span>
          <span
            style={{
              ...badge(report.enabled ? "#22c55e" : "#6b7280"),
              marginLeft: 8,
            }}
          >
            {report.enabled ? "AKTİF" : "KAPALI"}
          </span>
        </div>
        <button
          onClick={() => toggle(!report.enabled)}
          style={{
            ...card,
            cursor: "pointer",
            padding: "4px 12px",
            fontSize: 11,
            background: report.enabled ? "#fee2e2" : "#dcfce7",
          }}
        >
          {report.enabled ? "Kapat" : "Aç"}
        </button>
      </div>

      {/* Inject form */}
      {report.enabled && (
        <div style={card}>
          <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 11 }}>
            Hata Enjeksiyonu
          </div>
          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}
          >
            <label style={{ fontSize: 10 }}>
              Senaryo
              <select
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                style={{
                  width: "100%",
                  padding: 4,
                  fontSize: 11,
                  border: "1px solid #d6d2c2",
                  borderRadius: 3,
                  marginTop: 2,
                }}
              >
                {CHAOS_SCENARIOS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
            <label style={{ fontSize: 10 }}>
              Hedef
              <input
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="opsiyonel"
                style={{
                  width: "100%",
                  padding: 4,
                  fontSize: 11,
                  border: "1px solid #d6d2c2",
                  borderRadius: 3,
                  marginTop: 2,
                }}
              />
            </label>
            <label style={{ fontSize: 10 }}>
              Süre (sn): {duration}
              <input
                type="range"
                min={1}
                max={30}
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                style={{ width: "100%", marginTop: 2 }}
              />
            </label>
            <label style={{ fontSize: 10 }}>
              Yoğunluk: {(intensity * 100).toFixed(0)}%
              <input
                type="range"
                min={0.1}
                max={1}
                step={0.1}
                value={intensity}
                onChange={(e) => setIntensity(Number(e.target.value))}
                style={{ width: "100%", marginTop: 2 }}
              />
            </label>
          </div>
          <button
            onClick={inject}
            disabled={injecting}
            style={{
              ...card,
              cursor: "pointer",
              padding: "5px 16px",
              fontSize: 11,
              background: "#fef3c7",
              marginTop: 8,
              fontWeight: 600,
            }}
          >
            {injecting ? "Enjekte ediliyor..." : "🔥 Enjekte Et"}
          </button>
          {lastResult && (
            <div
              style={{
                marginTop: 6,
                fontSize: 11,
                color: lastResult.startsWith("✅") ? "#16a34a" : "#dc2626",
              }}
            >
              {lastResult}
            </div>
          )}
        </div>
      )}

      {/* History */}
      <div style={card}>
        <div style={{ fontWeight: 600, marginBottom: 6, fontSize: 11 }}>
          Geçmiş ({report.total_injections} toplam)
        </div>
        {report.history.length === 0 ? (
          <div style={{ fontSize: 11, color: "#888" }}>
            Henüz enjeksiyon yok
          </div>
        ) : (
          <div style={{ maxHeight: 200, overflowY: "auto" }}>
            {report.history.slice(0, 20).map((h, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "4px 0",
                  borderBottom: "1px solid #f0ede3",
                  fontSize: 11,
                }}
              >
                <span>
                  {h.success ? "✅" : "❌"} <b>{h.scenario}</b> → {h.target}
                </span>
                <span style={{ color: "#888" }}>
                  {h.recovery_ms.toFixed(0)}ms
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}