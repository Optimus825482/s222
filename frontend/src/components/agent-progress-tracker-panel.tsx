"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetcher } from "@/lib/api";
import { Activity, Clock, CheckCircle2, AlertCircle } from "lucide-react";

const WS_BASE =
  typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}:8001`
    : "ws://localhost:8001";

interface AgentProgress {
  agent_id: string;
  agent_role: string;
  current_task: string;
  status: "idle" | "thinking" | "executing" | "waiting" | "error" | "completed";
  progress_percentage: number;
  started_at: string;
  estimated_completion: string;
  sub_tasks: {
    id: string;
    description: string;
    status: "pending" | "in_progress" | "completed" | "failed";
  }[];
}

function backendToLive(p: Record<string, unknown>): AgentProgress {
  const step = (p.current_step as Record<string, unknown>) || {};
  const steps = ((p.steps as Record<string, unknown>[]) || []) as Array<{
    step_id?: string;
    description?: string;
    status?: string;
  }>;
  const mapStatus = (s: string) =>
    s === "completed" ? "completed" : s === "error" ? "failed" : s === "thinking" || s === "executing" ? "in_progress" : "pending";
  return {
    agent_id: (p.agent_id as string) ?? "",
    agent_role: (p.agent_name as string) ?? (p.agent_id as string) ?? "",
    current_task: (step.description as string) ?? (p.task_id as string) ?? "",
    status: (p.status as AgentProgress["status"]) ?? "idle",
    progress_percentage: (p.overall_progress as number) ?? 0,
    started_at: (p.started_at as string) ?? "",
    estimated_completion: (p.updated_at as string) ?? "",
    sub_tasks: steps.map((st, i) => ({
      id: st.step_id ?? String(i),
      description: st.description ?? "",
      status: mapStatus(st.status ?? "pending") as AgentProgress["sub_tasks"][0]["status"],
    })),
  };
}

export function AgentProgressTrackerPanel() {
  const [agents, setAgents] = useState<AgentProgress[]>([]);
  const [loading, setLoading] = useState(false);
  const agentsRef = useRef<AgentProgress[]>([]);

  const loadProgress = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetcher<AgentProgress[]>("/api/agent-progress/live");
      setAgents(data);
      agentsRef.current = data;
    } catch (err) {
      console.error("[AgentProgress] load error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProgress();
    const interval = setInterval(loadProgress, 5000);
    return () => clearInterval(interval);
  }, [loadProgress]);

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/progress`);
    ws.onmessage = (e) => {
      try {
        const p = JSON.parse(e.data) as Record<string, unknown>;
        const live = backendToLive(p);
        setAgents((prev) => {
          const next = prev.filter((a) => a.agent_id !== live.agent_id);
          next.push(live);
          agentsRef.current = next;
          return next;
        });
      } catch {
        /* ignore */
      }
    };
    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CLOSING) {
        ws.close();
      } else {
        ws.onmessage = null;
        ws.onerror = null;
        ws.onopen = null;
        ws.onclose = null;
      }
    };
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "idle":
        return "text-slate-400 bg-slate-400/10";
      case "thinking":
        return "text-yellow-400 bg-yellow-400/10";
      case "executing":
        return "text-cyan-400 bg-cyan-400/10";
      case "waiting":
        return "text-purple-400 bg-purple-400/10";
      case "completed":
        return "text-emerald-400 bg-emerald-400/10";
      case "error":
        return "text-red-400 bg-red-400/10";
      default:
        return "text-slate-400 bg-slate-400/10";
    }
  };

  const getSubTaskIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="w-3 h-3 text-emerald-400" />;
      case "in_progress":
        return <Activity className="w-3 h-3 text-cyan-400 animate-pulse" />;
      case "failed":
        return <AlertCircle className="w-3 h-3 text-red-400" />;
      default:
        return <Clock className="w-3 h-3 text-slate-500" />;
    }
  };

  return (
    <div className="bg-surface rounded-lg border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-surface-raised">
        <Activity className="w-5 h-5 text-cyan-400" />
        <h2 className="text-base font-semibold text-slate-200">
          Canlı Agent İlerlemesi
        </h2>
        {loading && (
          <div className="ml-auto">
            <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4 space-y-3">
        {agents.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            Şu anda aktif agent yok
          </div>
        ) : (
          agents.map((agent) => (
            <div
              key={agent.agent_id}
              className="p-4 rounded-lg bg-surface-raised border border-border"
            >
              {/* Agent Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-200">
                    {agent.agent_role}
                  </span>
                  <span
                    className={`text-xs px-2 py-1 rounded ${getStatusColor(agent.status)}`}
                  >
                    {agent.status}
                  </span>
                </div>
                <span className="text-xs text-slate-500">
                  {agent.progress_percentage}%
                </span>
              </div>

              {/* Progress Bar */}
              <div className="mb-3">
                <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-cyan-400 transition-all duration-300"
                    style={{ width: `${agent.progress_percentage}%` }}
                  />
                </div>
              </div>

              {/* Current Task */}
              <div className="mb-3">
                <div className="text-xs text-slate-500 mb-1">Mevcut Görev:</div>
                <div className="text-sm text-slate-300">
                  {agent.current_task}
                </div>
              </div>

              {/* Time Info */}
              <div className="flex items-center gap-4 mb-3 text-xs text-slate-500">
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>
                    Başlangıç:{" "}
                    {new Date(agent.started_at).toLocaleTimeString("tr-TR")}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>
                    Tahmini Bitiş:{" "}
                    {new Date(agent.estimated_completion).toLocaleTimeString(
                      "tr-TR",
                    )}
                  </span>
                </div>
              </div>

              {/* Sub Tasks */}
              {agent.sub_tasks.length > 0 && (
                <div>
                  <div className="text-xs text-slate-500 mb-2">
                    Alt Görevler ({agent.sub_tasks.length}):
                  </div>
                  <div className="space-y-1">
                    {agent.sub_tasks.map((st) => (
                      <div
                        key={st.id}
                        className="flex items-center gap-2 text-xs text-slate-400"
                      >
                        {getSubTaskIcon(st.status)}
                        <span>{st.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
