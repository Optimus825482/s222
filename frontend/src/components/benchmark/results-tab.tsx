"use client";
import { useState, useEffect, useCallback } from "react";
import { fetcher } from "@/lib/api";
import { type AnyData, crd, sCls, allRoles, ai, scoreText } from "./shared";
import { TimeFilterBar } from "./time-filter-bar";

export function ResultsTab() {
  const [results, setResults] = useState<AnyData[]>([]);
  const [agent, setAgent] = useState("");
  const [days, setDays] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (agent) params.set("agent_role", agent);
    if (days) params.set("days", days);
    params.set("limit", "50");
    fetcher<{ results: AnyData[] }>(`/api/benchmarks/results?${params}`)
      .then((r) => setResults(r.results ?? []))
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [agent, days]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
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
        <TimeFilterBar value={days} onChange={setDays} />
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
                  {(score ?? 0).toFixed(1)}
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
              {/* Dimension mini-bars */}
              {r.dimensions && typeof r.dimensions === "object" && (
                <div className="grid grid-cols-5 gap-1 px-1 pb-1.5 -mt-0.5">
                  {Object.entries(r.dimensions as Record<string, number>).map(
                    ([dim, val]) => {
                      const v = Number(val ?? 0);
                      const dimLabels: Record<string, string> = {
                        substance: "İçerik",
                        structure: "Yapı",
                        trait_match: "Eşleşme",
                        reliability: "Güvenilirlik",
                        speed: "Hız",
                      };
                      return (
                        <div key={dim} className="flex items-center gap-0.5">
                          <span className="text-[7px] text-slate-600 w-8 truncate">
                            {dimLabels[dim] ?? dim}
                          </span>
                          <div className="flex-1 h-0.5 bg-slate-700/50 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${v >= 4 ? "bg-emerald-500/70" : v >= 3 ? "bg-cyan-500/70" : "bg-amber-500/70"}`}
                              style={{ width: `${(v / 5) * 100}%` }}
                            />
                          </div>
                        </div>
                      );
                    },
                  )}
                </div>
              )}
            );
          })}
        </div>
      )}
    </div>
  );
}
