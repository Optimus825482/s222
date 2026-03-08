"use client";

import { useState, useEffect, useRef } from "react";
import {
  Brain,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Minimize2,
  X,
} from "lucide-react";

interface Props {
  thinking: string;
  agent: string;
  isStreaming: boolean;
}

export function ThinkingPanel({ thinking, agent, isStreaming }: Props) {
  const [expanded, setExpanded] = useState(true);
  const [fullScreen, setFullScreen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  // Auto-expand when new thinking content arrives
  useEffect(() => {
    if (thinking) setExpanded(true);
  }, [thinking]);

  // Auto-scroll to bottom when streaming
  useEffect(() => {
    if (contentRef.current && isStreaming) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [thinking, isStreaming]);

  // Fullscreen overlay
  if (fullScreen) {
    return (
      <div className="fixed inset-0 z-[200] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/50 shrink-0">
            <div className="flex items-center gap-2">
              <Brain
                className={`w-4 h-4 text-amber-400 ${isStreaming ? "animate-pulse" : ""}`}
                aria-hidden
              />
              <span className="text-sm font-semibold text-slate-200">
                {agent} — thinking
              </span>
              {isStreaming && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  LIVE
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setFullScreen(false)}
                className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-slate-200 transition-colors"
                aria-label="Küçült"
              >
                <Minimize2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setFullScreen(false)}
                className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-slate-200 transition-colors"
                aria-label="Kapat"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div
            ref={contentRef}
            className="flex-1 min-h-0 overflow-y-auto px-4 py-3"
          >
            <pre className="text-sm text-slate-300/90 font-mono whitespace-pre-wrap break-words leading-relaxed">
              {thinking}
              {isStreaming && (
                <span className="animate-pulse text-amber-400">▊</span>
              )}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="shrink-0 border-t border-slate-700/50 bg-slate-900/80">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-400 hover:text-slate-300 transition-colors cursor-pointer"
        aria-expanded={expanded}
      >
        <Brain
          className={`w-3.5 h-3.5 text-amber-400 ${isStreaming ? "animate-pulse" : ""}`}
          aria-hidden
        />
        <span className="font-medium">{agent} düşünüyor...</span>
        {isStreaming && (
          <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
        )}
        <span className="ml-auto flex items-center gap-1" aria-hidden>
          <span
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.stopPropagation();
              setFullScreen(true);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.stopPropagation();
                setFullScreen(true);
              }
            }}
            className="p-0.5 rounded hover:bg-white/10 transition-colors"
            aria-label="Tam ekran"
          >
            <Maximize2 className="w-3 h-3" />
          </span>
          {expanded ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5" />
          )}
        </span>
      </button>
      {expanded && (
        <div ref={contentRef} className="px-3 pb-2 max-h-64 overflow-y-auto">
          <pre className="text-xs text-slate-400/80 font-mono whitespace-pre-wrap break-words leading-relaxed">
            {thinking}
            {isStreaming && (
              <span className="animate-pulse text-amber-400">▊</span>
            )}
          </pre>
        </div>
      )}
    </div>
  );
}
