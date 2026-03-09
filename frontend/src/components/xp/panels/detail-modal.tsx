"use client";

import { X } from "lucide-react";

interface DetailModalProps {
  title: string;
  content: string;
  color: string;
  badge: string;
  onClose: () => void;
}

export function DetailModal({
  title,
  content,
  color,
  badge,
  onClose,
}: DetailModalProps) {
  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center"
      style={{ backgroundColor: "rgba(0, 0, 0, 0.4)" }}
      onClick={onClose}
    >
      <div
        className="rounded shadow-xl max-w-2xl w-[90%] max-h-[80vh] flex flex-col"
        style={{ backgroundColor: "#fff", border: "1px solid #d6d2c2" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center gap-2 px-4 py-3 border-b"
          style={{ backgroundColor: "#f8f6ee", borderColor: "#d6d2c2" }}
        >
          <span
            className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded"
            style={{ backgroundColor: color + "20", color: color }}
          >
            {badge}
          </span>
          <span
            className="text-[14px] font-semibold flex-1"
            style={{ color: "#003399" }}
          >
            {title}
          </span>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-200 transition-colors"
            style={{ color: "#666" }}
            aria-label="Kapat"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div
          className="flex-1 overflow-auto p-4"
          style={{ backgroundColor: "#fff" }}
        >
          <pre
            className="whitespace-pre-wrap text-[13px] leading-relaxed"
            style={{ color: "#333", fontFamily: "'Roboto', sans-serif" }}
          >
            {content}
          </pre>
        </div>

        {/* Footer */}
        <div
          className="flex justify-end px-4 py-3 border-t"
          style={{ backgroundColor: "#f8f6ee", borderColor: "#d6d2c2" }}
        >
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded text-[12px] font-medium transition-colors"
            style={{ backgroundColor: "#e5e5e5", color: "#333" }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = "#d5d5d5";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "#e5e5e5";
            }}
          >
            Kapat
          </button>
        </div>
      </div>
    </div>
  );
}