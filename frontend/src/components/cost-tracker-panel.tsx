"use client";

import { useState, useEffect, useCallback } from "react";
import { costApi } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────────────── */
interface CostSummary {
  hours: number;
  totals: {
    total_input: number;
    total_output: number;
    total_tokens: number;
    total_input_cost: number;
    total_output_cost: number;
    total_cost: number;
    event_count: number;
  };
  by_agent: {
    agent_role: string;
    total_cost: number;
    event_count: number;
    input_tokens: number;
    output_tokens: number;
  }[];
  by_model: {
    model: string;
    total_cost: number;
    event_count: number;
    input_tokens: number;
    output_tokens: number;
  }[];
  by_task_type: {
    task_type: string;
    total_cost: number;
    event_count: number;
  }[];
}
interface TimelinePoint {
  period: string;
  input_tokens: number;
  output_tokens: number;
  total_cost: number;
  event_count: number;
}
interface Consumer {
  agent_role: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  total_cost: number;
  event_count: number;
}
interface ForecastData {
  forecast_days: number;
  history_days: number;
  avg_daily_cost: number;
  trend_slope: number;
  projected_total: number;
  daily_forecast: { date: string; projected_cost: number }[];
  confidence: string;
}
interface UsageStats {
  total_events: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cost: number;
  avg_input_tokens: number;
  avg_output_tokens: number;
  avg_cost_per_event: number;
  unique_agents: number;
  unique_models: number;
  unique_task_types: number;
  first_event: string | null;
  last_event: string | null;
}

/* ── Constants ─────────────────────────────────────────────────── */
type CostTab = "overview" | "timeline" | "agents" | "forecast";
const TABS: { key: CostTab; label: string; icon: string }[] = [
  { key: "overview", label: "Genel Bakış", icon: "💰" },
  { key: "timeline", label: "Zaman Çizelgesi", icon: "📈" },
  { key: "agents", label: "Agent Maliyetleri", icon: "🤖" },
  { key: "forecast", label: "Tahmin", icon: "🔮" },
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
      <span className="text-[10px] text-slate-500 w-16 text-right tabular-nums">
        ${(Number(v) || 0).toFixed(4)}
      </span>
    </div>
  );
}

function fmtCost(v: number | undefined | null): string {
  const n = Number(v) || 0;
  if (n >= 1) return `$${n.toFixed(2)}`;
  if (n >= 0.01) return `$${n.toFixed(3)}`;
  return `$${n.toFixed(4)}`;
}

function fmtTokens(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return String(v);
}

/* ── Tab 1: Genel Bakış ────────────────────────────────────────── */
function OverviewTab() {
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const [sumData, stData] = await Promise.all([
        costApi.getSummary(24),
        costApi.getUsageStats(),
      ]);
      setSummary(sumData);
      setStats(stData);
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
  if (!summary) return null;

  const t = summary.totals;
  const byAgent = summary.by_agent ?? [];
  const byModel = summary.by_model ?? [];
  const mxAgent = Math.max(...byAgent.map((a) => a.total_cost), 0.0001);
  const mxModel = Math.max(...byModel.map((m) => m.total_cost), 0.0001);

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap">
        <StatCard
          label="Toplam Maliyet (24s)"
          value={fmtCost(t.total_cost)}
          accent="text-emerald-400"
        />
        <StatCard
          label="Toplam Token"
          value={fmtTokens(t.total_tokens)}
          accent="text-cyan-400"
        />
        <StatCard
          label="İşlem Sayısı"
          value={t.event_count}
          accent="text-amber-400"
        />
        <StatCard label="Benzersiz Agent" value={stats?.unique_agents ?? 0} />
      </div>

      <div className="flex gap-3 flex-wrap">
        <StatCard
          label="Input Token"
          value={fmtTokens(t.total_input)}
          accent="text-blue-400"
        />
        <StatCard
          label="Output Token"
          value={fmtTokens(t.total_output)}
          accent="text-purple-400"
        />
        <StatCard label="Input Maliyet" value={fmtCost(t.total_input_cost)} />
        <StatCard label="Output Maliyet" value={fmtCost(t.total_output_cost)} />
      </div>

      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Agent Bazlı Maliyet
        </h4>
        <div className="space-y-2">
          {byAgent.length === 0 && (
            <p className="text-xs text-slate-600 text-center py-4">Veri yok</p>
          )}
          {byAgent.slice(0, 8).map((a, i) => (
            <Bar
              key={a.agent_role}
              v={a.total_cost}
              mx={mxAgent}
              c={CL[i % CL.length]}
              l={a.agent_role}
            />
          ))}
        </div>
      </div>

      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          Model Bazlı Maliyet
        </h4>
        <div className="space-y-2">
          {byModel.length === 0 && (
            <p className="text-xs text-slate-600 text-center py-4">Veri yok</p>
          )}
          {byModel.slice(0, 8).map((m, i) => (
            <Bar
              key={m.model}
              v={m.total_cost}
              mx={mxModel}
              c={CL[i % CL.length]}
              l={m.model}
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
      const data = await costApi.getTimeline(24, "hour");
      setPoints(data.timeline ?? []);
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

  const maxCost = Math.max(...points.map((p) => p.total_cost), 0.0001);

  return (
    <div className={crd}>
      <h4 className="text-xs font-medium text-slate-200 mb-3">
        Son 24 Saat — Saatlik Maliyet
      </h4>
      {points.length === 0 ? (
        <p className="text-xs text-slate-600 text-center py-8">
          Zaman çizelgesi verisi yok
        </p>
      ) : (
        <div
          className="flex items-end gap-[3px] h-40"
          role="img"
          aria-label="Saatlik maliyet grafiği"
        >
          {points.map((p, i) => {
            const pct = (p.total_cost / maxCost) * 100;
            const hour = p.period?.slice(-5) ?? `${i}`;
            return (
              <div
                key={i}
                className="flex-1 flex flex-col items-center gap-1 min-w-0"
              >
                <div className="w-full flex flex-col justify-end h-32 relative group">
                  <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-slate-700 text-[9px] text-slate-300 px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                    {fmtCost(p.total_cost)} ·{" "}
                    {fmtTokens(p.input_tokens + p.output_tokens)} token
                  </div>
                  <div
                    className="w-full rounded-t bg-emerald-500 transition-all duration-300"
                    style={{ height: `${Math.max(pct, 2)}%` }}
                  />
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
          <span className="w-2 h-2 rounded-sm bg-emerald-500" /> Maliyet
        </span>
      </div>
    </div>
  );
}

/* ── Tab 3: Agent Maliyetleri ──────────────────────────────────── */
function AgentsTab() {
  const [consumers, setConsumers] = useState<Consumer[]>([]);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const data = await costApi.getTopConsumers(24, 15);
      setConsumers(data.consumers ?? []);
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

  if (consumers.length === 0) {
    return (
      <div className="text-center py-10">
        <div className="text-3xl mb-2">🤖</div>
        <p className="text-xs text-slate-500">Henüz kullanım verisi yok</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
      {consumers.map((c, i) => (
        <div
          key={c.agent_role}
          className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-3 py-2.5 hover:border-slate-600/40 transition-colors"
        >
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs text-slate-500 tabular-nums w-5">
              #{i + 1}
            </span>
            <span className="text-xs font-medium text-slate-200 flex-1">
              {c.agent_role}
            </span>
            <span className="text-xs font-bold text-emerald-400 tabular-nums">
              {fmtCost(c.total_cost)}
            </span>
          </div>
          <div className="flex items-center gap-4 text-[9px] text-slate-500">
            <span>
              Input:{" "}
              <span className="text-blue-400 tabular-nums">
                {fmtTokens(c.input_tokens)}
              </span>
            </span>
            <span>
              Output:{" "}
              <span className="text-purple-400 tabular-nums">
                {fmtTokens(c.output_tokens)}
              </span>
            </span>
            <span>
              Toplam:{" "}
              <span className="text-cyan-400 tabular-nums">
                {fmtTokens(c.total_tokens)}
              </span>
            </span>
            <span className="ml-auto">
              İşlem:{" "}
              <span className="text-amber-400 tabular-nums">
                {c.event_count}
              </span>
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Tab 4: Tahmin ─────────────────────────────────────────────── */
function ForecastTab() {
  const [forecast, setForecast] = useState<ForecastData | null>(null);
  const [ld, setLd] = useState(true);
  const [e, setE] = useState("");

  const load = useCallback(async () => {
    try {
      setE("");
      setLd(true);
      const data = await costApi.getForecast(7);
      setForecast(data);
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
  if (!forecast) return null;

  const confStyle: Record<string, string> = {
    high: "text-emerald-400",
    medium: "text-amber-400",
    low: "text-red-400",
    none: "text-slate-500",
  };
  const confLabel: Record<string, string> = {
    high: "Yüksek",
    medium: "Orta",
    low: "Düşük",
    none: "Veri Yok",
  };

  const maxFc = Math.max(
    ...(forecast.daily_forecast?.map((d) => d.projected_cost) ?? []),
    0.0001,
  );

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap">
        <StatCard
          label="Günlük Ortalama"
          value={fmtCost(forecast.avg_daily_cost)}
          accent="text-emerald-400"
        />
        <StatCard
          label="7 Gün Tahmini"
          value={fmtCost(forecast.projected_total)}
          accent="text-cyan-400"
        />
        <StatCard
          label="Güven"
          value={confLabel[forecast.confidence] ?? forecast.confidence}
          accent={confStyle[forecast.confidence]}
        />
        <StatCard label="Veri Günü" value={forecast.history_days} />
      </div>

      <div className={crd}>
        <h4 className="text-xs font-medium text-slate-200 mb-3">
          7 Günlük Maliyet Tahmini
        </h4>
        {(forecast.daily_forecast ?? []).length === 0 ? (
          <p className="text-xs text-slate-600 text-center py-8">
            Tahmin için yeterli veri yok
          </p>
        ) : (
          <div className="space-y-2">
            {forecast.daily_forecast.map((d) => (
              <div key={d.date} className="flex items-center gap-2">
                <span className="text-[10px] text-slate-400 w-20 tabular-nums">
                  {d.date.slice(5)}
                </span>
                <div className="flex-1 bg-slate-700/50 rounded-full h-2 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-cyan-500 transition-all duration-500"
                    style={{
                      width: `${Math.min((d.projected_cost / maxFc) * 100, 100)}%`,
                    }}
                  />
                </div>
                <span className="text-[10px] text-slate-500 w-16 text-right tabular-nums">
                  {fmtCost(d.projected_cost)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {forecast.trend_slope !== 0 && (
        <div className={crd}>
          <h4 className="text-xs font-medium text-slate-200 mb-2">
            Trend Analizi
          </h4>
          <p className="text-[11px] text-slate-400">
            Günlük maliyet trendi:{" "}
            <span
              className={
                forecast.trend_slope > 0 ? "text-red-400" : "text-emerald-400"
              }
            >
              {forecast.trend_slope > 0 ? "↑" : "↓"}{" "}
              {fmtCost(Math.abs(forecast.trend_slope))}/gün
            </span>
          </p>
          <p className="text-[10px] text-slate-500 mt-1">
            {forecast.trend_slope > 0
              ? "Maliyetler artış eğiliminde — bütçe limiti ayarlamayı düşünün"
              : "Maliyetler düşüş eğiliminde — optimizasyonlar etkili"}
          </p>
        </div>
      )}
    </div>
  );
}

/* ── Main Component ────────────────────────────────────────────── */
export default function CostTrackerPanel() {
  const [tab, setTab] = useState<CostTab>("overview");

  return (
    <div className="space-y-4">
      <nav
        className="flex gap-1 border-b border-slate-700/50"
        aria-label="Maliyet takibi sekmeleri"
      >
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-xs transition-colors border-b-2 ${
              tab === t.key
                ? "border-emerald-400 text-emerald-400"
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
        {tab === "agents" && <AgentsTab />}
        {tab === "forecast" && <ForecastTab />}
      </div>
    </div>
  );
}
