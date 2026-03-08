"use client";

import { useState, useEffect } from "react";
import { useAgentSocket } from "@/lib/use-agent-socket";
import { useAuth } from "@/lib/auth";
import type { Thread, PipelineType } from "@/lib/types";
import { PipelineSelector } from "@/components/pipeline-selector";
import { ChatArea } from "@/components/chat-area";
import { ChatInput } from "@/components/chat-input";
import type { AttachedFile } from "@/components/chat-input";
import { LiveEventLog } from "@/components/live-event-log";
import { ThinkingPanel } from "@/components/thinking-panel";
import { ToolExecutionDisplay } from "@/components/tool-execution-display";
import { api } from "@/lib/api";
import { consumePendingThread, setActiveThread } from "@/lib/ws-store";
import { trackBehavior } from "@/lib/behavior-tracker";
import { useSessionPersistence } from "@/lib/use-session-persistence";
import { useToast } from "@/components/toast";

export default function ChatDesktopPanel() {
  const { user } = useAuth();
  const toast = useToast();
  const [thread, setThread] = useState<Thread | null>(null);
  const [pipeline, setPipeline] = useState<PipelineType>("auto");
  const [lastError, setLastError] = useState<string | null>(null);
  const [streamThinking, setStreamThinking] = useState("");
  const [streamText, setStreamText] = useState("");
  const [streamAgent, setStreamAgent] = useState("");
  const [streamToolCalls, setStreamToolCalls] = useState<
    Array<{
      id: string;
      name: string;
      args: string;
      status: "running" | "complete";
    }>
  >([]);

  const {
    saveSessionDebounced,
    loadSession,
    lastSessionId,
    isReady: persistReady,
  } = useSessionPersistence();

  const { status, liveEvents, sendMessage, sendOrchestratorChat, stop } =
    useAgentSocket({
      enabled: !!user,
      onResult: (_tid, _result, updatedThread) => {
        setThread(updatedThread);
        setLastError(null);
        setStreamThinking("");
        setStreamText("");
        setStreamToolCalls([]);
        setStreamAgent("");
        // IndexedDB session persistence
        if (updatedThread) saveSessionDebounced(updatedThread);
        const lastTask = updatedThread?.tasks?.[updatedThread.tasks.length - 1];
        if (lastTask?.status === "completed") {
          trackBehavior(
            "task_complete",
            lastTask.user_input?.slice(0, 200) || "",
            {
              pipeline: lastTask.pipeline_type,
              tokens: lastTask.total_tokens,
              latency_ms: lastTask.total_latency_ms,
            },
          );
          // Task completion notification
          const latSec = lastTask.total_latency_ms
            ? (lastTask.total_latency_ms / 1000).toFixed(1)
            : null;
          toast({
            type: "success",
            title: "✅ Görev Tamamlandı",
            message: latSec
              ? `${lastTask.pipeline_type ?? "auto"} pipeline — ${latSec}s`
              : `${lastTask.pipeline_type ?? "auto"} pipeline tamamlandı`,
            duration: 5000,
          });
          // Browser notification (if tab not focused)
          if (document.hidden && Notification.permission === "granted") {
            new Notification("Görev Tamamlandı ✅", {
              body: latSec
                ? `${lastTask.pipeline_type ?? "auto"} — ${latSec}s`
                : "Yanıt hazır",
              icon: "/icon-192x192.png",
            });
          }
          // Completion sound
          try {
            const ctx = new AudioContext();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = 880;
            osc.type = "sine";
            gain.gain.value = 0.08;
            osc.start();
            gain.gain.exponentialRampToValueAtTime(
              0.001,
              ctx.currentTime + 0.3,
            );
            osc.stop(ctx.currentTime + 0.3);
          } catch {
            /* audio not available */
          }
        }
        if (lastTask?.status === "failed") {
          toast({
            type: "error",
            title: "Görev Başarısız",
            message: "Detaylar sohbet geçmişinde.",
            duration: 6000,
          });
        }
      },
      onError: (msg) => setLastError(msg),
      onStreamEvent: (ev) => {
        setStreamAgent(ev.agent);
        switch (ev.event_type) {
          case "thinking_delta":
            setStreamThinking((prev) => prev + ev.delta);
            break;
          case "text_delta":
            setStreamText((prev) => prev + ev.delta);
            break;
          case "toolcall_start":
            setStreamToolCalls((prev) => [
              ...prev,
              {
                id: (ev.extra.tool_call_id as string) || "",
                name: (ev.extra.tool_name as string) || "",
                args: "",
                status: "running",
              },
            ]);
            break;
          case "toolcall_delta":
            setStreamToolCalls((prev) =>
              prev.map((tc) =>
                tc.id === (ev.extra.tool_call_id as string)
                  ? { ...tc, args: tc.args + ev.delta }
                  : tc,
              ),
            );
            break;
          case "toolcall_end":
            setStreamToolCalls((prev) =>
              prev.map((tc) =>
                tc.id === (ev.extra.tool_call_id as string)
                  ? { ...tc, status: "complete" as const }
                  : tc,
              ),
            );
            break;
          case "done":
            setStreamThinking("");
            setStreamText("");
            setStreamToolCalls([]);
            setStreamAgent("");
            break;
        }
      },
    });

  // Request browser notification permission on mount
  useEffect(() => {
    if (
      typeof Notification !== "undefined" &&
      Notification.permission === "default"
    ) {
      Notification.requestPermission().catch(() => {});
    }
  }, []);

  // On mount: check if a pending thread was set before this panel mounted
  useEffect(() => {
    const pending = consumePendingThread();
    if (pending) {
      api
        .getThread(pending)
        .then((loaded) => setThread(loaded))
        .catch((err) =>
          console.error("[ChatDesktopPanel] pending thread load error:", err),
        );
      return;
    }
    // IndexedDB session restore — load last active session if no pending thread
    if (persistReady && lastSessionId && !thread) {
      loadSession(lastSessionId)
        .then((restored) => {
          if (restored) setThread(restored);
        })
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [persistReady]);

  // Sync active thread to ws-store so Görev Merkezi can read it
  useEffect(() => {
    setActiveThread(thread);
  }, [thread]);

  // Listen for "open-thread" custom events from XpSessionsPanel (when already mounted)
  useEffect(() => {
    const handler = async (e: Event) => {
      const threadId = (e as CustomEvent<string>).detail;
      if (!threadId) return;
      try {
        const loaded = await api.getThread(threadId);
        setThread(loaded);
      } catch (err) {
        console.error("[ChatDesktopPanel] load thread error:", err);
      }
    };
    window.addEventListener("open-thread", handler);
    return () => window.removeEventListener("open-thread", handler);
  }, []);

  const isProcessing = status === "running" || status === "connecting";

  const handleSend = async (message: string, attachments?: AttachedFile[]) => {
    // Attachment'ları yükle ve extracted text'i mesaja ekle
    let fullMessage = message;
    if (attachments?.length) {
      const extracts: string[] = [];
      for (const att of attachments) {
        try {
          const result = await api.uploadDocument(att.file);
          if (
            result.extracted_text &&
            !result.extracted_text.startsWith("[Image")
          ) {
            extracts.push(
              `📎 ${result.filename}:\n${result.extracted_text.slice(0, 8000)}`,
            );
          } else {
            extracts.push(
              `📎 ${result.filename} (${(result.size_bytes / 1024).toFixed(0)} KB)`,
            );
          }
        } catch (err) {
          console.error("[ChatDesktopPanel] upload error:", err);
          extracts.push(`📎 ${att.file.name} — yükleme başarısız`);
        }
      }
      if (extracts.length > 0) {
        fullMessage = `${message}\n\n---\n${extracts.join("\n\n")}`;
      }
    }
    sendMessage(fullMessage, thread?.id, pipeline);
    trackBehavior("task_submit", message.slice(0, 200), {
      pipeline,
      attachments: attachments?.length ?? 0,
    });
    // Görev başladığında Canlı İlerleme penceresini otomatik aç
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("open-app", { detail: "agent-progress" }),
      );
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex items-center gap-2 shrink-0 px-2 py-1 border-b border-slate-700/50">
        <div className="flex-1 min-w-0">
          <PipelineSelector
            selected={pipeline}
            onSelect={(p) => {
              setPipeline(p);
              trackBehavior("pipeline_change", p, { from: pipeline, to: p });
            }}
          />
        </div>
      </div>
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
        <ChatArea thread={thread} isProcessing={isProcessing} status={status} />
      </div>
      {isProcessing && streamThinking && (
        <ThinkingPanel
          thinking={streamThinking}
          agent={streamAgent}
          isStreaming={status === "running"}
        />
      )}
      {isProcessing && streamToolCalls.length > 0 && (
        <ToolExecutionDisplay toolCalls={streamToolCalls} agent={streamAgent} />
      )}
      {isProcessing && streamText && (
        <div className="shrink-0 px-3 py-2 border-t border-slate-700/50 max-h-32 overflow-y-auto">
          <div className="text-xs text-slate-400 mb-1 flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            {streamAgent} yanıtlıyor...
          </div>
          <div className="text-sm text-slate-300">{streamText.slice(-500)}</div>
        </div>
      )}
      {lastError && (
        <div className="shrink-0 px-3 py-1.5 bg-red-950/50 border-t border-red-900/50 text-red-300 text-xs flex items-center justify-between">
          <span className="truncate">{lastError}</span>
          <button
            onClick={() => setLastError(null)}
            className="text-red-400 hover:text-red-200 text-xs px-1"
            aria-label="Kapat"
          >
            ✕
          </button>
        </div>
      )}
      <div className="shrink-0">
        <ChatInput
          onSend={handleSend}
          onStop={stop}
          isProcessing={isProcessing}
          onSteering={(msg) => sendOrchestratorChat(msg, thread?.id)}
        />
      </div>
      {liveEvents.length > 0 && (
        <div className="shrink-0 max-h-24 overflow-y-auto border-t border-slate-700/50">
          <LiveEventLog events={liveEvents} status={status} />
        </div>
      )}
    </div>
  );
}
