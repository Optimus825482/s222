"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type {
  AgentHealth,
  AgentLeaderboardEntry,
  AgentRole,
  AgentStatus,
  SystemStats,
  AnomalyReport,
} from "@/lib/types";

// ── Shared Helpers ──────────────────────────────────────────────

const ROLE_ICON: Record<AgentRole, string> = {
  orchestrator: "🧠",
  thinker: "🔬",
  speed: "⚡",
  researcher: "🔍",
  reasoner: "🌊",
};

const ROLE_COLOR: Record<AgentRole, string> = {
  orchestrator: "#ec4899",
  thinker: "#00e5ff",
  speed: "#a78bfa",
  researcher: "#f59e0b",
  reasoner: "#10b981",
};

const STATUS_DOT: Record<AgentStatus, string> = {
  active: "bg-green-400",
  idle: "bg-yellow-400",
  error: "bg-red-400",
  offline: "bg-gray-500",
};

const STATUS_LABEL: Record<AgentStatus, string> = {
  active: "Aktif",
  idle: "Boşta",
  error: "Hata",
  offline: "Çevrimdışı",
};

function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded bg-slate-700/50 ${className}`}
      aria-hidden="true"
    />
  );
}

function InlineError({ message }: { message: string }) {
  return (
    <div role="alert" className="text-xs text-red-400 py-2 px-1">
      ⚠️ {message}
    </div>
  );
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}sa ${m}dk`;
}

// ── Component 1: AgentHealthPanel ───────────────────────────────

export function AgentHealthPanel() {
  const [agents, setAgents] = useState<AgentHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      const data = await api.getAgentsHealth();
      setAgents(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Veri alınamadı");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30_000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  if (loading) {
    return (
      <section
        aria-label="Agent sağlık durumu yükleniyor"
        className="space-y-2"
      >
        <h3 className="text-xs font-semibold text-slate-200 mb-2">
          Agent Sağlık Durumu
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-lg" />
          ))}
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Agent sağlık durumu" className="space-y-2">
      <h3 className="text-xs font-semibold text-slate-200 mb-2">
        Agent Sağlık Durumu
      </h3>
      {error && <InlineError message={error} />}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-[420px] overflow-y-auto pr-1">
        {agents.map((agent) => (
          <article
            key={agent.role}
            className="bg-[#1a1f2e] border border-border rounded-lg p-3 space-y-2"
            aria-label={`${agent.name} agent kartı`}
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-sm" aria-hidden="true">
                  {ROLE_ICON[agent.role]}
                </span>
                <span
                  className="text-xs font-medium truncate"
                  style={{ color: ROLE_COLOR[agent.role] }}
                >
                  {agent.name}
                </span>
              </div>
              <span
                className="flex items-center gap-1 text-[10px] text-slate-400"
                aria-label={`Durum: ${STATUS_LABEL[agent.status]}`}
              >
                <span
                  className={`inline-block w-1.5 h-1.5 rounded-full ${STATUS_DOT[agent.status]}`}
                />
                {STATUS_LABEL[agent.status]}
              </span>
            </div>

            {/* Success rate bar */}
            <div>
              <div className="flex items-center justify-between text-[10px] text-slate-400 mb-0.5">
                <span>Başarı Oranı</span>
                <span className="text-slate-300">
                  {(agent.success_rate ?? 0).toFixed(1)}%
                </span>
              </div>
              <div
                className="h-1 rounded-full bg-slate-700 overflow-hidden"
                role="progressbar"
                aria-valuenow={agent.success_rate ?? 0}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(agent.success_rate ?? 0, 100)}%`,
                    backgroundColor: ROLE_COLOR[agent.role],
                  }}
                />
              </div>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-1 text-center">
              <div>
                <div className="text-[10px] text-slate-500">Gecikme</div>
                <div className="text-xs text-slate-300">
                  {(agent.avg_latency_ms ?? 0).toFixed(0)}ms
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500">Çağrı</div>
                <div className="text-xs text-slate-300">
                  {agent.total_calls}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500">Hata</div>
                <div
                  className={`text-xs ${agent.error_count > 0 ? "text-red-400" : "text-slate-300"}`}
                >
                  {agent.error_count}
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

// ── Component 2: LeaderboardPanel ───────────────────────────────

export function LeaderboardPanel() {
  const [entries, setEntries] = useState<AgentLeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLeaderboard = useCallback(async () => {
    try {
      const data = await api.getAgentLeaderboard();
      setEntries(data.sort((a, b) => a.rank - b.rank));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Veri alınamadı");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard]);

  if (loading) {
    return (
      <section aria-label="Liderlik tablosu yükleniyor" className="space-y-2">
        <h3 className="text-xs font-semibold text-slate-200 mb-2">
          Liderlik Tablosu
        </h3>
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-8 rounded" />
        ))}
      </section>
    );
  }

  return (
    <section aria-label="Agent liderlik tablosu" className="space-y-2">
      <h3 className="text-xs font-semibold text-slate-200 mb-2">
        Liderlik Tablosu
      </h3>
      {error && <InlineError message={error} />}

      {/* Header row */}
      <div className="grid grid-cols-[2rem_1fr_3.5rem_3.5rem_3.5rem_3.5rem] gap-1 text-[10px] text-slate-500 px-2">
        <span>#</span>
        <span>Agent</span>
        <span className="text-right">Skor</span>
        <span className="text-right">Başarı</span>
        <span className="text-right">Gecikme</span>
        <span className="text-right">Verim</span>
      </div>

      <div className="space-y-1 max-h-[300px] overflow-y-auto">
        {entries.map((entry) => {
          const isTop = entry.rank === 1;
          return (
            <div
              key={entry.role}
              className={`grid grid-cols-[2rem_1fr_3.5rem_3.5rem_3.5rem_3.5rem] gap-1 items-center px-2 py-1.5 rounded-md text-xs ${
                isTop
                  ? "bg-yellow-500/10 border border-yellow-500/30"
                  : "bg-[#1a1f2e] border border-border"
              }`}
              aria-label={`Sıra ${entry.rank}: ${entry.name}`}
            >
              <span className="text-slate-400 font-medium">
                {isTop ? "👑" : `#${entry.rank}`}
              </span>
              <span className="flex items-center gap-1 min-w-0">
                <span className="text-sm" aria-hidden="true">
                  {ROLE_ICON[entry.role]}
                </span>
                <span
                  className="truncate font-medium"
                  style={{ color: ROLE_COLOR[entry.role] }}
                >
                  {entry.name}
                </span>
              </span>
              <span className="text-right font-bold text-slate-200">
                {(entry.score ?? 0).toFixed(0)}
              </span>
              <span className="text-right text-slate-300">
                {(entry.success_rate ?? 0).toFixed(0)}%
              </span>
              <span className="text-right text-slate-400">
                {(entry.avg_latency_ms ?? 0).toFixed(0)}ms
              </span>
              <span className="text-right text-slate-400">
                {(entry.efficiency ?? 0).toFixed(1)}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ── Component 3: SystemStatsPanel ───────────────────────────────

export function SystemStatsPanel() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const data = await api.getSystemStats();
      setStats(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Veri alınamadı");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15_000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  if (loading) {
    return (
      <section
        aria-label="Sistem istatistikleri yükleniyor"
        className="space-y-2"
      >
        <h3 className="text-xs font-semibold text-slate-200 mb-2">
          Sistem İstatistikleri
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
      </section>
    );
  }

  if (!stats) return error ? <InlineError message={error} /> : null;

  const dbOk = stats.db_status === "ok" || stats.db_status === "healthy";

  const items: {
    icon: string;
    label: string;
    value: string;
    accent?: string;
  }[] = [
    { icon: "🧵", label: "Aktif Thread", value: String(stats.active_threads) },
    { icon: "📋", label: "Toplam Görev", value: String(stats.total_tasks) },
    { icon: "📡", label: "Toplam Olay", value: String(stats.total_events) },
    {
      icon: "💾",
      label: "Bellek",
      value: `${(stats.memory_usage_mb ?? 0).toFixed(0)} MB`,
    },
    {
      icon: dbOk ? "🟢" : "🔴",
      label: "Veritabanı",
      value: dbOk ? "Sağlıklı" : "Sorunlu",
      accent: dbOk ? "text-green-400" : "text-red-400",
    },
    {
      icon: "⏱️",
      label: "Çalışma Süresi",
      value: formatUptime(stats.uptime_seconds),
    },
    {
      icon: "🤖",
      label: "Aktif Agent",
      value: `${stats.agents_active}/${stats.agents_total}`,
    },
  ];

  return (
    <section aria-label="Sistem istatistikleri" className="space-y-2">
      <h3 className="text-xs font-semibold text-slate-200 mb-2">
        Sistem İstatistikleri
      </h3>
      {error && <InlineError message={error} />}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {items.map((item) => (
          <div
            key={item.label}
            className="bg-[#1a1f2e] border border-border rounded-lg p-2.5"
          >
            <div className="flex items-center gap-1 text-[10px] text-slate-400 mb-1">
              <span aria-hidden="true">{item.icon}</span>
              <span>{item.label}</span>
            </div>
            <div
              className={`text-sm font-medium ${item.accent || "text-slate-200"}`}
            >
              {item.value}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ── Component 4: AnomalyPanel ───────────────────────────────────

const SEVERITY_ICON: Record<string, string> = {
  low: "🟢",
  medium: "🟡",
  high: "🔴",
};

const ANOMALY_TYPE_LABEL: Record<string, string> = {
  high_error_rate: "Yüksek Hata Oranı",
  slow_response: "Yavaş Yanıt",
  token_spike: "Token Artışı",
  unusual_pattern: "Olağandışı Örüntü",
};

const HEALTH_CONFIG: Record<string, { label: string; className: string }> = {
  healthy: {
    label: "Sağlıklı",
    className: "bg-green-500/20 text-green-400 border-green-500/30",
  },
  degraded: {
    label: "Düşük Performans",
    className: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  },
  critical: {
    label: "Kritik",
    className: "bg-red-500/20 text-red-400 border-red-500/30",
  },
};

export function AnomalyPanel() {
  const [report, setReport] = useState<AnomalyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnomalies = useCallback(async () => {
    try {
      const data = await api.getAnomalies();
      setReport(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Veri alınamadı");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnomalies();
    const interval = setInterval(fetchAnomalies, 30_000);
    return () => clearInterval(interval);
  }, [fetchAnomalies]);

  if (loading) {
    return (
      <section aria-label="Anomali raporu yükleniyor" className="space-y-2">
        <h3 className="text-xs font-semibold text-slate-200 mb-2">
          Anomali Tespiti
        </h3>
        <Skeleton className="h-6 w-24 rounded-full" />
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
      </section>
    );
  }

  const health = report
    ? HEALTH_CONFIG[report.overall_health]
    : HEALTH_CONFIG.healthy;

  return (
    <section aria-label="Anomali raporu" className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-200">
          Anomali Tespiti
        </h3>
        {report && (
          <span
            className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${health.className}`}
            role="status"
            aria-label={`Genel sağlık: ${health.label}`}
          >
            {health.label}
          </span>
        )}
      </div>

      {error && <InlineError message={error} />}

      <div className="max-h-[320px] overflow-y-auto space-y-1.5 pr-1">
        {report && report.anomalies.length === 0 ? (
          <div className="flex items-center gap-2 text-xs text-green-400 py-4 justify-center">
            <span aria-hidden="true">✅</span>
            <span>Anomali tespit edilmedi</span>
          </div>
        ) : (
          report?.anomalies.map((anomaly, idx) => (
            <div
              key={`${anomaly.type}-${anomaly.agent_role}-${idx}`}
              className="bg-[#1a1f2e] border border-border rounded-lg p-2.5 space-y-1"
              role="listitem"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span aria-label={`Önem: ${anomaly.severity}`}>
                    {SEVERITY_ICON[anomaly.severity]}
                  </span>
                  <span className="text-xs font-medium text-slate-200">
                    {ANOMALY_TYPE_LABEL[anomaly.type] || anomaly.type}
                  </span>
                </div>
                <span className="flex items-center gap-1 text-[10px] text-slate-400">
                  {ROLE_ICON[anomaly.agent_role]}
                  <span style={{ color: ROLE_COLOR[anomaly.agent_role] }}>
                    {anomaly.agent_role}
                  </span>
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-snug">
                {anomaly.description}
              </p>
              <div className="flex items-center gap-3 text-[10px] text-slate-500">
                <span>
                  Değer:{" "}
                  <span className="text-slate-300">
                    {(anomaly.metric_value ?? 0).toFixed(1)}
                  </span>
                </span>
                <span>
                  Eşik:{" "}
                  <span className="text-slate-300">
                    {(anomaly.threshold ?? 0).toFixed(1)}
                  </span>
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
