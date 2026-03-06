"use client";

import type { NavTab } from "@/components/cockpit-header";

interface Props {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  isProcessing: boolean;
  liveEventCount: number;
}

const MOBILE_TABS: { id: NavTab; label: string; emoji: string }[] = [
  { id: "chat", label: "Sohbet", emoji: "💬" },
  { id: "monitor", label: "Görev", emoji: "📊" },
  { id: "insights", label: "Sistem", emoji: "⚙️" },
  { id: "memory", label: "Bellek", emoji: "🧠" },
];

export function MobileNav({
  activeTab,
  onTabChange,
  isProcessing,
  liveEventCount,
}: Props) {
  return (
    <nav
      className="lg:hidden flex border-t border-border bg-surface-raised safe-bottom"
      aria-label="Mobil navigasyon"
    >
      {MOBILE_TABS.map(({ id, label, emoji }) => {
        const isActive = activeTab === id;
        return (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            aria-current={isActive ? "page" : undefined}
            aria-label={label}
            className={`
              flex-1 flex flex-col items-center justify-center gap-1
              min-h-[56px] py-2 text-xs font-medium transition-colors cursor-pointer
              ${isActive ? "text-blue-400" : "text-slate-500 hover:text-slate-300"}
            `}
          >
            <span className="relative text-base">
              {emoji}
              {id === "monitor" && isProcessing && liveEventCount > 0 && (
                <span
                  className="absolute -top-1 -right-2 w-2 h-2 bg-blue-500 rounded-full animate-pulse"
                  aria-label="Aktif"
                />
              )}
            </span>
            <span>{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
