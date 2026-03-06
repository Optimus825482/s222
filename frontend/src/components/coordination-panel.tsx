"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  CompetencyMatrix,
  CompetencyMatrixEntry,
  CoordinationAssignment,
  RotationEntry,
} from "@/lib/types";

function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse bg-white/5 rounded ${className}`}
      aria-hidden
    />
  );
}

function InlineError({ message }: { message: string }) {
  return (
    <p className="text-xs text-red-400 py-2" role="alert">
      {message}
    </p>
  );
}

const CATEGORY_LABELS: Record<string, string> = {
  reasoning: "Muhakeme",
  speed: "Hız",
  research: "Araştırma",
  creativity: "Yaratıcılık",
  accuracy: "Doğruluk",
};

const COMPLEXITY_OPTIONS = [
  { value: "low", label: "Düşük" },
  { value: "medium", label: "Orta" },
  { value: "high", label: "Yüksek" },
];

// ── Competency Heatmap ──────────────────────────────────────────

function CompetencyHeatmap() {
  const [data, setData] = useState<CompetencyMatrix | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getCompetencyMatrix();
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <Skeleton className="h-48" />;
  if (error) return <InlineError message={error} />;
  if (!data) return null;

  const maxScore = 100;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-300">
          Yetkinlik Matrisi
        </h3>
        <button
          onClick={load}
          className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
        >
          ↻ Yenile
        </button>
      </div>

      {/* Header row */}
      <div className="overflow-x-auto">
        <table
          className="w-full text-[10px]"
          role="grid"
          aria-label="Ajan yetkinlik matrisi"
        >
          <thead>
            <tr>
              <th className="text-left text-slate-500 pb-1 pr-2 font-medium">
                Ajan
              </th>
              {data.categories.map((cat) => (
                <th
                  key={cat}
                  className="text-center text-slate-500 pb-1 px-1 font-medium"
                >
                  {CATEGORY_LABELS[cat] ?? cat}
                </th>
              ))}
              <th className="text-center text-slate-500 pb-1 px-1 font-medium">
                Ort.
              </th>
            </tr>
          </thead>
          <tbody>
            {data.matrix.map((agent: CompetencyMatrixEntry) => (
              <tr key={agent.role} className="hover:bg-white/5">
                <td className="py-1 pr-2">
                  <span className="flex items-center gap-1">
                    <span>{agent.icon}</span>
                    <span
                      style={{ color: agent.color }}
                      className="font-medium truncate max-w-[80px]"
                    >
                      {agent.name}
                    </span>
                  </span>
                </td>
                {data.categories.map((cat) => {
                  const score = agent.scores[cat] ?? 0;
                  const intensity = Math.round((score / maxScore) * 100);
                  return (
                    <td key={cat} className="text-center py-1 px-1">
                      <div
                        className="mx-auto w-8 h-6 rounded flex items-center justify-center text-[9px] font-mono"
                        style={{
                          backgroundColor: `${agent.color}${Math.round(
                            intensity * 0.4 + 10,
                          )
                            .toString(16)
                            .padStart(2, "0")}`,
                          color: intensity > 50 ? "#fff" : "#94a3b8",
                        }}
                        title={`${agent.name}: ${CATEGORY_LABELS[cat] ?? cat} = ${score}`}
                      >
                        {Math.round(score)}
                      </div>
                    </td>
                  );
                })}
                <td className="text-center py-1 px-1">
                  <span
                    className="text-[10px] font-bold"
                    style={{ color: agent.color }}
                  >
                    {Math.round(agent.overall)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Agent Assignment ────────────────────────────────────────────

function AgentAssignment() {
  const [complexity, setComplexity] = useState("medium");
  const [taskType, setTaskType] = useState("general");
  const [result, setResult] = useState<CoordinationAssignment | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const assign = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.assignBestAgent(taskType, complexity);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Atama başarısız");
    } finally {
      setLoading(false);
    }
  }, [taskType, complexity]);

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold text-slate-300">Görev Ataması</h3>

      <div className="flex gap-2">
        <input
          type="text"
          value={taskType}
          onChange={(e) => setTaskType(e.target.value)}
          placeholder="Görev türü..."
          className="flex-1 bg-white/5 border border-border rounded px-2 py-1 text-[11px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
          aria-label="Görev türü"
        />
        <select
          value={complexity}
          onChange={(e) => setComplexity(e.target.value)}
          className="bg-white/5 border border-border rounded px-2 py-1 text-[11px] text-slate-300 focus:outline-none focus:border-blue-500/50"
          aria-label="Karmaşıklık seviyesi"
        >
          {COMPLEXITY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <button
          onClick={assign}
          disabled={loading}
          className="px-3 py-1 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 text-[11px] font-medium rounded border border-blue-500/20 transition-colors disabled:opacity-50"
        >
          {loading ? "..." : "Ata"}
        </button>
      </div>

      {error && <InlineError message={error} />}

      {result?.all_candidates && (
        <div className="space-y-1">
          {result.all_candidates.map((c, i) => {
            const isBest = i === 0;
            return (
              <div
                key={c.role}
                className={`flex items-center gap-2 px-2 py-1.5 rounded text-[11px] transition-colors ${
                  isBest
                    ? "bg-white/10 ring-1 ring-blue-500/30"
                    : "bg-white/5 hover:bg-white/8"
                }`}
              >
                <span className="text-sm">{c.icon}</span>
                <span
                  style={{ color: c.color }}
                  className="font-medium flex-1 truncate"
                >
                  {c.name}
                </span>
                <span className="text-slate-500 text-[10px]">
                  %{Math.round(c.success_rate)}
                </span>
                <span
                  className="font-mono text-[10px] font-bold"
                  style={{ color: c.color }}
                >
                  {(c.score ?? 0).toFixed(1)}
                </span>
                {isBest && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 font-medium">
                    EN İYİ
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Rotation History ────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  completed: "text-emerald-400",
  running: "text-blue-400",
  failed: "text-red-400",
  pending: "text-slate-500",
};

function RotationHistory() {
  const [entries, setEntries] = useState<RotationEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getRotationHistory(30);
      setEntries(Array.isArray(res?.entries) ? res.entries : []);
      setTotal(res?.total ?? 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <Skeleton className="h-32" />;
  if (error) return <InlineError message={error} />;

  const AGENT_COLORS: Record<string, string> = {
    orchestrator: "#ec4899",
    thinker: "#00e5ff",
    speed: "#a78bfa",
    researcher: "#f59e0b",
    reasoner: "#10b981",
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-300">
          Rotasyon Geçmişi
        </h3>
        <span className="text-[10px] text-slate-500">{total} toplam</span>
      </div>

      <div className="space-y-1 max-h-48 overflow-y-auto">
        {entries.length === 0 && (
          <p className="text-[11px] text-slate-600 py-4 text-center">
            Henüz rotasyon verisi yok
          </p>
        )}
        {entries.slice(0, 20).map((entry) => (
          <div
            key={entry.sub_task_id}
            className="flex items-center gap-2 px-2 py-1 rounded bg-white/5 hover:bg-white/8 text-[10px] transition-colors"
          >
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{
                backgroundColor:
                  AGENT_COLORS[entry.assigned_agent] ?? "#6b7280",
              }}
            />
            <span
              className="font-medium shrink-0"
              style={{ color: AGENT_COLORS[entry.assigned_agent] ?? "#6b7280" }}
            >
              {entry.assigned_agent}
            </span>
            <span className="text-slate-400 truncate flex-1">
              {entry.description}
            </span>
            <span className={STATUS_COLORS[entry.status] ?? "text-slate-500"}>
              {entry.status}
            </span>
            <span className="text-slate-600 font-mono">
              {entry.latency_ms > 0
                ? `${((entry.latency_ms ?? 0) / 1000).toFixed(1)}s`
                : "-"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Export ──────────────────────────────────────────────────

export function CoordinationPanel() {
  return (
    <div className="space-y-4" role="region" aria-label="Dinamik Koordinasyon">
      <CompetencyHeatmap />
      <div className="border-t border-border/50" />
      <AgentAssignment />
      <div className="border-t border-border/50" />
      <RotationHistory />
    </div>
  );
}
