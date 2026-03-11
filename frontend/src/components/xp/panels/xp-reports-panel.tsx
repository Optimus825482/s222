"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { api, fetchBlob } from "@/lib/api";
import { trackBehavior } from "@/lib/behavior-tracker";
import type { ThreadSummary, Thread, Task, AgentEvent } from "@/lib/types";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Clock,
  Download,
  FileText,
  FolderOpen,
  Loader2,
  MessageSquare,
  Presentation,
  Trash2,
  Cpu,
  Zap,
  AlertCircle,
  CheckCircle2,
  Brain,
  Search,
  Play,
  BarChart3,
  User,
  Wrench,
  ShieldCheck,
} from "lucide-react";
import { DetailModal } from "./detail-modal";
import ArtifactsPanel, { hasRenderableArtifacts } from "@/components/artifacts-panel";

// ── Helpers ──────────────────────────────────────────────────────

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString("tr-TR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function buildThreadMarkdown(thread: Thread): string {
  let md = `# Thread: ${thread.id}\n\nOluşturulma: ${formatDate(thread.created_at)}\n\n`;
  md += `## Görevler (${thread.tasks.length})\n\n`;
  for (const t of thread.tasks) {
    md += `### ${t.user_input}\n- Durum: ${t.status}\n- Pipeline: ${t.pipeline_type}\n- Token: ${t.total_tokens}\n- Süre: ${t.total_latency_ms}ms\n`;
    if (t.final_result) md += `\n**Sonuç:**\n${t.final_result}\n`;
    md += "\n";
  }
  md += `## Olaylar (${thread.events.length})\n\n`;
  for (const e of thread.events) {
    md += `- [${e.event_type}] ${e.agent_role ?? "system"}: ${e.content.slice(0, 200)}\n`;
  }
  return md;
}

function buildCleanReportMarkdown(thread: Thread): string {
  const completedTasks = thread.tasks.filter(
    (t) => t.status === "completed" && t.final_result,
  );
  if (completedTasks.length === 0)
    return "# Sonuç Raporu\n\nTamamlanmış görev bulunamadı.\n";

  const date = formatDate(thread.created_at);
  let md = `# Sonuç Raporu\n\nTarih: ${date}\n\n---\n\n`;

  for (const t of completedTasks) {
    md += `## ${t.user_input}\n\n${t.final_result}\n\n---\n\n`;
  }
  return md;
}

const UTF8_BOM = "\uFEFF";

function downloadMarkdown(filename: string, content: string) {
  const blob = new Blob([UTF8_BOM + content], {
    type: "text/markdown;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Event styling config ─────────────────────────────────────────

const EVENT_STYLES: Record<
  string,
  {
    containerClass: string;
    iconClass: string;
    textClass: string;
    badgeClass: string;
    icon: typeof Cpu;
    label: string;
  }
> = {
  user_message: {
    containerClass: "border-l-[#4285f4] bg-[#e8f0fe]",
    iconClass: "text-[#4285f4]",
    textClass: "text-[#1a56db]",
    badgeClass: "bg-[#4285f418] text-[#1a56db]",
    icon: User,
    label: "Kullanıcı",
  },
  agent_thinking: {
    containerClass: "border-l-[#f59e0b] bg-[#fef9e7]",
    iconClass: "text-[#f59e0b]",
    textClass: "text-[#92400e]",
    badgeClass: "bg-[#f59e0b18] text-[#92400e]",
    icon: Brain,
    label: "Düşünme",
  },
  agent_response: {
    containerClass: "border-l-[#10b981] bg-[#ecfdf5]",
    iconClass: "text-[#10b981]",
    textClass: "text-[#065f46]",
    badgeClass: "bg-[#10b98118] text-[#065f46]",
    icon: CheckCircle2,
    label: "Yanıt",
  },
  agent_start: {
    containerClass: "border-l-[#3b82f6] bg-[#f0f9ff]",
    iconClass: "text-[#3b82f6]",
    textClass: "text-[#1e40af]",
    badgeClass: "bg-[#3b82f618] text-[#1e40af]",
    icon: Play,
    label: "Başlangıç",
  },
  tool_call: {
    containerClass: "border-l-[#6366f1] bg-[#eff6ff]",
    iconClass: "text-[#6366f1]",
    textClass: "text-[#3730a3]",
    badgeClass: "bg-[#6366f118] text-[#3730a3]",
    icon: Wrench,
    label: "Araç Çağrısı",
  },
  tool_result: {
    containerClass: "border-l-[#8b5cf6] bg-[#f5f3ff]",
    iconClass: "text-[#8b5cf6]",
    textClass: "text-[#5b21b6]",
    badgeClass: "bg-[#8b5cf618] text-[#5b21b6]",
    icon: Cpu,
    label: "Araç Sonucu",
  },
  routing_decision: {
    containerClass: "border-l-[#d946ef] bg-[#fdf4ff]",
    iconClass: "text-[#d946ef]",
    textClass: "text-[#86198f]",
    badgeClass: "bg-[#d946ef18] text-[#86198f]",
    icon: Zap,
    label: "Yönlendirme",
  },
  pipeline_start: {
    containerClass: "border-l-[#14b8a6] bg-[#f0fdfa]",
    iconClass: "text-[#14b8a6]",
    textClass: "text-[#115e59]",
    badgeClass: "bg-[#14b8a618] text-[#115e59]",
    icon: Play,
    label: "Pipeline Başlangıç",
  },
  pipeline_step: {
    containerClass: "border-l-[#14b8a6] bg-[#f0fdfa]",
    iconClass: "text-[#14b8a6]",
    textClass: "text-[#115e59]",
    badgeClass: "bg-[#14b8a618] text-[#115e59]",
    icon: BarChart3,
    label: "Pipeline Adım",
  },
  pipeline_complete: {
    containerClass: "border-l-[#10b981] bg-[#ecfdf5]",
    iconClass: "text-[#10b981]",
    textClass: "text-[#065f46]",
    badgeClass: "bg-[#10b98118] text-[#065f46]",
    icon: CheckCircle2,
    label: "Pipeline Tamamlandı",
  },
  synthesis: {
    containerClass: "border-l-[#f59e0b] bg-[#fffbeb]",
    iconClass: "text-[#f59e0b]",
    textClass: "text-[#78350f]",
    badgeClass: "bg-[#f59e0b18] text-[#78350f]",
    icon: Brain,
    label: "Sentez",
  },
  error: {
    containerClass: "border-l-[#ef4444] bg-[#fef2f2]",
    iconClass: "text-[#ef4444]",
    textClass: "text-[#991b1b]",
    badgeClass: "bg-[#ef444418] text-[#991b1b]",
    icon: AlertCircle,
    label: "Hata",
  },
  rag_query: {
    containerClass: "border-l-[#0ea5e9] bg-[#f0f9ff]",
    iconClass: "text-[#0ea5e9]",
    textClass: "text-[#0c4a6e]",
    badgeClass: "bg-[#0ea5e918] text-[#0c4a6e]",
    icon: Search,
    label: "RAG Sorgu",
  },
  evaluation: {
    containerClass: "border-l-[#eab308] bg-[#fefce8]",
    iconClass: "text-[#eab308]",
    textClass: "text-[#713f12]",
    badgeClass: "bg-[#eab30818] text-[#713f12]",
    icon: BarChart3,
    label: "Değerlendirme",
  },
};

const DEFAULT_EVENT_STYLE = {
  containerClass: "border-l-[#aca899] bg-[#f8f6ee]",
  iconClass: "text-[#aca899]",
  textClass: "text-[#333]",
  badgeClass: "bg-[#aca89918] text-[#333]",
  icon: FileText,
  label: "Olay",
};

function getEventStyle(eventType: string) {
  return EVENT_STYLES[eventType] ?? DEFAULT_EVENT_STYLE;
}

const STATUS_BADGE_CLASSES: Record<string, string> = {
  completed: "bg-[#dcfce7] text-[#166534]",
  running: "bg-[#dbeafe] text-[#1e40af]",
  pending: "bg-[#fef9c3] text-[#854d0e]",
  failed: "bg-[#fee2e2] text-[#991b1b]",
  routing: "bg-[#f3e8ff] text-[#6b21a8]",
  reviewing: "bg-[#e0f2fe] text-[#075985]",
};

// ── Types ────────────────────────────────────────────────────────

type Folder = "threads" | "projects" | "presentations" | "workflows";

interface ProjectSummary {
  name: string;
  phases: string[];
  phase_count: number;
  total_phases: number;
}

interface PresentationSummary {
  id: string;
  title: string;
  slide_count: number;
  theme: string;
  style: string;
  palette_name: string;
  created_at: string;
  updated_at: string;
}

interface PresentationDetail extends PresentationSummary {
  slides: Array<{
    id: number;
    title: string;
    content: string;
    bullets: string[];
    layout: string;
    imageUrl?: string;
    colors?: {
      background: string;
      text: string;
      accent: string;
      accent_secondary: string;
      muted: string;
    };
  }>;
}

interface ContextMenu {
  x: number;
  y: number;
  type: Folder;
  id: string;
  label: string;
}

// ── Presentation Detail View ─────────────────────────────────────

function PresentationDetailView({
  presentation,
  onBack,
  onDelete,
}: {
  presentation: PresentationDetail;
  onBack: () => void;
  onDelete: (id: string) => void;
}) {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [downloading, setDownloading] = useState(false);
  const slide = presentation.slides[currentSlide];
  const slideBackground = slide?.colors?.background || "#1a1a2e";
  const slideText = slide?.colors?.text || "#f1f5f9";
  const slideAccent = slide?.colors?.accent || "#8b5cf6";

  const handleDownload = async () => {
    setDownloading(true);
    try {
      // Sunumu HTML olarak indir
      const html = generatePresentationHTML(presentation);
      const blob = new Blob([html], { type: "text/html;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${presentation.title.replace(/[^a-zA-Z0-9]/g, "_")}.html`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download error:", err);
    } finally {
      setDownloading(false);
    }
  };

  const handleDelete = () => {
    if (confirm(`"${presentation.title}" silinsin mi?`)) {
      onDelete(presentation.id);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white text-[#1a1a1a]">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[#d6d2c2] bg-[#f8f6ee]">
        <button
          onClick={onBack}
          className="rounded p-1 text-[#333]"
          aria-label="Sunum listesine geri dön"
          title="Geri"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <Presentation className="h-4 w-4 text-[#8b5cf6]" />
        <span className="truncate text-[13px] font-semibold text-[#003399]">
          {presentation.title}
        </span>
        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="flex items-center gap-1 rounded bg-[#ecfdf5] p-1.5 text-[10px] text-[#065f46] disabled:opacity-60"
          >
            {downloading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Download className="w-3.5 h-3.5" />
            )}
            <span>İndir</span>
          </button>
          <button
            onClick={handleDelete}
            className="flex items-center gap-1 rounded bg-[#fef2f2] p-1.5 text-[10px] text-[#dc2626]"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Sil</span>
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="flex flex-wrap gap-3 border-b border-[#ece9d8] bg-[#faf8f0] px-3 py-2 text-[11px] text-[#555]">
        <span>{presentation.slide_count} slayt</span>
        <span>Tema: {presentation.theme}</span>
        <span>
          Palet: {presentation.palette_name}
        </span>
        <span>
          {formatDate(presentation.created_at)}
        </span>
      </div>

      {/* Slide Navigation */}
      <div className="flex items-center gap-2 border-b border-[#ece9d8] px-3 py-2">
        <button
          onClick={() => setCurrentSlide(Math.max(0, currentSlide - 1))}
          disabled={currentSlide === 0}
          className="rounded p-1 text-[#333] disabled:opacity-50"
          aria-label="Önceki slayt"
          title="Önceki slayt"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="text-[11px] text-[#666]">
          {currentSlide + 1} / {presentation.slides.length}
        </span>
        <button
          onClick={() =>
            setCurrentSlide(
              Math.min(presentation.slides.length - 1, currentSlide + 1),
            )
          }
          disabled={currentSlide === presentation.slides.length - 1}
          className="rounded p-1 text-[#333] disabled:opacity-50"
          aria-label="Sonraki slayt"
          title="Sonraki slayt"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        {/* Slide thumbnails */}
        <div className="flex gap-1 ml-2 overflow-x-auto flex-1">
          {presentation.slides.map((s, i) => (
            <button
              key={i}
              onClick={() => setCurrentSlide(i)}
              className={clsx(
                "whitespace-nowrap rounded px-2 py-1 text-[10px]",
                i === currentSlide
                  ? "bg-[#8b5cf6] text-white"
                  : "bg-[#f3f4f6] text-[#333]",
              )}
              aria-label={`${i + 1}. slaytı aç`}
              title={s.title}
            >
              {s.title.slice(0, 15)}...
            </button>
          ))}
        </div>
      </div>

      {/* Slide Preview */}
      <div className="presentation-slide-preview flex flex-1 items-center justify-center p-4">
        <div className="presentation-slide-card flex aspect-video w-full max-w-2xl flex-col justify-center rounded-lg p-8 shadow-xl">
          <h2 className="presentation-slide-title mb-4 text-2xl font-bold">
            {slide?.title}
          </h2>
          {slide?.content && (
            <p className="text-sm mb-4 opacity-90">{slide.content}</p>
          )}
          {slide?.bullets && slide.bullets.length > 0 && (
            <ul className="space-y-2">
              {slide.bullets.map((b: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="presentation-slide-bullet">•</span>
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          )}
          {slide?.imageUrl && (
            <div className="mt-4 rounded overflow-hidden">
              <img
                src={slide.imageUrl}
                alt={slide.title}
                className="w-full h-32 object-cover"
              />
            </div>
          )}
        </div>
      </div>
      <style jsx>{`
        .presentation-slide-preview,
        .presentation-slide-card {
          background-color: ${slideBackground};
          color: ${slideText};
        }

        .presentation-slide-title,
        .presentation-slide-bullet {
          color: ${slideAccent};
        }
      `}</style>
    </div>
  );
}

function generatePresentationHTML(presentation: PresentationDetail): string {
  const slides = presentation.slides
    .map((slide, i) => {
      const colors = slide.colors || {
        background: "#1a1a2e",
        text: "#f1f5f9",
        accent: "#8b5cf6",
      };
      return `
      <section class="slide" style="background: ${colors.background}; color: ${colors.text}">
        <div class="slide-content">
          <h2 style="color: ${colors.accent}">${slide.title}</h2>
          ${slide.content ? `<p>${slide.content}</p>` : ""}
          ${slide.bullets?.length ? `<ul>${slide.bullets.map((b) => `<li>${b}</li>`).join("")}</ul>` : ""}
          ${slide.imageUrl ? `<img src="${slide.imageUrl}" alt="${slide.title}" />` : ""}
        </div>
      </section>
    `;
    })
    .join("\n");

  return `<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <title>${presentation.title}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { height: 100%; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    .slide { height: 100vh; display: flex; align-items: center; justify-content: center; padding: 2rem; }
    .slide-content { max-width: 800px; text-align: center; }
    h2 { font-size: 2.5rem; margin-bottom: 1rem; }
    p { font-size: 1.25rem; opacity: 0.9; margin-bottom: 1rem; }
    ul { text-align: left; list-style: none; }
    li { padding: 0.5rem 0; font-size: 1.1rem; }
    li::before { content: "•"; margin-right: 0.5rem; }
    img { max-width: 100%; max-height: 200px; object-fit: cover; border-radius: 0.5rem; margin-top: 1rem; }
  </style>
</head>
<body>
  ${slides}
</body>
</html>`;
}

// ── Structured Event Renderer ────────────────────────────────────

function EventBlock({ event }: { event: AgentEvent }) {
  const style = getEventStyle(event.event_type);
  const Icon = style.icon;
  const content = event.content || "";
  const isLong = content.length > 300;
  const [expanded, setExpanded] = useState(false);
  const displayContent =
    isLong && !expanded ? content.slice(0, 300) + "..." : content;

  return (
    <div
      className={clsx(
        "mb-2 rounded-r border-l-[3px] px-3 py-2",
        style.containerClass,
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <Icon className={clsx("h-3.5 w-3.5 shrink-0", style.iconClass)} />
        <span className={clsx("text-[11px] font-semibold", style.textClass)}>
          {style.label}
        </span>
        {event.agent_role && (
          <span className={clsx("rounded px-1.5 py-0.5 text-[10px]", style.badgeClass)}>
            {event.agent_role}
          </span>
        )}
        <span className="ml-auto text-[10px] text-[#888]">
          {new Date(event.timestamp).toLocaleTimeString("tr-TR")}
        </span>
      </div>
      <div className={clsx("break-words whitespace-pre-wrap text-[12px] leading-relaxed", style.textClass)}>
        {displayContent}
      </div>
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          className={clsx("mt-1 text-[10px] underline", style.iconClass)}
        >
          {expanded ? "Daralt" : "Devamını göster"}
        </button>
      )}
    </div>
  );
}

// ── Structured Task Card ─────────────────────────────────────────

function TaskCard({ task, index }: { task: Task; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const [showConfidence, setShowConfidence] = useState(false);
  const statusClass =
    STATUS_BADGE_CLASSES[task.status] ?? "bg-[#f3f4f6] text-[#374151]";

  return (
    <div className="mb-3 rounded border border-[#d6d2c2] bg-white">
      {/* Task header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-2 px-3 py-2.5 text-left"
        aria-expanded={expanded}
      >
        <span className="shrink-0 text-[11px] font-bold text-[#003399]">
          #{index + 1}
        </span>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-medium leading-snug text-[#1a1a1a]">
            {task.user_input}
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-1.5">
            <span className={clsx("rounded px-2 py-0.5 text-[10px] font-medium", statusClass)}>
              {task.status}
            </span>
            <span className="text-[10px] text-[#666]">
              {task.pipeline_type}
            </span>
            <span className="text-[10px] text-[#666]">
              {task.total_tokens.toLocaleString()} token
            </span>
            <span className="text-[10px] text-[#666]">
              {((task.total_latency_ms ?? 0) / 1000).toFixed(1)}s
            </span>
          </div>
        </div>
        <svg
          className={clsx(
            "mt-1 h-4 w-4 shrink-0 text-[#888] transition-transform",
            expanded && "rotate-180",
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-[#d6d2c2] px-3 py-2">
          {/* Sub-tasks */}
          {task.sub_tasks.length > 0 && (
            <div className="mb-3">
              <div className="mb-1.5 text-[11px] font-semibold text-[#003399]">
                Alt Görevler ({task.sub_tasks.length})
              </div>
              {task.sub_tasks.map((st) => {
                const stStatusClass =
                  STATUS_BADGE_CLASSES[st.status] ??
                  "bg-[#f3f4f6] text-[#374151]";
                return (
                  <div
                    key={st.id}
                    className="flex items-start gap-2 py-1 text-[11px]"
                    style={undefined}
                  >
                    <span className={clsx("shrink-0 rounded px-1.5 py-0.5 text-[9px] font-medium", stStatusClass)}>
                      {st.status}
                    </span>
                    <span className="flex-1 text-[#333]">
                      {st.description}
                    </span>
                    <span className="shrink-0 text-[10px] text-[#888]">
                      {st.assigned_agent}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Final result */}
          {task.final_result && (
            <div className="rounded border border-[#a7f3d0] bg-[#ecfdf5] p-2.5">
              <div className="flex items-center justify-between mb-1">
                <div className="text-[11px] font-semibold text-[#065f46]">
                  Sonuç
                </div>
                {task.confidence_footer && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowConfidence(true);
                    }}
                    className="flex items-center gap-1 rounded border border-[#bfdbfe] bg-[#eff6ff] px-2 py-0.5 text-[10px] font-medium text-[#1e40af] transition-colors"
                    title="Güven Analizi"
                  >
                    <ShieldCheck className="w-3 h-3" />
                    Güven Analizi
                  </button>
                )}
              </div>
              <div className="whitespace-pre-wrap text-[12px] leading-relaxed text-[#064e3b]">
                {task.final_result}
              </div>
              {hasRenderableArtifacts(task.final_result) && (
                <div className="mt-2">
                  <ArtifactsPanel content={task.final_result} />
                </div>
              )}
            </div>
          )}

          {/* Confidence analysis modal */}
          {showConfidence && task.confidence_footer && (
            <DetailModal
              title="Güven Analizi"
              content={task.confidence_footer}
              color="#3b82f6"
              badge="Confidence"
              onClose={() => setShowConfidence(false)}
            />
          )}
        </div>
      )}
    </div>
  );
}

// ── Structured Thread Detail View ────────────────────────────────

function ThreadDetailView({
  thread,
  onBack,
}: {
  thread: Thread;
  onBack: () => void;
}) {
  const [activeTab, setActiveTab] = useState<"tasks" | "events">("tasks");
  const [exportingPdf, setExportingPdf] = useState(false);
  const [showThreadConfidence, setShowThreadConfidence] = useState(false);
  const totalTokens = thread.tasks.reduce((s, t) => s + t.total_tokens, 0);
  const totalLatency = thread.tasks.reduce((s, t) => s + t.total_latency_ms, 0);
  const lastStatus = thread.tasks.length
    ? thread.tasks[thread.tasks.length - 1].status
    : "boş";

  // Combine all confidence footers from tasks
  const allConfidenceFooters = thread.tasks
    .filter((t) => t.confidence_footer)
    .map(
      (t, i) => `## Görev ${i + 1}: ${t.user_input}\n\n${t.confidence_footer}`,
    )
    .join("\n\n---\n\n");
  const hasConfidence = allConfidenceFooters.length > 0;
  const lastStatusClass =
    STATUS_BADGE_CLASSES[lastStatus] ?? "bg-[#f3f4f6] text-[#374151]";

  return (
    <div className="flex h-full bg-white text-[#1a1a1a]">
      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header bar */}
        <div className="flex items-center gap-2 border-b border-[#d6d2c2] bg-[#f8f6ee] px-3 py-2">
          <button
            onClick={onBack}
            className="rounded p-1 text-[#333]"
            aria-label="Geri"
            title="Geri"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <FileText className="h-4 w-4 text-[#003399]" />
          <span className="truncate text-[13px] font-semibold text-[#003399]">
            Thread: {thread.id.slice(0, 8)}...
          </span>
          <div className="ml-auto flex items-center gap-1">
            {hasConfidence && (
              <button
                onClick={() => setShowThreadConfidence(true)}
                className="flex items-center gap-1 rounded bg-[#eff6ff] p-1.5 text-[10px] text-[#1e40af]"
                title="Güven Analizi"
                aria-label="Güven analizini görüntüle"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Güven</span>
              </button>
            )}
            <button
              onClick={() => {
                const md = buildCleanReportMarkdown(thread);
                downloadMarkdown(
                  `sonuc-raporu-${thread.id.slice(0, 8)}.md`,
                  md,
                );
                trackBehavior("report_download", thread.id, { format: "md" });
              }}
              className="flex items-center gap-1 rounded bg-[#ecfdf5] p-1.5 text-[10px] text-[#065f46]"
              title="Sonuç Raporu (MD)"
              aria-label="Sonuç raporunu Markdown olarak indir"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>MD</span>
            </button>
            <button
              onClick={async () => {
                setExportingPdf(true);
                try {
                  const md = buildCleanReportMarkdown(thread);
                  const title =
                    thread.tasks[0]?.user_input?.slice(0, 60) || "Sonuç Raporu";
                  const blob = await fetchBlob("/api/export/pdf", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ markdown: md, title }),
                  });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `sonuc-raporu-${thread.id.slice(0, 8)}.pdf`;
                  a.click();
                  URL.revokeObjectURL(url);
                  trackBehavior("report_download", thread.id, {
                    format: "pdf",
                  });
                } catch (err) {
                  console.error("[XpReports] PDF export error:", err);
                } finally {
                  setExportingPdf(false);
                }
              }}
              disabled={exportingPdf}
              className="flex items-center gap-1 rounded bg-[#dbeafe] p-1.5 text-[10px] text-[#1e40af] disabled:opacity-60"
              title="Sonuç Raporu (PDF)"
              aria-label="Sonuç raporunu PDF olarak indir"
            >
              {exportingPdf ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Download className="w-3.5 h-3.5" />
              )}
              <span>PDF</span>
            </button>
            <button
              onClick={() =>
                downloadMarkdown(
                  `thread-${thread.id.slice(0, 8)}.md`,
                  buildThreadMarkdown(thread),
                )
              }
              className="rounded p-1.5 text-[#666]"
              title="Tüm detayları indir (.md)"
              aria-label="Tüm detayları Markdown olarak indir"
            >
              <Download className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Stats bar */}
        <div className="flex flex-wrap gap-3 border-b border-[#ece9d8] bg-[#faf8f0] px-3 py-2 text-[11px] text-[#555]">
          <span>
            <Clock className="mr-1 inline h-3 w-3 align-[-2px]" />
            {formatDate(thread.created_at)}
          </span>
          <span>{thread.tasks.length} görev</span>
          <span>{thread.events.length} olay</span>
          <span>
            {totalTokens.toLocaleString()} token
          </span>
          <span>
            {((totalLatency ?? 0) / 1000).toFixed(1)}s
          </span>
          <span className={clsx("rounded px-1.5 py-0.5 text-[10px] font-medium", lastStatusClass)}>
            {lastStatus}
          </span>
          {thread.branch_label && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-white border border-[#d6d2c2] text-[#333]">
              Branch: {thread.branch_label}
            </span>
          )}
          {thread.compacted_summary && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-white border border-[#d6d2c2] text-[#333]">
              Compact özeti var
            </span>
          )}
        </div>

        {thread.compacted_summary && (
          <div className="border-b border-[#ece9d8] bg-[#fffdf5] px-3 py-2 text-[11px]">
            <div className="mb-1 font-semibold text-[#7c5a00]">
              Compact Özeti
            </div>
            <div className="whitespace-pre-wrap leading-relaxed text-[#5f4b00]">
              {thread.compacted_summary}
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-[#d6d2c2] bg-[#f8f6ee]">
          <button
            onClick={() => setActiveTab("tasks")}
            className={clsx(
              "border-b-2 px-4 py-2 text-[12px] font-medium transition-colors",
              activeTab === "tasks"
                ? "border-[#003399] bg-white text-[#003399]"
                : "border-transparent text-[#666]",
            )}
          >
            Görevler ({thread.tasks.length})
          </button>
          <button
            onClick={() => setActiveTab("events")}
            className={clsx(
              "border-b-2 px-4 py-2 text-[12px] font-medium transition-colors",
              activeTab === "events"
                ? "border-[#003399] bg-white text-[#003399]"
                : "border-transparent text-[#666]",
            )}
          >
            Olaylar ({thread.events.length})
          </button>
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-auto bg-white p-3">
          {activeTab === "tasks" ? (
            thread.tasks.length === 0 ? (
              <div className="py-8 text-center text-[12px] text-[#888]">
                Bu thread&apos;de görev yok
              </div>
            ) : (
              thread.tasks.map((t, i) => (
                <TaskCard key={t.id} task={t} index={i} />
              ))
            )
          ) : thread.events.length === 0 ? (
              <div className="py-8 text-center text-[12px] text-[#888]">
              Bu thread&apos;de olay yok
            </div>
          ) : (
            thread.events.map((e) => <EventBlock key={e.id} event={e} />)
          )}
        </div>
      </div>

      {/* Right sidebar — agent metrics */}
      {Object.keys(thread.agent_metrics).length > 0 && (
        <div
          className="flex w-52 flex-col border-l border-[#d6d2c2] bg-[#f8f6ee]"
        >
          <div className="border-b border-[#d6d2c2] px-3 py-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[#003399]">
              Agent Metrikleri
            </span>
          </div>
          <div className="flex-1 overflow-auto p-2 space-y-2">
            {Object.entries(thread.agent_metrics).map(([role, m]) => (
              <div key={role} className="rounded border border-[#ece9d8] bg-white p-2">
                <div className="mb-1 text-[11px] font-semibold text-[#003399]">
                  {role}
                </div>
                <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[10px]">
                  <span className="text-[#888]">Çağrı</span>
                  <span className="text-right text-[#333]">
                    {m.total_calls}
                  </span>
                  <span className="text-[#888]">Token</span>
                  <span className="text-right text-[#333]">
                    {m.total_tokens.toLocaleString()}
                  </span>
                  <span className="text-[#888]">Başarı</span>
                  <span className="text-right text-[#333]">
                    {m.success_count}/{m.total_calls}
                  </span>
                  <span className="text-[#888]">Hata</span>
                  <span className={clsx("text-right", m.error_count > 0 ? "text-[#dc2626]" : "text-[#333]")}>
                    {m.error_count}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Thread-level confidence analysis modal */}
      {showThreadConfidence && hasConfidence && (
        <DetailModal
          title="Güven Analizi — Tüm Görevler"
          content={allConfidenceFooters}
          color="#3b82f6"
          badge="Confidence"
          onClose={() => setShowThreadConfidence(false)}
        />
      )}
    </div>
  );
}

// ── Project Detail View (markdown) ───────────────────────────────

function ProjectDetailView({
  title,
  content,
  onBack,
    <div className = "flex h-full flex-col bg-white text-[#1a1a1a]" >
      <div className="flex items-center gap-2 border-b border-[#d6d2c2] bg-[#f8f6ee] px-3 py-2">
      style={{ backgroundColor: "#fff", color: "#1a1a1a" }}
    >
          className="rounded p-1 text-[#333]"
          title="Geri"
          aria-label="Proje listesine geri dön"
        style={{ backgroundColor: "#f8f6ee", borderColor: "#d6d2c2" }}
      >
        <button
        <FolderOpen className="h-4 w-4 text-[#b45309]" />
        <span className="truncate text-[13px] font-semibold text-[#003399]">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <FolderOpen className="w-4 h-4" style={{ color: "#b45309" }} />
        <span
          className="text-[13px] font-semibold truncate"
          style={{ color: "#003399" }}
        >
          {title}
        </span>
        <button
          onClick={() =>
            downloadMarkdown(
              `${title.replace(/[^a-zA-Z0-9]/g, "_")}.md`,
              content,
            )
          }
          className="ml-auto rounded p-1.5 text-[#666]"
          title="İndir (.md)"
          aria-label="Markdown olarak indir"
        >
          <Download className="w-4 h-4" />
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <pre className="whitespace-pre-wrap text-[13px] leading-relaxed text-[#333] font-sans">
          {content}
        </pre>
      </div>
    </div>
  );
}

// ── Component ────────────────────────────────────────────────────

export function XpReportsPanel() {
  const [activeFolder, setActiveFolder] = useState<Folder | null>(null);
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [presentations, setPresentations] = useState<PresentationSummary[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // Detail views
  const [detailThread, setDetailThread] = useState<Thread | null>(null);
  const [projectContent, setProjectContent] = useState<string | null>(null);
  const [projectTitle, setProjectTitle] = useState("");
  const [detailPresentation, setDetailPresentation] =
    useState<PresentationDetail | null>(null);

  // Context menu
  const [ctxMenu, setCtxMenu] = useState<ContextMenu | null>(null);
  const ctxRef = useRef<HTMLDivElement>(null);

  // Close context menu on outside click
  useEffect(() => {
    if (!ctxMenu) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        ctxRef.current &&
        document.contains(target) &&
        !ctxRef.current.contains(target)
      ) {
        setCtxMenu(null);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [ctxMenu]);

  useEffect(() => {
    if (!ctxMenu || !ctxRef.current) return;
    ctxRef.current.style.left = `${ctxMenu.x}px`;
    ctxRef.current.style.top = `${ctxMenu.y}px`;
  }, [ctxMenu]);

  // ── Data fetching ──

  const loadThreads = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listThreads(50);
      setThreads(data);
    } catch (err) {
      console.error("[XpReports] threads error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listProjects();
      setProjects(data);
    } catch (err) {
      console.error("[XpReports] projects error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadPresentations = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/presentations/list");
      const data = await res.json();
      setPresentations(data.presentations || []);
    } catch (err) {
      console.error("[XpReports] presentations error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadWorkflows = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/workflow-results");
      const data = await res.json();
      setWorkflows(data.results || []);
    } catch (err) {
      console.error("[XpReports] workflows error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const openFolder = useCallback(
    (folder: Folder) => {
      setActiveFolder(folder);
      setDetailThread(null);
      setProjectContent(null);
      setDetailPresentation(null);
      if (folder === "threads") loadThreads();
      else if (folder === "projects") loadProjects();
      else if (folder === "presentations") loadPresentations();
      else if (folder === "workflows") loadWorkflows();
    },
    [loadThreads, loadProjects, loadPresentations, loadWorkflows],
  );

  // ── Detail view ──

  const openThreadDetail = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const thread = await api.getThread(id);
      setDetailThread(thread);
    } catch (err) {
      console.error("[XpReports] thread detail error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const openProjectDetail = useCallback(async (name: string) => {
    setLoading(true);
    try {
      const data = await api.exportProject(name);
      setProjectTitle(name);
      setProjectContent(data.markdown);
    } catch (err) {
      console.error("[XpReports] project detail error:", err);
      setProjectContent("Yüklenirken hata oluştu.");
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Context menu actions ──

  const handleContextMenu = useCallback(
    (e: React.MouseEvent, type: Folder, id: string, label: string) => {
      e.preventDefault();
      e.stopPropagation();
      setCtxMenu({ x: e.clientX, y: e.clientY, type, id, label });
    },
    [],
  );

  const ctxDownload = useCallback(async () => {
    if (!ctxMenu) return;
    try {
      if (ctxMenu.type === "threads") {
        const thread = await api.getThread(ctxMenu.id);
        const md = buildThreadMarkdown(thread);
        downloadMarkdown(`thread-${ctxMenu.id.slice(0, 8)}.md`, md);
      } else if (ctxMenu.type === "presentations") {
        const res = await fetch(`/api/presentations/${ctxMenu.id}`);
        const data = await res.json();
        const html = generatePresentationHTML(data.presentation);
        const blob = new Blob([html], { type: "text/html;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${ctxMenu.label.replace(/[^a-zA-Z0-9]/g, "_")}.html`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        const data = await api.exportProject(ctxMenu.id);
        downloadMarkdown(`project-${ctxMenu.id}.md`, data.markdown);
      }
    } catch (err) {
      console.error("[XpReports] download error:", err);
    }
    setCtxMenu(null);
  }, [ctxMenu]);

  const ctxDelete = useCallback(async () => {
    if (!ctxMenu) return;
    if (!confirm(`"${ctxMenu.label}" silinsin mi?`)) {
      setCtxMenu(null);
      return;
    }
    try {
      if (ctxMenu.type === "threads") {
        await api.deleteThread(ctxMenu.id);
        setThreads((prev) => prev.filter((t) => t.id !== ctxMenu.id));
        trackBehavior("thread_delete", ctxMenu.id, { label: ctxMenu.label });
      } else if (ctxMenu.type === "presentations") {
        await fetch(`/api/presentations/${ctxMenu.id}`, { method: "DELETE" });
        setPresentations((prev) => prev.filter((p) => p.id !== ctxMenu.id));
      }
    } catch (err) {
      console.error("[XpReports] delete error:", err);
    }
    setCtxMenu(null);
  }, [ctxMenu]);

  const openPresentationDetail = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/presentations/${id}`);
      const data = await res.json();
      setDetailPresentation(data.presentation);
    } catch (err) {
      console.error("[XpReports] presentation detail error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const deletePresentation = useCallback(async (id: string) => {
    try {
      await fetch(`/api/presentations/${id}`, { method: "DELETE" });
      setPresentations((prev) => prev.filter((p) => p.id !== id));
      setDetailPresentation(null);
    } catch (err) {
      console.error("[XpReports] presentation delete error:", err);
    }
  }, []);

  // ── Render: Thread Detail ──
  if (detailThread) {
    return (
      <ThreadDetailView
        thread={detailThread}
        onBack={() => setDetailThread(null)}
      />
    );
  }

  // ── Render: Project Detail ──
  if (projectContent) {
    return (
      <ProjectDetailView
        title={projectTitle}
        content={projectContent}
        onBack={() => setProjectContent(null)}
      />
    );
  }

  // ── Render: Presentation Detail ──
  if (detailPresentation) {
    return (
      <PresentationDetailView
        presentation={detailPresentation}
        onBack={() => setDetailPresentation(null)}
        onDelete={deletePresentation}
      />
    );
  }

  // ── Render: List View ──
  return (
    <div className="flex h-full flex-col bg-white text-[#1a1a1a]">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-[#d6d2c2] bg-[#f8f6ee] px-3 py-2">
        {activeFolder && (
          <button
            onClick={() => {
              setActiveFolder(null);
              setDetailThread(null);
              setProjectContent(null);
            }}
            className="rounded p-1 text-[#333]"
            aria-label="Geri"
            title="Geri"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
        )}
        <FolderOpen className="h-4 w-4 text-[#b45309]" />
        <span className="text-[13px] font-semibold text-[#003399]">
          {activeFolder === "threads"
            ? "Görev Raporları"
            : activeFolder === "projects"
              ? "Proje Raporları"
              : "Raporlar"}
        </span>
        {loading && (
          <Loader2 className="ml-auto h-4 w-4 animate-spin text-[#3b82f6]" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {!activeFolder ? (
          /* Folder selection */
          <div className="p-4 space-y-2">
            <button
              onClick={() => openFolder("threads")}
              className="w-full rounded border border-[#d6d2c2] bg-white p-3 text-left transition-colors hover:bg-[#f0f4ff]"
            >
              <MessageSquare className="h-5 w-5 text-[#3b82f6]" />
              <div>
                <div className="text-[13px] font-medium text-[#1a1a1a]">
                  Görev Raporları
                </div>
                <div className="text-[11px] text-[#666]">
                  Thread geçmişi ve detayları
                </div>
              </div>
              <ChevronRight className="ml-auto h-4 w-4 text-[#aaa]" />
            </button>
            <button
              onClick={() => openFolder("projects")}
              className="w-full rounded border border-[#d6d2c2] bg-white p-3 text-left transition-colors hover:bg-[#fffbeb]"
            >
              <FolderOpen className="h-5 w-5 text-[#d97706]" />
              <div>
                <div className="text-[13px] font-medium text-[#1a1a1a]">
                  Proje Raporları
                </div>
                <div className="text-[11px] text-[#666]">
                  Fikir→Proje dönüşüm raporları
                </div>
              </div>
              <ChevronRight className="ml-auto h-4 w-4 text-[#aaa]" />
            </button>
            <button
              onClick={() => openFolder("presentations")}
              className="w-full rounded border border-[#d6d2c2] bg-white p-3 text-left transition-colors hover:bg-[#f5f3ff]"
            >
              <Presentation className="h-5 w-5 text-[#8b5cf6]" />
              <div>
                <div className="text-[13px] font-medium text-[#1a1a1a]">
                  Sunumlar
                </div>
                <div className="text-[11px] text-[#666]">
                  Oluşturulan sunum arşivi
                </div>
              </div>
              <ChevronRight className="ml-auto h-4 w-4 text-[#aaa]" />
            </button>
            <button
              onClick={() => openFolder("workflows")}
              className="w-full rounded border border-[#d6d2c2] bg-white p-3 text-left transition-colors hover:bg-[#ecfdf5]"
            >
              <Play className="h-5 w-5 text-[#10b981]" />
              <div>
                <div className="text-[13px] font-medium text-[#1a1a1a]">
                  İş Akışları
                </div>
                <div className="text-[11px] text-[#666]">
                  Çalıştırılan workflow sonuçları
                </div>
              </div>
              <ChevronRight className="ml-auto h-4 w-4 text-[#aaa]" />
            </button>
          </div>
        ) : activeFolder === "threads" ? (
          /* Thread list */
          <div>
            {threads.length === 0 && !loading && (
                <div className="p-6 text-center text-[13px] text-[#888]">
                Henüz rapor yok
              </div>
            )}
            {threads.map((t) => (
              <button
                key={t.id}
                onClick={() => openThreadDetail(t.id)}
                onContextMenu={(e) =>
                  handleContextMenu(
                    e,
                    "threads",
                    t.id,
                    t.preview || t.id.slice(0, 8),
                  )
                }
                className="w-full border-b border-[#ece9d8] p-3 text-left transition-colors hover:bg-[#f8f6ee]"
              >
                <FileText className="mt-0.5 h-4 w-4 shrink-0 text-[#3b82f6]" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] text-[#1a1a1a]">
                    {t.preview || t.id}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[11px] text-[#888]">
                    <Clock className="w-3 h-3" />
                    <span>{formatDate(t.created_at)}</span>
                    <span className="text-[#ccc]">•</span>
                    <span>{t.task_count} görev</span>
                    <span className="text-[#ccc]">•</span>
                    <span>{t.event_count} olay</span>
                  </div>
                </div>
                <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-[#ccc]" />
              </button>
            ))}
          </div>
        ) : activeFolder === "projects" ? (
          /* Project list */
          <div>
            {projects.length === 0 && !loading && (
                  <div className="p-6 text-center text-[13px] text-[#888]">
                Henüz proje yok
              </div>
            )}
            {projects.map((p) => (
              <button
                key={p.name}
                onClick={() => openProjectDetail(p.name)}
                onContextMenu={(e) =>
                  handleContextMenu(e, "projects", p.name, p.name)
                }
                className="w-full border-b border-[#ece9d8] p-3 text-left transition-colors hover:bg-[#f8f6ee]"
              >
                <FolderOpen className="mt-0.5 h-4 w-4 shrink-0 text-[#d97706]" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] text-[#1a1a1a]">
                    {p.name}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[11px] text-[#888]">
                    <span>
                      {p.phase_count}/{p.total_phases} faz
                    </span>
                    {p.phases.length > 0 && (
                      <>
                        <span className="text-[#ccc]">•</span>
                        <span className="truncate">{p.phases.join(", ")}</span>
                      </>
                    )}
                  </div>
                </div>
                <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-[#ccc]" />
              </button>
            ))}
          </div>
        ) : activeFolder === "presentations" ? (
          /* Presentations list */
          <div>
            {presentations.length === 0 && !loading && (
                    <div className="p-6 text-center text-[13px] text-[#888]">
                Henüz sunum yok
              </div>
            )}
            {presentations.map((p) => (
              <button
                key={p.id}
                onClick={() => openPresentationDetail(p.id)}
                onContextMenu={(e) =>
                  handleContextMenu(e, "presentations", p.id, p.title)
                }
                className="w-full border-b border-[#ece9d8] p-3 text-left transition-colors hover:bg-[#f8f6ee]"
              >
                <Presentation className="mt-0.5 h-4 w-4 shrink-0 text-[#8b5cf6]" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] text-[#1a1a1a]">
                    {p.title}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[11px] text-[#888]">
                    <span>{p.slide_count} slayt</span>
                    <span className="text-[#ccc]">•</span>
                    <span>{p.palette_name}</span>
                    <span className="text-[#ccc]">•</span>
                    <span>{formatDate(p.created_at)}</span>
                  </div>
                </div>
                <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-[#ccc]" />
              </button>
            ))}
          </div>
        ) : activeFolder === "workflows" ? (
          /* Workflows list */
          <div>
            {workflows.length === 0 && !loading && (
                      <div className="p-6 text-center text-[13px] text-[#888]">
                Henüz iş akışı yok
              </div>
            )}
            {workflows.map((w) => (
              <button
                key={w.id || w.workflow_id}
                onClick={() => {}}
                className="w-full border-b border-[#ece9d8] p-3 text-left transition-colors hover:bg-[#f8f6ee]"
              >
                <Play
                  className={clsx(
                    "mt-0.5 h-4 w-4 shrink-0",
                    w.status === "completed" ? "text-[#10b981]" : "text-[#ef4444]",
                  )}
                />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] text-[#1a1a1a]">
                    {w.workflow_id}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-[11px] text-[#888]">
                    <span
                      className={clsx(
                        "rounded px-1.5 py-0.5",
                        w.status === "completed"
                          ? "bg-[#dcfce7] text-[#166534]"
                          : "bg-[#fee2e2] text-[#991b1b]",
                      )}
                    >
                      {w.status}
                    </span>
                    <span>{w.duration_ms?.toFixed(0)}ms</span>
                    <span className="text-[#ccc]">•</span>
                    <span>{formatDate(w.created_at)}</span>
                  </div>
                </div>
                <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-[#ccc]" />
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {/* Context Menu */}
      {ctxMenu && (
        <div
          ref={ctxRef}
          className="fixed z-[9999] min-w-[160px] rounded border border-[#d6d2c2] bg-white py-1 shadow-xl"
        >
          <button
            onClick={ctxDownload}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-[#333] transition-colors hover:bg-[#f0f4ff]"
          >
            <Download className="h-4 w-4 text-[#3b82f6]" />
            <span>İndir (.md)</span>
          </button>
          {ctxMenu.type === "threads" && (
            <button
              onClick={ctxDelete}
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-[#dc2626] transition-colors hover:bg-[#fef2f2]"
            >
              <Trash2 className="w-4 h-4" />
              <span>Sil</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
