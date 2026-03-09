"use client";
import { type AnyData, ai, scoreColor, scoreText } from "./shared";

export function SingleResultView({ data }: { data: AnyData }) {
  const score = Number(data.score ?? 0);
  const dims = data.dimensions ?? {};

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <span className="text-sm">{ai(data.agent_role ?? "").icon}</span>
        <span className="text-xs text-slate-200">
          {data.scenario_name ?? data.scenario_id}
        </span>
        <span className={`font-mono text-sm ${scoreText(score)}`}>
          {(score ?? 0).toFixed(2)}/5
        </span>
      </div>
      {Object.keys(dims).length > 0 && (
        <div className="space-y-1.5">
          {Object.entries(dims).map(([k, v]) => {
            const val = Number(v);
            return (
              <div key={k} className="flex items-center gap-2">
                <span className="text-[10px] text-slate-400 w-20 capitalize">
                  {k.replace(/_/g, " ")}
                </span>
                <div className="flex-1 h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${scoreColor(val)}`}
                    style={{ width: `${(val / 5) * 100}%` }}
                  />
                </div>
                <span
                  className={`font-mono text-[10px] w-6 text-right ${scoreText(val)}`}
                >
                  {(val ?? 0).toFixed(1)}
                </span>
              </div>
            );
          })}
        </div>
      )}
      <div className="flex gap-4 text-[10px] text-slate-500">
        <span>Gecikme: {(data.latency_ms ?? 0).toFixed(0)}ms</span>
        {data.tokens_used > 0 && <span>Token: {data.tokens_used}</span>}
      </div>
      {data.output_preview && (
        <details className="text-[10px]">
          <summary className="text-slate-500 cursor-pointer hover:text-slate-300">
            Çıktı önizleme
          </summary>
          <pre className="mt-1 text-slate-400 whitespace-pre-wrap max-h-32 overflow-auto bg-slate-900/50 rounded p-2">
            {data.output_preview}
          </pre>
        </details>
      )}
    </div>
  );
}
