"use client";
import { useState, useEffect, useCallback } from "react";
import { fetcher } from "@/lib/api";
interface LearningDashboard {
  teachings: { total: number; active: number; top_used: Teaching[] };
  recommendations: {
    pending: Recommendation[];
    applied: number;
    dismissed: number;
    total: number;
  };
  error_patterns: {
    active: number;
    critical: number;
    patterns: ErrorPattern[];
  };
  optimizer_stats: { total_recommendations: number; health_avg: number };
  tool_stats: { total_analyses: number };
  workflow_stats: { total_executions: number };
  benchmark: { leaderboard: BenchmarkEntry[] };
}
interface Teaching {
  id: number;
  category: string;
  instruction: string;
  trigger_text: string;
  use_count: number;
  active: boolean;
  created_at: string;
}
interface Recommendation {
  id: number;
  type: string;
  title: string;
  description: string;
  affected_agents: string[];
  confidence: number;
  status: string;
  created_at: string;
}
interface ErrorPattern {
  id: string;
  pattern: string;
  count: number;
  severity: string;
  first_seen: string;
  last_seen: string;
  status: string;
}
interface BenchmarkEntry {
  agent_role: string;
  avg_score: number;
  total_runs: number;
}
interface AgentProfile {
  agent_role: string;
  health_score: number;
  eval_stats: Record<string, number>;
  error_stats: Record<string, number>;
  benchmark_stats: Record<string, number>;
  pending_recommendations: number;
  recommendations: Recommendation[];
}
interface TimelineEvent {
  id: string;
  type: string;
  description: string;
  timestamp: string;
  source: string;
}
interface AnalysisResult {
  new_recommendations: number;
  new_patterns: number;
  new_suggestions: number;
  details: Record<string, unknown>;
}
type HubTab =
  | "overview"
  | "recommendations"
  | "teachings"
  | "agents"
  | "errors";
const TABS: { key: HubTab; label: string; icon: string }[] = [
  { key: "overview", label: "Genel Bakış", icon: "📊" },
  { key: "recommendations", label: "Öneriler", icon: "💡" },
  { key: "teachings", label: "Öğrenmeler", icon: "🧠" },
  { key: "agents", label: "Agent Profilleri", icon: "🤖" },
  { key: "errors", label: "Hata Örüntüleri", icon: "🔴" },
];
const cd = "bg-slate-800/50 border border-slate-700/50 rounded-lg p-3";
const AGENTS = [
  "orchestrator",
  "researcher",
  "synthesizer",
  "reasoner",
  "critic",
  "thinker",
  "speed",
];
const TS: Record<string, string> = {
  reliability: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  performance: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  quality: "bg-teal-500/15 text-teal-400 border-teal-500/30",
  cost: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  critical: "bg-red-500/15 text-red-400 border-red-500/30",
};
const SS: Record<string, string> = {
  low: "bg-slate-500/15 text-slate-400 border-slate-500/30",
  medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  high: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  critical: "bg-red-500/15 text-red-400 border-red-500/30",
};
const EI: Record<string, string> = {
  teaching: "🧠",
  recommendation: "💡",
  error_pattern: "🔴",
  analysis: "🔍",
  optimization: "⚡",
  default: "📌",
};
const CATS = [
  "general",
  "performance",
  "reliability",
  "cost",
  "quality",
  "architecture",
];
const tabSt = (on: boolean): React.CSSProperties => ({
  padding: "6px 14px",
  fontSize: 11,
  fontFamily: "Tahoma, sans-serif",
  cursor: "pointer",
  border: "none",
  borderBottom: on ? "2px solid #22d3ee" : "2px solid transparent",
  color: on ? "#22d3ee" : "#94a3b8",
  background: "transparent",
  transition: "color .15s, border-color .15s",
});
const inp =
  "bg-slate-800/60 border border-slate-700/50 rounded px-2 py-1.5 text-[10px] text-slate-300 focus:outline-none focus:border-cyan-500/50 w-full";
const ab =
  "px-2 py-1 text-[9px] rounded border transition-colors disabled:opacity-40";
const hc = (s: number) =>
  s >= 80 ? "text-emerald-400" : s >= 50 ? "text-amber-400" : "text-red-400";
const hbg = (s: number) =>
  s >= 80 ? "#10b981" : s >= 50 ? "#f59e0b" : "#ef4444";
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
function Bd({ t, s }: { t: string; s?: string }) {
  return (
    <span
      className={`text-[9px] px-1.5 py-0.5 rounded border ${s ?? "bg-slate-600/20 text-slate-400 border-slate-500/30"}`}
    >
      {t}
    </span>
  );
}
function fmt(d: string) {
  try {
    return new Date(d).toLocaleString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}
function Mt({ icon, text }: { icon: string; text: string }) {
  return (
    <div className="text-center py-8">
      <div className="text-3xl mb-2">{icon}</div>
      <p className="text-xs text-slate-500">{text}</p>
    </div>
  );
}
function KV({ data, color }: { data: Record<string, number>; color: string }) {
  return (
    <>
      {Object.entries(data).map(([k, v]) => (
        <div key={k} className="flex justify-between text-[10px] py-0.5">
          <span className="text-slate-500">{k}</span>
          <span className={`${color} tabular-nums`}>
            {typeof v === "number" ? v.toLocaleString() : v}
          </span>
        </div>
      ))}
    </>
  );
}
function OverviewTab() {
  const [d, setD] = useState<LearningDashboard | null>(null);
  const [tl, setTl] = useState<TimelineEvent[]>([]);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");
  const [az, setAz] = useState(false);
  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const [da, ti] = await Promise.all([
        fetcher<LearningDashboard>("/api/learning-hub/dashboard"),
        fetcher<TimelineEvent[]>("/api/learning-hub/timeline"),
      ]);
      setD(da);
      setTl(ti);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  const trigger = useCallback(async () => {
    try {
      setAz(true);
      await fetcher<AnalysisResult>("/api/learning-hub/trigger-analysis", {
        method: "POST",
      });
      await load();
    } catch {
    } finally {
      setAz(false);
    }
  }, [load]);
  if (ld) return <Sk n={5} />;
  if (e) return <Er m={e} r={load} />;
  if (!d) return null;
  const hp = Math.round(d.optimizer_stats.health_avg ?? 0);
  const stats = [
    { l: "Toplam Öğrenme", v: d.teachings.total, c: "text-cyan-400" },
    {
      l: "Aktif Öneriler",
      v: d.recommendations.pending.length,
      c: "text-amber-400",
    },
    { l: "Hata Örüntüleri", v: d.error_patterns.active, c: "text-red-400" },
    { l: "Sistem Sağlığı", v: `%${hp}`, c: hc(hp) },
  ];
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-4 gap-2">
        {stats.map((s) => (
          <div key={s.l} className={cd + " text-center"}>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">
              {s.l}
            </div>
            <div className={`text-lg font-bold tabular-nums ${s.c}`}>{s.v}</div>
          </div>
        ))}
      </div>
      <button
        onClick={trigger}
        disabled={az}
        style={{ fontFamily: "Tahoma, sans-serif" }}
        className="w-full px-3 py-2 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 text-xs font-medium rounded border border-cyan-500/20 transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {az ? (
          <span className="inline-block w-3 h-3 border border-cyan-400 border-t-transparent rounded-full animate-spin" />
        ) : (
          "🔍"
        )}
        {az ? "Analiz Ediliyor…" : "Tam Analiz Çalıştır"}
      </button>
      <div className={cd}>
        <h4 className="text-xs font-medium text-slate-200 mb-2">Son Olaylar</h4>
        {tl.length === 0 ? (
          <p className="text-[10px] text-slate-600 text-center py-4">
            Henüz olay yok
          </p>
        ) : (
          <div className="space-y-1.5 max-h-[260px] overflow-y-auto pr-1">
            {tl.map((ev) => (
              <div
                key={ev.id}
                className="flex items-start gap-2 py-1 border-b border-slate-700/30 last:border-0"
              >
                <span className="text-sm flex-shrink-0">
                  {EI[ev.type] ?? EI.default}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] text-slate-300 leading-snug">
                    {ev.description}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[9px] text-slate-600 tabular-nums">
                      {fmt(ev.timestamp)}
                    </span>
                    <Bd t={ev.type} s={TS[ev.type]} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
function RecommendationsTab() {
  const [d, setD] = useState<LearningDashboard | null>(null);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");
  const [busy, setBusy] = useState<number | null>(null);
  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      setD(await fetcher<LearningDashboard>("/api/learning-hub/dashboard"));
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  const act = useCallback(
    async (id: number, a: "apply" | "dismiss") => {
      try {
        setBusy(id);
        await fetcher<unknown>(`/api/learning-hub/recommendations/${id}/${a}`, {
          method: "POST",
        });
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
  if (!d) return null;
  const pend = d.recommendations.pending.filter((r) => r.status === "pending");
  return (
    <div className="space-y-3">
      {pend.length === 0 ? (
        <Mt icon="💡" text="Bekleyen öneri yok" />
      ) : (
        <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
          {pend.map((r) => (
            <div
              key={r.id}
              className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2.5 hover:border-slate-600/40 transition-colors"
            >
              <div className="flex items-start gap-2 mb-1">
                <span className="text-xs font-medium text-slate-200 flex-1">
                  {r.title}
                </span>
                <Bd t={r.type} s={TS[r.type]} />
              </div>
              <p className="text-[11px] text-slate-400 mb-2 leading-relaxed">
                {r.description}
              </p>
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
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[9px] text-slate-500 w-12">Güven:</span>
                <div className="flex-1 bg-slate-700/50 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-cyan-500 transition-all duration-500"
                    style={{ width: `${Math.min(r.confidence * 100, 100)}%` }}
                  />
                </div>
                <span className="text-[9px] text-slate-500 tabular-nums w-8 text-right">
                  %{Math.round(r.confidence * 100)}
                </span>
              </div>
              <div className="flex gap-1.5 justify-end">
                <button
                  onClick={() => act(r.id, "apply")}
                  disabled={busy === r.id}
                  className={`${ab} bg-emerald-600/15 hover:bg-emerald-600/25 text-emerald-400 border-emerald-500/20`}
                >
                  ✓ Uygula
                </button>
                <button
                  onClick={() => act(r.id, "dismiss")}
                  disabled={busy === r.id}
                  className={`${ab} bg-slate-600/15 hover:bg-slate-600/25 text-slate-400 border-slate-500/20`}
                >
                  ✕ Reddet
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      {(d.recommendations.applied > 0 || d.recommendations.dismissed > 0) && (
        <div className="flex items-center gap-2 text-[10px] text-slate-500 px-1">
          <span>{d.recommendations.applied} uygulandı</span>
          <span>·</span>
          <span>{d.recommendations.dismissed} reddedildi</span>
        </div>
      )}
    </div>
  );
}
function TeachingsTab() {
  const [list, setList] = useState<Teaching[]>([]);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");
  const [form, setForm] = useState(false);
  const [cat, setCat] = useState(CATS[0]);
  const [inst, setInst] = useState("");
  const [trig, setTrig] = useState("");
  const [sav, setSav] = useState(false);
  const [busy, setBusy] = useState<number | null>(null);
  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      setList(await fetcher<Teaching[]>("/api/learning-hub/teachings"));
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  const add = useCallback(async () => {
    if (!inst.trim()) return;
    try {
      setSav(true);
      await fetcher<Teaching>("/api/learning-hub/teachings", {
        method: "POST",
        body: JSON.stringify({
          category: cat,
          instruction: inst,
          trigger_text: trig,
        }),
      });
      setInst("");
      setTrig("");
      setForm(false);
      await load();
    } catch {
    } finally {
      setSav(false);
    }
  }, [cat, inst, trig, load]);
  const deact = useCallback(
    async (id: number) => {
      try {
        setBusy(id);
        await fetcher<unknown>(`/api/learning-hub/teachings/${id}/deactivate`, {
          method: "POST",
        });
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
  const active = list.filter((t) => t.active);
  return (
    <div className="space-y-3">
      <button
        onClick={() => setForm(!form)}
        style={{ fontFamily: "Tahoma, sans-serif" }}
        className="px-3 py-1.5 text-xs bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 rounded border border-cyan-500/20 transition-colors"
      >
        {form ? "✕ İptal" : "＋ Yeni Öğrenme Ekle"}
      </button>
      {form && (
        <div className={cd + " space-y-2"}>
          <div>
            <label className="text-[10px] text-slate-500 block mb-1">
              Kategori
            </label>
            <select
              value={cat}
              onChange={(x) => setCat(x.target.value)}
              className={inp}
            >
              {CATS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-slate-500 block mb-1">
              Talimat
            </label>
            <textarea
              value={inst}
              onChange={(x) => setInst(x.target.value)}
              rows={3}
              placeholder="Öğrenme talimatını yazın…"
              className={inp + " resize-none"}
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-500 block mb-1">
              Tetikleyici
            </label>
            <input
              value={trig}
              onChange={(x) => setTrig(x.target.value)}
              placeholder="Tetikleyici metin…"
              className={inp}
            />
          </div>
          <button
            onClick={add}
            disabled={sav || !inst.trim()}
            className="px-3 py-1.5 text-xs bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 rounded border border-emerald-500/20 transition-colors disabled:opacity-40"
          >
            {sav ? "Kaydediliyor…" : "Kaydet"}
          </button>
        </div>
      )}
      {active.length === 0 ? (
        <Mt icon="🧠" text="Henüz öğrenme yok" />
      ) : (
        <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
          {active.map((t) => (
            <div
              key={t.id}
              className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2.5 hover:border-slate-600/40 transition-colors"
            >
              <div className="flex items-start gap-2 mb-1">
                <Bd t={t.category} s={TS[t.category]} />
                <span className="text-[9px] text-slate-600 ml-auto tabular-nums">
                  ×{t.use_count}
                </span>
              </div>
              <p className="text-[11px] text-slate-300 mb-1 leading-relaxed">
                {t.instruction}
              </p>
              {t.trigger_text && (
                <p className="text-[10px] text-slate-500">
                  Tetikleyici: {t.trigger_text}
                </p>
              )}
              <div className="flex justify-end mt-1.5">
                <button
                  onClick={() => deact(t.id)}
                  disabled={busy === t.id}
                  className={`${ab} bg-red-600/10 hover:bg-red-600/20 text-red-400 border-red-500/20`}
                  aria-label={`${t.instruction} öğrenmesini devre dışı bırak`}
                >
                  🗑 Kaldır
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
function AgentProfilesTab() {
  const [role, setRole] = useState(AGENTS[0]);
  const [p, setP] = useState<AgentProfile | null>(null);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");
  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      setP(
        await fetcher<AgentProfile>(`/api/learning-hub/agent-profile/${role}`),
      );
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, [role]);
  useEffect(() => {
    load();
  }, [load]);
  return (
    <div className="space-y-3">
      <select
        value={role}
        onChange={(x) => setRole(x.target.value)}
        className={inp}
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
      ) : !p ? null : (
        <div className="space-y-3">
          <div className={cd}>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-medium text-slate-200">
                Sağlık Skoru
              </h4>
              <span
                className={`text-2xl font-bold tabular-nums ${hc(p.health_score ?? 0)}`}
              >
                {p.health_score ?? 0}
              </span>
            </div>
            <div className="w-full bg-slate-700/50 rounded-full h-2 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min(p.health_score ?? 0, 100)}%`,
                  backgroundColor: hbg(p.health_score ?? 0),
                }}
              />
            </div>
          </div>
          {[
            { d: p.eval_stats, t: "Değerlendirme", c: "text-slate-300" },
            { d: p.error_stats, t: "Hatalar", c: "text-red-400" },
            { d: p.benchmark_stats, t: "Benchmark", c: "text-cyan-400" },
          ].map((s) =>
            s.d && Object.keys(s.d).length > 0 ? (
              <div key={s.t} className={cd}>
                <h4 className="text-[10px] font-medium text-slate-300 mb-1.5">
                  {s.t}
                </h4>
                <KV data={s.d} color={s.c} />
              </div>
            ) : null,
          )}
          {(p.pending_recommendations ?? 0) > 0 && (
            <div className="text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded px-3 py-2">
              ⚠ {p.pending_recommendations} bekleyen öneri mevcut
            </div>
          )}
        </div>
      )}
    </div>
  );
}
function ErrorPatternsTab() {
  const [d, setD] = useState<LearningDashboard | null>(null);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      setD(await fetcher<LearningDashboard>("/api/learning-hub/dashboard"));
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  const resolve = useCallback(
    async (id: string) => {
      try {
        setBusy(id);
        await fetcher<unknown>(
          `/api/learning-hub/error-patterns/${id}/resolve`,
          { method: "POST" },
        );
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
  if (!d) return null;
  const pts = d.error_patterns.patterns;
  if (pts.length === 0)
    return <Mt icon="🔴" text="Tespit edilen hata örüntüsü yok" />;
  return (
    <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
      {pts.map((p) => (
        <div
          key={p.id}
          className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2.5 hover:border-slate-600/40 transition-colors"
        >
          <div className="flex items-start gap-2 mb-1">
            <span className="text-[11px] text-slate-200 flex-1 leading-snug">
              {p.pattern}
            </span>
            <Bd t={p.severity} s={SS[p.severity]} />
          </div>
          <div className="flex items-center gap-3 text-[9px] text-slate-500 mb-1.5">
            <span>
              Tekrar:{" "}
              <span className="text-slate-300 tabular-nums">{p.count}</span>
            </span>
            <span>İlk: {fmt(p.first_seen)}</span>
            <span>Son: {fmt(p.last_seen)}</span>
            {p.status !== "active" && <Bd t={p.status} />}
          </div>
          {p.status === "active" && (
            <div className="flex justify-end">
              <button
                onClick={() => resolve(p.id)}
                disabled={busy === p.id}
                className={`${ab} bg-emerald-600/15 hover:bg-emerald-600/25 text-emerald-400 border-emerald-500/20`}
              >
                ✓ Çözüldü
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
export function LearningHubPanel() {
  const [tab, setTab] = useState<HubTab>("overview");
  return (
    <div className="space-y-3">
      <nav
        className="flex gap-0.5 border-b border-slate-700/50"
        role="tablist"
        aria-label="Öğrenme Merkezi sekmeleri"
      >
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={tabSt(tab === t.key)}
            role="tab"
            aria-selected={tab === t.key}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </nav>
      <div role="tabpanel">
        {tab === "overview" && <OverviewTab />}
        {tab === "recommendations" && <RecommendationsTab />}
        {tab === "teachings" && <TeachingsTab />}
        {tab === "agents" && <AgentProfilesTab />}
        {tab === "errors" && <ErrorPatternsTab />}
      </div>
    </div>
  );
}
