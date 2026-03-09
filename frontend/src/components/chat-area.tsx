"use client";

import {
  useEffect,
  useRef,
  useState,
  useMemo,
  useSyncExternalStore,
} from "react";
import type { Thread, AgentEvent } from "@/lib/types";
import { getAgentInfo } from "@/lib/agents";
import { Brain, CheckCircle, Clock, Coins, ShieldCheck } from "lucide-react";
import { detectArtifacts, ArtifactCard } from "@/components/artifacts-panel";
import { getWSSnapshot, subscribeWS } from "@/lib/ws-store";
import { DetailModal } from "./detail-modal";

interface Props {
  thread: Thread | null;
  isProcessing?: boolean;
  status?: "idle" | "connecting" | "running" | "complete" | "error";
}

const CHAT_EVENTS = new Set(["user_message", "agent_response", "error"]);

// ── Lightweight Markdown renderer (no deps) ──────────────────────
function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split("\n");
  const nodes: React.ReactNode[] = [];
  let key = 0;

  const inlineFormat = (line: string): React.ReactNode => {
    // Split by bold/italic/code/link/image patterns
    const parts: React.ReactNode[] = [];
    let remaining = line;
    let i = 0;

    while (remaining.length > 0) {
      // Inline image ![alt](url)
      const img = remaining.match(/^(.*?)!\[([^\]]*)\]\(([^)]+)\)(.*)/s);
      // Bold **text**
      const bold = remaining.match(/^(.*?)\*\*(.+?)\*\*(.*)/s);
      // Inline code `code`
      const code = remaining.match(/^(.*?)`([^`]+)`(.*)/s);
      // Link [text](url)
      const link = remaining.match(/^(.*?)\[([^\]]+)\]\(([^)]+)\)(.*)/s);

      const firstImg = img ? img[1].length : Infinity;
      const firstBold = bold ? bold[1].length : Infinity;
      const firstCode = code ? code[1].length : Infinity;
      const firstLink = link ? link[1].length : Infinity;
      const first = Math.min(firstImg, firstBold, firstCode, firstLink);

      if (first === Infinity) {
        parts.push(remaining);
        break;
      }

      if (first === firstImg && img) {
        if (img[1]) parts.push(img[1]);
        const imgSrc = img[3];
        const imgAlt = img[2];
        parts.push(
          <span key={i++} className="inline-block relative group">
            {/* eslint-disable-next-line @next/next/no-img-element -- dynamic markdown URLs (agent/user content) */}
            <img
              src={imgSrc}
              alt={imgAlt}
              loading="lazy"
              className="inline-block max-w-full rounded border border-slate-700 my-1"
              style={{ maxHeight: "300px" }}
            />
            <a
              href={imgSrc}
              download={`image-${Date.now()}.png`}
              target="_blank"
              rel="noopener noreferrer"
              className="absolute top-2 right-2 bg-black/70 hover:bg-black/90 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
              title="İndir"
            >
              ⬇ İndir
            </a>
          </span>,
        );
        remaining = img[4];
      } else if (first === firstBold && bold) {
        if (bold[1]) parts.push(bold[1]);
        parts.push(<strong key={i++}>{bold[2]}</strong>);
        remaining = bold[3];
      } else if (first === firstCode && code) {
        if (code[1]) parts.push(code[1]);
        parts.push(
          <code
            key={i++}
            className="bg-slate-800 text-pink-300 px-1 py-0.5 rounded text-xs font-mono break-all"
          >
            {code[2]}
          </code>,
        );
        remaining = code[3];
      } else if (first === firstLink && link) {
        if (link[1]) parts.push(link[1]);
        parts.push(
          <a
            key={i++}
            href={link[3]}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 underline hover:text-blue-300 break-words"
          >
            {link[2]}
          </a>,
        );
        remaining = link[4];
      } else {
        parts.push(remaining);
        break;
      }
    }
    return parts.length === 1 && typeof parts[0] === "string" ? (
      parts[0]
    ) : (
      <>{parts}</>
    );
  };

  let inCode = false;
  let codeBuf: string[] = [];

  for (let idx = 0; idx < lines.length; idx++) {
    const line = lines[idx];
    const stripped = line.trim();

    if (stripped.startsWith("```")) {
      if (inCode) {
        nodes.push(
          <pre
            key={key++}
            className="bg-slate-900 rounded-lg p-2 md:p-3 my-2 overflow-x-auto text-[11px] md:text-xs font-mono text-slate-300 border border-slate-700 max-w-full"
          >
            <code className="whitespace-pre-wrap break-words md:whitespace-pre md:break-normal">
              {codeBuf.join("\n")}
            </code>
          </pre>,
        );
        codeBuf = [];
        inCode = false;
      } else {
        inCode = true;
      }
      continue;
    }

    if (inCode) {
      codeBuf.push(line);
      continue;
    }

    if (!stripped) {
      nodes.push(<div key={key++} className="h-2" />);
      continue;
    }

    if (stripped === "---" || stripped === "***") {
      nodes.push(<hr key={key++} className="border-slate-700 my-3" />);
      continue;
    }

    if (stripped.startsWith("#### ")) {
      nodes.push(
        <h4
          key={key++}
          className="text-xs md:text-sm font-semibold text-slate-300 mt-3 mb-1"
        >
          {inlineFormat(stripped.slice(5))}
        </h4>,
      );
    } else if (stripped.startsWith("### ")) {
      nodes.push(
        <h3
          key={key++}
          className="text-sm md:text-base font-bold text-slate-200 mt-3 md:mt-4 mb-1.5"
        >
          {inlineFormat(stripped.slice(4))}
        </h3>,
      );
    } else if (stripped.startsWith("## ")) {
      nodes.push(
        <h2
          key={key++}
          className="text-base md:text-lg font-bold text-white mt-4 md:mt-5 mb-2 border-b border-slate-700 pb-1"
        >
          {inlineFormat(stripped.slice(3))}
        </h2>,
      );
    } else if (stripped.startsWith("# ")) {
      nodes.push(
        <h1
          key={key++}
          className="text-lg md:text-xl font-bold text-white mt-4 md:mt-5 mb-2 border-b border-slate-600 pb-1"
        >
          {inlineFormat(stripped.slice(2))}
        </h1>,
      );
    } else if (
      stripped.startsWith("- ") ||
      stripped.startsWith("* ") ||
      stripped.startsWith("• ")
    ) {
      nodes.push(
        <div key={key++} className="flex gap-2 my-0.5 ml-2">
          <span className="text-slate-500 mt-0.5 shrink-0">•</span>
          <span>{inlineFormat(stripped.slice(2))}</span>
        </div>,
      );
    } else if (/^\d+\.\s/.test(stripped)) {
      const m = stripped.match(/^(\d+)\.\s+(.+)/);
      if (m) {
        nodes.push(
          <div key={key++} className="flex gap-2 my-0.5 ml-2">
            <span className="text-slate-500 shrink-0 w-5 text-right">
              {m[1]}.
            </span>
            <span>{inlineFormat(m[2])}</span>
          </div>,
        );
      }
    } else if (stripped.startsWith("> ")) {
      nodes.push(
        <blockquote
          key={key++}
          className="border-l-2 border-purple-500 pl-3 my-2 text-slate-400 italic"
        >
          {inlineFormat(stripped.slice(2))}
        </blockquote>,
      );
    } else if (/^!\[([^\]]*)\]\(([^)]+)\)$/.test(stripped)) {
      const imgMatch = stripped.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
      if (imgMatch) {
        nodes.push(
          <figure key={key++} className="my-3 text-center relative group">
            {/* eslint-disable-next-line @next/next/no-img-element -- dynamic markdown URLs (agent/user content) */}
            <img
              src={imgMatch[2]}
              alt={imgMatch[1]}
              loading="lazy"
              className="max-w-full rounded-lg border border-slate-700 mx-auto"
              style={{ maxHeight: "400px" }}
            />
            <a
              href={imgMatch[2]}
              download={`image-${Date.now()}.png`}
              target="_blank"
              rel="noopener noreferrer"
              className="absolute top-2 right-2 bg-black/70 hover:bg-black/90 text-white text-xs px-3 py-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1"
              title="Görseli indir"
            >
              ⬇ İndir
            </a>
            {imgMatch[1] && (
              <figcaption className="text-[11px] text-slate-500 mt-1">
                {imgMatch[1]}
              </figcaption>
            )}
          </figure>,
        );
      }
    } else {
      nodes.push(
        <p key={key++} className="my-1 leading-relaxed">
          {inlineFormat(stripped)}
        </p>,
      );
    }
  }

  if (inCode && codeBuf.length > 0) {
    nodes.push(
      <pre
        key={key++}
        className="bg-slate-900 rounded-lg p-2 md:p-3 my-2 overflow-x-auto text-[11px] md:text-xs font-mono text-slate-300 border border-slate-700 max-w-full"
      >
        <code className="whitespace-pre-wrap break-words md:whitespace-pre md:break-normal">
          {codeBuf.join("\n")}
        </code>
      </pre>,
    );
  }

  return nodes;
}

export function ChatArea({ thread, isProcessing, status }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread?.events?.length]);

  if (!thread || !thread.events.length) {
    return <WelcomeScreen isProcessing={isProcessing} status={status} />;
  }

  // Build clean chat: user messages + errors + ONLY the final report per round.
  // A "round" = everything between two user_messages.
  // Within each round, prefer task.final_result (full synthesis) over individual agent_response events.
  const allChat = thread.events.filter((e) => CHAT_EVENTS.has(e.event_type));
  const chatEvents: AgentEvent[] = [];
  let pendingResponses: AgentEvent[] = [];

  // Map: find the final_result for each round by matching user_input to task
  const completedTasks = thread.tasks.filter(
    (t) => t.status === "completed" && t.final_result,
  );

  const flushResponses = () => {
    if (pendingResponses.length === 0) return;

    // Try to find a completed task whose final_result is the full synthesis
    // Match by checking if any completed task's final_result is longer than individual responses
    const lastTask = completedTasks.shift();
    if (lastTask?.final_result && lastTask.final_result.length > 50) {
      // Create a synthetic event with the full final_result
      const syntheticEvent: AgentEvent = {
        id: `synth_${lastTask.id}`,
        timestamp: lastTask.completed_at || lastTask.created_at,
        event_type: "agent_response" as AgentEvent["event_type"],
        agent_role: "orchestrator",
        content: lastTask.final_result,
        metadata: { synthetic: true, task_id: lastTask.id },
      };
      chatEvents.push(syntheticEvent);
    } else {
      // Fallback: find the last orchestrator response that's substantial (>100 chars)
      const finalReport = [...pendingResponses]
        .reverse()
        .find((e) => e.agent_role === "orchestrator" && e.content.length > 100);
      if (finalReport) {
        chatEvents.push(finalReport);
      } else {
        // Last resort: show the very last response
        chatEvents.push(pendingResponses[pendingResponses.length - 1]);
      }
    }
    pendingResponses = [];
  };

  for (const ev of allChat) {
    if (ev.event_type === "user_message" || ev.event_type === "error") {
      flushResponses();
      chatEvents.push(ev);
    } else {
      // agent_response — buffer it
      pendingResponses.push(ev);
    }
  }
  flushResponses();

  return (
    <div
      className="flex-1 min-h-0 overflow-y-auto px-3 md:px-6 py-4 space-y-3"
      role="log"
      aria-label="Sohbet geçmişi"
      aria-live="polite"
    >
      {chatEvents.map((event) => (
        <ChatBubble key={event.id} event={event} thread={thread} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

function WelcomeScreen({
  isProcessing,
  status,
}: {
  isProcessing?: boolean;
  status?: "idle" | "connecting" | "running" | "complete" | "error";
}) {
  const hints = [
    { label: "Derin Araştırma", desc: "Kapsamlı analiz" },
    { label: "Paralel", desc: "Hızlı çoklu agent" },
    { label: "Uzlaşı", desc: "Ortak karar" },
    { label: "Fikir→Proje", desc: "Plan oluştur" },
    { label: "Beyin Fırtınası", desc: "Çok yönlü tartışma" },
  ];

  const statusLabel =
    status === "connecting"
      ? "Bağlanıyor..."
      : status === "running" || isProcessing
        ? "Gönderiliyor..."
        : null;

  return (
    <div className="flex-1 min-h-0 flex flex-col items-center justify-center px-4">
      {statusLabel && (
        <div
          className="mb-4 flex items-center gap-2 rounded-full bg-blue-500/10 border border-blue-500/20 px-4 py-2 text-sm text-blue-300"
          role="status"
          aria-live="polite"
        >
          <span
            className="h-2 w-2 rounded-full bg-blue-400 animate-pulse"
            aria-hidden
          />
          {statusLabel}
        </div>
      )}
      <div className="text-center max-w-sm">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/nexus-logo.png"
          alt="Nexus Logo"
          className="w-12 h-12 md:w-14 md:h-14 mx-auto mb-4 rounded-xl"
        />
        <h1 className="text-lg md:text-xl font-bold text-slate-200 mb-2">
          Nexus AI Team
        </h1>
        <p className="text-sm text-slate-500 mb-6">
          Görev gönder — orchestrator analiz edip specialist agent&apos;lara
          yönlendirsin.
        </p>
        <div className="flex gap-2 justify-center flex-wrap">
          {hints.map((h) => (
            <span
              key={h.label}
              className="px-3 py-1.5 rounded-full bg-surface-overlay text-xs text-slate-400 border border-border"
            >
              {h.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function ChatBubble({ event, thread }: { event: AgentEvent; thread: Thread }) {
  const [showConfModal, setShowConfModal] = useState(false);
  const wsSnap = useSyncExternalStore(
    subscribeWS,
    getWSSnapshot,
    getWSSnapshot,
  );

  // Find the latest confidence_analysis from live events
  const confidenceText = useMemo(() => {
    for (let i = wsSnap.liveEvents.length - 1; i >= 0; i--) {
      const ev = wsSnap.liveEvents[i];
      if (ev.event_type === "confidence_analysis") {
        return ev.content;
      }
    }
    return undefined;
  }, [wsSnap.liveEvents]);

  if (event.event_type === "user_message") {
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="max-w-[85%] md:max-w-[70%] bg-blue-600/20 border border-blue-500/30 rounded-2xl rounded-br-md px-3 md:px-4 py-3">
          <div className="text-[10px] text-blue-400 font-semibold mb-1">
            SEN
          </div>
          <div className="text-sm text-slate-200 whitespace-pre-wrap break-words">
            {event.content}
          </div>
        </div>
      </div>
    );
  }

  if (event.event_type === "error") {
    return (
      <div className="animate-fade-in" role="alert">
        <div className="bg-red-950/30 border border-red-900/40 rounded-xl px-3 md:px-4 py-3 text-sm text-red-300">
          {event.content}
        </div>
      </div>
    );
  }

  const role = event.agent_role ?? "orchestrator";
  const info = getAgentInfo(role);
  const isFinal = role === "orchestrator" && event.content.length > 100;

  // Find matching task for metadata
  const lastTask = thread?.tasks?.length
    ? thread.tasks[thread.tasks.length - 1]
    : null;

  return (
    <div className="animate-slide-up">
      <div
        className={`rounded-2xl rounded-bl-md px-3 md:px-4 py-3 max-w-[100%] md:max-w-[85%] ${
          isFinal
            ? "bg-surface-overlay border-2 border-opacity-40"
            : "bg-surface-raised border border-border"
        }`}
        style={{ borderColor: isFinal ? info.color : undefined }}
      >
        {/* Agent header */}
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg" aria-hidden="true">
            {info.icon}
          </span>
          <span className="text-xs font-bold" style={{ color: info.color }}>
            {info.name}
          </span>
          {isFinal && (
            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-green-900/40 text-green-400 border border-green-800/40 inline-flex items-center gap-0.5">
              <CheckCircle className="w-3 h-3" aria-hidden="true" />
              SONUÇ
            </span>
          )}
        </div>

        {/* Content */}
        <div className="text-sm text-slate-300 leading-relaxed break-words overflow-hidden">
          {renderMarkdown(event.content)}
        </div>

        {/* Artifacts — interactive HTML/SVG/CSV/Mermaid rendering */}
        {(() => {
          const artifacts = detectArtifacts(event.content);
          if (artifacts.length === 0) return null;
          return (
            <div className="space-y-3 mt-3">
              {artifacts.map((a) => (
                <ArtifactCard key={a.id} artifact={a} />
              ))}
            </div>
          );
        })()}

        {/* Mobile-friendly metadata footer for final results */}
        {isFinal && lastTask && (
          <div className="mt-3 pt-2 border-t border-border/50 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-slate-500">
            {lastTask.total_tokens > 0 && (
              <span className="inline-flex items-center gap-0.5">
                <Coins className="w-3 h-3" aria-hidden="true" />
                {lastTask.total_tokens.toLocaleString("tr-TR")} token
              </span>
            )}
            {lastTask.total_latency_ms > 0 && (
              <span className="inline-flex items-center gap-0.5">
                <Clock className="w-3 h-3" aria-hidden="true" />
                {((lastTask.total_latency_ms ?? 0) / 1000).toFixed(1)}s
              </span>
            )}
            {lastTask.sub_tasks?.length > 0 && (
              <span className="inline-flex items-center gap-0.5">
                <Brain className="w-3 h-3" aria-hidden="true" />
                {lastTask.sub_tasks.length} agent
              </span>
            )}
            {confidenceText && (
              <button
                type="button"
                onClick={() => setShowConfModal(true)}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-900/30 text-amber-400 hover:bg-amber-900/50 transition-colors cursor-pointer border border-amber-800/30"
                title="Güven Analizi"
              >
                <ShieldCheck className="w-3 h-3" aria-hidden="true" />
                Güven Analizi
              </button>
            )}
          </div>
        )}

        {/* Confidence Analysis Modal */}
        {showConfModal && confidenceText && (
          <DetailModal
            title="Güven Analizi"
            content={confidenceText}
            color="#f59e0b"
            badge="CONFIDENCE"
            onClose={() => setShowConfModal(false)}
          />
        )}
      </div>
    </div>
  );
}
