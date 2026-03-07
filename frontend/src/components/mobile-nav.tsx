"use client";

import { useState } from "react";
import {
  MessageSquare,
  BarChart3,
  Settings,
  Brain,
  TrendingUp,
  Link2,
  Globe,
  Bot,
  Radio,
  Trophy,
  Bug,
  Zap,
  DollarSign,
  Wrench,
} from "lucide-react";
import type { NavTab } from "@/components/cockpit-header";

interface Props {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  isProcessing: boolean;
  liveEventCount: number;
}

const MOBILE_TABS: { id: NavTab; label: string; icon: React.ReactNode }[] = [
  { id: "chat", label: "Sohbet", icon: <MessageSquare className="w-5 h-5" /> },
  { id: "monitor", label: "Görev", icon: <BarChart3 className="w-5 h-5" /> },
  { id: "insights", label: "Sistem", icon: <Settings className="w-5 h-5" /> },
  { id: "memory", label: "Bellek", icon: <Brain className="w-5 h-5" /> },
];

const MORE_ITEMS: { id: NavTab; label: string; icon: React.ReactNode }[] = [
  {
    id: "evolution",
    label: "Gelişim",
    icon: <TrendingUp className="w-5 h-5" />,
  },
  {
    id: "coordination",
    label: "Koordinasyon",
    icon: <Link2 className="w-5 h-5" />,
  },
  { id: "ecosystem", label: "Ekosistem", icon: <Globe className="w-5 h-5" /> },
  { id: "autonomous", label: "Özerk", icon: <Bot className="w-5 h-5" /> },
  { id: "comms", label: "İletişim", icon: <Radio className="w-5 h-5" /> },
  { id: "benchmark", label: "Benchmark", icon: <Trophy className="w-5 h-5" /> },
  { id: "errors", label: "Hatalar", icon: <Bug className="w-5 h-5" /> },
  { id: "optimizer", label: "Optimizer", icon: <Zap className="w-5 h-5" /> },
  { id: "costs", label: "Maliyet", icon: <DollarSign className="w-5 h-5" /> },
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
            {MORE_ITEMS.map(({ id, label, icon }) => {
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
                  {icon}
                  <span className="text-xs font-medium">{label}</span>
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
        {MOBILE_TABS.map(({ id, label, icon }) => {
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
              <span className="relative">
                {icon}
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
          <Wrench className="w-5 h-5" />
          <span>Araçlar</span>
        </button>
      </nav>
    </>
  );
}
