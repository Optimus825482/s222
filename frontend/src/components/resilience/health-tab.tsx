"use client";

import { useState, useEffect, useCallback } from "react";
import { fetcher } from "@/lib/api";
import type { HealthData } from "./types";
import { REFRESH_MS } from "./types";
import { card, badge, StatusDot } from "./shared";

export function HealthTab() {
  const [data, setData] = useState<HealthData | null>(null);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    setErr("");
    fetcher<HealthData>("/api/resilience/health")
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, REFRESH_MS);
    return () => clearInterval(t);
  }, [load]);

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

  if (!data)
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

  const statusColor =
    data.status === "healthy"
      ? "#22c55e"
      : data.status === "degraded"
        ? "#f59e0b"
        : "#ef4444";

  return (
    <div style={{ padding: 12 }}>
      <div style={{ ...card, display: "flex", alignItems: "center", gap: 8 }}>
        <span style={badge(statusColor)}>{data.status.toUpperCase()}</span>
        <span style={{ fontSize: 11, color: "#666" }}>Genel sistem durumu</span>
      </div>

      {Object.entries(data.components).map(([name, comp]) => {
        const ok =
          comp.status === "healthy" ||
          comp.status === "running" ||
          comp.sdk_installed === true;
        return (
          <div
            key={name}
            style={{
              ...card,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center" }}>
              <StatusDot ok={ok} />
              <span style={{ fontWeight: 600, textTransform: "capitalize" }}>
                {name.replace(/_/g, " ")}
              </span>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span style={badge(ok ? "#22c55e" : "#ef4444")}>
                {comp.status || (ok ? "OK" : "DOWN")}
              </span>
              {comp.channels !== undefined && (
                <span style={{ fontSize: 10, color: "#888" }}>
                  {comp.channels} ch
                </span>
              )}
              {comp.dlq_size !== undefined && comp.dlq_size > 0 && (
                <span style={{ fontSize: 10, color: "#f59e0b" }}>
                  DLQ: {comp.dlq_size}
                </span>
              )}
              {comp.error && (
                <span
                  style={{ fontSize: 10, color: "#ef4444" }}
                  title={comp.error}
                >
                  ⚠️
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
