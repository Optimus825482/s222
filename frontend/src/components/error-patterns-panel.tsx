"use client";

import { useState, useEffect, useCallback } from "react";
import { errorPatternApi } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────────────── */
interface ErrorStats {
  total_errors: number;
  active_patterns: number;
  critical_errors: number;
  most_failing_agent: string;
  by_type: Record<string, number>;
  by_agent: Record<string, number>;
}
interface TimelinePoint {
  hour: string;
  count: number;
  critical: number;
  warning: number;
  info: number;
}
interface ErrorPattern {
  id: number;
  name: string;
  description: string;
  frequency: number;
  affected_agents: string[];
  status: "active" | "resolved" | "suppressed";
  first_seen?: string;
}
interface Recommendation {
  id: number;
  title: string;
  description: string;
  priority: "high" | "medium" | "low";
  affected_agent: string;
  suggested_action: string;
}

/* ── Constants ─────────────────────────────────────────────────── */
type ErrTab = "overview" | "timeline" | "patterns" | "recommendations";
const TABS: { key: ErrTab; label: string; icon: string }[] = [
  { key: "overview", label: "Genel Bakış", icon: "📊" },
  { key: "timeline", label: "Zaman Çizelgesi", icon: "📈" },
  { key: "patterns", label: "Patternler", icon: "🔍" },
  { key: "recommendations", label: "Öneriler", icon: "💡" },
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

const STATUS_STYLE: Record<string, string> = {
  active: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  resolved: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  suppressed: "bg-slate-500/15 text-slate-400 border-slate-500/30",
};
const PRIORITY_STYLE: Record<string, string> = {
  high: "bg-red-500/15 text-red-400 border-red-500/30",
  medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  low: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
};

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
  const [stats, setStats] = useState<ErrorStats | null>(null);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const data = await errorPatternApi.getStats(undefined, 24);
      setStats(data);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (ld) return <Sk n={5} />;
  if (e) return <Er m={e} r={load} />;
  if (!stats) return null;

  const byType = Object.entries(stats.by_type ?? {}).sort(
    ([, a], [, b]) => b - a,
  );
  const byAgent = Object.entries(stats.by_agent ?? {}).sort(
    ([, a], [, b]) => b - a,
  );
  const mxType = Math.max(...byType.map(([, v]) => v), 1);
  const mxAgent = Math.max(...byAgent.map(([, v]) => v), 1);

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap">
        <StatCard
          label="Toplam Hata (24s)"
          value={stats.total_errors}
          accent="text-red-400"
        />
        <StatCard
          label="Aktif Pattern"
          value={stats.active_patterns}
          accent="text-blue-400"
        />
        <StatCard
          label="Kritik Hata"
          value={stats.critical_errors}
          accent="text-orange-400"
        />
        <StatCard
          label="En Çok Hata Veren"
          value={stats.most_failing_agent || "—"}
        />
      </div>

      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Hata Tipi Dağılımı
        </h4>
        <div className="space-y-2">
          {byType.length === 0 && (
            <p className="text-xs text-slate-600 text-center py-4">Veri yok</p>
          )}
          {byType.slice(0, 8).map(([type, count], i) => (
            <Bar
              key={type}
              v={count}
              mx={mxType}
              c={CL[i % CL.length]}
              l={type}
            />
          ))}
        </div>
      </div>

      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Agent Bazlı Hatalar
        </h4>
        <div className="space-y-2">
          {byAgent.length === 0 && (
            <p className="text-xs text-slate-600 text-center py-4">Veri yok</p>
          )}
          {byAgent.slice(0, 8).map(([agent, count], i) => (
            <Bar
              key={agent}
              v={count}
              mx={mxAgent}
              c={CL[i % CL.length]}
              l={agent}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Tab 2: Zaman Çizelgesi ────────────────────────────────────── */
function TimelineTab() {
  const [points, setPoints] = useState<TimelinePoint[]>([]);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const data = await errorPatternApi.getTimeline(24);
      setPoints(data.timeline ?? data ?? []);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (ld) return <Sk n={6} />;
  if (e) return <Er m={e} r={load} />;

  const maxCount = Math.max(...points.map((p) => p.count), 1);

  return (
    <div className={crd}>
      <h4 className="text-xs font-medium text-slate-200 mb-3">
        Son 24 Saat — Saatlik Hata Sayısı
      </h4>
      {points.length === 0 ? (
        <p className="text-xs text-slate-600 text-center py-8">
          Zaman çizelgesi verisi yok
        </p>
      ) : (
        <div
          className="flex items-end gap-[3px] h-40"
          role="img"
          aria-label="Saatlik hata grafiği"
        >
          {points.map((p, i) => {
            const pct = (p.count / maxCount) * 100;
            const critPct = p.count > 0 ? (p.critical / p.count) * pct : 0;
            const warnPct = p.count > 0 ? (p.warning / p.count) * pct : 0;
            const infoPct = Math.max(pct - critPct - warnPct, 0);
            const hour = p.hour?.slice(-5) ?? `${i}`;
            return (
              <div
                key={i}
                className="flex-1 flex flex-col items-center gap-1 min-w-0"
              >
                <div className="w-full flex flex-col justify-end h-32 relative group">
                  <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-slate-700 text-[9px] text-slate-300 px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                    {p.count} hata
                  </div>
                  <div
                    className="w-full rounded-t overflow-hidden flex flex-col justify-end"
                    style={{ height: `${Math.max(pct, 2)}%` }}
                  >
                    {critPct > 0 && (
                      <div
                        className="w-full bg-red-500"
                        style={{ height: `${critPct}%`, minHeight: "2px" }}
                      />
                    )}
                    {warnPct > 0 && (
                      <div
                        className="w-full bg-amber-500"
                        style={{ height: `${warnPct}%`, minHeight: "2px" }}
                      />
                    )}
                    {infoPct > 0 && (
                      <div
                        className="w-full bg-cyan-500"
                        style={{ height: `${infoPct}%`, minHeight: "2px" }}
                      />
                    )}
                    {p.count === 0 && (
                      <div className="w-full bg-slate-700/40 h-[2px]" />
                    )}
                  </div>
                </div>
                <span className="text-[8px] text-slate-600 truncate w-full text-center">
                  {hour}
                </span>
              </div>
            );
          })}
        </div>
      )}
      <div className="flex gap-4 mt-3 justify-center">
        <span className="flex items-center gap-1 text-[9px] text-slate-500">
          <span className="w-2 h-2 rounded-sm bg-red-500" />
          Kritik
        </span>
        <span className="flex items-center gap-1 text-[9px] text-slate-500">
          <span className="w-2 h-2 rounded-sm bg-amber-500" />
          Uyarı
        </span>
        <span className="flex items-center gap-1 text-[9px] text-slate-500">
          <span className="w-2 h-2 rounded-sm bg-cyan-500" />
          Bilgi
        </span>
      </div>
    </div>
  );
}

/* ── Tab 3: Patternler ─────────────────────────────────────────── */
function PatternsTab() {
  const [patterns, setPatterns] = useState<ErrorPattern[]>([]);
  const [filter, setFilter] = useState<string>("");
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");
  const [detecting, setDetecting] = useState(false);
  const [busy, setBusy] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const data = await errorPatternApi.getPatterns(filter || undefined);
      setPatterns(data.patterns ?? data ?? []);
    } catch (x) {
      setE(x instanceof Error ? x.message : "Veri yüklenemedi");
    } finally {
      setLd(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  const detect = useCallback(async () => {
    try {
      setDetecting(true);
      await errorPatternApi.detectPatterns(24);
      await load();
    } catch {
    } finally {
      setDetecting(false);
    }
  }, [load]);

  const resolve = useCallback(
    async (id: number) => {
      try {
        setBusy(id);
        await errorPatternApi.resolvePattern(id);
        await load();
      } catch {
      } finally {
        setBusy(null);
      }
    },
    [load],
  );

  const suppress = useCallback(
    async (id: number) => {
      try {
        setBusy(id);
        await errorPatternApi.suppressPattern(id);
        await load();
      } catch {
      } finally {
        setBusy(null);
      }
    },
    [load],
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <select
          value={filter}
          onChange={(x) => setFilter(x.target.value)}
          className="bg-slate-800/60 border border-slate-700/50 rounded px-2 py-1.5 text-[10px] text-slate-300 focus:outline-none focus:border-cyan-500/50"
          aria-label="Durum filtresi"
        >
          <option value="">Tüm Durumlar</option>
          <option value="active">Aktif</option>
          <option value="resolved">Çözüldü</option>
          <option value="suppressed">Bastırıldı</option>
        </select>
        <button
          onClick={detect}
          disabled={detecting}
          className="ml-auto px-3 py-1.5 bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 text-[10px] font-medium rounded border border-cyan-500/20 transition-colors disabled:opacity-40 flex items-center gap-1"
          aria-label="Pattern algıla"
        >
          {detecting ? (
            <span className="inline-block w-3 h-3 border border-cyan-400 border-t-transparent rounded-full animate-spin" />
          ) : (
            "🔍"
          )}
          {detecting ? "Algılanıyor…" : "Pattern Algıla"}
        </button>
      </div>

      {ld ? (
        <Sk n={4} />
      ) : e ? (
        <Er m={e} r={load} />
      ) : patterns.length === 0 ? (
        <div className="text-center py-10">
          <div className="text-3xl mb-2">🔍</div>
          <p className="text-xs text-slate-500">Henüz pattern algılanmadı</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
          {patterns.map((p) => (
            <div
              key={p.id}
              className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2.5 hover:border-slate-600/40 transition-colors"
            >
              <div className="flex items-start gap-2 mb-1.5">
                <span className="text-xs font-medium text-slate-200 flex-1">
                  {p.name}
                </span>
                <span
                  className={`text-[9px] px-1.5 py-0.5 rounded border ${STATUS_STYLE[p.status] ?? STATUS_STYLE.active}`}
                >
                  {p.status === "active"
                    ? "Aktif"
                    : p.status === "resolved"
                      ? "Çözüldü"
                      : "Bastırıldı"}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mb-2 leading-relaxed">
                {p.description}
              </p>
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-[9px] text-slate-500">
                  Sıklık:{" "}
                  <span className="text-amber-400 tabular-nums">
                    {p.frequency}
                  </span>
                </span>
                <span className="text-[9px] text-slate-500">
                  Etkilenen:{" "}
                  {(p.affected_agents ?? []).map((a) => (
                    <span
                      key={a}
                      className="inline-block ml-1 px-1 py-0.5 bg-slate-700/60 text-slate-400 rounded text-[8px]"
                    >
                      {a}
                    </span>
                  ))}
                </span>
                {p.status === "active" && (
                  <div className="ml-auto flex gap-1.5">
                    <button
                      onClick={() => resolve(p.id)}
                      disabled={busy === p.id}
                      className="px-2 py-1 text-[9px] bg-emerald-600/15 hover:bg-emerald-600/25 text-emerald-400 rounded border border-emerald-500/20 transition-colors disabled:opacity-40"
                    >
                      ✓ Çöz
                    </button>
                    <button
                      onClick={() => suppress(p.id)}
                      disabled={busy === p.id}
                      className="px-2 py-1 text-[9px] bg-slate-600/15 hover:bg-slate-600/25 text-slate-400 rounded border border-slate-500/20 transition-colors disabled:opacity-40"
                    >
                      ✕ Bastır
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Tab 4: Öneriler ───────────────────────────────────────────── */
function RecommendationsTab() {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const data = await errorPatternApi.getRecommendations();
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

  if (ld) return <Sk n={4} />;
  if (e) return <Er m={e} r={load} />;

  if (recs.length === 0) {
    return (
      <div className="text-center py-10">
        <div className="text-3xl mb-2">💡</div>
        <p className="text-xs text-slate-500">Henüz öneri yok</p>
        <p className="text-[10px] text-slate-600 mt-1">
          Pattern algılandığında öneriler otomatik oluşturulur
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
      {recs.map((r, i) => (
        <div
          key={r.id ?? i}
          className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2.5 hover:border-slate-600/40 transition-colors"
        >
          <div className="flex items-start gap-2 mb-1.5">
            <span className="text-xs font-medium text-slate-200 flex-1">
              {r.title}
            </span>
            <span
              className={`text-[9px] px-1.5 py-0.5 rounded border ${PRIORITY_STYLE[r.priority] ?? PRIORITY_STYLE.medium}`}
            >
              {r.priority === "high"
                ? "Yüksek"
                : r.priority === "medium"
                  ? "Orta"
                  : "Düşük"}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mb-2 leading-relaxed">
            {r.description}
          </p>
          <div className="flex items-center gap-3 flex-wrap text-[9px]">
            {r.affected_agent && (
              <span className="text-slate-500">
                Agent:{" "}
                <span className="px-1 py-0.5 bg-slate-700/60 text-slate-400 rounded text-[8px]">
                  {r.affected_agent}
                </span>
              </span>
            )}
            {r.suggested_action && (
              <span className="text-slate-500 flex-1">
                Öneri:{" "}
                <span className="text-cyan-400">{r.suggested_action}</span>
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Main Component ────────────────────────────────────────────── */
export default function ErrorPatternsPanel() {
  const [tab, setTab] = useState<ErrTab>("overview");

  return (
    <div className="space-y-4">
      <nav
        className="flex gap-1 border-b border-slate-700/50"
        aria-label="Hata analizi sekmeleri"
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
        {tab === "timeline" && <TimelineTab />}
        {tab === "patterns" && <PatternsTab />}
        {tab === "recommendations" && <RecommendationsTab />}
      </div>
    </div>
  );
}
