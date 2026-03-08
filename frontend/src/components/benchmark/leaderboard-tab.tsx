"use client";
import { useState, useEffect } from "react";
import { fetcher } from "@/lib/api";
import { type AnyData, crd, ai, scoreColor, scoreText } from "./shared";
import { TimeFilterBar } from "./time-filter-bar";

export function LeaderboardTab() {
  const [data, setData] = useState<AnyData[]>([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState("");

  useEffect(() => {
    setLoading(true);
    const q = days ? `?days=${days}` : "";
    fetcher<{ leaderboard: AnyData[] }>(`/api/benchmarks/leaderboard${q}`)
      .then((r) => setData(r.leaderboard ?? []))
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [days]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-slate-500">Dönem:</span>
        <TimeFilterBar value={days} onChange={setDays} />
      </div>
      {loading ? (
        <div className="text-center text-slate-500 py-8 text-xs animate-pulse">
          Yükleniyor…
        </div>
      ) : !data.length ? (
        <div className="text-center text-slate-500 py-8 text-xs">
          Henüz veri yok
        </div>
      ) : (
        <div className={crd} role="table" aria-label="Agent sıralama tablosu">
          <div
            className="grid grid-cols-[40px_1fr_140px_70px_70px_90px] gap-2 text-[10px] text-slate-500 uppercase tracking-wider pb-2 border-b border-slate-700/50"
            role="row"
          >
            <span role="columnheader">#</span>
            <span role="columnheader">Agent</span>
            <span role="columnheader">Ort. Skor</span>
            <span role="columnheader">En İyi</span>
            <span role="columnheader">Test</span>
            <span role="columnheader">Gecikme</span>
          </div>
          {data.map((e: AnyData, i: number) => {
            const a = ai(e.agent_role ?? e.role ?? "");
            const score = Number(e.avg_score ?? e.score ?? 0);
            const best = Number(e.best_score ?? 0);
            return (
              <div
                key={i}
                className="grid grid-cols-[40px_1fr_140px_70px_70px_90px] gap-2 items-center py-2 text-xs border-b border-slate-700/30 last:border-0"
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
                <span
                  className={`font-mono text-[10px] ${scoreText(best)}`}
                  role="cell"
                >
                  {best.toFixed(2)}
                </span>
                <span
                  className="text-slate-400 font-mono text-[10px]"
                  role="cell"
                >
                  {e.total_runs ?? e.tests_run ?? 0}
                </span>
                <span
                  className="text-slate-400 font-mono text-[10px]"
                  role="cell"
                >
                  {(e.avg_latency_ms ?? 0).toFixed(0)}ms
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
