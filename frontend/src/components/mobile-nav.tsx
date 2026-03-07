"use client";

import { useState } from "react";
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

const MORE_ITEMS: { id: NavTab; label: string; emoji: string }[] = [
  { id: "evolution", label: "Gelişim", emoji: "📈" },
  { id: "coordination", label: "Koordinasyon", emoji: "🔗" },
  { id: "ecosystem", label: "Ekosistem", emoji: "🌐" },
  { id: "autonomous", label: "Özerk", emoji: "🤖" },
  { id: "comms", label: "İletişim", emoji: "📡" },
  { id: "benchmark", label: "Benchmark", emoji: "🏆" },
  { id: "errors", label: "Hatalar", emoji: "🐛" },
  { id: "optimizer", label: "Optimizer", emoji: "⚡" },
  { id: "costs", label: "Maliyet", emoji: "💰" },
];

const MORE_KEYS = new Set(MORE_ITEMS.map((i) => i.id));

export function MobileNav({
  activeTab,
  onTabChange,
  isProcessing,
  liveEventCount,
}: Props) {
  const [moreOpen, setMoreOpen] = useState(false);
  const isMoreActive = MORE_KEYS.has(activeTab);

  return (
    <>
      {/* More panel overlay */}
      {moreOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-black/50"
          onClick={() => setMoreOpen(false)}
          role="presentation"
        />
      )}

      {/* More panel slide-up */}
      {moreOpen && (
        <div className="lg:hidden fixed bottom-[56px] left-0 right-0 z-50 bg-slate-900 border-t border-slate-700/60 rounded-t-xl shadow-xl shadow-black/40 safe-bottom animate-in slide-in-from-bottom-2 duration-200">
          <div className="px-4 py-3 border-b border-slate-800/60">
            <span className="text-xs font-medium text-slate-300">Araçlar</span>
          </div>
          <div className="grid grid-cols-3 gap-1 p-3">
            {MORE_ITEMS.map(({ id, label, emoji }) => {
              const isActive = activeTab === id;
              return (
                <button
                  key={id}
                  onClick={() => {
                    onTabChange(id);
                    setMoreOpen(false);
                  }}
                  className={`flex flex-col items-center gap-1 py-3 px-2 rounded-lg transition-colors ${
                    isActive
                      ? "bg-slate-800 text-cyan-400"
                      : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
                  }`}
                >
                  <span className="text-lg">{emoji}</span>
                  <span className="text-[10px] font-medium">{label}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Bottom nav bar */}
      <nav
        className="lg:hidden flex border-t border-border bg-surface-raised safe-bottom"
        aria-label="Mobil navigasyon"
      >
        {MOBILE_TABS.map(({ id, label, emoji }) => {
          const isActive = activeTab === id && !moreOpen;
          return (
            <button
              key={id}
              onClick={() => {
                onTabChange(id);
                setMoreOpen(false);
              }}
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

        {/* More button */}
        <button
          onClick={() => setMoreOpen((v) => !v)}
          aria-label="Daha fazla"
          aria-expanded={moreOpen}
          className={`
            flex-1 flex flex-col items-center justify-center gap-1
            min-h-[56px] py-2 text-xs font-medium transition-colors cursor-pointer
            ${isMoreActive || moreOpen ? "text-cyan-400" : "text-slate-500 hover:text-slate-300"}
          `}
        >
          <span className="text-base">🔧</span>
          <span>Araçlar</span>
        </button>
      </nav>
    </>
  );
}
