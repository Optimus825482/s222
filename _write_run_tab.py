import pathlib

content = '''"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { fetcher } from "@/lib/api";
import { type AnyData, crd, sCls, allRoles, CATEGORIES, ai } from "./shared";
import { SuiteResultView } from "./suite-result";
import { SingleResultView } from "./single-result";

interface ProgressInfo {
  run_id: string;
  status: "running" | "done" | "error";
  total: number;
  completed: number;
  current_agent: string | null;
  current_scenario: string | null;
  current_scenario_name: string | null;
  summary?: AnyData;
  error?: string;
}

export function RunTab() {
  const [scenarios, setScenarios] = useState<AnyData[]>([]);
  const [agent, setAgent] = useState("");
  const [category, setCategory] = useState("");
  const [scenario, setScenario] = useState("");
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<ProgressInfo | null>(null);
  const [result, setResult] = useState<AnyData | null>(null);
  const [resultType, setResultType] = useState<"single" | "suite" | null>(null);
  const [error, setError] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetcher<{ scenarios: AnyData[] }>("/api/benchmarks/scenarios")
      .then((r) => setScenarios(r.scenarios ?? []))
      .catch(() => {});
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const startPolling = useCallback(
    (runId: string) => {
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const p = await fetcher<ProgressInfo>(
            `/api/benchmarks/progress/${runId}`
          );
          setProgress(p);
          if (p.status === "done") {
            stopPolling();
            setResultType("suite");
            setResult(p.summary ?? null);
            setRunning(false);
          } else if (p.status === "error") {
            stopPolling();
            setError(p.error ?? "Suite hatasi");
            setRunning(false);
          }
        } catch {
          /* network blip */
        }
      }, 1500);
    },
    [stopPolling]
  );

  const run = useCallback(async () => {
    setRunning(true);
    setResult(null);
    setResultType(null);
    setError("");
    setProgress(null);
    try {
      const body: Record<string, unknown> = {};
      if (agent) body.agent_role = agent;
      if (scenario) body.scenario_id = scenario;
      if (category) body.category = category;
      const r = await fetcher<AnyData>("/api/benchmarks/run", {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (r.type === "single") {
        setResultType("single");
        setResult(r.result ?? r);
        setRunning(false);
      } else if (r.type === "suite_async" && r.run_id) {
        setProgress({
          run_id: r.run_id,
          status: "running",
          total: 0,
          completed: 0,
          current_agent: null,
          current_scenario: null,
          current_scenario_name: null,
        });
        startPolling(r.run_id);
      } else {
        setResultType("suite");
        setResult(r.summary ?? r);
        setRunning(false);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Bilinmeyen hata");
      setRunning(false);
    }
  }, [agent, category, scenario, startPolling]);

  const pct =
    progress && progress.total > 0
      ? Math.round((progress.completed / progress.total) * 100)
      : 0;

  return (
    <div className="space-y-4">
      <div className={`${crd} space-y-3`}>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-[10px] text-slate-500 block mb-1" htmlFor="ba">
              Agent
            </label>
            <select
              id="ba"
              className={sCls + " w-full"}
              value={agent}
              onChange={(e) => setAgent(e.target.value)}
              disabled={running}
              aria-label="Agent secimi"
            >
              <option value="">Hepsi</option>
              {allRoles.map((r) => (
                <option key={r} value={r}>
                  {ai(r).icon} {ai(r).name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-slate-500 block mb-1" htmlFor="bc">
              Kategori
            </label>
            <select
              id="bc"
              className={sCls + " w-full"}
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={running}
              aria-label="Kategori secimi"
            >
              <option value="">Hepsi</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-slate-500 block mb-1" htmlFor="bs">
              Senaryo
            </label>
            <select
              id="bs"
              className={sCls + " w-full"}
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
              disabled={running}
              aria-label="Senaryo secimi"
            >
              <option value="">Suite (Hepsi)</option>
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
          aria-label="Benchmark baslat"
        >
          {running ? (
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Calisiyor...
            </span>
          ) : (
            "\\u25b6\\ufe0f Baslat"
          )}
        </button>

        {running && progress && <ProgressBar pct={pct} progress={progress} />}

        {!running && result && (
          <div className="flex items-center gap-2 text-[10px] text-emerald-400">
            <span>\\u2713</span>
            <span>Tamamlandi</span>
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
          <div className="flex items-center gap-2 mb-3">
            <h4 className="text-xs text-slate-400">
              {resultType === "suite" ? "Suite Sonuclari" : "Tekil Sonuc"}
            </h4>
          </div>
          {resultType === "suite" ? (
            <SuiteResultView data={result} />
          ) : (
            <SingleResultView data={result} />
          )}
        </div>
      )}
    </div>
  );
}

function ProgressBar({
  pct,
  progress,
}: {
  pct: number;
  progress: ProgressInfo;
}) {
  return (
    <div className="space-y-2">
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Benchmark ilerleme"
      >
        <div className="flex justify-between text-[10px] mb-1">
          <span className="text-blue-400 font-medium">
            {progress.total > 0
              ? `${progress.completed}/${progress.total} tamamlandi`
              : "Baslatiliyor..."}
          </span>
          <span className="text-slate-400 font-mono">%{pct}</span>
        </div>
        <div className="h-3 bg-gray-600 border border-gray-500 rounded-sm overflow-hidden shadow-inner">
          <div
            className="h-full rounded-sm transition-all duration-500 ease-out"
            style={{
              width: `${Math.min(pct, 100)}%`,
              background:
                "linear-gradient(180deg, #3b82f6 0%, #1d4ed8 40%, #1e40af 100%)",
              boxShadow: "inset 0 1px 0 rgba(255,255,255,0.3)",
            }}
          />
        </div>
      </div>
      {progress.current_agent && (
        <div className="flex items-center gap-2 text-[10px] text-slate-400">
          <span>
            {ai(progress.current_agent).icon}{" "}
            {ai(progress.current_agent).name}
          </span>
          <span className="text-slate-600">{"\\u2192"}</span>
          <span className="text-slate-300">
            {progress.current_scenario_name ?? progress.current_scenario}
          </span>
        </div>
      )}
    </div>
  );
}
'''

p = pathlib.Path("frontend") / "src" / "components" / "benchmark" / "run-tab.tsx"
p.write_text(content, encoding="utf-8")
lines = content.splitlines()
print(f"OK: {len(lines)} lines, {len(content)} chars")
