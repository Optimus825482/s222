"use client";

import { useEffect, useRef, useCallback } from "react";
import { X } from "lucide-react";

interface DetailModalProps {
  title: string;
  content: string;
  color?: string;
  badge?: string;
  onClose: () => void;
}

export function DetailModal({
  title,
  content,
  color,
  badge,
  onClose,
}: DetailModalProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const prevLen = useRef(content.length);
  const prevActiveElement = useRef<HTMLElement | null>(null);

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
        handleClose();
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
      <div className="relative z-10 w-full max-w-2xl max-h-[85vh] flex flex-col min-h-0 rounded-xl bg-[#1a1f2e] border border-border shadow-2xl overflow-hidden">
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
        {/* Content: bounded height so scrollbars appear; break-all so long lines wrap */}
        <div
          ref={contentRef}
          className="flex-1 min-h-0 max-h-[70vh] overflow-y-auto overflow-x-auto px-5 py-4 text-[12px] text-slate-300 leading-relaxed whitespace-pre-wrap break-all font-mono"
        >
          {content || "İçerik yok"}
        </div>
      </div>
    </div>
  );
}
