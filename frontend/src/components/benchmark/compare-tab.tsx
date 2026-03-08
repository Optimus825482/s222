"use client";
import { useState } from "react";
import { fetcher } from "@/lib/api";
import { type AnyData, crd, sCls, allRoles, ai, scoreText } from "./shared";

export function CompareTab() {
  const [roleA, setRoleA] = useState<string>(allRoles[0]);
  const [roleB, setRoleB] = useState<string>(allRoles[1] ?? allRoles[0]);
  const [data, setData] = useState<AnyData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const compare = async () => {
    if (roleA === roleB) {
      setError("Aynı agent seçilemez.");
      setData(null);
      return;
    }
    setError("");
    setLoading(true);
    try {
      const r = await fetcher<{ comparison: AnyData }>(
        `/api/benchmarks/compare?role_a=${roleA}&role_b=${roleB}`,
      );
      // Normalize API response to { a_avg, b_avg, categories: {cat: {a, b}}, winner }
      const raw = r.comparison;
      const aStats = raw[roleA] ?? {};
      const bStats = raw[roleB] ?? {};
      const catRaw = raw.category_comparison ?? {};
      const categories: Record<string, { a: number; b: number }> = {};
      for (const [cat, vals] of Object.entries(catRaw) as [string, AnyData][]) {
        categories[cat] = {
          a: Number(vals?.[roleA] ?? 0),
          b: Number(vals?.[roleB] ?? 0),
        };
      }
      setData({
        a_avg: Number(aStats.avg_score ?? 0),
        b_avg: Number(bStats.avg_score ?? 0),
        a_runs: aStats.total_runs ?? 0,
        b_runs: bStats.total_runs ?? 0,
        a_latency: aStats.avg_latency_ms ?? 0,
        b_latency: bStats.avg_latency_ms ?? 0,
        categories,
        winner: raw.overall_winner ?? null,
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Karşılaştırma başarısız");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const aA = ai(roleA);
  const aB = ai(roleB);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-slate-400 block mb-1">Agent A</label>
          <select
            className={sCls + " w-full"}
            value={roleA}
            onChange={(e) => setRoleA(e.target.value)}
          >
            {allRoles.map((r) => (
              <option key={r} value={r}>
                {ai(r).icon} {ai(r).name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-400 block mb-1">Agent B</label>
          <select
            className={sCls + " w-full"}
            value={roleB}
            onChange={(e) => setRoleB(e.target.value)}
          >
            {allRoles.map((r) => (
              <option key={r} value={r}>
                {ai(r).icon} {ai(r).name}
              </option>
            ))}
          </select>
        </div>
      </div>
      {roleA === roleB && (
        <p className="text-xs text-amber-400">⚠ Aynı agent seçili.</p>
      )}
      <button
        onClick={compare}
        disabled={loading || roleA === roleB}
        className="w-full py-2 rounded text-sm font-medium transition-colors bg-purple-600 hover:bg-purple-500 text-white disabled:opacity-50"
      >
        {loading ? "Karşılaştırılıyor…" : "⚔ Karşılaştır"}
      </button>
      {error && <p className="text-xs text-red-400">{error}</p>}
      {data && (
        <div className="space-y-2">
          <div className={crd + " flex items-center justify-between"}>
            <div className="text-center flex-1">
              <span className="text-lg">{aA.icon}</span>
              <p className="text-xs text-slate-300">{aA.name}</p>
              <p className={`text-lg font-bold ${scoreText(data.a_avg ?? 0)}`}>
                {(data.a_avg ?? 0).toFixed(2)}
              </p>
              {data.a_runs != null && (
                <p className="text-[10px] text-slate-500">
                  {data.a_runs} test · {Math.round(data.a_latency ?? 0)}ms
                </p>
              )}
            </div>
            <span className="text-slate-600 text-xl">vs</span>
            <div className="text-center flex-1">
              <span className="text-lg">{aB.icon}</span>
              <p className="text-xs text-slate-300">{aB.name}</p>
              <p className={`text-lg font-bold ${scoreText(data.b_avg ?? 0)}`}>
                {(data.b_avg ?? 0).toFixed(2)}
              </p>
              {data.b_runs != null && (
                <p className="text-[10px] text-slate-500">
                  {data.b_runs} test · {Math.round(data.b_latency ?? 0)}ms
                </p>
              )}
            </div>
          </div>
          {data.categories &&
            Object.entries(data.categories).map(
              ([cat, vals]: [string, AnyData]) => {
                const sA = Number(vals?.a ?? 0);
                const sB = Number(vals?.b ?? 0);
                return (
                  <div key={cat} className="space-y-1">
                    <p className="text-xs text-slate-400 capitalize">{cat}</p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-4 bg-slate-800 rounded overflow-hidden relative">
                        <div
                          className="h-full rounded"
                          style={{
                            width: `${(sA / 5) * 100}%`,
                            backgroundColor: aA.color,
                            opacity: 0.8,
                          }}
                        />
                        <span className="absolute right-1 top-0 text-[10px] text-slate-300 leading-4">
                          {sA.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex-1 h-4 bg-slate-800 rounded overflow-hidden relative">
                        <div
                          className="h-full rounded"
                          style={{
                            width: `${(sB / 5) * 100}%`,
                            backgroundColor: aB.color,
                            opacity: 0.8,
                          }}
                        />
                        <span className="absolute right-1 top-0 text-[10px] text-slate-300 leading-4">
                          {sB.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              },
            )}
          {data.winner && (
            <div className="text-center py-2">
              <span className="text-xs text-slate-400">Kazanan: </span>
              <span className="text-sm text-emerald-400 font-medium">
                {ai(data.winner).icon} {ai(data.winner).name}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
