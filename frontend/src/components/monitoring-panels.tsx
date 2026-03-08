"use client";

import { useState } from "react";
import { useSyncExternalStore } from "react";
import { api } from "@/lib/api";
import type { AgentRole } from "@/lib/types";
import {
  ROLE_ICON,
  ROLE_COLOR,
  STATUS_DOT,
  STATUS_LABEL,
} from "@/lib/constants";
import { getWSSnapshot, subscribeWS } from "@/lib/ws-store";
import { LiveEventLog } from "@/components/live-event-log";
import { useMonitoringData } from "@/hooks/use-monitoring-data";

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
  if (!seconds || !Number.isFinite(seconds)) return "0sa 0dk";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}sa ${m}dk`;
}

// ── Component 1: AgentHealthPanel ───────────────────────────────

export function AgentHealthPanel() {
  const {
    agentHealth: agents,
    sharedLoading: loading,
    sharedError: error,
  } = useMonitoringData();

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
                  className={`inline-block w-1.5 h-1.5 rounded-full ${STATUS_DOT[agent.status] ?? "bg-gray-500"}`}
                />
                {STATUS_LABEL[agent.status] ?? "Bilinmiyor"}
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

// ── Component 3: SystemStatsPanel ───────────────────────────────

export function SystemStatsPanel() {
  const {
    systemStats: stats,
    sharedLoading: loading,
    sharedError: error,
  } = useMonitoringData();

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
    {
      icon: "🧵",
      label: "Aktif Thread",
      value: String(stats.active_threads ?? 0),
    },
    {
      icon: "📋",
      label: "Toplam Görev",
      value: String(stats.total_tasks ?? 0),
    },
    {
      icon: "📡",
      label: "Toplam Olay",
      value: String(stats.total_events ?? 0),
    },
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
      value: formatUptime(stats.uptime_seconds ?? 0),
    },
    {
      icon: "🤖",
      label: "Aktif Agent",
      value: `${stats.agents_active ?? 0}/${stats.agents_total ?? 0}`,
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
  warning: {
    label: "Uyarı",
    className: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  },
  critical: {
    label: "Kritik",
    className: "bg-red-500/20 text-red-400 border-red-500/30",
  },
  unknown: {
    label: "Bilinmiyor",
    className: "bg-slate-500/20 text-slate-400 border-slate-500/30",
  },
};

export function AnomalyPanel() {
  const {
    anomalies: report,
    sharedLoading: loading,
    sharedError: error,
  } = useMonitoringData();

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
    ? (HEALTH_CONFIG[report.overall_health] ?? HEALTH_CONFIG.healthy)
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

// ── Component 5: HeartbeatPanel (Faz 11.2) ─────────────────────────────

const FREQ_LABEL: Record<string, string> = {
  minutely: "Her dakika",
  hourly: "Saatlik",
  daily: "Günlük",
  weekly: "Haftalık",
};

export function HeartbeatPanel() {
  const {
    heartbeatTasks: tasks,
    heartbeatEvents: events,
    heartbeatLoading: loading,
    refreshHeartbeatData,
  } = useMonitoringData();
  const [triggering, setTriggering] = useState<string | null>(null);

  const onTrigger = async (name: string) => {
    setTriggering(name);
    try {
      await api.triggerHeartbeatTask(name);
      await refreshHeartbeatData();
    } finally {
      setTriggering(null);
    }
  };

  const onToggle = async (name: string, enabled: boolean) => {
    try {
      await api.toggleHeartbeatTask(name, enabled);
      await refreshHeartbeatData();
    } catch {}
  };

  const ago = (ts: string) => {
    const m = Math.floor((Date.now() - new Date(ts).getTime()) / 60000);
    return m < 1
      ? "az önce"
      : m < 60
        ? `${m}dk`
        : m < 1440
          ? `${Math.floor(m / 60)}sa`
          : `${Math.floor(m / 1440)}g`;
  };

  if (loading) {
    return (
      <section aria-label="Heartbeat yükleniyor" className="space-y-2">
        <h3 className="text-xs font-semibold text-slate-200 mb-2">Heartbeat</h3>
        <Skeleton className="h-24 rounded-lg" />
      </section>
    );
  }

  return (
    <section aria-label="Heartbeat görevleri" className="space-y-2">
      <h3 className="text-xs font-semibold text-slate-200 mb-2">
        Proaktif Görevler (Heartbeat)
      </h3>
      <div className="space-y-1.5">
        {tasks.map((t) => (
          <div
            key={t.name}
            className="bg-[#1a1f2e] border border-border rounded-lg p-2.5 flex items-center justify-between gap-2"
          >
            <div className="min-w-0">
              <div className="text-xs font-medium text-slate-200">{t.name}</div>
              <div className="text-[10px] text-slate-500">
                {FREQ_LABEL[t.frequency] ?? t.frequency} · {t.run_count} çalıştı
                {t.last_run ? ` · ${ago(t.last_run)}` : ""}
              </div>
            </div>
            <div className="flex items-center gap-1 flex-shrink-0">
              <button
                type="button"
                aria-label={t.enabled ? "Devre dışı bırak" : "Etkinleştir"}
                onClick={() => onToggle(t.name, !t.enabled)}
                className={`text-[10px] px-2 py-1 rounded ${t.enabled ? "bg-green-500/20 text-green-400" : "bg-slate-600/40 text-slate-500"}`}
              >
                {t.enabled ? "Açık" : "Kapalı"}
              </button>
              <button
                type="button"
                disabled={triggering === t.name}
                onClick={() => onTrigger(t.name)}
                className="text-[10px] px-2 py-1 rounded bg-cyan-500/20 text-cyan-400 disabled:opacity-50"
              >
                {triggering === t.name ? "…" : "Şimdi"}
              </button>
            </div>
          </div>
        ))}
      </div>
      {events.length > 0 && (
        <details className="mt-2">
          <summary className="text-[10px] text-slate-500 cursor-pointer">
            Son olaylar
          </summary>
          <ul className="mt-1 space-y-0.5 max-h-32 overflow-y-auto text-[10px] text-slate-400">
            {events.slice(0, 8).map((ev, i) => (
              <li key={i}>
                {ev.task} — {ago(ev.timestamp)}
                {ev.error ? ` — ${ev.error}` : ""}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

// ── Component 6: Autonomous Oversight Panel (Faz 12.7 — İnsan gözetimi) ─

/** Otonom davranış ve konuşmaları tek ekranda izleme: canlı akış + otonom sohbetler + heartbeat. */
export function AutonomousOversightPanel() {
  const snapshot = useSyncExternalStore(
    subscribeWS,
    getWSSnapshot,
    getWSSnapshot,
  );
  const { status, liveEvents } = snapshot;

  const {
    autonomousConversations: convs,
    autonomousLoading: loading,
    heartbeatEvents,
  } = useMonitoringData();

  const ago = (ts: string) => {
    const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
    if (s < 60) return "az önce";
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}dk`;
    const h = Math.floor(m / 60);
    return `${h}sa`;
  };

  return (
    <section
      aria-label="Otonom izleme — canlı aktivite, otonom sohbetler, heartbeat"
      className="space-y-4"
    >
      <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
        <span aria-hidden>👁</span>
        Otonom İzleme — İnsan Gözetimi
      </h2>
      <p className="text-[11px] text-slate-500">
        Agent&apos;ların otonom davranışları ve konuşmaları tek ekrandan takip
        edilir. Detay: İletişim (Otonom Sohbet), Sistem Durumu (Heartbeat).
      </p>

      {/* 1. Canlı aktivite akışı (WebSocket) */}
      <div className="bg-[#1a1f2e] border border-border rounded-lg overflow-hidden">
        <div className="px-3 py-2 border-b border-border flex items-center justify-between">
          <span className="text-xs font-medium text-slate-300">
            Canlı Aktivite Akışı
          </span>
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded ${
              status === "running"
                ? "bg-amber-500/20 text-amber-400"
                : status === "complete"
                  ? "bg-green-500/20 text-green-400"
                  : "bg-slate-600/40 text-slate-400"
            }`}
          >
            {status === "running"
              ? "Aktif"
              : status === "complete"
                ? "Tamamlandı"
                : "Beklemede"}
          </span>
        </div>
        <div className="max-h-48 overflow-y-auto p-2">
          {liveEvents.length > 0 ? (
            <LiveEventLog events={liveEvents} status={status} />
          ) : (
            <p className="text-[11px] text-slate-500 py-2 text-center">
              Sohbetten görev gönderildiğinde olaylar burada görünür.
            </p>
          )}
        </div>
      </div>

      {/* 2. Son otonom sohbetler */}
      <div className="bg-[#1a1f2e] border border-border rounded-lg overflow-hidden">
        <div className="px-3 py-2 border-b border-border">
          <span className="text-xs font-medium text-slate-300">
            Son Otonom Sohbetler
          </span>
        </div>
        <div className="max-h-40 overflow-y-auto p-2">
          {loading ? (
            <div className="animate-pulse h-12 rounded bg-slate-700/50" />
          ) : convs.length === 0 ? (
            <p className="text-[11px] text-slate-500 py-2 text-center">
              Otonom sohbet zamanlayıcısı aktif — kısa süre içinde sohbetler
              başlayacak.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {convs.slice(0, 6).map((c) => (
                <li
                  key={c.id}
                  className="flex items-center gap-2 text-[11px] text-slate-400"
                >
                  <span
                    style={{
                      color: ROLE_COLOR[c.initiator as AgentRole] ?? "#94a3b8",
                    }}
                  >
                    {ROLE_ICON[c.initiator as AgentRole] ?? "⚙"}
                  </span>
                  <span className="text-slate-500">⇄</span>
                  <span
                    style={{
                      color: ROLE_COLOR[c.responder as AgentRole] ?? "#94a3b8",
                    }}
                  >
                    {ROLE_ICON[c.responder as AgentRole] ?? "⚙"}
                  </span>
                  <span className="truncate flex-1 text-slate-300">
                    {c.topic || "Konuşma"}
                  </span>
                  <span className="text-slate-600 tabular-nums">
                    {c.message_count} mesaj · {ago(c.started_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* 3. Son heartbeat olayları */}
      <div className="bg-[#1a1f2e] border border-border rounded-lg overflow-hidden">
        <div className="px-3 py-2 border-b border-border">
          <span className="text-xs font-medium text-slate-300">
            Son Heartbeat Olayları
          </span>
        </div>
        <div className="max-h-32 overflow-y-auto p-2">
          {loading ? (
            <div className="animate-pulse h-10 rounded bg-slate-700/50" />
          ) : heartbeatEvents.length === 0 ? (
            <p className="text-[11px] text-slate-500 py-2 text-center">
              Henüz heartbeat olayı yok.
            </p>
          ) : (
            <ul className="space-y-0.5 text-[11px] text-slate-400">
              {heartbeatEvents.slice(0, 8).map((ev, i) => (
                <li key={i}>
                  {ev.task} — {ago(ev.timestamp)}
                  {ev.error ? (
                    <span className="text-red-400/80"> — {ev.error}</span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
