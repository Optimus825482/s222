"use client";

import { useState, useEffect, useCallback } from "react";
import { fetcher } from "@/lib/api";
import { card, badge, Sk, Er } from "./shared";

interface ModerationItem {
  id: number;
  solution: string;
  confidence: number;
  source_agents: string;
  submitted_at: string;
  reason: string;
}

export function ModerationTab() {
  const [queue, setQueue] = useState<ModerationItem[]>([]);
  const [err, setErr] = useState("");
  const [reviewing, setReviewing] = useState<number | null>(null);

  const load = useCallback(() => {
    setErr("");
    fetcher<ModerationItem[]>("/api/moderate/queue?limit=30")
      .then(setQueue)
      .catch((e) => setErr(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const review = async (queueId: number, approved: boolean) => {
    setReviewing(queueId);
    try {
      await fetcher<{ success: boolean }>("/api/moderate/review", {
        method: "POST",
        body: JSON.stringify({
          queue_id: queueId,
          approved,
          reviewer: "human",
        }),
      });
      load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setReviewing(null);
    }
  };

  if (err) return <Er m={err} r={load} />;

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
        <span style={{ fontWeight: 600 }}>Bekleyen İncelemeler</span>
        <span style={badge(queue.length > 0 ? "#f59e0b" : "#22c55e")}>
          {queue.length} bekliyor
        </span>
      </div>

      {queue.length === 0 ? (
        <div style={{ ...card, textAlign: "center", color: "#888" }}>
          ✅ Bekleyen inceleme yok
        </div>
      ) : (
        <div style={{ maxHeight: 400, overflowY: "auto" }}>
          {queue.map((item) => (
            <div key={item.id} style={card}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: 6,
                }}
              >
                <span style={{ fontSize: 10, color: "#888" }}>#{item.id}</span>
                <span
                  style={badge(item.confidence >= 0.8 ? "#3b82f6" : "#f59e0b")}
                >
                  %{(item.confidence * 100).toFixed(0)} güven
                </span>
              </div>
              <div
                style={{
                  fontSize: 11,
                  marginBottom: 6,
                  lineHeight: 1.4,
                  maxHeight: 60,
                  overflow: "hidden",
                }}
              >
                {item.solution}
              </div>
              <div style={{ fontSize: 10, color: "#888", marginBottom: 6 }}>
                Kaynak: {item.source_agents || "—"} · Sebep:{" "}
                {item.reason || "—"}
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <button
                  onClick={() => review(item.id, true)}
                  disabled={reviewing === item.id}
                  style={{
                    ...card,
                    cursor: "pointer",
                    padding: "3px 12px",
                    fontSize: 10,
                    background: "#dcfce7",
                    fontWeight: 600,
                  }}
                >
                  ✅ Onayla
                </button>
                <button
                  onClick={() => review(item.id, false)}
                  disabled={reviewing === item.id}
                  style={{
                    ...card,
                    cursor: "pointer",
                    padding: "3px 12px",
                    fontSize: 10,
                    background: "#fee2e2",
                    fontWeight: 600,
                  }}
                >
                  ❌ Reddet
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
