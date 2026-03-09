"use client";

import { useState, useEffect, useCallback } from "react";
import { fetcher } from "@/lib/api";
import { card, badge, StatusDot, Sk, Er, REFRESH_MS } from "./shared";

interface FederatedStats {
  registered_nodes: number;
  current_round: number;
  model_version: string;
  total_rounds: number;
}
interface RoundStatus {
  round_number: number;
  status: string;
  min_participants?: number;
  timeout_seconds?: number;
  deltas_received?: number;
}

export function FederatedTab() {
  const [stats, setStats] = useState<FederatedStats | null>(null);
  const [nodes, setNodes] = useState<{
    nodes: Record<string, { node_id?: string; status: string }>;
    total: number;
  } | null>(null);
  const [round, setRound] = useState<RoundStatus | null>(null);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    setErr("");
    Promise.all([
      fetcher<FederatedStats>("/api/federated/stats"),
      fetcher<{
        nodes: Record<string, { node_id?: string; status: string }>;
        total: number;
      }>("/api/federated/nodes"),
      fetcher<RoundStatus>("/api/federated/round/status"),
    ])
      .then(([s, n, r]) => {
        setStats(s);
        setNodes(n);
        setRound(r);
      })
      .catch((e) => setErr(e.message));
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, REFRESH_MS);
    return () => clearInterval(t);
  }, [load]);

  const startRound = async () => {
    try {
      await fetcher<Record<string, unknown>>("/api/federated/round/start", {
        method: "POST",
        body: JSON.stringify({ min_participants: 2, timeout_seconds: 3600 }),
      });
      load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };

  if (err) return <Er m={err} r={load} />;
  if (!stats) return <Sk />;

  return (
    <div style={{ padding: 12 }}>
      {/* Stats overview */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr 1fr",
          gap: 8,
          marginBottom: 10,
        }}
      >
        {[
          { label: "Node'lar", value: stats.registered_nodes ?? 0, color: "#3b82f6" },
          { label: "Round", value: stats.current_round ?? 0, color: "#8b5cf6" },
          { label: "Model", value: stats.model_version ?? "—", color: "#10b981" },
          { label: "Toplam Round", value: stats.total_rounds ?? 0, color: "#f59e0b" },
        ].map((item) => (
          <div key={item.label} style={{ ...card, textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "#888" }}>{item.label}</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: item.color }}>
              {item.value}
            </div>
          </div>
        ))}
      </div>

      {/* Round status */}
      {round && (
        <div
          style={{
            ...card,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <span style={{ fontWeight: 600 }}>Round #{round.round_number}</span>
            <span
              style={{
                ...badge(round.status === "active" ? "#22c55e" : "#6b7280"),
                marginLeft: 8,
              }}
            >
              {round.status}
            </span>
            {round.deltas_received !== undefined && (
              <span style={{ fontSize: 10, color: "#888", marginLeft: 8 }}>
                {round.deltas_received} delta
              </span>
            )}
          </div>
          <button
            onClick={startRound}
            style={{
              ...card,
              cursor: "pointer",
              padding: "4px 12px",
              fontSize: 11,
              background: "#dbeafe",
              fontWeight: 600,
            }}
          >
            🚀 Yeni Round
          </button>
        </div>
      )}

      {/* Nodes */}
      <div style={card}>
        <div style={{ fontWeight: 600, marginBottom: 6, fontSize: 11 }}>
          Kayıtlı Node&apos;lar ({nodes?.total ?? 0})
        </div>
        {!nodes || Object.keys(nodes.nodes).length === 0 ? (
          <div style={{ fontSize: 11, color: "#888" }}>
            Henüz kayıtlı node yok
          </div>
        ) : (
          <div style={{ maxHeight: 200, overflowY: "auto" }}>
            {Object.entries(nodes.nodes).map(([key, node]) => (
              <div
                key={key}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "4px 0",
                  borderBottom: "1px solid #f0ede3",
                  fontSize: 11,
                }}
              >
                <span>
                  <StatusDot
                    ok={node.status === "active" || node.status === "idle"}
                  />
                  {node.node_id || key}
                </span>
                <span
                  style={badge(
                    node.status === "active" ? "#22c55e" : "#6b7280",
                  )}
                >
                  {node.status || "unknown"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
