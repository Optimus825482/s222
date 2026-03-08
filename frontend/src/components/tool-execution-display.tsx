"use client";

import { Wrench, Check, Loader2 } from "lucide-react";

interface ToolCall {
  id: string;
  name: string;
  args: string;
  status: "running" | "complete";
}

interface Props {
  toolCalls: ToolCall[];
  agent: string;
}

export function ToolExecutionDisplay({ toolCalls, agent }: Props) {
  if (toolCalls.length === 0) return null;

  return (
    <div className="shrink-0 border-t border-slate-700/50 bg-slate-900/60 px-3 py-2 max-h-36 overflow-y-auto">
      <div className="text-[10px] text-slate-500 mb-1.5 font-medium">
        {agent} — araç çağrıları
      </div>
      <div className="space-y-1">
        {toolCalls.map((tc) => (
          <div
            key={tc.id || tc.name}
            className="flex items-start gap-2 text-xs"
          >
            {tc.status === "running" ? (
              <Loader2
                className="w-3.5 h-3.5 text-amber-400 animate-spin shrink-0 mt-0.5"
                aria-hidden
              />
            ) : (
              <Check
                className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5"
                aria-hidden
              />
            )}
            <div className="min-w-0 flex-1">
              <span className="text-slate-300 font-medium">{tc.name}</span>
              {tc.args && (
                <pre className="text-[10px] text-slate-500 font-mono truncate mt-0.5">
                  {tc.args.slice(0, 200)}
                </pre>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
