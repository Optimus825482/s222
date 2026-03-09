"use client";

import { useState, useEffect, useCallback } from "react";
import { card } from "./shared";
import { REFRESH_MS } from "./types";

export function MetricsTab() {
  const [raw, setRaw] = useState("");
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    setErr("");
    // Backend URL - environment variable veya fallback
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://ykok0ckoooo880w0cwo0w0w0.77.42.68.4.sslip.io";
    fetch(`${apiUrl}/api/metrics`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then(setRaw)
      .catch((e) => setErr(e.message));
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, REFRESH_MS);
    return () => clearInterval(t);
  }, [load]);

  // Parse prometheus text into metric groups
  const sections = raw
    .split("\n")
    .reduce<{ name: string; lines: string[] }[]>((acc, line) => {
      if (line.startsWith("# HELP ")) {
        acc.push({
          name: line.replace("# HELP ", "").split(" ")[0],
          lines: [line],
        });
      } else if (acc.length > 0) {
        acc[acc.length - 1].lines.push(line);
      }
      return acc;
    }, []);

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

  if (!raw)
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
      <div
        style={{
          ...card,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ fontWeight: 600 }}>Prometheus Metrikleri</span>
        <button
          onClick={load}
          style={{
            ...card,
            cursor: "pointer",
            padding: "4px 10px",
            fontSize: 10,
          }}
        >
          🔄 Yenile
        </button>
      </div>

      {sections.length > 0 ? (
        sections.map((s) => (
          <div key={s.name} style={{ ...card, marginBottom: 6 }}>
            <div
              style={{
                fontSize: 11,
                fontWeight: 600,
                marginBottom: 4,
                color: "#3b82f6",
              }}
            >
              {s.name}
            </div>
            <pre
              style={{
                fontFamily: "Consolas, monospace",
                fontSize: 10,
                whiteSpace: "pre-wrap",
                background: "#f8f8f8",
                border: "1px solid #e5e5e5",
                borderRadius: 3,
                padding: 6,
                maxHeight: 120,
                overflow: "auto",
                margin: 0,
              }}
            >
              {s.lines.join("\n")}
            </pre>
          </div>
        ))
      ) : (
        <pre
          style={{
            fontFamily: "Consolas, monospace",
            fontSize: 10,
            whiteSpace: "pre-wrap",
            background: "#f8f8f8",
            border: "1px solid #e5e5e5",
            borderRadius: 3,
            padding: 8,
            maxHeight: 400,
            overflow: "auto",
          }}
        >
          {raw}
        </pre>
      )}
    </div>
  );
}
