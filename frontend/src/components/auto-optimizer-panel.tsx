"use client";

import { useState, useEffect, useCallback } from "react";
import { optimizerApi } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────────────── */
interface OptimizationStats {
  total_recommendations: number;
  pending: number;
  applied: number;
  dismissed: number;
  by_category: Record<string, number>;
  by_priority: Record<string, number>;
}
interface Recommendation {
  id: number;
  category: "performance" | "reliability" | "cost" | "quality";
  priority: "critical" | "high" | "medium" | "low";
  title: string;
  description: string;
  affected_agents: string[];
  suggested_actions: string[];
  estimated_impact: string;
  status: "pending" | "applied" | "dismissed";
  created_at: string;
}
interface AgentProfile {
  agent_role: string;
  recommendations: Recommendation[];
  performance_score: number;
  optimization_potential: string;
  health_score: number;
  eval_stats: Record<string, number>;
  error_stats: Record<string, number>;
  benchmark_stats: Record<string, number>;
  pending_recommendations: number;
  applied_recommendations: number;
  total_recommendations: number;
}
interface HistoryEntry {
  id: number;
  recommendation_id: number;
  title: string;
  category: string;
  priority: string;
  action: string;
  notes?: string;
  performed_at: string;
}

/* ── Constants ─────────────────────────────────────────────────── */
type OptTab = "overview" | "recommendations" | "agent-profile" | "history";
const TABS: { key: OptTab; label: string; icon: string }[] = [
  { key: "overview", label: "Genel Bakış", icon: "📊" },
  { key: "recommendations", label: "Öneriler", icon: "💡" },
  { key: "agent-profile", label: "Agent Profili", icon: "🤖" },
  { key: "history", label: "Geçmiş", icon: "📜" },
];
const crd = "bg-slate-800/50 border border-slate-700/50 rounded-lg p-4";
const CL = [
  "#ef4444",
  "#f59e0b",
  "#10b981",
  "#06b6d4",
  "#ec4899",
  "#84cc16",
  "#a78bfa",
];

const CATEGORY_STYLE: Record<string, string> = {
  performance: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  reliability: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  cost: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  quality: "bg-purple-500/15 text-purple-400 border-purple-500/30",
};
const CATEGORY_LABEL: Record<string, string> = {
  performance: "Performans",
  reliability: "Güvenilirlik",
  cost: "Maliyet",
  quality: "Kalite",
};
const PRIORITY_STYLE: Record<string, string> = {
  critical: "bg-red-500/15 text-red-400 border-red-500/30",
  high: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  low: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
};
const PRIORITY_LABEL: Record<string, string> = {
  critical: "Kritik",
  high: "Yüksek",
  medium: "Orta",
  low: "Düşük",
};
const AGENTS = [
  "orchestrator",
  "researcher",
  "synthesizer",
  "reasoner",
  "critic",
  "thinker",
  "speed",
];

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

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: string;
}) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2 flex-1 min-w-0">
      <div className="text-[10px] text-slate-500 uppercase tracking-wider truncate">
        {label}
      </div>
      <div
        className={`text-lg font-bold tabular-nums ${accent ?? "text-slate-200"}`}
      >
        {value}
      </div>
    </div>
  );
}

function Bar({ v, mx, c, l }: { v: number; mx: number; c: string; l: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-slate-400 w-24 truncate" title={l}>
        {l}
      </span>
      <div className="flex-1 bg-slate-700/50 rounded-full h-2 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${mx > 0 ? Math.min((v / mx) * 100, 100) : 0}%`,
            backgroundColor: c,
          }}
        />
      </div>
      <span className="text-[10px] text-slate-500 w-8 text-right tabular-nums">
        {v}
      </span>
    </div>
  );
}

/* ── Tab 1: Genel Bakış ────────────────────────────────────────── */
function OverviewTab() {
  const [stats, setStats] = useState<OptimizationStats | null>(null);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");
  const [analyzing, setAnalyzing] = useState(false);

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const data = await optimizerApi.getStats();
      setStats({
        total_recommendations: data.total_recommendations ?? 0,
        pending: data.by_status?.pending ?? 0,
        applied: data.by_status?.applied ?? 0,
        dismissed: data.by_status?.dismissed ?? 0,
        by_category: data.by_category ?? {},
        by_priority: data.by_priority ?? {},
      });
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const analyze = useCallback(async () => {
    try {
      setAnalyzing(true);
      await optimizerApi.analyze();
      await load();
    } catch {
    } finally {
      setAnalyzing(false);
    }
  }, [load]);

  if (ld) return <Sk n={5} />;
  if (e) return <Er m={e} r={load} />;
  if (!stats) return null;

  const byCat = Object.entries(stats.by_category).sort(([, a], [, b]) => b - a);
  const byPri = Object.entries(stats.by_priority).sort(([, a], [, b]) => b - a);
  const mxCat = Math.max(...byCat.map(([, v]) => v), 1);
  const mxPri = Math.max(...byPri.map(([, v]) => v), 1);

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap">
        <StatCard
          label="Toplam Öneri"
          value={stats.total_recommendations}
          accent="text-cyan-400"
        />
        <StatCard
          label="Bekleyen"
          value={stats.pending}
          accent="text-amber-400"
        />
        <StatCard
          label="Uygulanan"
          value={stats.applied}
          accent="text-emerald-400"
        />
        <StatCard
          label="Reddedilen"
          value={stats.dismissed}
          accent="text-slate-400"
        />
      </div>

      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Kategori Dağılımı
        </h4>
        <div className="space-y-2">
          {byCat.length === 0 && (
            <p className="text-xs text-slate-600 text-center py-4">Veri yok</p>
          )}
          {byCat.map(([cat, count], i) => (
            <Bar
              key={cat}
              v={count}
              mx={mxCat}
              c={CL[i % CL.length]}
              l={CATEGORY_LABEL[cat] ?? cat}
            />
          ))}
        </div>
      </div>

      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Öncelik Dağılımı
        </h4>
        <div className="space-y-2">
          {byPri.length === 0 && (
            <p className="text-xs text-slate-600 text-center py-4">Veri yok</p>
          )}
          {byPri.map(([pri, count], i) => (
            <Bar
              key={pri}
              v={count}
              mx={mxPri}
              c={CL[i % CL.length]}
              l={PRIORITY_LABEL[pri] ?? pri}
            />
          ))}
        </div>
      </div>

      <button
        onClick={analyze}
        disabled={analyzing}
        className="w-full px-3 py-2 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 text-xs font-medium rounded border border-cyan-500/20 transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
        aria-label="Analiz başlat"
      >
        {analyzing ? (
          <span className="inline-block w-3 h-3 border border-cyan-400 border-t-transparent rounded-full animate-spin" />
        ) : (
          "🔍"
        )}
        {analyzing ? "Analiz Ediliyor…" : "Analiz Başlat"}
      </button>
    </div>
  );
}

/* ── Tab 2: Öneriler ───────────────────────────────────────────── */
function RecommendationsTab() {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");
  const [busy, setBusy] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const data = await optimizerApi.getRecommendations("pending");
      setRecs(data.recommendations ?? data ?? []);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const apply = useCallback(
    async (id: number) => {
      try {
        setBusy(id);
        await optimizerApi.apply(id);
        await load();
      } catch {
      } finally {
        setBusy(null);
      }
    },
    [load],
  );

  const dismiss = useCallback(
    async (id: number) => {
      try {
        setBusy(id);
        await optimizerApi.dismiss(id);
        await load();
      } catch {
      } finally {
        setBusy(null);
      }
    },
    [load],
  );

  if (ld) return <Sk n={4} />;
  if (e) return <Er m={e} r={load} />;

  if (recs.length === 0) {
    return (
      <div className="text-center py-10">
        <div className="text-3xl mb-2">💡</div>
        <p className="text-xs text-slate-500">Bekleyen öneri yok</p>
        <p className="text-[10px] text-slate-600 mt-1">
          Genel Bakış sekmesinden analiz başlatarak yeni öneriler
          oluşturabilirsiniz
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
      {recs.map((r) => (
        <div
          key={r.id}
          className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2.5 hover:border-slate-600/40 transition-colors"
        >
          <div className="flex items-start gap-2 mb-1.5">
            <span className="text-xs font-medium text-slate-200 flex-1">
              {r.title}
            </span>
            <span
              className={`text-[9px] px-1.5 py-0.5 rounded border ${CATEGORY_STYLE[r.category] ?? CATEGORY_STYLE.performance}`}
            >
              {CATEGORY_LABEL[r.category] ?? r.category}
            </span>
            <span
              className={`text-[9px] px-1.5 py-0.5 rounded border ${PRIORITY_STYLE[r.priority] ?? PRIORITY_STYLE.medium}`}
            >
              {PRIORITY_LABEL[r.priority] ?? r.priority}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mb-2 leading-relaxed">
            {r.description}
          </p>

          {/* Affected agents */}
          {r.affected_agents?.length > 0 && (
            <div className="flex items-center gap-1 mb-2 flex-wrap">
              <span className="text-[9px] text-slate-500">Etkilenen:</span>
              {r.affected_agents.map((a) => (
                <span
                  key={a}
                  className="inline-block px-1 py-0.5 bg-slate-700/60 text-slate-400 rounded text-[8px]"
                >
                  {a}
                </span>
              ))}
            </div>
          )}

          {/* Suggested actions */}
          {r.suggested_actions?.length > 0 && (
            <div className="mb-2">
              <span className="text-[9px] text-slate-500 block mb-1">
                Önerilen Aksiyonlar:
              </span>
              <ol className="list-decimal list-inside space-y-0.5">
                {r.suggested_actions.map((action, i) => (
                  <li
                    key={i}
                    className="text-[10px] text-cyan-400/80 leading-relaxed"
                  >
                    {action}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {r.estimated_impact && (
            <p className="text-[9px] text-slate-500 mb-2">
              Tahmini Etki:{" "}
              <span className="text-emerald-400">{r.estimated_impact}</span>
            </p>
          )}

          <div className="flex gap-1.5 justify-end">
            <button
              onClick={() => apply(r.id)}
              disabled={busy === r.id}
              className="px-2 py-1 text-[9px] bg-emerald-600/15 hover:bg-emerald-600/25 text-emerald-400 rounded border border-emerald-500/20 transition-colors disabled:opacity-40"
            >
              ✓ Uygula
            </button>
            <button
              onClick={() => dismiss(r.id)}
              disabled={busy === r.id}
              className="px-2 py-1 text-[9px] bg-slate-600/15 hover:bg-slate-600/25 text-slate-400 rounded border border-slate-500/20 transition-colors disabled:opacity-40"
            >
              ✕ Reddet
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Tab 3: Agent Profili ──────────────────────────────────────── */
function AgentProfileTab() {
  const [role, setRole] = useState(AGENTS[0]);
  const [profile, setProfile] = useState<AgentProfile | null>(null);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const data = await optimizerApi.getAgentProfile(role);
      setProfile(data);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, [role]);

  useEffect(() => {
    load();
  }, [load]);

  const healthColor = (score: number) =>
    score >= 80
      ? "text-emerald-400"
      : score >= 50
        ? "text-amber-400"
        : "text-red-400";

  return (
    <div className="space-y-3">
      <select
        value={role}
        onChange={(x) => setRole(x.target.value)}
        className="bg-slate-800/60 border border-slate-700/50 rounded px-2 py-1.5 text-[10px] text-slate-300 focus:outline-none focus:border-cyan-500/50 w-full"
        aria-label="Agent seçimi"
      >
        {AGENTS.map((a) => (
          <option key={a} value={a}>
            {a}
          </option>
        ))}
      </select>

      {ld ? (
        <Sk n={5} />
      ) : e ? (
        <Er m={e} r={load} />
      ) : !profile ? null : (
        <div className="space-y-3">
          {/* Health score */}
          <div className={crd}>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-medium text-slate-200">
                Sağlık Skoru
              </h4>
              <span
                className={`text-2xl font-bold tabular-nums ${healthColor(profile.health_score ?? 0)}`}
              >
                {profile.health_score ?? 0}
              </span>
            </div>
            <div className="w-full bg-slate-700/50 rounded-full h-2 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min(profile.health_score ?? 0, 100)}%`,
                  backgroundColor:
                    (profile.health_score ?? 0) >= 80
                      ? "#10b981"
                      : (profile.health_score ?? 0) >= 50
                        ? "#f59e0b"
                        : "#ef4444",
                }}
              />
            </div>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-3 gap-2">
            <StatCard
              label="Bekleyen"
              value={profile.pending_recommendations ?? 0}
              accent="text-amber-400"
            />
            <StatCard
              label="Uygulanan"
              value={profile.applied_recommendations ?? 0}
              accent="text-emerald-400"
            />
            <StatCard
              label="Toplam"
              value={profile.total_recommendations ?? 0}
            />
          </div>

          {/* Eval stats */}
          {profile.eval_stats && Object.keys(profile.eval_stats).length > 0 && (
            <div className={crd}>
              <h4 className="text-xs font-medium text-slate-200 mb-2">
                Değerlendirme İstatistikleri
              </h4>
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                {Object.entries(profile.eval_stats).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-slate-500">{k}</span>
                    <span className="text-slate-300 tabular-nums">
                      {typeof v === "number" ? v.toLocaleString() : v}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error stats */}
          {profile.error_stats &&
            Object.keys(profile.error_stats).length > 0 && (
              <div className={crd}>
                <h4 className="text-xs font-medium text-slate-200 mb-2">
                  Hata İstatistikleri
                </h4>
                <div className="grid grid-cols-2 gap-2 text-[10px]">
                  {Object.entries(profile.error_stats).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-slate-500">{k}</span>
                      <span className="text-red-400 tabular-nums">
                        {typeof v === "number" ? v.toLocaleString() : v}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

          {/* Benchmark stats */}
          {profile.benchmark_stats &&
            Object.keys(profile.benchmark_stats).length > 0 && (
              <div className={crd}>
                <h4 className="text-xs font-medium text-slate-200 mb-2">
                  Benchmark İstatistikleri
                </h4>
                <div className="grid grid-cols-2 gap-2 text-[10px]">
                  {Object.entries(profile.benchmark_stats).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-slate-500">{k}</span>
                      <span className="text-cyan-400 tabular-nums">
                        {typeof v === "number" ? v.toLocaleString() : v}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

          {/* Agent recommendations */}
          {profile.recommendations?.length > 0 && (
            <div className={crd}>
              <h4 className="text-xs font-medium text-slate-200 mb-2">
                Öneriler ({profile.recommendations.length})
              </h4>
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {profile.recommendations.map((r) => (
                  <div
                    key={r.id}
                    className="flex items-center gap-2 text-[10px]"
                  >
                    <span
                      className={`px-1 py-0.5 rounded border ${PRIORITY_STYLE[r.priority] ?? PRIORITY_STYLE.medium}`}
                    >
                      {PRIORITY_LABEL[r.priority] ?? r.priority}
                    </span>
                    <span className="text-slate-300 flex-1 truncate">
                      {r.title}
                    </span>
                    <span
                      className={`px-1 py-0.5 rounded border text-[8px] ${
                        r.status === "applied"
                          ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                          : r.status === "dismissed"
                            ? "bg-slate-500/15 text-slate-400 border-slate-500/30"
                            : "bg-amber-500/15 text-amber-400 border-amber-500/30"
                      }`}
                    >
                      {r.status === "applied"
                        ? "Uygulandı"
                        : r.status === "dismissed"
                          ? "Reddedildi"
                          : "Bekliyor"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Tab 4: Geçmiş ─────────────────────────────────────────────── */
function HistoryTab() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const data = await optimizerApi.getHistory(50);
      setHistory(data.history ?? data ?? []);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (ld) return <Sk n={4} />;
  if (e) return <Er m={e} r={load} />;

  if (history.length === 0) {
    return (
      <div className="text-center py-10">
        <div className="text-3xl mb-2">📜</div>
        <p className="text-xs text-slate-500">Henüz geçmiş kaydı yok</p>
        <p className="text-[10px] text-slate-600 mt-1">
          Öneriler uygulandığında veya reddedildiğinde burada görünür
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
      {history.map((h) => (
        <div
          key={h.id}
          className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2.5 hover:border-slate-600/40 transition-colors"
        >
          <div className="flex items-start gap-2 mb-1">
            <span
              className={`text-[9px] px-1.5 py-0.5 rounded border ${
                h.action === "applied"
                  ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                  : "bg-slate-500/15 text-slate-400 border-slate-500/30"
              }`}
            >
              {h.action === "applied" ? "✓ Uygulandı" : "✕ Reddedildi"}
            </span>
            <span
              className={`text-[9px] px-1.5 py-0.5 rounded border ${CATEGORY_STYLE[h.category] ?? CATEGORY_STYLE.performance}`}
            >
              {CATEGORY_LABEL[h.category] ?? h.category}
            </span>
            <span className="text-[9px] text-slate-600 ml-auto tabular-nums">
              {h.performed_at
                ? new Date(h.performed_at).toLocaleString("tr-TR", {
                    day: "2-digit",
                    month: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                : "—"}
            </span>
          </div>
          <p className="text-xs text-slate-300">{h.title}</p>
          {h.notes && (
            <p className="text-[10px] text-slate-500 mt-1">Not: {h.notes}</p>
          )}
        </div>
      ))}
    </div>
  );
}

/* ── Main Component ────────────────────────────────────────────── */
export default function AutoOptimizerPanel() {
  const [tab, setTab] = useState<OptTab>("overview");

  return (
    <div className="space-y-4">
      <nav
        className="flex gap-1 border-b border-slate-700/50"
        aria-label="Optimizasyon sekmeleri"
      >
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-xs transition-colors border-b-2 ${
              tab === t.key
                ? "border-cyan-400 text-cyan-400"
                : "border-transparent text-slate-400 hover:text-slate-700"
            }`}
            aria-selected={tab === t.key}
            role="tab"
          >
            {t.icon} {t.label}
          </button>
        ))}
      </nav>

      <div role="tabpanel">
        {tab === "overview" && <OverviewTab />}
        {tab === "recommendations" && <RecommendationsTab />}
        {tab === "agent-profile" && <AgentProfileTab />}
        {tab === "history" && <HistoryTab />}
      </div>
    </div>
  );
}
