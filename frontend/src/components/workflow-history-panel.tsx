"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import {
  History,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Loader2,
  Play,
} from "lucide-react";

interface WorkflowExecution {
  id: number;
  workflow_id: string;
  status: string;
  step_results: Record<string, unknown>;
  error: string | null;
  duration_ms: number;
  variables: Record<string, unknown>;
  created_at: string;
}

type SIcon = typeof CheckCircle2;
const ST: Record<string, { c: string; bg: string; i: SIcon }> = {
  completed: {
    c: "text-emerald-400",
    bg: "bg-emerald-500/15 border-emerald-500/30",
    i: CheckCircle2,
  },
  failed: {
    c: "text-red-400",
    bg: "bg-red-500/15 border-red-500/30",
    i: XCircle,
  },
  partial: {
    c: "text-amber-400",
    bg: "bg-amber-500/15 border-amber-500/30",
    i: AlertTriangle,
  },
  rolled_back: {
    c: "text-orange-400",
    bg: "bg-orange-500/15 border-orange-500/30",
    i: RefreshCw,
  },
};
const FALLBACK = {
  c: "text-slate-400",
  bg: "bg-slate-500/15 border-slate-500/30",
  i: Clock,
};
const dur = (ms: number) =>
  ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
const fdt = (iso: string) => {
  try {
    return new Date(iso).toLocaleString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
};

export function WorkflowHistoryPanel() {
  const [execs, setExecs] = useState<WorkflowExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const [replayId, setReplayId] = useState<number | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const d = await api.getHistory(30);
      setExecs(d);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Veri yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    timer.current = setInterval(load, 10_000);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [load]);

  const replay = useCallback(
    async (ex: WorkflowExecution) => {
      setReplayId(ex.id ?? null);
      try {
        const v = Object.fromEntries(
          Object.entries(ex.variables).map(([k, val]) => [k, String(val)]),
        );
        await api.runWorkflow(ex.workflow_id, v);
        await load();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Tekrar çalıştırılamadı");
      } finally {
        setReplayId(null);
      }
    },
    [load],
  );

  if (loading)
    return (
      <div className="flex items-center justify-center py-16 text-slate-500 gap-2 text-xs">
        <Loader2 className="w-4 h-4 animate-spin" /> Yükleniyor…
      </div>
    );
  if (error && !execs.length)
    return (
      <div
        className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-xs text-red-400 m-2"
        role="alert"
      >
        {error}
      </div>
    );
  if (!execs.length)
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3 text-slate-500">
        <History className="w-8 h-8 opacity-40" />
        <span className="text-xs">Henüz workflow çalıştırılmamış</span>
      </div>
    );

  return (
    <div className="space-y-1.5 p-2">
      <div className="flex items-center justify-between px-2 pb-2 border-b border-slate-700/50">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <History className="w-3.5 h-3.5" />
          <span>Çalışma Geçmişi</span>
          <span className="text-[10px] text-slate-600">({execs.length})</span>
        </div>
        <button
          onClick={load}
          className="p-1 rounded hover:bg-slate-700/50 text-slate-500 hover:text-slate-300 transition-colors"
          aria-label="Yenile"
        >
          <RefreshCw className="w-3 h-3" />
        </button>
      </div>
      {error && (
        <div className="text-[10px] text-red-400 px-2" role="alert">
          {error}
        </div>
      )}

      {execs.map((ex, idx) => {
        const s = ST[ex.status] ?? FALLBACK;
        const Icon = s.i;
        const open = openId === (ex.id ?? null);
        const steps = ex.step_results ? Object.entries(ex.step_results) : [];
        const panelId = `workflow-details-${ex.id ?? idx}`;
        const buttonId = `workflow-toggle-${ex.id ?? idx}`;
        return (
          <div
            key={ex.id ?? idx}
            className="bg-slate-800/40 border border-slate-700/40 rounded-lg overflow-hidden"
          >
            <button
              id={buttonId}
              onClick={() =>
                setOpenId((p) =>
                  p === (ex.id ?? null) ? null : (ex.id ?? null),
                )
              }
              className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-slate-700/30 transition-colors"
              {...(open
                ? { "aria-expanded": "true" }
                : { "aria-expanded": "false" })}
              aria-controls={panelId}
            >
              {open ? (
                <ChevronDown className="w-3 h-3 text-slate-500 shrink-0" />
              ) : (
                <ChevronRight className="w-3 h-3 text-slate-500 shrink-0" />
              )}
              <span className="text-xs text-slate-200 font-mono truncate flex-1">
                {ex.workflow_id}
              </span>
              <span
                className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] border ${s.bg} ${s.c}`}
              >
                <Icon className="w-2.5 h-2.5" />
                {ex.status}
              </span>
              <span className="text-[10px] text-slate-500 font-mono w-14 text-right shrink-0">
                {dur(ex.duration_ms)}
              </span>
              <span className="text-[10px] text-slate-600 w-28 text-right shrink-0 hidden sm:block">
                {fdt(ex.created_at ?? "")}
              </span>
            </button>

            {open && (
              <div
                id={panelId}
                role="region"
                aria-labelledby={buttonId}
                className="border-t border-slate-700/40 px-3 py-3 space-y-3"
              >
                {steps.length > 0 ? (
                  <div className="space-y-1.5">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                      Adımlar
                    </span>
                    {steps.map(([name, result], i) => (
                      <div key={name} className="flex items-start gap-2 pl-2">
                        <div className="flex flex-col items-center mt-1">
                          <div className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
                          {i < steps.length - 1 && (
                            <div className="w-px h-4 bg-slate-700" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <span className="text-[11px] text-slate-300 font-medium">
                            {name}
                          </span>
                          <pre className="text-[10px] text-slate-500 truncate max-w-full mt-0.5">
                            {typeof result === "string"
                              ? result
                              : JSON.stringify(result)?.slice(0, 120)}
                          </pre>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <span className="text-[10px] text-slate-600">
                    Adım sonucu yok
                  </span>
                )}
                {ex.error && (
                  <div className="bg-red-500/10 border border-red-500/20 rounded p-2 text-[10px] text-red-400">
                    {ex.error}
                  </div>
                )}
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[10px] text-slate-600 sm:hidden">
                    {fdt(ex.created_at ?? "")}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      replay(ex);
                    }}
                    disabled={replayId === ex.id}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded text-[11px] font-medium bg-cyan-600/80 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors ml-auto"
                    aria-label={`${ex.workflow_id} tekrar çalıştır`}
                  >
                    {replayId === ex.id ? (
                      <>
                        <Loader2 className="w-3 h-3 animate-spin" /> Çalışıyor…
                      </>
                    ) : (
                      <>
                        <Play className="w-3 h-3" /> Tekrar Çalıştır
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
