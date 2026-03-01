"use client";

import { Menu } from "lucide-react";

interface Props {
  onMenuToggle: () => void;
}

export function CockpitHeader({ onMenuToggle }: Props) {
  return (
    <header className="flex items-center gap-2 px-3 md:px-6 py-3 border-b border-border bg-surface-raised safe-top">
      <button
        onClick={onMenuToggle}
        className="lg:hidden p-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg hover:bg-surface-overlay transition-colors"
        aria-label="Menüyü aç"
      >
        <Menu className="w-5 h-5 text-slate-400" />
      </button>
      <span className="text-xl md:text-2xl" aria-hidden="true">
        🧠
      </span>
      <span className="text-base md:text-lg font-bold text-slate-200 truncate">
        Ops Center
      </span>
      <span className="hidden sm:inline text-xs text-slate-500 ml-2 truncate">
        Qwen3 80B • 4 Agents • 7 Pipelines
      </span>
    </header>
  );
}
