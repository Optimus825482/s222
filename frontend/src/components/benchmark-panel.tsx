"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { AGENT_CONFIG } from "@/lib/agents";
import type { AgentRole } from "@/lib/types";

/* ── Constants ─────────────────────────────────────────────────── */
const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
const allRoles = Object.keys(AGENT_CONFIG) as AgentRole[];
const crd = "bg-slate-800/50 border border-slate-700/50 rounded-lg p-4";
const sCls =
  "bg-slate-800/60 border border-slate-700/50 rounded px-2 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/50";
const CATEGORIES = [
  "speed",
  "quality",
  "reasoning",
  "tool_use",
  "creativity",
] as const;

type BenchTab = "leaderboard" | "run" | "results" | "compare";
const BENCH_TABS: { key: BenchTab; label: string; icon: string }[] = [
  { key: "leaderboard", label: "Sıralama", icon: "🏆" },
  { key: "run", label: "Test Çalıştır", icon: "▶️" },
  { key: "results", label: "Sonuçlar", icon: "📊" },
  { key: "compare", label: "Karşılaştır", icon: "⚔️" },
];

/* ── API helpers ───────────────────────────────────────────────── */
async function bApi<T>(path: string): Promise<T> {
  const raw = localStorage.getItem("ops-center-auth");
  const parsed = raw ? JSON.parse(raw) : null;
  const token = parsed?.state?.user?.token;
  const res = await fetch(`${BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function bPost<T>(
  path: string,
  body: Record<string, unknown>,
): Promise<T> {
  const raw = localStorage.getItem("ops-center-auth");
  const parsed = raw ? JSON.parse(raw) : null;
  const token = parsed?.state?.user?.token;
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

/* ── Helpers ───────────────────────────────────────────────────── */
function ai(r: string) {
  return (
    AGENT_CONFIG[r as AgentRole] ?? { icon: "⚙️", color: "#6b7280", name: r }
  );
}

function scoreColor(s: number) {
  if (s >= 4) return "bg-emerald-500";
  if (s >= 3) return "bg-cyan-500";
  if (s >= 2) return "bg-amber-500";
  return "bg-red-500";
}

function scoreText(s: number) {
  if (s >= 4) return "text-emerald-400";
  if (s >= 3) return "text-cyan-400";
  if (s >= 2) return "text-amber-400";
  return "text-red-400";
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyData = any;

/* ── Leaderboard Tab ───────────────────────────────────────────── */
function LeaderboardTab() {
  const [data, setData] = useState<AnyData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    bApi<{ leaderboard: AnyData[] }>("/api/benchmarks/leaderboard")
      .then((r) => setData(r.leaderboard ?? []))
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <div className="text-center text-slate-500 py-8 text-xs animate-pulse">
        Yükleniyor…
      </div>
    );
  if (!data.length)
    return (
      <div className="text-center text-slate-500 py-8 text-xs">
        Henüz veri yok
      </div>
    );

  return (
    <div className={crd} role="table" aria-label="Agent sıralama tablosu">
      <div
        className="grid grid-cols-[40px_1fr_140px_70px_90px] gap-2 text-[10px] text-slate-500 uppercase tracking-wider pb-2 border-b border-slate-700/50"
        role="row"
      >
        <span role="columnheader">#</span>
        <span role="columnheader">Agent</span>
        <span role="columnheader">Ort. Skor</span>
        <span role="columnheader">Test</span>
        <span role="columnheader">Gecikme</span>
      </div>
      {data.map((e: AnyData, i: number) => {
        const a = ai(e.agent_role ?? e.role ?? "");
        const score = Number(e.avg_score ?? e.score ?? 0);
        return (
          <div
            key={i}
            className="grid grid-cols-[40px_1fr_140px_70px_90px] gap-2 items-center py-2 text-xs border-b border-slate-700/30 last:border-0"
            role="row"
          >
            <span className="text-slate-400 font-mono" role="cell">
              {i + 1}
            </span>
            <span className="flex items-center gap-1.5" role="cell">
              <span>{a.icon}</span>
              <span className="text-slate-200 truncate">{a.name}</span>
            </span>
            <span className="flex items-center gap-2" role="cell">
              <div className="flex-1 h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${scoreColor(score)}`}
                  style={{ width: `${(score / 5) * 100}%` }}
                />
              </div>
              <span className={`font-mono text-[10px] ${scoreText(score)}`}>
                {score.toFixed(2)}
              </span>
            </span>
            <span className="text-slate-400 font-mono text-[10px]" role="cell">
              {e.tests_run ?? e.total_tests ?? 0}
            </span>
            <span className="text-slate-400 font-mono text-[10px]" role="cell">
              {(e.avg_latency_ms ?? e.avg_latency ?? 0).toFixed(0)}ms
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* ── Run Tab ───────────────────────────────────────────────────── */
function RunTab() {
  const [scenarios, setScenarios] = useState<AnyData[]>([]);
  const [agent, setAgent] = useState("");
  const [category, setCategory] = useState("");
  const [scenario, setScenario] = useState("");
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<AnyData | null>(null);
  const [error, setError] = useState("");
  const progressRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    bApi<{ scenarios: AnyData[] }>("/api/benchmarks/scenarios")
      .then((r) => setScenarios(r.scenarios ?? []))
      .catch(() => {});
  }, []);

  // Cleanup progress interval on unmount
  useEffect(() => {
    return () => {
      if (progressRef.current) clearInterval(progressRef.current);
    };
  }, []);

  const run = useCallback(async () => {
    setRunning(true);
    setResult(null);
    setError("");
    setProgress(0);

    // Simulate progress: fast 0-60% (~3s), slow 60-90% (~5s), never 100% until done
    progressRef.current = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) return prev;
        if (prev < 60) return prev + Math.random() * 6 + 4; // ~3s to reach 60%
        return prev + Math.random() * 1.5 + 0.5; // ~5s for 60→90%
      });
    }, 300);

    try {
      const body: Record<string, unknown> = {};
      if (agent) body.agent_role = agent;
      if (scenario) body.scenario_id = scenario;
      if (category) body.category = category;
      const r = await bPost<AnyData>("/api/benchmarks/run", body);
      setResult(r.summary ?? r.result ?? r);
      if (progressRef.current) clearInterval(progressRef.current);
      progressRef.current = null;
      setProgress(100);
      // Brief 100% display before hiding
      await new Promise((res) => setTimeout(res, 500));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Bilinmeyen hata");
      if (progressRef.current) clearInterval(progressRef.current);
      progressRef.current = null;
      setProgress(0);
    } finally {
      setRunning(false);
    }
  }, [agent, category, scenario]);

  return (
    <div
      className="space-y-4"
      onPointerDown={(e) => {
        if (running) e.stopPropagation();
      }}
    >
      <div className={`${crd} space-y-3`}>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label
              className="text-[10px] text-slate-500 block mb-1"
              htmlFor="bench-agent"
            >
              Agent
            </label>
            <select
              id="bench-agent"
              className={sCls + " w-full"}
              value={agent}
              onChange={(e) => setAgent(e.target.value)}
              disabled={running}
              aria-label="Agent seçimi"
            >
              <option value="">Tümü</option>
              {allRoles.map((r) => (
                <option key={r} value={r}>
                  {ai(r).icon} {ai(r).name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label
              className="text-[10px] text-slate-500 block mb-1"
              htmlFor="bench-cat"
            >
              Kategori
            </label>
            <select
              id="bench-cat"
              className={sCls + " w-full"}
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={running}
              aria-label="Kategori seçimi"
            >
              <option value="">Tümü</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label
              className="text-[10px] text-slate-500 block mb-1"
              htmlFor="bench-sc"
            >
              Senaryo
            </label>
            <select
              id="bench-sc"
              className={sCls + " w-full"}
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
              disabled={running}
              aria-label="Senaryo seçimi"
            >
              <option value="">Tümü (Suite)</option>
              {scenarios.map((s: AnyData) => (
                <option key={s.id} value={s.id}>
                  {s.name ?? s.id}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={run}
          disabled={running}
          className="px-4 py-1.5 rounded text-xs font-medium bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
          aria-label="Benchmark başlat"
        >
          {running ? (
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Çalışıyor…
            </span>
          ) : (
            "▶️ Başlat"
          )}
        </button>

        {/* XP-style Progress bar */}
        {(running || progress === 100) && (
          <div
            className="space-y-1.5"
            role="progressbar"
            aria-valuenow={Math.round(progress)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Benchmark ilerleme durumu"
          >
            <div className="flex justify-between text-[10px]">
              <span className="text-blue-400 font-medium">
                {progress === 100 ? "Tamamlandı!" : "Test çalışıyor…"}
              </span>
              <span className="text-slate-400 font-mono">
                %{Math.round(progress)}
              </span>
            </div>
            <div className="h-3 bg-gray-600 border border-gray-500 rounded-sm overflow-hidden shadow-inner">
              <div
                className="h-full rounded-sm transition-all duration-300 ease-out"
                style={{
                  width: `${Math.min(progress, 100)}%`,
                  background:
                    "linear-gradient(180deg, #3b82f6 0%, #1d4ed8 40%, #1e40af 100%)",
                  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.3)",
                }}
              />
            </div>
          </div>
        )}
      </div>

      {error && (
        <div
          className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-xs text-red-400"
          role="alert"
        >
          {error}
        </div>
      )}

      {result && (
        <div className={crd}>
          <div className="flex items-center gap-2 mb-2">
            <h4 className="text-xs text-slate-400">Sonuç</h4>
            <span className="text-[10px] text-emerald-400">✓ Tamamlandı</span>
          </div>
          <pre className="text-[10px] text-slate-300 overflow-auto max-h-60 whitespace-pre-wrap">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

/* ── Results Tab ───────────────────────────────────────────────── */
function ResultsTab() {
  const [results, setResults] = useState<AnyData[]>([]);
  const [agent, setAgent] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    const q = agent ? `?agent_role=${agent}&limit=50` : "?limit=50";
    bApi<{ results: AnyData[] }>(`/api/benchmarks/results${q}`)
      .then((r) => setResults(r.results ?? []))
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [agent]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <select
          className={sCls}
          value={agent}
          onChange={(e) => setAgent(e.target.value)}
          aria-label="Agent filtresi"
        >
          <option value="">Tüm Agent&apos;lar</option>
          {allRoles.map((r) => (
            <option key={r} value={r}>
              {ai(r).icon} {ai(r).name}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-center text-slate-500 py-6 text-xs animate-pulse">
          Yükleniyor…
        </div>
      ) : !results.length ? (
        <div className="text-center text-slate-500 py-6 text-xs">
          Sonuç bulunamadı
        </div>
      ) : (
        <div className={crd} role="table" aria-label="Benchmark sonuçları">
          <div
            className="grid grid-cols-[1fr_100px_60px_70px_100px] gap-2 text-[10px] text-slate-500 uppercase tracking-wider pb-2 border-b border-slate-700/50"
            role="row"
          >
            <span role="columnheader">Senaryo</span>
            <span role="columnheader">Agent</span>
            <span role="columnheader">Skor</span>
            <span role="columnheader">Gecikme</span>
            <span role="columnheader">Tarih</span>
          </div>
          {results.map((r: AnyData, i: number) => {
            const a = ai(r.agent_role ?? "");
            const score = Number(r.score ?? 0);
            return (
              <div
                key={i}
                className="grid grid-cols-[1fr_100px_60px_70px_100px] gap-2 items-center py-1.5 text-xs border-b border-slate-700/30 last:border-0"
                role="row"
              >
                <span className="text-slate-300 truncate" role="cell">
                  {r.scenario_name ?? r.scenario_id ?? "-"}
                </span>
                <span className="flex items-center gap-1" role="cell">
                  <span className="text-[10px]">{a.icon}</span>
                  <span className="text-slate-400 text-[10px] truncate">
                    {a.name}
                  </span>
                </span>
                <span
                  className={`font-mono text-[10px] ${scoreText(score)}`}
                  role="cell"
                >
                  {score.toFixed(1)}
                </span>
                <span
                  className="text-slate-400 font-mono text-[10px]"
                  role="cell"
                >
                  {(r.latency_ms ?? 0).toFixed(0)}ms
                </span>
                <span className="text-slate-500 text-[10px]" role="cell">
                  {r.created_at
                    ? new Date(r.created_at).toLocaleDateString("tr-TR")
                    : "-"}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ── Compare Tab ───────────────────────────────────────────────── */
function CompareTab() {
  const [roleA, setRoleA] = useState<string>(allRoles[0]);
  const [roleB, setRoleB] = useState<string>(allRoles[1] ?? allRoles[0]);
  const [data, setData] = useState<AnyData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const compare = useCallback(async () => {
    if (roleA === roleB) {
      setError("Farklı agent seçin");
      return;
    }
    setLoading(true);
    setError("");
    setData(null);
    try {
      const r = await bApi<{ comparison: AnyData }>(
        `/api/benchmarks/compare?role_a=${roleA}&role_b=${roleB}`,
      );
      setData(r.comparison ?? r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Hata oluştu");
    } finally {
      setLoading(false);
    }
  }, [roleA, roleB]);

  const dims: [string, number, number][] = data?.dimensions
    ? Object.entries(data.dimensions).map(([k, v]: [string, AnyData]) => [
        k,
        v?.a ?? v?.score_a ?? 0,
        v?.b ?? v?.score_b ?? 0,
      ])
    : data?.scores_a && data?.scores_b
      ? Object.keys(data.scores_a).map((k) => [
          k,
          data.scores_a[k],
          data.scores_b[k],
        ])
      : [];

  return (
    <div className="space-y-4">
      <div className={`${crd} flex items-end gap-3`}>
        <div className="flex-1">
          <label
            className="text-[10px] text-slate-500 block mb-1"
            htmlFor="cmp-a"
          >
            Agent A
          </label>
          <select
            id="cmp-a"
            className={sCls + " w-full"}
            value={roleA}
            onChange={(e) => setRoleA(e.target.value)}
            aria-label="Karşılaştırma Agent A"
          >
            {allRoles.map((r) => (
              <option key={r} value={r}>
                {ai(r).icon} {ai(r).name}
              </option>
            ))}
          </select>
        </div>
        <span className="text-slate-600 text-xs pb-1.5">vs</span>
        <div className="flex-1">
          <label
            className="text-[10px] text-slate-500 block mb-1"
            htmlFor="cmp-b"
          >
            Agent B
          </label>
          <select
            id="cmp-b"
            className={sCls + " w-full"}
            value={roleB}
            onChange={(e) => setRoleB(e.target.value)}
            aria-label="Karşılaştırma Agent B"
          >
            {allRoles.map((r) => (
              <option key={r} value={r}>
                {ai(r).icon} {ai(r).name}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={compare}
          disabled={loading}
          className="px-4 py-1.5 rounded text-xs font-medium bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white transition-colors whitespace-nowrap"
          aria-label="Karşılaştırmayı başlat"
        >
          {loading ? "…" : "⚔️ Karşılaştır"}
        </button>
      </div>

      {error && (
        <div
          className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-xs text-red-400"
          role="alert"
        >
          {error}
        </div>
      )}

      {dims.length > 0 && (
        <div className={crd}>
          <div className="flex justify-between text-[10px] text-slate-500 mb-3">
            <span className="flex items-center gap-1">
              {ai(roleA).icon} {ai(roleA).name}
            </span>
            <span className="flex items-center gap-1">
              {ai(roleB).icon} {ai(roleB).name}
            </span>
          </div>
          <div className="space-y-2.5">
            {dims.map(([dim, a, b]) => (
              <div key={dim}>
                <div className="text-[10px] text-slate-400 mb-1 capitalize">
                  {dim.replace(/_/g, " ")}
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 flex justify-end">
                    <div className="h-2 rounded-full bg-slate-700/50 w-full overflow-hidden flex justify-end">
                      <div
                        className="h-full rounded-full bg-cyan-500"
                        style={{ width: `${(Number(a) / 5) * 100}%` }}
                      />
                    </div>
                  </div>
                  <span
                    className={`font-mono text-[10px] w-8 text-center ${scoreText(Number(a))}`}
                  >
                    {Number(a).toFixed(1)}
                  </span>
                  <span className="text-slate-600 text-[10px]">|</span>
                  <span
                    className={`font-mono text-[10px] w-8 text-center ${scoreText(Number(b))}`}
                  >
                    {Number(b).toFixed(1)}
                  </span>
                  <div className="flex-1">
                    <div className="h-2 rounded-full bg-slate-700/50 w-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-emerald-500"
                        style={{ width: `${(Number(b) / 5) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Main Component ────────────────────────────────────────────── */
export function BenchmarkPanel() {
  const [tab, setTab] = useState<BenchTab>("leaderboard");

  return (
    <div className="space-y-4">
      {/* Tab bar */}
      <nav
        className="flex gap-1 border-b border-slate-700/50"
        aria-label="Benchmark sekmeleri"
      >
        {BENCH_TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-xs transition-colors border-b-2 ${
              tab === t.key
                ? "border-cyan-400 text-cyan-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
            aria-selected={tab === t.key}
            role="tab"
          >
            {t.icon} {t.label}
          </button>
        ))}
      </nav>

      {/* Tab content */}
      <div role="tabpanel">
        {tab === "leaderboard" && <LeaderboardTab />}
        {tab === "run" && <RunTab />}
        {tab === "results" && <ResultsTab />}
        {tab === "compare" && <CompareTab />}
      </div>
    </div>
  );
}
