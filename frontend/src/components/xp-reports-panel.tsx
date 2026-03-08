"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ThreadSummary, Thread, Task, AgentEvent } from "@/lib/types";
import {
  ArrowLeft,
  ChevronRight,
  Clock,
  Download,
  FileText,
  FolderOpen,
  Loader2,
  MessageSquare,
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
} from "lucide-react";

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

function downloadMarkdown(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
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
  { bg: string; border: string; text: string; icon: typeof Cpu; label: string }
> = {
  user_message: {
    bg: "#e8f0fe",
    border: "#4285f4",
    text: "#1a56db",
    icon: User,
    label: "Kullanıcı",
  },
  agent_thinking: {
    bg: "#fef9e7",
    border: "#f59e0b",
    text: "#92400e",
    icon: Brain,
    label: "Düşünme",
  },
  agent_response: {
    bg: "#ecfdf5",
    border: "#10b981",
    text: "#065f46",
    icon: CheckCircle2,
    label: "Yanıt",
  },
  agent_start: {
    bg: "#f0f9ff",
    border: "#3b82f6",
    text: "#1e40af",
    icon: Play,
    label: "Başlangıç",
  },
  tool_call: {
    bg: "#eff6ff",
    border: "#6366f1",
    text: "#3730a3",
    icon: Wrench,
    label: "Araç Çağrısı",
  },
  tool_result: {
    bg: "#f5f3ff",
    border: "#8b5cf6",
    text: "#5b21b6",
    icon: Cpu,
    label: "Araç Sonucu",
  },
  routing_decision: {
    bg: "#fdf4ff",
    border: "#d946ef",
    text: "#86198f",
    icon: Zap,
    label: "Yönlendirme",
  },
  pipeline_start: {
    bg: "#f0fdfa",
    border: "#14b8a6",
    text: "#115e59",
    icon: Play,
    label: "Pipeline Başlangıç",
  },
  pipeline_step: {
    bg: "#f0fdfa",
    border: "#14b8a6",
    text: "#115e59",
    icon: BarChart3,
    label: "Pipeline Adım",
  },
  pipeline_complete: {
    bg: "#ecfdf5",
    border: "#10b981",
    text: "#065f46",
    icon: CheckCircle2,
    label: "Pipeline Tamamlandı",
  },
  synthesis: {
    bg: "#fffbeb",
    border: "#f59e0b",
    text: "#78350f",
    icon: Brain,
    label: "Sentez",
  },
  error: {
    bg: "#fef2f2",
    border: "#ef4444",
    text: "#991b1b",
    icon: AlertCircle,
    label: "Hata",
  },
  rag_query: {
    bg: "#f0f9ff",
    border: "#0ea5e9",
    text: "#0c4a6e",
    icon: Search,
    label: "RAG Sorgu",
  },
  evaluation: {
    bg: "#fefce8",
    border: "#eab308",
    text: "#713f12",
    icon: BarChart3,
    label: "Değerlendirme",
  },
};

const DEFAULT_EVENT_STYLE = {
  bg: "#f8f6ee",
  border: "#aca899",
  text: "#333",
  icon: FileText,
  label: "Olay",
};

function getEventStyle(eventType: string) {
  return EVENT_STYLES[eventType] ?? DEFAULT_EVENT_STYLE;
}

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  completed: { bg: "#dcfce7", text: "#166534" },
  running: { bg: "#dbeafe", text: "#1e40af" },
  pending: { bg: "#fef9c3", text: "#854d0e" },
  failed: { bg: "#fee2e2", text: "#991b1b" },
  routing: { bg: "#f3e8ff", text: "#6b21a8" },
  reviewing: { bg: "#e0f2fe", text: "#075985" },
};

// ── Types ────────────────────────────────────────────────────────

type Folder = "threads" | "projects";

interface ProjectSummary {
  name: string;
  phases: string[];
  phase_count: number;
  total_phases: number;
}

interface ContextMenu {
  x: number;
  y: number;
  type: Folder;
  id: string;
  label: string;
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
      style={{ borderLeftColor: style.border, backgroundColor: style.bg }}
      className="border-l-[3px] rounded-r px-3 py-2 mb-2"
    >
      <div className="flex items-center gap-2 mb-1">
        <Icon
          style={{ color: style.border }}
          className="w-3.5 h-3.5 shrink-0"
        />
        <span
          style={{ color: style.text }}
          className="text-[11px] font-semibold"
        >
          {style.label}
        </span>
        {event.agent_role && (
          <span
            className="text-[10px] px-1.5 py-0.5 rounded"
            style={{ backgroundColor: style.border + "18", color: style.text }}
          >
            {event.agent_role}
          </span>
        )}
        <span className="text-[10px] ml-auto" style={{ color: "#888" }}>
          {new Date(event.timestamp).toLocaleTimeString("tr-TR")}
        </span>
      </div>
      <div
        style={{ color: style.text }}
        className="text-[12px] leading-relaxed whitespace-pre-wrap break-words"
      >
        {displayContent}
      </div>
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-[10px] mt-1 underline"
          style={{ color: style.border }}
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
  const statusStyle = STATUS_COLORS[task.status] ?? {
    bg: "#f3f4f6",
    text: "#374151",
  };

  return (
    <div
      className="rounded border mb-3"
      style={{ borderColor: "#d6d2c2", backgroundColor: "#fff" }}
    >
      {/* Task header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-2 px-3 py-2.5 text-left"
        style={{ backgroundColor: "#f8f6ee" }}
      >
        <span
          className="text-[11px] font-bold shrink-0"
          style={{ color: "#003399" }}
        >
          #{index + 1}
        </span>
        <div className="flex-1 min-w-0">
          <div
            className="text-[13px] font-medium leading-snug"
            style={{ color: "#1a1a1a" }}
          >
            {task.user_input}
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-1.5">
            <span
              className="text-[10px] px-2 py-0.5 rounded font-medium"
              style={{
                backgroundColor: statusStyle.bg,
                color: statusStyle.text,
              }}
            >
              {task.status}
            </span>
            <span className="text-[10px]" style={{ color: "#666" }}>
              {task.pipeline_type}
            </span>
            <span className="text-[10px]" style={{ color: "#666" }}>
              {task.total_tokens.toLocaleString()} token
            </span>
            <span className="text-[10px]" style={{ color: "#666" }}>
              {(task.total_latency_ms / 1000).toFixed(1)}s
            </span>
          </div>
        </div>
        <svg
          className={`w-4 h-4 shrink-0 mt-1 transition-transform ${expanded ? "rotate-180" : ""}`}
          style={{ color: "#888" }}
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
        <div className="px-3 py-2 border-t" style={{ borderColor: "#d6d2c2" }}>
          {/* Sub-tasks */}
          {task.sub_tasks.length > 0 && (
            <div className="mb-3">
              <div
                className="text-[11px] font-semibold mb-1.5"
                style={{ color: "#003399" }}
              >
                Alt Görevler ({task.sub_tasks.length})
              </div>
              {task.sub_tasks.map((st) => {
                const stStatus = STATUS_COLORS[st.status] ?? {
                  bg: "#f3f4f6",
                  text: "#374151",
                };
                return (
                  <div
                    key={st.id}
                    className="flex items-start gap-2 py-1 text-[11px]"
                    style={{ borderBottom: "1px solid #ece9d8" }}
                  >
                    <span
                      className="px-1.5 py-0.5 rounded text-[9px] font-medium shrink-0"
                      style={{
                        backgroundColor: stStatus.bg,
                        color: stStatus.text,
                      }}
                    >
                      {st.status}
                    </span>
                    <span style={{ color: "#333" }} className="flex-1">
                      {st.description}
                    </span>
                    <span
                      style={{ color: "#888" }}
                      className="shrink-0 text-[10px]"
                    >
                      {st.assigned_agent}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Final result */}
          {task.final_result && (
            <div
              className="rounded p-2.5"
              style={{
                backgroundColor: "#ecfdf5",
                border: "1px solid #a7f3d0",
              }}
            >
              <div
                className="text-[11px] font-semibold mb-1"
                style={{ color: "#065f46" }}
              >
                Sonuç
              </div>
              <div
                className="text-[12px] leading-relaxed whitespace-pre-wrap"
                style={{ color: "#064e3b" }}
              >
                {task.final_result}
              </div>
            </div>
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
  const totalTokens = thread.tasks.reduce((s, t) => s + t.total_tokens, 0);
  const totalLatency = thread.tasks.reduce((s, t) => s + t.total_latency_ms, 0);
  const lastStatus = thread.tasks.length
    ? thread.tasks[thread.tasks.length - 1].status
    : "boş";

  return (
    <div
      className="flex h-full"
      style={{ backgroundColor: "#fff", color: "#1a1a1a" }}
    >
      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header bar */}
        <div
          className="flex items-center gap-2 px-3 py-2 border-b"
          style={{ backgroundColor: "#f8f6ee", borderColor: "#d6d2c2" }}
        >
          <button
            onClick={onBack}
            className="p-1 rounded"
            style={{ color: "#333" }}
            aria-label="Geri"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <FileText className="w-4 h-4" style={{ color: "#003399" }} />
          <span
            className="text-[13px] font-semibold truncate"
            style={{ color: "#003399" }}
          >
            Thread: {thread.id.slice(0, 8)}...
          </span>
          <button
            onClick={() =>
              downloadMarkdown(
                `thread-${thread.id.slice(0, 8)}.md`,
                buildThreadMarkdown(thread),
              )
            }
            className="ml-auto p-1.5 rounded"
            title="İndir (.md)"
            aria-label="Markdown olarak indir"
            style={{ color: "#666" }}
          >
            <Download className="w-4 h-4" />
          </button>
        </div>

        {/* Stats bar */}
        <div
          className="flex flex-wrap gap-3 px-3 py-2 border-b text-[11px]"
          style={{ backgroundColor: "#faf8f0", borderColor: "#ece9d8" }}
        >
          <span style={{ color: "#555" }}>
            <Clock
              className="w-3 h-3 inline mr-1"
              style={{ verticalAlign: "-2px" }}
            />
            {formatDate(thread.created_at)}
          </span>
          <span style={{ color: "#555" }}>{thread.tasks.length} görev</span>
          <span style={{ color: "#555" }}>{thread.events.length} olay</span>
          <span style={{ color: "#555" }}>
            {totalTokens.toLocaleString()} token
          </span>
          <span style={{ color: "#555" }}>
            {(totalLatency / 1000).toFixed(1)}s
          </span>
          <span
            className="px-1.5 py-0.5 rounded text-[10px] font-medium"
            style={{
              backgroundColor: (STATUS_COLORS[lastStatus] ?? { bg: "#f3f4f6" })
                .bg,
              color: (STATUS_COLORS[lastStatus] ?? { text: "#374151" }).text,
            }}
          >
            {lastStatus}
          </span>
        </div>

        {/* Tabs */}
        <div
          className="flex border-b"
          style={{ borderColor: "#d6d2c2", backgroundColor: "#f8f6ee" }}
        >
          <button
            onClick={() => setActiveTab("tasks")}
            className="px-4 py-2 text-[12px] font-medium border-b-2 transition-colors"
            style={{
              borderColor: activeTab === "tasks" ? "#003399" : "transparent",
              color: activeTab === "tasks" ? "#003399" : "#666",
              backgroundColor: activeTab === "tasks" ? "#fff" : "transparent",
            }}
          >
            Görevler ({thread.tasks.length})
          </button>
          <button
            onClick={() => setActiveTab("events")}
            className="px-4 py-2 text-[12px] font-medium border-b-2 transition-colors"
            style={{
              borderColor: activeTab === "events" ? "#003399" : "transparent",
              color: activeTab === "events" ? "#003399" : "#666",
              backgroundColor: activeTab === "events" ? "#fff" : "transparent",
            }}
          >
            Olaylar ({thread.events.length})
          </button>
        </div>

        {/* Tab content */}
        <div
          className="flex-1 overflow-auto p-3"
          style={{ backgroundColor: "#fff" }}
        >
          {activeTab === "tasks" ? (
            thread.tasks.length === 0 ? (
              <div
                className="text-center py-8 text-[12px]"
                style={{ color: "#888" }}
              >
                Bu thread&apos;de görev yok
              </div>
            ) : (
              thread.tasks.map((t, i) => (
                <TaskCard key={t.id} task={t} index={i} />
              ))
            )
          ) : thread.events.length === 0 ? (
            <div
              className="text-center py-8 text-[12px]"
              style={{ color: "#888" }}
            >
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
          className="w-52 border-l flex flex-col"
          style={{ backgroundColor: "#f8f6ee", borderColor: "#d6d2c2" }}
        >
          <div
            className="px-3 py-2 border-b"
            style={{ borderColor: "#d6d2c2" }}
          >
            <span
              className="text-[11px] font-semibold uppercase tracking-wider"
              style={{ color: "#003399" }}
            >
              Agent Metrikleri
            </span>
          </div>
          <div className="flex-1 overflow-auto p-2 space-y-2">
            {Object.entries(thread.agent_metrics).map(([role, m]) => (
              <div
                key={role}
                className="rounded p-2"
                style={{ backgroundColor: "#fff", border: "1px solid #ece9d8" }}
              >
                <div
                  className="text-[11px] font-semibold mb-1"
                  style={{ color: "#003399" }}
                >
                  {role}
                </div>
                <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[10px]">
                  <span style={{ color: "#888" }}>Çağrı</span>
                  <span style={{ color: "#333" }} className="text-right">
                    {m.total_calls}
                  </span>
                  <span style={{ color: "#888" }}>Token</span>
                  <span style={{ color: "#333" }} className="text-right">
                    {m.total_tokens.toLocaleString()}
                  </span>
                  <span style={{ color: "#888" }}>Başarı</span>
                  <span style={{ color: "#333" }} className="text-right">
                    {m.success_count}/{m.total_calls}
                  </span>
                  <span style={{ color: "#888" }}>Hata</span>
                  <span
                    style={{ color: m.error_count > 0 ? "#dc2626" : "#333" }}
                    className="text-right"
                  >
                    {m.error_count}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Project Detail View (markdown) ───────────────────────────────

function ProjectDetailView({
  title,
  content,
  onBack,
}: {
  title: string;
  content: string;
  onBack: () => void;
}) {
  return (
    <div
      className="flex flex-col h-full"
      style={{ backgroundColor: "#fff", color: "#1a1a1a" }}
    >
      <div
        className="flex items-center gap-2 px-3 py-2 border-b"
        style={{ backgroundColor: "#f8f6ee", borderColor: "#d6d2c2" }}
      >
        <button
          onClick={onBack}
          className="p-1 rounded"
          style={{ color: "#333" }}
          aria-label="Geri"
        >
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
          className="ml-auto p-1.5 rounded"
          title="İndir (.md)"
          aria-label="Markdown olarak indir"
          style={{ color: "#666" }}
        >
          <Download className="w-4 h-4" />
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <pre
          className="whitespace-pre-wrap text-[13px] leading-relaxed"
          style={{ color: "#333", fontFamily: "'Roboto', sans-serif" }}
        >
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
  const [loading, setLoading] = useState(false);

  // Detail views
  const [detailThread, setDetailThread] = useState<Thread | null>(null);
  const [projectContent, setProjectContent] = useState<string | null>(null);
  const [projectTitle, setProjectTitle] = useState("");

  // Context menu
  const [ctxMenu, setCtxMenu] = useState<ContextMenu | null>(null);
  const ctxRef = useRef<HTMLDivElement>(null);

  // Close context menu on outside click
  useEffect(() => {
    if (!ctxMenu) return;
    const handler = (e: MouseEvent) => {
      if (ctxRef.current && !ctxRef.current.contains(e.target as Node)) {
        setCtxMenu(null);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
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

  const openFolder = useCallback(
    (folder: Folder) => {
      setActiveFolder(folder);
      setDetailThread(null);
      setProjectContent(null);
      if (folder === "threads") loadThreads();
      else loadProjects();
    },
    [loadThreads, loadProjects],
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
      }
    } catch (err) {
      console.error("[XpReports] delete error:", err);
    }
    setCtxMenu(null);
  }, [ctxMenu]);

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

  // ── Render: List View ──
  return (
    <div
      className="flex flex-col h-full"
      style={{ backgroundColor: "#fff", color: "#1a1a1a" }}
    >
      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 border-b"
        style={{ backgroundColor: "#f8f6ee", borderColor: "#d6d2c2" }}
      >
        {activeFolder && (
          <button
            onClick={() => {
              setActiveFolder(null);
              setDetailThread(null);
              setProjectContent(null);
            }}
            className="p-1 rounded"
            style={{ color: "#333" }}
            aria-label="Geri"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
        )}
        <FolderOpen className="w-4 h-4" style={{ color: "#b45309" }} />
        <span
          className="text-[13px] font-semibold"
          style={{ color: "#003399" }}
        >
          {activeFolder === "threads"
            ? "Görev Raporları"
            : activeFolder === "projects"
              ? "Proje Raporları"
              : "Raporlar"}
        </span>
        {loading && (
          <Loader2
            className="w-4 h-4 animate-spin ml-auto"
            style={{ color: "#3b82f6" }}
          />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {!activeFolder ? (
          /* Folder selection */
          <div className="p-4 space-y-2">
            <button
              onClick={() => openFolder("threads")}
              className="w-full flex items-center gap-3 p-3 rounded border text-left transition-colors"
              style={{ borderColor: "#d6d2c2", backgroundColor: "#fff" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "#f0f4ff";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "#fff";
              }}
            >
              <MessageSquare className="w-5 h-5" style={{ color: "#3b82f6" }} />
              <div>
                <div
                  className="text-[13px] font-medium"
                  style={{ color: "#1a1a1a" }}
                >
                  Görev Raporları
                </div>
                <div className="text-[11px]" style={{ color: "#666" }}>
                  Thread geçmişi ve detayları
                </div>
              </div>
              <ChevronRight
                className="w-4 h-4 ml-auto"
                style={{ color: "#aaa" }}
              />
            </button>
            <button
              onClick={() => openFolder("projects")}
              className="w-full flex items-center gap-3 p-3 rounded border text-left transition-colors"
              style={{ borderColor: "#d6d2c2", backgroundColor: "#fff" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "#fffbeb";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "#fff";
              }}
            >
              <FolderOpen className="w-5 h-5" style={{ color: "#d97706" }} />
              <div>
                <div
                  className="text-[13px] font-medium"
                  style={{ color: "#1a1a1a" }}
                >
                  Proje Raporları
                </div>
                <div className="text-[11px]" style={{ color: "#666" }}>
                  Fikir→Proje dönüşüm raporları
                </div>
              </div>
              <ChevronRight
                className="w-4 h-4 ml-auto"
                style={{ color: "#aaa" }}
              />
            </button>
          </div>
        ) : activeFolder === "threads" ? (
          /* Thread list */
          <div>
            {threads.length === 0 && !loading && (
              <div
                className="p-6 text-center text-[13px]"
                style={{ color: "#888" }}
              >
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
                className="w-full flex items-start gap-3 p-3 text-left transition-colors border-b"
                style={{ borderColor: "#ece9d8" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = "#f8f6ee";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = "transparent";
                }}
              >
                <FileText
                  className="w-4 h-4 mt-0.5 shrink-0"
                  style={{ color: "#3b82f6" }}
                />
                <div className="min-w-0 flex-1">
                  <div
                    className="text-[13px] truncate"
                    style={{ color: "#1a1a1a" }}
                  >
                    {t.preview || t.id}
                  </div>
                  <div
                    className="flex items-center gap-2 mt-1 text-[11px]"
                    style={{ color: "#888" }}
                  >
                    <Clock className="w-3 h-3" />
                    <span>{formatDate(t.created_at)}</span>
                    <span style={{ color: "#ccc" }}>•</span>
                    <span>{t.task_count} görev</span>
                    <span style={{ color: "#ccc" }}>•</span>
                    <span>{t.event_count} olay</span>
                  </div>
                </div>
                <ChevronRight
                  className="w-4 h-4 mt-1 shrink-0"
                  style={{ color: "#ccc" }}
                />
              </button>
            ))}
          </div>
        ) : (
          /* Project list */
          <div>
            {projects.length === 0 && !loading && (
              <div
                className="p-6 text-center text-[13px]"
                style={{ color: "#888" }}
              >
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
                className="w-full flex items-start gap-3 p-3 text-left transition-colors border-b"
                style={{ borderColor: "#ece9d8" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = "#f8f6ee";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = "transparent";
                }}
              >
                <FolderOpen
                  className="w-4 h-4 mt-0.5 shrink-0"
                  style={{ color: "#d97706" }}
                />
                <div className="min-w-0 flex-1">
                  <div
                    className="text-[13px] truncate"
                    style={{ color: "#1a1a1a" }}
                  >
                    {p.name}
                  </div>
                  <div
                    className="flex items-center gap-2 mt-1 text-[11px]"
                    style={{ color: "#888" }}
                  >
                    <span>
                      {p.phase_count}/{p.total_phases} faz
                    </span>
                    {p.phases.length > 0 && (
                      <>
                        <span style={{ color: "#ccc" }}>•</span>
                        <span className="truncate">{p.phases.join(", ")}</span>
                      </>
                    )}
                  </div>
                </div>
                <ChevronRight
                  className="w-4 h-4 mt-1 shrink-0"
                  style={{ color: "#ccc" }}
                />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Context Menu */}
      {ctxMenu && (
        <div
          ref={ctxRef}
          className="fixed z-[9999] rounded shadow-xl py-1 min-w-[160px]"
          style={{
            left: ctxMenu.x,
            top: ctxMenu.y,
            backgroundColor: "#fff",
            border: "1px solid #d6d2c2",
          }}
        >
          <button
            onClick={ctxDownload}
            className="w-full flex items-center gap-2 px-3 py-2 text-[12px] text-left transition-colors"
            style={{ color: "#333" }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = "#f0f4ff";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "transparent";
            }}
          >
            <Download className="w-4 h-4" style={{ color: "#3b82f6" }} />
            <span>İndir (.md)</span>
          </button>
          {ctxMenu.type === "threads" && (
            <button
              onClick={ctxDelete}
              className="w-full flex items-center gap-2 px-3 py-2 text-[12px] text-left transition-colors"
              style={{ color: "#dc2626" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "#fef2f2";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "transparent";
              }}
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
