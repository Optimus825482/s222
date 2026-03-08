"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import {
  Copy,
  Download,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Minimize2,
  Code,
  Eye,
} from "lucide-react";

/* ── Types ─────────────────────────────────────────────────────── */

export interface Artifact {
  id: string;
  type: "html" | "svg" | "mermaid" | "csv";
  content: string;
  label?: string;
}

type TabId = "preview" | "source";

/* ── Detection ─────────────────────────────────────────────────── */

const FENCE_RE = /```(html|svg|mermaid|csv)\s*\n([\s\S]*?)```/gi;

const INLINE_SVG_RE = /<svg[\s\S]*?<\/svg>/gi;

let _counter = 0;
function uid(): string {
  return `art-${Date.now().toString(36)}-${(++_counter).toString(36)}`;
}

/**
 * Scan raw markdown/text for renderable artifact blocks.
 * Returns an array of Artifact objects for each detected block.
 */
export function detectArtifacts(content: string): Artifact[] {
  const artifacts: Artifact[] = [];
  const consumed = new Set<string>();

  // Fenced code blocks: ```html, ```svg, ```mermaid, ```csv
  let m: RegExpExecArray | null;
  FENCE_RE.lastIndex = 0;
  while ((m = FENCE_RE.exec(content)) !== null) {
    const type = m[1].toLowerCase() as Artifact["type"];
    const body = m[2].trim();
    if (!body) continue;
    artifacts.push({ id: uid(), type, content: body });
    consumed.add(body);
  }

  // Inline <svg> tags not already captured by fenced blocks
  INLINE_SVG_RE.lastIndex = 0;
  while ((m = INLINE_SVG_RE.exec(content)) !== null) {
    const body = m[0].trim();
    if (consumed.has(body)) continue;
    artifacts.push({ id: uid(), type: "svg", content: body });
  }

  return artifacts;
}

/* ── Helpers ────────────────────────────────────────────────────── */

const TYPE_META: Record<
  Artifact["type"],
  { label: string; ext: string; mime: string; color: string }
> = {
  html: {
    label: "HTML",
    ext: "html",
    mime: "text/html",
    color: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  },
  svg: {
    label: "SVG",
    ext: "svg",
    mime: "image/svg+xml",
    color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  },
  mermaid: {
    label: "Mermaid",
    ext: "mmd",
    mime: "text/plain",
    color: "bg-pink-500/15 text-pink-400 border-pink-500/30",
  },
  csv: {
    label: "CSV",
    ext: "csv",
    mime: "text/csv",
    color: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  },
};

function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard) return navigator.clipboard.writeText(text);
  // Fallback
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  document.body.removeChild(ta);
  return Promise.resolve();
}

function downloadBlob(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Parse CSV string into 2D array */
function parseCsv(raw: string): string[][] {
  return raw
    .trim()
    .split("\n")
    .map((row) =>
      row.split(",").map((cell) => cell.trim().replace(/^"|"$/g, "")),
    );
}

/** Basic SVG sanitization — strip script tags and event handlers */
function sanitizeSvg(raw: string): string {
  return raw
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/\bon\w+\s*=\s*"[^"]*"/gi, "")
    .replace(/\bon\w+\s*=\s*'[^']*'/gi, "");
}

/* ── Sub-components ────────────────────────────────────────────── */

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handle = useCallback(() => {
    copyToClipboard(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }, [text]);
  return (
    <button
      onClick={handle}
      className="p-1.5 rounded hover:bg-slate-700/60 text-slate-400 hover:text-slate-200 transition-colors"
      title="Kopyala"
      aria-label="Kaynak kodunu kopyala"
    >
      {copied ? (
        <span className="text-emerald-400 text-[10px] font-medium px-0.5">
          ✓
        </span>
      ) : (
        <Copy className="w-3.5 h-3.5" />
      )}
    </button>
  );
}

function DownloadBtn({
  content,
  type,
}: {
  content: string;
  type: Artifact["type"];
}) {
  const meta = TYPE_META[type];
  const handle = useCallback(() => {
    downloadBlob(content, `artifact.${meta.ext}`, meta.mime);
  }, [content, meta]);
  return (
    <button
      onClick={handle}
      className="p-1.5 rounded hover:bg-slate-700/60 text-slate-400 hover:text-slate-200 transition-colors"
      title="İndir"
      aria-label="Dosya olarak indir"
    >
      <Download className="w-3.5 h-3.5" />
    </button>
  );
}

/* ── Preview renderers ─────────────────────────────────────────── */

function HtmlPreview({ content }: { content: string }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Wrap content with a minimal dark-themed base
  const doc = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  body { margin: 0; padding: 12px; background: #1e293b; color: #cbd5e1;
         font-family: system-ui, sans-serif; font-size: 14px; }
  a { color: #38bdf8; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid #334155; padding: 6px 10px; text-align: left; }
  th { background: #0f172a; }
</style></head><body>${content}</body></html>`;

  return (
    <iframe
      ref={iframeRef}
      srcDoc={doc}
      sandbox="allow-scripts"
      title="HTML önizleme"
      className="w-full rounded border border-slate-700/50 bg-slate-900"
      style={{ minHeight: 160, maxHeight: 480 }}
      onLoad={() => {
        // Auto-resize to content height
        const frame = iframeRef.current;
        if (!frame?.contentDocument?.body) return;
        const h = frame.contentDocument.body.scrollHeight;
        frame.style.height = `${Math.min(Math.max(h + 24, 160), 480)}px`;
      }}
    />
  );
}

function SvgPreview({ content }: { content: string }) {
  const clean = sanitizeSvg(content);
  return (
    <div
      className="flex items-center justify-center p-4 overflow-auto"
      dangerouslySetInnerHTML={{ __html: clean }}
      role="img"
      aria-label="SVG önizleme"
    />
  );
}

function MermaidPreview({ content }: { content: string }) {
  // Placeholder — actual mermaid.js integration later
  return (
    <div className="p-3">
      <div className="text-[10px] text-slate-500 mb-2 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-pink-400/60" />
        Mermaid önizleme yakında — şimdilik kaynak kod gösteriliyor
      </div>
      <pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed">
        {content}
      </pre>
    </div>
  );
}

function CsvPreview({ content }: { content: string }) {
  const rows = parseCsv(content);
  if (rows.length === 0) return null;
  const [header, ...body] = rows;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr>
            {header.map((cell, i) => (
              <th
                key={i}
                className="text-left px-3 py-2 bg-slate-900/80 text-slate-300 font-medium border-b border-slate-700/60 whitespace-nowrap"
              >
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, ri) => (
            <tr
              key={ri}
              className="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors"
            >
              {row.map((cell, ci) => (
                <td
                  key={ci}
                  className="px-3 py-1.5 text-slate-400 whitespace-nowrap"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PreviewArea({ artifact }: { artifact: Artifact }) {
  return (
    <div
      className="relative rounded-md overflow-hidden"
      style={{
        backgroundImage:
          "radial-gradient(circle, rgba(71,85,105,0.15) 1px, transparent 1px)",
        backgroundSize: "16px 16px",
      }}
    >
      {artifact.type === "html" && <HtmlPreview content={artifact.content} />}
      {artifact.type === "svg" && <SvgPreview content={artifact.content} />}
      {artifact.type === "mermaid" && (
        <MermaidPreview content={artifact.content} />
      )}
      {artifact.type === "csv" && <CsvPreview content={artifact.content} />}
    </div>
  );
}

function SourceView({ content, type }: { content: string; type: string }) {
  return (
    <div className="relative">
      <pre className="text-xs font-mono text-slate-300 bg-slate-900/60 rounded-md p-3 overflow-x-auto leading-relaxed max-h-[400px] overflow-y-auto">
        <code>{content}</code>
      </pre>
      <span className="absolute top-2 right-2 text-[9px] text-slate-600 font-mono select-none">
        {type}
      </span>
    </div>
  );
}

/* ── ArtifactCard ──────────────────────────────────────────────── */

export function ArtifactCard({ artifact }: { artifact: Artifact }) {
  const [tab, setTab] = useState<TabId>("preview");
  const [collapsed, setCollapsed] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  const meta = TYPE_META[artifact.type];

  // ESC to exit fullscreen
  useEffect(() => {
    if (!fullscreen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFullscreen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [fullscreen]);

  // Lock body scroll in fullscreen
  useEffect(() => {
    if (fullscreen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [fullscreen]);

  const card = (
    <div
      ref={cardRef}
      className={`bg-slate-800/60 border border-slate-700 rounded-lg overflow-hidden transition-all ${
        fullscreen
          ? "fixed inset-4 z-50 flex flex-col shadow-2xl shadow-black/60"
          : ""
      }`}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-700/50">
        {/* Type badge */}
        <span
          className={`text-[9px] font-medium px-1.5 py-0.5 rounded border ${meta.color}`}
        >
          {meta.label}
        </span>

        {artifact.label && (
          <span className="text-[11px] text-slate-400 truncate flex-1">
            {artifact.label}
          </span>
        )}
        {!artifact.label && <span className="flex-1" />}

        {/* Tab pills */}
        <div className="flex items-center gap-0.5 bg-slate-900/50 rounded-md p-0.5">
          <button
            onClick={() => setTab("preview")}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors ${
              tab === "preview"
                ? "bg-slate-700/80 text-slate-200"
                : "text-slate-500 hover:text-slate-300"
            }`}
            aria-label="Önizleme sekmesi"
          >
            <Eye className="w-3 h-3" />
            Önizleme
          </button>
          <button
            onClick={() => setTab("source")}
            className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors ${
              tab === "source"
                ? "bg-slate-700/80 text-slate-200"
                : "text-slate-500 hover:text-slate-300"
            }`}
            aria-label="Kaynak sekmesi"
          >
            <Code className="w-3 h-3" />
            Kaynak
          </button>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-0.5 ml-1">
          <CopyBtn text={artifact.content} />
          <DownloadBtn content={artifact.content} type={artifact.type} />
          <button
            onClick={() => setFullscreen((f) => !f)}
            className="p-1.5 rounded hover:bg-slate-700/60 text-slate-400 hover:text-slate-200 transition-colors"
            title={fullscreen ? "Küçült" : "Tam ekran"}
            aria-label={fullscreen ? "Tam ekrandan çık" : "Tam ekran"}
          >
            {fullscreen ? (
              <Minimize2 className="w-3.5 h-3.5" />
            ) : (
              <Maximize2 className="w-3.5 h-3.5" />
            )}
          </button>
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="p-1.5 rounded hover:bg-slate-700/60 text-slate-400 hover:text-slate-200 transition-colors"
            title={collapsed ? "Genişlet" : "Daralt"}
            aria-label={collapsed ? "Genişlet" : "Daralt"}
          >
            {collapsed ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronUp className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* Body */}
      {!collapsed && (
        <div className={`p-2 ${fullscreen ? "flex-1 overflow-auto" : ""}`}>
          {tab === "preview" ? (
            <PreviewArea artifact={artifact} />
          ) : (
            <SourceView content={artifact.content} type={meta.label} />
          )}
        </div>
      )}
    </div>
  );

  // Fullscreen overlay backdrop
  if (fullscreen) {
    return (
      <>
        <div
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm"
          onClick={() => setFullscreen(false)}
          aria-hidden="true"
        />
        {card}
      </>
    );
  }

  return card;
}

/* ── ArtifactsPanel (renders all artifacts from a content string) ── */

export default function ArtifactsPanel({ content }: { content: string }) {
  const artifacts = detectArtifacts(content);
  if (artifacts.length === 0) return null;

  return (
    <div className="space-y-3 mt-3">
      {artifacts.map((a) => (
        <ArtifactCard key={a.id} artifact={a} />
      ))}
    </div>
  );
}
