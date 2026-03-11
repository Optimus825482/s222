import pathlib

code = r'''"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { fetcher } from "@/lib/api";
import { type AnyData, crd, sCls, allRoles, CATEGORIES, ai } from "./shared";
import { SuiteResultView } from "./suite-result";
import { SingleResultView } from "./single-result";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function RunTab() {
  const [scenarios, setScenarios] = useState<AnyData[]>([]);
  const [agent, setAgent] = useState("");
  const [category, setCategory] = useState("");
  const [scenario, setScenario] = useState("");
  const [running, setRunning] = useState(false);
  const [pct, setPct] = useState(0);
  const [total, setTotal] = useState(0);
  const [completed, setCompleted] = useState(0);
  const [curLabel, setCurLabel] = useState("");
  const [result, setResult] = useState<AnyData | null>(null);
  const [resultType, setResultType] = useState<"single" | "suite" | null>(null);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetcher<{ scenarios: AnyData[] }>("/api/benchmarks/scenarios")
      .then((r) => setScenarios(r.scenarios ?? []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const run = useCallback(async () => {
    setRunning(true);
    setResult(null);
    setResultType(null);
    setError("");
    setPct(0);
    setTotal(0);
    setCompleted(0);
    setCurLabel("");
    const ac = new AbortController();
    abortRef.current = ac;

    try {
      const body: Record<string, unknown> = {};
      if (agent) body.agent_role = agent;
      if (scenario) body.scenario_id = scenario;
      if (category) body.category = category;

      const resp = await fetch(`${API_BASE}/api/benchmarks/run-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: ac.signal,
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      const reader = resp.body?.getReader();
      if (!reader) throw new Error("No readable stream");

      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const evt = JSON.parse(line.slice(6));
            if (evt.event === "started") {
              setTotal(evt.total);
            } else if (evt.event === "progress") {
              setCompleted(evt.completed);
              setTotal(evt.total);
              setCurLabel(`${ai(evt.agent_role).icon} ${evt.scenario_name}`);
              setPct(Math.round((evt.completed / evt.total) * 100));
            } else if (evt.event === "done") {
              setPct(100);
              setCurLabel("");
              if (evt.type === "single") {
                setResultType("single");
                setResult(evt.result);
              } else {
                setResultType("suite");
                setResult(evt.summary);
              }
            } else if (evt.event === "error") {
              throw new Error(evt.message);
            }
          } catch {
            /* skip malformed SSE */
          }
        }
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        setError(e instanceof Error ? e.message : "Bilinmeyen hata");
        setPct(0);
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }, [agent, category, scenario]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setRunning(false);
    setPct(0);
    setCurLabel("");
  }, []);

  const showBar = running || pct === 100;
  const barBg =
    pct === 100
      ? "linear-gradient(180deg,#10b981 0%,#059669 40%,#047857 100%)"
      : "linear-gradient(180deg,#3b82f6 0%,#1d4ed8 40%,#1e40af 100%)";

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
            <label className="text-[10px] text-slate-500 block mb-1" htmlFor="bc">
              Kategori
            </label>
            <select
              id="bc"
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
            <label className="text-[10px] text-slate-500 block mb-1" htmlFor="bs">
              Senaryo
            </label>
            <select
              id="bs"
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

        <div className="flex gap-2">
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
          {running && (
            <button
              onClick={cancel}
              className="px-3 py-1.5 rounded text-xs font-medium bg-red-600/80 hover:bg-red-500 text-white transition-colors"
              aria-label="İptal"
            >
              ✕ İptal
            </button>
          )}
        </div>

        {showBar && (
          <div
            className="space-y-1.5"
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Benchmark ilerleme"
          >
            <div className="flex justify-between text-[10px]">
              <span className="text-blue-400 font-medium">
                {pct === 100 ? "Tamamlandı!" : curLabel || "Başlatılıyor…"}
              </span>
              <span className="text-slate-400 font-mono">
                {total > 0 ? `${completed}/${total}` : ""} — %{pct}
              </span>
            </div>
            <div className="h-3 bg-gray-600 border border-gray-500 rounded-sm overflow-hidden shadow-inner">
              <div
                className="h-full rounded-sm transition-all duration-300 ease-out"
                style={{
                  width: `${Math.min(pct, 100)}%`,
                  background: barBg,
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
          <div className="flex items-center gap-2 mb-3">
            <h4 className="text-xs text-slate-400">
              {resultType === "suite" ? "Suite Sonuçları" : "Tekil Sonuç"}
            </h4>
            <span className="text-[10px] text-emerald-400">✓ Tamamlandı</span>
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
'''

p = pathlib.Path('frontend/src/components/benchmark/run-tab.tsx')
p.write_text(code.strip() + '\n', encoding='utf-8')
print(f'Written: {len(code.strip())} chars, {code.strip().count(chr(10))+1} lines')
