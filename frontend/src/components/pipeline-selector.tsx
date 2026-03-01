"use client";

import { useState } from "react";
import type { PipelineType } from "@/lib/types";
import { PIPELINE_OPTIONS } from "@/lib/agents";
import { Info } from "lucide-react";

interface Props {
  selected: PipelineType;
  onSelect: (p: PipelineType) => void;
}

export function PipelineSelector({ selected, onSelect }: Props) {
  const [showDesc, setShowDesc] = useState(false);
  const selectedOpt = PIPELINE_OPTIONS.find((o) => o.id === selected);

  return (
    <div className="border-b border-border bg-surface">
      <div
        className="flex gap-1.5 px-3 lg:px-6 py-2 overflow-x-auto scrollbar-none snap-x snap-mandatory"
        role="radiogroup"
        aria-label="Pipeline tipi seçimi"
      >
        {PIPELINE_OPTIONS.map((opt) => {
          const isSelected = selected === opt.id;
          return (
            <button
              key={opt.id}
              onClick={() => onSelect(opt.id as PipelineType)}
              role="radio"
              aria-checked={isSelected}
              title={opt.desc}
              className={`
                px-3 lg:px-4 py-2 rounded-lg text-xs font-medium transition-all shrink-0 snap-start
                min-h-[44px] cursor-pointer
                ${
                  isSelected
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                    : "bg-surface-raised text-slate-400 hover:text-slate-200 hover:bg-surface-overlay border border-border"
                }
              `}
            >
              <span className="hidden md:inline">{opt.label}</span>
              <span className="md:hidden">{opt.short}</span>
            </button>
          );
        })}

        {/* Info toggle — mobile only */}
        <button
          onClick={() => setShowDesc((v) => !v)}
          className="lg:hidden shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg bg-surface-raised border border-border text-slate-500 hover:text-slate-300 cursor-pointer snap-start"
          aria-label="Pipeline açıklamalarını göster"
          aria-expanded={showDesc}
        >
          <Info className="w-4 h-4" />
        </button>
      </div>

      {/* Selected pipeline description — always visible on mobile when toggled, hover on desktop */}
      {showDesc && selectedOpt && (
        <div className="px-3 lg:px-6 pb-2 lg:hidden">
          <p className="text-[11px] text-slate-400 bg-surface-raised rounded-lg px-3 py-2 border border-border">
            <span className="text-blue-400 font-semibold">
              {selectedOpt.label}:
            </span>{" "}
            {selectedOpt.desc}
          </p>
        </div>
      )}
    </div>
  );
}
