"use client";

import { useEffect, useRef } from "react";
import type { Thread, AgentEvent } from "@/lib/types";
import { getAgentInfo } from "@/lib/agents";
import { Brain, CheckCircle, Clock, Coins } from "lucide-react";

interface Props {
  thread: Thread | null;
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
        parts.push(
          <img
            key={i++}
            src={img[3]}
            alt={img[2]}
            loading="lazy"
            className="inline-block max-w-full rounded border border-slate-700 my-1"
            style={{ maxHeight: "300px" }}
          />,
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
            className="bg-slate-800 text-pink-300 px-1 py-0.5 rounded text-xs font-mono"
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
            className="text-blue-400 underline hover:text-blue-300"
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
  let codeLang = "";

  for (let idx = 0; idx < lines.length; idx++) {
    const line = lines[idx];
    const stripped = line.trim();

    if (stripped.startsWith("```")) {
      if (inCode) {
        nodes.push(
          <pre
            key={key++}
            className="bg-slate-900 rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono text-slate-300 border border-slate-700"
          >
            <code>{codeBuf.join("\n")}</code>
          </pre>,
        );
        codeBuf = [];
        inCode = false;
        codeLang = "";
      } else {
        inCode = true;
        codeLang = stripped.slice(3).trim();
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
          className="text-sm font-semibold text-slate-300 mt-3 mb-1"
        >
          {inlineFormat(stripped.slice(5))}
        </h4>,
      );
    } else if (stripped.startsWith("### ")) {
      nodes.push(
        <h3
          key={key++}
          className="text-base font-bold text-slate-200 mt-4 mb-1.5"
        >
          {inlineFormat(stripped.slice(4))}
        </h3>,
      );
    } else if (stripped.startsWith("## ")) {
      nodes.push(
        <h2
          key={key++}
          className="text-lg font-bold text-white mt-5 mb-2 border-b border-slate-700 pb-1"
        >
          {inlineFormat(stripped.slice(3))}
        </h2>,
      );
    } else if (stripped.startsWith("# ")) {
      nodes.push(
        <h1
          key={key++}
          className="text-xl font-bold text-white mt-5 mb-2 border-b border-slate-600 pb-1"
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
          <figure key={key++} className="my-3 text-center">
            <img
              src={imgMatch[2]}
              alt={imgMatch[1]}
              loading="lazy"
              className="max-w-full rounded-lg border border-slate-700 mx-auto"
              style={{ maxHeight: "400px" }}
            />
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
        className="bg-slate-900 rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono text-slate-300 border border-slate-700"
      >
        <code>{codeBuf.join("\n")}</code>
      </pre>,
    );
  }

  return nodes;
}

export function ChatArea({ thread }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread?.events?.length]);

  if (!thread || !thread.events.length) {
    return <WelcomeScreen />;
  }

  const chatEvents = thread.events.filter((e) => CHAT_EVENTS.has(e.event_type));

  return (
    <div
      className="flex-1 overflow-y-auto px-3 md:px-6 py-4 space-y-3"
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

function WelcomeScreen() {
  const hints = [
    { label: "Derin Araştırma", desc: "Kapsamlı analiz" },
    { label: "Paralel", desc: "Hızlı çoklu agent" },
    { label: "Uzlaşı", desc: "Ortak karar" },
    { label: "Fikir→Proje", desc: "Plan oluştur" },
    { label: "Beyin Fırtınası", desc: "Çok yönlü tartışma" },
  ];

  return (
    <div className="flex-1 flex items-center justify-center px-4">
      <div className="text-center max-w-sm">
        <Brain
          className="w-10 h-10 md:w-12 md:h-12 mx-auto mb-4 text-pink-400"
          aria-hidden="true"
        />
        <h1 className="text-lg md:text-xl font-bold text-slate-200 mb-2">
          Multi-Agent Ops Center
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
        <div className="text-sm text-slate-300 leading-relaxed break-words">
          {renderMarkdown(event.content)}
        </div>

        {/* Mobile-friendly metadata footer for final results */}
        {isFinal && lastTask && (
          <div className="mt-3 pt-2 border-t border-border/50 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-slate-500">
            {lastTask.total_tokens > 0 && (
              <span className="inline-flex items-center gap-0.5">
                <Coins className="w-3 h-3" aria-hidden="true" />
                {lastTask.total_tokens.toLocaleString("tr-TR")} token
              </span>
            )}
            {lastTask.total_latency_ms > 0 && (
              <span className="inline-flex items-center gap-0.5">
                <Clock className="w-3 h-3" aria-hidden="true" />
                {(lastTask.total_latency_ms / 1000).toFixed(1)}s
              </span>
            )}
            {lastTask.sub_tasks?.length > 0 && (
              <span className="inline-flex items-center gap-0.5">
                <Brain className="w-3 h-3" aria-hidden="true" />
                {lastTask.sub_tasks.length} agent
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
