"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { fetcher, authHeaders } from "@/lib/api";
import { type AnyData, crd, sCls, CATEGORIES, allRoles, ai } from "./shared";
import { SuiteResultView } from "./suite-result";
import { SingleResultView } from "./single-result";

export function RunTab() {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const [scenarios, setScenarios] = useState<AnyData[]>([]);
  const [agent, setAgent] = useState("");
  const [category, setCategory] = useState("");
  const [scenario, setScenario] = useState("");
  const [running, setRunning] = useState(false);
  const [pct, setPct] = useState(0);
  const [total, setTotal] = useState(0);
  const [completed, setCompleted] = useState(0);
  const [curAgent, setCurAgent] = useState("");
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

  const run = useCallback(async () => {
    setRunning(true);
    setResult(null);
    setResultType(null);
    setError("");
    setPct(0);
    setTotal(0);
    setCompleted(0);
    setCurAgent("");
    setCurLabel("");

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const body: Record<string, unknown> = {};
      if (agent) body.agent_role = agent;
      if (scenario) body.scenario_id = scenario;
      if (category) body.category = category;

      const resp = await fetch(`${API_BASE}/api/benchmarks/run-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });

      if (!resp.ok || !resp.body) {
        throw new Error(`HTTP ${resp.status}`);
      }

      const reader = resp.body.getReader();
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
          const raw = line.slice(6).trim();
          if (!raw) continue;
          let ev: AnyData;
          try {
            ev = JSON.parse(raw);
          } catch {
            continue;
          }

          if (ev.event === "started") {
            setTotal(ev.total ?? 0);
          } else if (ev.event === "progress") {
            const c = ev.completed ?? 0;
            const t = ev.total ?? 1;
            setCompleted(c);
            setTotal(t);
            setCurAgent(ev.agent_role ?? "");
            setCurLabel(ev.scenario_name ?? ev.scenario_id ?? "");
            setPct(Math.round((c / t) * 100));
          } else if (ev.event === "done") {
            if (ev.type === "single") {
              setResultType("single");
              setResult(ev.result ?? ev);
            } else {
              setResultType("suite");
              setResult(ev.summary ?? ev);
            }
            setPct(100);
          } else if (ev.event === "error") {
            setError(ev.message ?? "Bilinmeyen hata");
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === "AbortError") {
        setError("İptal edildi");
      } else {
        setError(e instanceof Error ? e.message : "Bilinmeyen hata");
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }, [agent, category, scenario, API_BASE]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return (
    <div className="space-y-4">
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
              className="px-3 py-1.5 rounded text-xs font-medium bg-red-600 hover:bg-red-500 text-white transition-colors"
              aria-label="İptal et"
            >
              ⏹ İptal
            </button>
          )}
        </div>
        {running && total > 0 && (
          <div
            className="space-y-1.5"
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Benchmark ilerleme durumu"
          >
            <div className="flex justify-between text-[10px]">
              <span className="text-blue-400 font-medium">
                {curLabel
                  ? `${ai(curAgent).icon} ${curLabel}`
                  : "Hazırlanıyor…"}
              </span>
              <span className="text-slate-400 font-mono">
                {completed}/{total} — %{pct}
              </span>
            </div>
            <div className="h-3 bg-gray-600 border border-gray-500 rounded-sm overflow-hidden shadow-inner">
              <div
                className="h-full rounded-sm transition-all duration-300 ease-out"
                style={{
                  width: `${pct}%`,
                  background:
                    pct === 100
                      ? "linear-gradient(180deg, #22c55e 0%, #16a34a 40%, #15803d 100%)"
                      : "linear-gradient(180deg, #3b82f6 0%, #1d4ed8 40%, #1e40af 100%)",
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
