"use client";

import { useState, useEffect, useCallback } from "react";
import { fetcher } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────────────── */
interface AgentMetrics {
  agent_role: string;
  avg_response_time: number;
  success_rate: number;
  total_tokens: number;
  task_count: number;
}

interface SystemMetrics {
  total_tokens: number;
  total_tasks: number;
  uptime_seconds: number;
  cost_estimate: number;
  runtime?: {
    schema_version?: string;
    rollout_ready?: boolean;
    feature_flags?: Record<string, boolean>;
  };
  failure_analytics?: {
    failure_count?: number;
    fallback_usage_count?: number;
    runtime_v2_adoption_rate?: number;
    total_count?: number;
  };
}

interface ScheduledExecution {
  id: string;
  task_id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  error: string | null;
}

interface SystemOverview {
  runtime?: {
    schema_version?: string;
    rollout_ready?: boolean;
    feature_flags?: Record<string, boolean>;
  };
  queueing?: {
    available?: boolean;
    event_bus?: {
      dlq_size?: number;
      pending_requests?: number;
      total_subscriptions?: number;
    };
    delegation?: {
      active_tasks?: number;
      priority_queue_size?: number;
      pending_futures?: number;
    };
  };
  scheduled_tasks?: {
    available?: boolean;
    total?: number;
    enabled?: number;
    recent_execution_count?: number;
  };
  sandbox?: {
    available?: boolean;
    mode?: string;
    isolation_level?: string;
    workspace_isolation?: boolean;
    docker_backed?: boolean;
  };
}

type Period = "1h" | "24h" | "7d";

/* ── Constants ─────────────────────────────────────────────────── */
const PERIODS: { key: Period; label: string }[] = [
  { key: "1h", label: "1h" },
  { key: "24h", label: "24h" },
  { key: "7d", label: "7d" },
];

const REFRESH_MS = 5_000;

/* ── Helpers ────────────────────────────────────────────────────── */
function Sk({ n = 4 }: { n?: number }) {
  return (
    <div
      className="space-y-3 animate-pulse"
      role="status"
      aria-label="Yükleniyor"
    >
      {Array.from({ length: n }, (_, i) => (
        <div key={i} className="h-8 bg-slate-700/40 rounded" />
      ))}
    </div>
  );
}

function Er({ m, r }: { m: string; r: () => void }) {
  return (
    <div className="flex flex-col items-center gap-2 py-8">
      <span className="text-xs text-red-400">⚠️ {m}</span>
      <button
        onClick={r}
        className="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 rounded transition-colors"
      >
        Tekrar Dene
      </button>
    </div>
  );
}

function fmtMs(v: number): string {
  return `${Math.round(v)} ms`;
}

function fmtRate(v: number | undefined | null): string {
  return `${(v ?? 0).toFixed(1)}%`;
}

function fmtTokens(v: number | undefined | null): string {
  const n = v ?? 0;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString("tr-TR");
}

function fmtCost(v: number | undefined | null): string {
  return `${(v ?? 0).toFixed(4)}`;
}

function fmtUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function fmtDate(value: string | null | undefined): string {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString("tr-TR", {
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
    });
  } catch {
    return value;
  }
}

/* ── Summary Card ──────────────────────────────────────────────── */
function SummaryCard({
  icon,
  label,
  value,
  accent,
}: {
  icon: string;
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-4 py-3 flex-1 min-w-[140px]">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-base">{icon}</span>
        <span className="text-[10px] text-slate-500 uppercase tracking-wider truncate">
          {label}
        </span>
      </div>
      <div
        className={`text-lg font-bold tabular-nums ${accent ?? "text-slate-200"}`}
      >
        {value}
      </div>
    </div>
  );
}

/* ── Main Component ────────────────────────────────────────────── */
export default function PerformanceDashboard() {
  const [period, setPeriod] = useState<Period>("24h");
  const [agents, setAgents] = useState<AgentMetrics[]>([]);
  const [system, setSystem] = useState<SystemMetrics | null>(null);
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [executions, setExecutions] = useState<ScheduledExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setError("");
      const [agentData, sysData, overviewData, executionData] = await Promise.all([
        fetcher<{ agents: AgentMetrics[] }>(
          `/api/metrics/agents?period=${period}`,
        ),
        fetcher<SystemMetrics>("/api/metrics/system"),
        fetcher<SystemOverview>("/api/system/overview"),
        fetcher<{ executions: ScheduledExecution[] }>(
          "/api/scheduled-tasks/executions?limit=5",
        ),
      ]);
      setAgents(agentData.agents ?? []);
      setSystem(sysData);
      setOverview(overviewData);
      setExecutions(executionData.executions ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Metrikler yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, [period]);

  /* initial load + period change */
  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  /* auto-refresh every 5s */
  useEffect(() => {
    const id = setInterval(load, REFRESH_MS);
    return () => clearInterval(id);
  }, [load]);

  if (loading && agents.length === 0) return <Sk n={6} />;
  if (error && agents.length === 0) return <Er m={error} r={load} />;

  return (
    <div className="space-y-4">
      {/* ── Period Selector ──────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-200">
          Performans Metrikleri
        </h3>
        <div
          className="flex gap-0.5 bg-slate-800/60 border border-slate-700/50 rounded-lg p-0.5"
          role="radiogroup"
          aria-label="Zaman aralığı seçimi"
        >
          {PERIODS.map((p) => (
            <button
              key={p.key}
              onClick={() => setPeriod(p.key)}
              title={`${p.label} aralığını göster`}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                period === p.key
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : "text-slate-400 hover:text-slate-300 border border-transparent"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── System Summary Cards ─────────────────────────────── */}
      {system && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <SummaryCard
            icon="🔤"
            label="Toplam Token"
            value={fmtTokens(system.total_tokens)}
            accent="text-cyan-400"
          />
          <SummaryCard
            icon="💵"
            label="Tahmini Maliyet"
            value={fmtCost(system.cost_estimate)}
            accent="text-emerald-400"
          />
          <SummaryCard
            icon="📋"
            label="Toplam Görev"
            value={(system.total_tasks ?? 0).toLocaleString("tr-TR")}
            accent="text-amber-400"
          />
          <SummaryCard
            icon="⏱️"
            label="Uptime"
            value={fmtUptime(system.uptime_seconds)}
            accent="text-sky-400"
          />
        </div>
      )}

      {(system?.runtime || system?.failure_analytics || overview) && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-3">
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold text-slate-200">Runtime Rollout</h4>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-medium ${overview?.runtime?.rollout_ready
                    ? "bg-emerald-500/15 text-emerald-400"
                    : "bg-amber-500/15 text-amber-400"
                  }`}
              >
                {overview?.runtime?.rollout_ready ? "Ready" : "Degraded"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-slate-900/40 rounded px-3 py-2">
                <div className="text-slate-500 text-[10px] uppercase">Schema</div>
                <div className="text-slate-200 font-mono">
                  {system?.runtime?.schema_version ?? overview?.runtime?.schema_version ?? "-"}
                </div>
              </div>
              <div className="bg-slate-900/40 rounded px-3 py-2">
                <div className="text-slate-500 text-[10px] uppercase">Flags</div>
                <div className="text-slate-200">
                  {Object.values(system?.runtime?.feature_flags ?? {}).filter(Boolean).length}
                </div>
              </div>
            </div>
            <div className="space-y-1">
              {Object.entries(system?.runtime?.feature_flags ?? {}).map(([flag, enabled]) => (
                <div key={flag} className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-400 truncate">{flag}</span>
                  <span className={enabled ? "text-emerald-400" : "text-slate-500"}>
                    {enabled ? "on" : "off"}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4 space-y-3">
            <h4 className="text-xs font-semibold text-slate-200">Queueing ve Sandbox</h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-slate-900/40 rounded px-3 py-2">
                <div className="text-slate-500 text-[10px] uppercase">DLQ</div>
                <div className="text-slate-200 tabular-nums">{overview?.queueing?.event_bus?.dlq_size ?? 0}</div>
              </div>
              <div className="bg-slate-900/40 rounded px-3 py-2">
                <div className="text-slate-500 text-[10px] uppercase">Active Tasks</div>
                <div className="text-slate-200 tabular-nums">{overview?.queueing?.delegation?.active_tasks ?? 0}</div>
              </div>
              <div className="bg-slate-900/40 rounded px-3 py-2">
                <div className="text-slate-500 text-[10px] uppercase">Priority Queue</div>
                <div className="text-slate-200 tabular-nums">{overview?.queueing?.delegation?.priority_queue_size ?? 0}</div>
              </div>
              <div className="bg-slate-900/40 rounded px-3 py-2">
                <div className="text-slate-500 text-[10px] uppercase">Sandbox</div>
                <div className="text-slate-200">{overview?.sandbox?.mode ?? "-"}</div>
              </div>
            </div>
            <div className="text-[11px] text-slate-400 space-y-1">
              <div>Isolation: <span className="text-slate-300">{overview?.sandbox?.isolation_level ?? "-"}</span></div>
              <div>Workspace isolation: <span className="text-slate-300">{overview?.sandbox?.workspace_isolation ? "yes" : "no"}</span></div>
            </div>
          </div>

          <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4 space-y-3">
            <h4 className="text-xs font-semibold text-slate-200">Failure Analytics</h4>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="bg-slate-900/40 rounded px-3 py-2">
                <div className="text-slate-500 text-[10px] uppercase">Failures</div>
                <div className="text-red-400 tabular-nums">{system?.failure_analytics?.failure_count ?? 0}</div>
              </div>
              <div className="bg-slate-900/40 rounded px-3 py-2">
                <div className="text-slate-500 text-[10px] uppercase">Fallback</div>
                <div className="text-amber-400 tabular-nums">{system?.failure_analytics?.fallback_usage_count ?? 0}</div>
              </div>
              <div className="bg-slate-900/40 rounded px-3 py-2">
                <div className="text-slate-500 text-[10px] uppercase">Adoption</div>
                <div className="text-emerald-400 tabular-nums">{fmtRate(system?.failure_analytics?.runtime_v2_adoption_rate)}</div>
              </div>
            </div>
            <div className="text-[11px] text-slate-400">
              Son 24 saatte {system?.failure_analytics?.total_count ?? 0} kayit uzerinden hesaplandi.
            </div>
          </div>
        </div>
      )}

      <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between">
          <h4 className="text-xs font-semibold text-slate-200">Replay / Scheduled Executions</h4>
          <span className="text-[10px] text-slate-500">
            {overview?.scheduled_tasks?.enabled ?? 0}/{overview?.scheduled_tasks?.total ?? 0} aktif task
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-700/50">
                <th className="text-left px-3 py-2 text-[10px] text-slate-500 uppercase tracking-wider">Task</th>
                <th className="text-left px-3 py-2 text-[10px] text-slate-500 uppercase tracking-wider">Status</th>
                <th className="text-right px-3 py-2 text-[10px] text-slate-500 uppercase tracking-wider">Duration</th>
                <th className="text-right px-3 py-2 text-[10px] text-slate-500 uppercase tracking-wider">Started</th>
              </tr>
            </thead>
            <tbody>
              {executions.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center py-6 text-slate-600">Replay kaydi yok</td>
                </tr>
              )}
              {executions.map((execution) => (
                <tr key={execution.id} className="border-b border-slate-700/30 hover:bg-slate-700/20">
                  <td className="px-3 py-2.5 font-mono text-slate-300">{execution.task_id}</td>
                  <td className="px-3 py-2.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] ${execution.status === "completed" ? "bg-emerald-500/15 text-emerald-400" : execution.status === "failed" ? "bg-red-500/15 text-red-400" : "bg-amber-500/15 text-amber-400"}`}>
                      {execution.status}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-right tabular-nums text-slate-300">
                    {execution.duration_ms ? fmtMs(execution.duration_ms) : "-"}
                  </td>
                  <td className="px-3 py-2.5 text-right text-slate-500">{fmtDate(execution.started_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Agent Comparison Table ───────────────────────────── */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs" role="table">
            <thead>
              <tr className="border-b border-slate-700/50">
                <th className="text-left px-3 py-2.5 text-[10px] text-slate-500 uppercase tracking-wider font-medium">
                  Agent Rolü
                </th>
                <th className="text-right px-3 py-2.5 text-[10px] text-slate-500 uppercase tracking-wider font-medium">
                  Ort. Yanıt
                </th>
                <th className="text-right px-3 py-2.5 text-[10px] text-slate-500 uppercase tracking-wider font-medium">
                  Başarı Oranı
                </th>
                <th className="text-right px-3 py-2.5 text-[10px] text-slate-500 uppercase tracking-wider font-medium">
                  Görev
                </th>
                <th className="text-right px-3 py-2.5 text-[10px] text-slate-500 uppercase tracking-wider font-medium">
                  Token
                </th>
              </tr>
            </thead>
            <tbody>
              {agents.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-slate-600">
                    Bu dönem için metrik verisi yok
                  </td>
                </tr>
              )}
              {agents.map((a) => {
                const isWarn = a.success_rate < 80;
                return (
                  <tr
                    key={a.agent_role}
                    className={`border-b border-slate-700/30 transition-colors ${
                      isWarn
                        ? "bg-red-500/10 hover:bg-red-500/15"
                        : "hover:bg-slate-700/20"
                    }`}
                  >
                    <td className="px-3 py-2.5 font-medium text-slate-200">
                      <div className="flex items-center gap-2">
                        {isWarn && (
                          <span
                            className="text-red-400 text-[10px]"
                            title="Başarı oranı düşük"
                          >
                            ⚠
                          </span>
                        )}
                        {a.agent_role}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-slate-300">
                      {fmtMs(a.avg_response_time)}
                    </td>
                    <td
                      className={`px-3 py-2.5 text-right tabular-nums font-medium ${
                        isWarn ? "text-red-400" : "text-emerald-400"
                      }`}
                    >
                      {fmtRate(a.success_rate)}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-slate-300">
                      {(a.task_count ?? 0).toLocaleString("tr-TR")}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-slate-400">
                      {fmtTokens(a.total_tokens)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Refresh indicator ────────────────────────────────── */}
      <div className="flex items-center justify-end gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-[9px] text-slate-600">
          Her 5 saniyede güncellenir
        </span>
      </div>
    </div>
  );
}
