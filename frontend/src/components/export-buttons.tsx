"use client";

import { useCallback, useEffect, useState } from "react";
import { api, fetchBlob } from "@/lib/api";
import type { Task } from "@/lib/types";
import {
  FileText,
  FileDown,
  FileJson,
  Loader2,
  Palette,
  Code2,
} from "lucide-react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface Props {
  result: string;
  task?: Task | null;
}

export function ExportButtons({ result, task }: Props) {
  const [projects, setProjects] = useState<
    {
      name: string;
      phases: string[];
      phase_count: number;
      total_phases: number;
    }[]
  >([]);
  const [presentations, setPresentations] = useState<
    { name: string; filename: string; size_kb: number }[]
  >([]);
  const [exporting, setExporting] = useState<string | null>(null);

  useEffect(() => {
    if (task?.pipeline_type === "idea_to_project") {
      api
        .listProjects()
        .then(setProjects)
        .catch(() => {});
    }
    if (
      result &&
      (result.includes("Sunum Hazır") || result.includes(".pptx"))
    ) {
      api
        .listPresentations()
        .then(setPresentations)
        .catch(() => {});
    }
  }, [task?.pipeline_type, task?.status, result]);

  // ── MD download (client-side) ──
  const exportMd = useCallback(() => {
    const lines = ["# Multi-Agent Result\n"];
    if (task) {
      lines.push(`**Query:** ${task.user_input}\n`);
      lines.push(`**Pipeline:** ${task.pipeline_type}\n`);
      if (task.sub_tasks?.length) {
        lines.push(
          `**Agents:** ${task.sub_tasks.map((s) => s.assigned_agent).join(", ")}\n`,
        );
      }
      lines.push("---\n");
    }
    lines.push(result);
    download(lines.join("\n"), "result.md", "text/markdown");
  }, [result, task]);

  // ── Project report MD download ──
  const exportProjectMd = useCallback(async (projectName: string) => {
    setExporting("project-md");
    try {
      const data = await api.exportProject(projectName);
      const safeName = projectName.replace(/[^a-zA-Z0-9_-]/g, "_");
      download(data.markdown, `${safeName}_rapor.md`, "text/markdown");
    } catch (e) {
      console.error("Project MD export failed:", e);
    } finally {
      setExporting(null);
    }
  }, []);

  // ── Project report PDF download ──
  const exportProjectPdf = useCallback(async (projectName: string) => {
    setExporting("project-pdf");
    try {
      const blob = await fetchBlob(
        `/api/projects/${encodeURIComponent(projectName)}/export/pdf`,
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${projectName.slice(0, 40)}_rapor.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Project PDF export failed:", e);
    } finally {
      setExporting(null);
    }
  }, []);

  // ── Generic PDF download (any result) ──
  const exportPdf = useCallback(async () => {
    setExporting("pdf");
    try {
      if (
        result &&
        (result.includes("Sunum Hazır") || result.includes(".pptx")) &&
        presentations.length > 0
      ) {
        const p = presentations[0];
        try {
          const blob = await fetchBlob(
            `/api/presentations/${encodeURIComponent(p.filename)}/pdf`,
          );
          const blobUrl = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = blobUrl;
          a.download = p.filename.replace(".pptx", ".pdf");
          a.click();
          URL.revokeObjectURL(blobUrl);
          setExporting(null);
          return;
        } catch {
          /* fall through to generic PDF export */
        }
      }

      const title = task?.user_input?.slice(0, 60) || "Rapor";
      const blob = await fetchBlob(`/api/export/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ markdown: result, title }),
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "rapor.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("PDF export failed:", e);
    } finally {
      setExporting(null);
    }
  }, [result, task, presentations]);

  // ── JSON download ──
  const exportJson = useCallback(() => {
    const data = {
      result,
      task: task
        ? {
            id: task.id,
            query: task.user_input,
            pipeline: task.pipeline_type,
            status: task.status,
            total_tokens: task.total_tokens,
          }
        : null,
      exported_at: new Date().toISOString(),
    };
    download(JSON.stringify(data, null, 2), "result.json", "application/json");
  }, [result, task]);

  // ── HTML download ──
  const exportHtml = useCallback(async () => {
    setExporting("html");
    try {
      const title = task?.user_input?.slice(0, 60) || "Rapor";
      const blob = await fetchBlob(`/api/export/html`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ markdown: result, title }),
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "rapor.html";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("HTML export failed:", e);
    } finally {
      setExporting(null);
    }
  }, [result, task]);

  if (!result || result.trim().length < 10) return null;

  const isIdeaProject = task?.pipeline_type === "idea_to_project";

  return (
    <div
      className="flex flex-wrap items-center gap-2 lg:gap-3 px-3 lg:px-4 py-2 border-t border-border"
      role="toolbar"
      aria-label="Dışa aktarma seçenekleri"
    >
      {/* Idea-to-Project: prominent project export buttons */}
      {isIdeaProject &&
        projects.length > 0 &&
        projects.slice(-1).map((p) => (
          <div key={p.name} className="flex gap-1.5">
            <button
              onClick={() => exportProjectMd(p.name)}
              disabled={exporting !== null}
              aria-label={`${p.name} projesini Markdown olarak indir`}
              className="px-3 lg:px-4 min-h-[44px] rounded-lg bg-emerald-900/40 text-[11px] font-semibold text-emerald-300 hover:text-emerald-100 border border-emerald-700/50 hover:border-emerald-500 transition-colors flex items-center gap-1 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {exporting === "project-md" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}{" "}
              Proje MD
              <span className="text-[9px] text-emerald-500">
                {p.phase_count}/{p.total_phases}
              </span>
            </button>
            <button
              onClick={() => exportProjectPdf(p.name)}
              disabled={exporting !== null}
              aria-label={`${p.name} projesini PDF olarak indir`}
              className="px-3 lg:px-4 min-h-[44px] rounded-lg bg-blue-900/40 text-[11px] font-semibold text-blue-300 hover:text-blue-100 border border-blue-700/50 hover:border-blue-500 transition-colors flex items-center gap-1 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {exporting === "project-pdf" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileDown className="w-4 h-4" />
              )}{" "}
              Proje PDF
            </button>
          </div>
        ))}

      {/* Standard exports */}
      <ExportBtn
        icon={<FileText className="w-4 h-4" />}
        label="MD"
        ariaLabel="Markdown olarak dışa aktar"
        onClick={exportMd}
        disabled={exporting !== null}
      />
      <ExportBtn
        icon={
          exporting === "pdf" ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <FileDown className="w-4 h-4" />
          )
        }
        label={exporting === "pdf" ? "PDF..." : "PDF"}
        ariaLabel="PDF olarak dışa aktar"
        onClick={exportPdf}
        disabled={exporting !== null}
      />
      <ExportBtn
        icon={<FileJson className="w-4 h-4" />}
        label="JSON"
        ariaLabel="JSON olarak dışa aktar"
        onClick={exportJson}
        disabled={exporting !== null}
      />
      <ExportBtn
        icon={<Code2 className="w-4 h-4" />}
        label="HTML"
        ariaLabel="HTML raporu olarak dışa aktar"
        onClick={exportHtml}
        disabled={exporting !== null}
      />

      {/* Presentation downloads */}
      {presentations.length > 0 &&
        presentations.map((p) => (
          <div key={p.filename} className="flex gap-1.5">
            <a
              href={`${BASE}/api/presentations/${encodeURIComponent(p.filename)}/download`}
              download={p.filename}
              aria-label={`${p.filename} PPTX sunumunu indir`}
              className="px-3 lg:px-4 min-h-[44px] rounded-lg bg-orange-900/40 text-[11px] font-semibold text-orange-300 hover:text-orange-100 border border-orange-700/50 hover:border-orange-500 transition-colors flex items-center gap-1 no-underline cursor-pointer"
            >
              <Palette className="w-4 h-4" /> PPTX
              <span className="text-[9px] text-orange-500">{p.size_kb}KB</span>
            </a>
            <a
              href={`${BASE}/api/presentations/${encodeURIComponent(p.filename)}/pdf`}
              download={p.filename.replace(".pptx", ".pdf")}
              aria-label={`${p.filename} sunumunu PDF olarak indir`}
              className="px-3 lg:px-4 min-h-[44px] rounded-lg bg-red-900/40 text-[11px] font-semibold text-red-300 hover:text-red-100 border border-red-700/50 hover:border-red-500 transition-colors flex items-center gap-1 no-underline cursor-pointer"
            >
              <FileDown className="w-4 h-4" /> PDF
            </a>
          </div>
        ))}
    </div>
  );
}

function ExportBtn({
  icon,
  label,
  ariaLabel,
  onClick,
  disabled,
}: {
  icon: React.ReactNode;
  label: string;
  ariaLabel: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      className="px-3 lg:px-4 min-h-[44px] rounded-lg bg-surface-overlay text-[11px] text-slate-400 hover:text-slate-200 border border-border hover:border-slate-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 cursor-pointer"
    >
      {icon} {label}
    </button>
  );
}

function download(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
