"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import {
  X,
  Maximize2,
  Minimize2,
  Camera,
  Copy,
  Check,
  ShieldCheck,
} from "lucide-react";
import ReactMarkdown from "react-markdown";

/** Close unclosed markdown fences so ReactMarkdown renders streaming content properly */
function sanitizeStreamingMarkdown(md: string): string {
  const fenceCount = (md.match(/^```/gm) || []).length;
  if (fenceCount % 2 !== 0) return md + "\n```";
  return md;
}

interface DetailModalProps {
  title: string;
  content: string;
  color?: string;
  badge?: string;
  confidenceAnalysis?: string;
  onClose: () => void;
}

export function DetailModal({
  title,
  content,
  color,
  badge,
  confidenceAnalysis,
  onClose,
}: DetailModalProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const prevLen = useRef(content.length);
  const prevActiveElement = useRef<HTMLElement | null>(null);
  const [fullScreen, setFullScreen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showConfidence, setShowConfidence] = useState(false);
  const fullScreenRef = useRef(fullScreen);
  fullScreenRef.current = fullScreen;

  const handleClose = useCallback(() => {
    onClose();
    prevActiveElement.current?.focus();
  }, [onClose]);

  // On mount: store previous focus and focus close button
  useEffect(() => {
    prevActiveElement.current = document.activeElement as HTMLElement | null;
    closeButtonRef.current?.focus();
  }, []);

  // Auto-scroll when content grows (live update)
  useEffect(() => {
    if (content.length > prevLen.current && contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
    prevLen.current = content.length;
  }, [content]);

  // Escape to close and restore focus; Tab trap
  useEffect(() => {
    const overlay = overlayRef.current;
    const closeBtn = closeButtonRef.current;
    if (!overlay) return;

    const getFocusables = (): HTMLElement[] => {
      const panel = overlay.children[1];
      if (!panel) return [closeBtn].filter(Boolean) as HTMLElement[];
      const nodes = panel.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      const list = Array.from(nodes);
      if (closeBtn && !list.includes(closeBtn)) list.unshift(closeBtn);
      return list;
    };

    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (fullScreenRef.current) {
          setFullScreen(false);
        } else {
          handleClose();
        }
        return;
      }
      if (e.key !== "Tab") return;
      const focusables = getFocusables();
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleClose]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard not available */
    }
  }, [content]);

  const handleScreenshot = useCallback(async () => {
    // Tam ekran: tüm sayfayı yakala; normal mod: sadece paneli yakala
    const el = fullScreenRef.current ? document.body : panelRef.current;
    if (!el) return;
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { default: html2canvas } = await import("html2canvas" as any);
      const canvas = await html2canvas(el, {
        backgroundColor: fullScreenRef.current ? null : "#1a1f2e",
        scale: 2,
        useCORS: true,
        windowWidth: document.documentElement.scrollWidth,
        windowHeight: document.documentElement.scrollHeight,
      });
      canvas.toBlob((blob: Blob | null) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `screenshot-${Date.now()}.png`;
        a.click();
        URL.revokeObjectURL(url);
      });
    } catch {
      // html2canvas not available — fallback: copy text
      await handleCopy();
    }
  }, [handleCopy]);

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        className={`relative z-10 flex flex-col min-h-0 rounded-xl bg-[#1a1f2e] border border-border shadow-2xl overflow-hidden transition-all ${
          fullScreen
            ? "fixed inset-4 w-[calc(100vw-2rem)] h-[calc(100vh-2rem)] max-w-none"
            : "w-full max-w-2xl max-h-[85vh]"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            {color && (
              <div
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: color }}
              />
            )}
            <span className="text-sm font-semibold text-slate-200 truncate">
              {title}
            </span>
            {badge && (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-950/40 text-blue-400 shrink-0">
                {badge}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1 shrink-0">
            {/* Copy button */}
            <button
              type="button"
              onClick={handleCopy}
              aria-label="Kopyala"
              className="min-w-[36px] min-h-[36px] flex items-center justify-center text-slate-500 hover:text-slate-300 rounded hover:bg-white/5 transition-colors"
            >
              {copied ? (
                <Check className="w-4 h-4 text-emerald-400" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </button>
            {/* Close button */}
            <button
              ref={closeButtonRef}
              type="button"
              onClick={handleClose}
              aria-label="Kapat"
              className="min-w-[36px] min-h-[36px] flex items-center justify-center text-slate-500 hover:text-slate-300 cursor-pointer rounded hover:bg-white/5 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content — markdown rendered, selectable text (mouse ile seçilebilir) */}
        <div
          ref={contentRef}
          className="flex-1 min-h-0 overflow-y-auto overflow-x-auto px-5 py-4 pb-16 text-sm text-slate-300 leading-relaxed"
          style={{
            userSelect: "text",
            WebkitUserSelect: "text",
            cursor: "text",
          }}
        >
          {content ? (
            <div
              className="prose prose-invert prose-sm max-w-none prose-headings:text-slate-200 prose-p:text-slate-300 prose-strong:text-slate-200 prose-code:text-cyan-300 prose-code:bg-slate-800/50 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-slate-900 prose-pre:border prose-pre:border-border prose-li:text-slate-300 prose-a:text-cyan-400 [&_*]:select-text"
              style={{ userSelect: "text", WebkitUserSelect: "text" }}
            >
              <ReactMarkdown>
                {sanitizeStreamingMarkdown(content)}
              </ReactMarkdown>
            </div>
          ) : (
            <span className="text-slate-500">İçerik yok</span>
          )}
        </div>

        {/* FAB buttons — bottom right: Confidence + Copy + Screenshot + Fullscreen */}
        <div className="absolute bottom-4 right-4 flex items-center gap-2 z-20">
          {confidenceAnalysis && (
            <button
              type="button"
              onClick={() => setShowConfidence(true)}
              aria-label="Güven Analizi"
              className="w-10 h-10 flex items-center justify-center rounded-full bg-amber-600 hover:bg-amber-500 text-white shadow-lg transition-colors"
              title="Güven Analizi"
            >
              <ShieldCheck className="w-5 h-5" />
            </button>
          )}
          <button
            type="button"
            onClick={handleCopy}
            aria-label="Tümünü kopyala"
            className="w-10 h-10 flex items-center justify-center rounded-full bg-slate-700 hover:bg-slate-600 text-white shadow-lg transition-colors"
            title="Tümünü kopyala"
          >
            {copied ? (
              <Check className="w-5 h-5 text-emerald-400" />
            ) : (
              <Copy className="w-5 h-5" />
            )}
          </button>
          <button
            type="button"
            onClick={handleScreenshot}
            aria-label="Ekran görüntüsü al"
            className="w-10 h-10 flex items-center justify-center rounded-full bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg transition-colors"
            title="Ekran görüntüsü"
          >
            <Camera className="w-5 h-5" />
          </button>
          <button
            type="button"
            onClick={() => setFullScreen(!fullScreen)}
            aria-label={fullScreen ? "Küçült" : "Tam ekran"}
            className="w-10 h-10 flex items-center justify-center rounded-full bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg transition-colors"
            title={fullScreen ? "Küçült" : "Tam ekran"}
          >
            {fullScreen ? (
              <Minimize2 className="w-5 h-5" />
            ) : (
              <Maximize2 className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>

      {/* Confidence Analysis Overlay */}
      {showConfidence && confidenceAnalysis && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Güven Analizi"
        >
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowConfidence(false)}
            aria-hidden="true"
          />
          <div className="relative z-10 w-full max-w-lg max-h-[70vh] flex flex-col rounded-xl bg-[#1a1f2e] border border-amber-500/30 shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-amber-500/20 bg-amber-950/20 shrink-0">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-amber-400" />
                <span className="text-sm font-semibold text-amber-200">
                  Güven Analizi
                </span>
              </div>
              <button
                type="button"
                onClick={() => setShowConfidence(false)}
                aria-label="Güven analizini kapat"
                className="min-w-[36px] min-h-[36px] flex items-center justify-center text-slate-500 hover:text-slate-300 cursor-pointer rounded hover:bg-white/5 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto px-5 py-4 text-sm text-slate-300 leading-relaxed">
              <div className="prose prose-invert prose-sm max-w-none prose-headings:text-amber-200 prose-strong:text-amber-200 prose-code:text-cyan-300">
                <ReactMarkdown>{confidenceAnalysis}</ReactMarkdown>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
