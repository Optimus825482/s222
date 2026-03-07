"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ThreadSummary, Thread } from "@/lib/types";
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

// ── Component ────────────────────────────────────────────────────

export function XpReportsPanel() {
  const [activeFolder, setActiveFolder] = useState<Folder | null>(null);
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(false);

  // Detail view
  const [detailContent, setDetailContent] = useState<string | null>(null);
  const [detailTitle, setDetailTitle] = useState("");
  const [detailMeta, setDetailMeta] = useState<Record<string, string>>({});

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
      setDetailContent(null);
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
      const md = buildThreadMarkdown(thread);
      setDetailTitle(`Thread: ${id.slice(0, 8)}...`);
      setDetailContent(md);
      setDetailMeta({
        ID: id,
        Tarih: formatDate(thread.created_at),
        "Görev Sayısı": String(thread.tasks.length),
        "Olay Sayısı": String(thread.events.length),
        "Toplam Token": String(
          thread.tasks.reduce((s, t) => s + t.total_tokens, 0),
        ),
        Durum: thread.tasks.length
          ? thread.tasks[thread.tasks.length - 1].status
          : "boş",
      });
    } catch (err) {
      console.error("[XpReports] thread detail error:", err);
      setDetailContent("Yüklenirken hata oluştu.");
      setDetailMeta({});
    } finally {
      setLoading(false);
    }
  }, []);

  const openProjectDetail = useCallback(async (name: string) => {
    setLoading(true);
    try {
      const data = await api.exportProject(name);
      setDetailTitle(name);
      setDetailContent(data.markdown);
      setDetailMeta({
        Proje: name,
        "Faz Sayısı": "—",
      });
    } catch (err) {
      console.error("[XpReports] project detail error:", err);
      setDetailContent("Yüklenirken hata oluştu.");
      setDetailMeta({});
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
      // Projects don't have a delete API — just close menu
    } catch (err) {
      console.error("[XpReports] delete error:", err);
    }
    setCtxMenu(null);
  }, [ctxMenu]);

  // ── Detail View (with right sidebar) ──

  if (detailContent) {
    return (
      <div className="flex h-full bg-white text-slate-800">
        {/* Main content */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex items-center gap-2 px-3 py-2 border-b bg-slate-50">
            <button
              onClick={() => setDetailContent(null)}
              className="p-1 rounded hover:bg-slate-200 transition-colors"
              aria-label="Geri"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <FileText className="w-4 h-4 text-blue-600" />
            <span className="text-sm font-medium truncate">{detailTitle}</span>
            <button
              onClick={() =>
                downloadMarkdown(
                  `${detailTitle.replace(/[^a-zA-Z0-9]/g, "_")}.md`,
                  detailContent,
                )
              }
              className="ml-auto p-1.5 rounded hover:bg-slate-200 transition-colors"
              title="İndir (.md)"
              aria-label="Markdown olarak indir"
            >
              <Download className="w-4 h-4 text-slate-500" />
            </button>
          </div>
          <div className="flex-1 overflow-auto p-4">
            <pre className="whitespace-pre-wrap text-xs leading-relaxed font-mono text-slate-700">
              {detailContent}
            </pre>
          </div>
        </div>

        {/* Right sidebar — metadata */}
        {Object.keys(detailMeta).length > 0 && (
          <div className="w-56 border-l bg-slate-50 flex flex-col">
            <div className="px-3 py-2 border-b">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Detaylar
              </span>
            </div>
            <div className="flex-1 overflow-auto p-3 space-y-3">
              {Object.entries(detailMeta).map(([key, val]) => (
                <div key={key}>
                  <div className="text-[10px] font-medium text-slate-400 uppercase">
                    {key}
                  </div>
                  <div className="text-xs text-slate-700 mt-0.5 break-all">
                    {val}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── List View ──

  return (
    <div className="flex flex-col h-full bg-white text-slate-800">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b bg-slate-50">
        {activeFolder && (
          <button
            onClick={() => {
              setActiveFolder(null);
              setDetailContent(null);
            }}
            className="p-1 rounded hover:bg-slate-200 transition-colors"
            aria-label="Geri"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
        )}
        <FolderOpen className="w-4 h-4 text-amber-600" />
        <span className="text-sm font-medium">
          {activeFolder === "threads"
            ? "Görev Raporları"
            : activeFolder === "projects"
              ? "Proje Raporları"
              : "Raporlar"}
        </span>
        {loading && (
          <Loader2 className="w-4 h-4 animate-spin text-blue-500 ml-auto" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {!activeFolder ? (
          /* Folder selection */
          <div className="p-4 space-y-2">
            <button
              onClick={() => openFolder("threads")}
              className="w-full flex items-center gap-3 p-3 rounded-lg border hover:bg-blue-50 hover:border-blue-200 transition-colors text-left"
            >
              <MessageSquare className="w-5 h-5 text-blue-500" />
              <div>
                <div className="text-sm font-medium">Görev Raporları</div>
                <div className="text-xs text-slate-500">
                  Thread geçmişi ve detayları
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-400 ml-auto" />
            </button>
            <button
              onClick={() => openFolder("projects")}
              className="w-full flex items-center gap-3 p-3 rounded-lg border hover:bg-amber-50 hover:border-amber-200 transition-colors text-left"
            >
              <FolderOpen className="w-5 h-5 text-amber-500" />
              <div>
                <div className="text-sm font-medium">Proje Raporları</div>
                <div className="text-xs text-slate-500">
                  Fikir→Proje dönüşüm raporları
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-400 ml-auto" />
            </button>
          </div>
        ) : activeFolder === "threads" ? (
          /* Thread list */
          <div className="divide-y">
            {threads.length === 0 && !loading && (
              <div className="p-6 text-center text-sm text-slate-400">
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
                className="w-full flex items-start gap-3 p-3 hover:bg-slate-50 transition-colors text-left"
              >
                <FileText className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm truncate">{t.preview || t.id}</div>
                  <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-400">
                    <Clock className="w-3 h-3" />
                    <span>{formatDate(t.created_at)}</span>
                    <span className="text-slate-300">•</span>
                    <span>{t.task_count} görev</span>
                    <span className="text-slate-300">•</span>
                    <span>{t.event_count} olay</span>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-300 mt-1 shrink-0" />
              </button>
            ))}
          </div>
        ) : (
          /* Project list */
          <div className="divide-y">
            {projects.length === 0 && !loading && (
              <div className="p-6 text-center text-sm text-slate-400">
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
                className="w-full flex items-start gap-3 p-3 hover:bg-slate-50 transition-colors text-left"
              >
                <FolderOpen className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm truncate">{p.name}</div>
                  <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-400">
                    <span>
                      {p.phase_count}/{p.total_phases} faz
                    </span>
                    {p.phases.length > 0 && (
                      <>
                        <span className="text-slate-300">•</span>
                        <span className="truncate">{p.phases.join(", ")}</span>
                      </>
                    )}
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-300 mt-1 shrink-0" />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Context Menu */}
      {ctxMenu && (
        <div
          ref={ctxRef}
          className="fixed z-[9999] bg-white border border-slate-200 rounded-lg shadow-xl py-1 min-w-[160px]"
          style={{ left: ctxMenu.x, top: ctxMenu.y }}
        >
          <button
            onClick={ctxDownload}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-slate-100 transition-colors text-left"
          >
            <Download className="w-4 h-4 text-blue-500" />
            <span>İndir (.md)</span>
          </button>
          {ctxMenu.type === "threads" && (
            <button
              onClick={ctxDelete}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-red-50 text-red-600 transition-colors text-left"
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
