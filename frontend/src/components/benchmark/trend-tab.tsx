"use client";
import { useState, useEffect, useCallback } from "react";
import { fetcher } from "@/lib/api";
import { type AnyData, crd, sCls, TREND_COLORS, allRoles, ai } from "./shared";
import { TimeFilterBar } from "./time-filter-bar";

function buildPath(points: { x: number; y: number }[]): string {
  if (points.length === 0) return "";
  return points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
}

export function TrendTab() {
  const [agent, setAgent] = useState<string>(allRoles[0]);
  const [days, setDays] = useState("30");
  const [history, setHistory] = useState<AnyData[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    if (!agent) return;
    setLoading(true);
    const params = new URLSearchParams({ agent_role: agent });
    if (days) params.set("days", days);
    fetcher<{ history: AnyData[] }>(`/api/benchmarks/history?${params}`)
      .then((r) => setHistory(r.history ?? []))
      .catch(() => setHistory([]))
      .finally(() => setLoading(false));
  }, [agent, days]);

  useEffect(() => {
    load();
  }, [load]);

  const byScenario: Record<string, { date: string; score: number }[]> = {};
  for (const h of history) {
    const sid = h.scenario_id ?? "unknown";
    if (!byScenario[sid]) byScenario[sid] = [];
    byScenario[sid].push({
      date: h.created_at ?? "",
      score: Number(h.score ?? 0),
    });
  }
  const scenarioIds = Object.keys(byScenario);
  const W = 560,
    H = 200,
    PAD = 30;
  const chartW = W - PAD * 2,
    chartH = H - PAD * 2;

  const dateMap: Record<string, number[]> = {};
  for (const h of history) {
    const d = (h.created_at ?? "").slice(0, 10);
    if (!dateMap[d]) dateMap[d] = [];
    dateMap[d].push(Number(h.score ?? 0));
  }
  const sortedDates = Object.keys(dateMap).sort();
  const avgByDate = sortedDates.map((d) => {
    const scores = dateMap[d];
    return { date: d, avg: scores.reduce((a, b) => a + b, 0) / scores.length };
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <select
          className={sCls}
          value={agent}
          onChange={(e) => setAgent(e.target.value)}
          aria-label="Agent seçimi"
        >
          {allRoles.map((r) => (
            <option key={r} value={r}>
              {ai(r).icon} {ai(r).name}
            </option>
          ))}
        </select>
        <TimeFilterBar value={days} onChange={setDays} />
      </div>
      {loading ? (
        <div className="text-center text-slate-500 py-8 text-xs animate-pulse">
          Yükleniyor…
        </div>
      ) : history.length === 0 ? (
        <div className="text-center text-slate-500 py-8 text-xs">
          Bu agent için trend verisi yok
        </div>
      ) : (
        <div className={crd}>
          <div className="text-[10px] text-slate-500 mb-2">
            {ai(agent).icon} {ai(agent).name} — Skor Trendi
          </div>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="w-full"
            aria-label="Skor trend grafiği"
          >
            {[1, 2, 3, 4, 5].map((v) => {
              const y = PAD + chartH - (v / 5) * chartH;
              return (
                <g key={v}>
                  <line
                    x1={PAD}
                    y1={y}
                    x2={W - PAD}
                    y2={y}
                    stroke="#334155"
                    strokeWidth={0.5}
                    strokeDasharray="4,4"
                  />
                  <text
                    x={PAD - 4}
                    y={y + 3}
                    textAnchor="end"
                    fill="#64748b"
                    fontSize={8}
                  >
                    {v}
                  </text>
                </g>
              );
            })}
            {avgByDate.length > 1 && (
              <path
                d={buildPath(
                  avgByDate.map((p, i) => ({
                    x: PAD + (i / (avgByDate.length - 1)) * chartW,
                    y: PAD + chartH - (p.avg / 5) * chartH,
                  })),
                )}
                fill="none"
                stroke="#06b6d4"
                strokeWidth={2.5}
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity={0.9}
              />
            )}
            {scenarioIds.map((sid, si) => {
              const pts = byScenario[sid];
              if (pts.length < 2) return null;
              const color = TREND_COLORS[(si + 1) % TREND_COLORS.length];
              return (
                <path
                  key={sid}
                  d={buildPath(
                    pts.map((p, i) => ({
                      x: PAD + (i / (pts.length - 1)) * chartW,
                      y: PAD + chartH - (p.score / 5) * chartH,
                    })),
                  )}
                  fill="none"
                  stroke={color}
                  strokeWidth={1}
                  strokeLinecap="round"
                  opacity={0.5}
                />
              );
            })}
            {avgByDate.map((p, i) => (
              <circle
                key={i}
                cx={PAD + (i / Math.max(avgByDate.length - 1, 1)) * chartW}
                cy={PAD + chartH - (p.avg / 5) * chartH}
                r={3}
                fill="#06b6d4"
              />
            ))}
            {sortedDates.length > 0 &&
              sortedDates
                .filter(
                  (_, i) =>
                    i === 0 ||
                    i === sortedDates.length - 1 ||
                    i === Math.floor(sortedDates.length / 2),
                )
                .map((d, i, arr) => (
                  <text
                    key={d}
                    x={
                      PAD +
                      (sortedDates.indexOf(d) /
                        Math.max(sortedDates.length - 1, 1)) *
                        chartW
                    }
                    y={H - 5}
                    textAnchor={
                      i === 0
                        ? "start"
                        : i === arr.length - 1
                          ? "end"
                          : "middle"
                    }
                    fill="#64748b"
                    fontSize={8}
                  >
                    {d.slice(5)}
                  </text>
                ))}
          </svg>
          <div className="flex flex-wrap gap-3 mt-2">
            <span className="flex items-center gap-1 text-[10px]">
              <span className="w-3 h-0.5 bg-cyan-500 inline-block rounded" />{" "}
              Ortalama
            </span>
            {scenarioIds.slice(0, 5).map((sid, si) => (
              <span
                key={sid}
                className="flex items-center gap-1 text-[10px] text-slate-400"
              >
                <span
                  className="w-3 h-0.5 inline-block rounded"
                  style={{
                    backgroundColor:
                      TREND_COLORS[(si + 1) % TREND_COLORS.length],
                    opacity: 0.5,
                  }}
                />
                {sid.replace(/-/g, " ").slice(0, 20)}
              </span>
            ))}
          </div>
          {avgByDate.length >= 2 &&
            (() => {
              const first = avgByDate[0].avg;
              const last = avgByDate[avgByDate.length - 1].avg;
              const diff = last - first;
              const pct = first > 0 ? ((diff / first) * 100).toFixed(1) : "0";
              return (
                <div className="mt-3 flex items-center gap-2 text-[10px]">
                  <span className="text-slate-500">Değişim:</span>
                  <span
                    className={diff >= 0 ? "text-emerald-400" : "text-red-400"}
                  >
                    {diff >= 0 ? "↑" : "↓"} {Math.abs(diff).toFixed(2)} (
                    {diff >= 0 ? "+" : ""}
                    {pct}%)
                  </span>
                  <span className="text-slate-600">|</span>
                  <span className="text-slate-500">
                    İlk: {first.toFixed(2)}
                  </span>
                  <span className="text-slate-500">Son: {last.toFixed(2)}</span>
                </div>
              );
            })()}
        </div>
      )}
    </div>
  );
}
