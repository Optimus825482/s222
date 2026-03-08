"use client";
import { type AnyData, ai, scoreColor, scoreText } from "./shared";

export function SuiteResultView({ data }: { data: AnyData }) {
  const results: AnyData[] = data.results ?? [];
  const errors: AnyData[] = data.errors ?? [];
  const scored = results.filter((r: AnyData) => r.score != null);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-4 gap-2">
        <div className="bg-slate-700/30 rounded p-2 text-center">
          <div className="text-lg font-mono text-slate-200">
            {data.total_runs ?? 0}
          </div>
          <div className="text-[10px] text-slate-500">Toplam</div>
        </div>
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded p-2 text-center">
          <div className="text-lg font-mono text-emerald-400">
            {data.successful ?? 0}
          </div>
          <div className="text-[10px] text-emerald-500/70">Başarılı</div>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded p-2 text-center">
          <div className="text-lg font-mono text-red-400">
            {data.failed ?? 0}
          </div>
          <div className="text-[10px] text-red-500/70">Başarısız</div>
        </div>
        <div className="bg-cyan-500/10 border border-cyan-500/20 rounded p-2 text-center">
          <div
            className={`text-lg font-mono ${scoreText(data.avg_score ?? 0)}`}
          >
            {(data.avg_score ?? 0).toFixed(2)}
          </div>
          <div className="text-[10px] text-cyan-500/70">Ort. Skor</div>
        </div>
      </div>

      {scored.length > 0 && (
        <div className="space-y-1">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">
            Senaryo Detayları
          </div>
          {scored.map((r: AnyData, i: number) => {
            const score = Number(r.score ?? 0);
            const a = ai(r.agent_role ?? "");
            return (
              <div
                key={i}
                className="flex items-center gap-2 py-1 border-b border-slate-700/20 last:border-0"
              >
                <span className="text-[10px] w-5">{a.icon}</span>
                <span className="text-[10px] text-slate-300 flex-1 truncate">
                  {r.scenario_name ?? r.scenario_id}
                </span>
                <div className="w-20 h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${scoreColor(score)}`}
                    style={{ width: `${(score / 5) * 100}%` }}
                  />
                </div>
                <span
                  className={`font-mono text-[10px] w-8 text-right ${scoreText(score)}`}
                >
                  {score.toFixed(2)}
                </span>
                <span className="text-[10px] text-slate-500 w-14 text-right">
                  {(r.latency_ms ?? 0).toFixed(0)}ms
                </span>
              </div>
            );
          })}
        </div>
      )}

      {errors.length > 0 && (
        <div className="space-y-1">
          <div className="text-[10px] text-red-400 uppercase tracking-wider">
            Hatalar
          </div>
          {errors.map((e: AnyData, i: number) => (
            <div
              key={i}
              className="bg-red-500/10 border border-red-500/20 rounded p-2 text-[10px] text-red-300"
            >
              <span className="text-slate-400">
                {e.agent_role}/{e.scenario_id}:
              </span>{" "}
              {e.error}
            </div>
          ))}
        </div>
      )}

      {data.avg_latency_ms != null && (
        <div className="text-[10px] text-slate-500 text-right">
          Ort. gecikme: {data.avg_latency_ms.toFixed(0)}ms
        </div>
      )}
    </div>
  );
}
