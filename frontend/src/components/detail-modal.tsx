"use client";

import { useEffect, useRef } from "react";
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
  const prevLen = useRef(content.length);

  // Auto-scroll when content grows (live update)
  useEffect(() => {
    if (content.length > prevLen.current && contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
    prevLen.current = content.length;
  }, [content]);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative z-10 w-full max-w-2xl max-h-[80vh] flex flex-col rounded-xl bg-[#1a1f2e] border border-border shadow-2xl overflow-hidden">
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
            onClick={onClose}
            aria-label="Kapat"
            className="min-w-[36px] min-h-[36px] flex items-center justify-center text-slate-500 hover:text-slate-300 cursor-pointer rounded hover:bg-white/5 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        {/* Content */}
        <div
          ref={contentRef}
          className="flex-1 overflow-y-auto px-5 py-4 text-[12px] text-slate-300 leading-relaxed whitespace-pre-wrap break-words font-mono"
        >
          {content || "İçerik yok"}
        </div>
      </div>
    </div>
  );
}
