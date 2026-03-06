"use client";

import { LogOut, Menu } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";

export type NavTab =
  | "chat"
  | "monitor"
  | "insights"
  | "memory"
  | "evolution"
  | "coordination"
  | "ecosystem"
  | "autonomous";

const NAV_TABS: { key: NavTab; label: string; color: string }[] = [
  {
    key: "chat",
    label: "💬 Sohbet",
    color: "text-blue-400 border-blue-400 bg-blue-400/5",
  },
  {
    key: "monitor",
    label: "📊 Görev",
    color: "text-sky-400 border-sky-400 bg-sky-400/5",
  },
  {
    key: "insights",
    label: "⚙️ Sistem",
    color: "text-emerald-400 border-emerald-400 bg-emerald-400/5",
  },
  {
    key: "memory",
    label: "🧠 Bellek",
    color: "text-purple-400 border-purple-400 bg-purple-400/5",
  },
  {
    key: "evolution",
    label: "📈 Gelişim",
    color: "text-amber-400 border-amber-400 bg-amber-400/5",
  },
  {
    key: "coordination",
    label: "🔗 Koordinasyon",
    color: "text-pink-400 border-pink-400 bg-pink-400/5",
  },
  {
    key: "ecosystem",
    label: "🌐 Ekosistem",
    color: "text-cyan-400 border-cyan-400 bg-cyan-400/5",
  },
  {
    key: "autonomous",
    label: "🤖 Özerk",
    color: "text-rose-400 border-rose-400 bg-rose-400/5",
  },
];

interface Props {
  onMenuToggle: () => void;
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
}

export function CockpitHeader({ onMenuToggle, activeTab, onTabChange }: Props) {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  return (
    <header className="shrink-0 border-b border-border bg-surface-raised safe-top">
      {/* Top bar */}
      <div className="flex items-center gap-2 px-3 md:px-6 py-2">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg hover:bg-surface-overlay transition-colors"
          aria-label="Menüyü aç"
        >
          <Menu className="w-5 h-5 text-slate-400" />
        </button>
        <span className="text-xl" aria-hidden="true">
          🧠
        </span>
        <span className="text-base font-bold text-slate-200 truncate">
          Ops Center
        </span>
        <span className="hidden sm:inline text-[10px] text-slate-500 ml-1">
          Qwen3 80B • 4 Agents
        </span>
        <div className="flex-1" />
        {user && (
          <div className="flex items-center gap-2">
            <span className="hidden sm:inline text-xs text-slate-400 truncate max-w-[120px]">
              {user.full_name}
            </span>
            <button
              onClick={handleLogout}
              className="p-2 min-w-[36px] min-h-[36px] flex items-center justify-center rounded-lg hover:bg-surface-overlay text-slate-500 hover:text-slate-300 transition-colors"
              aria-label="Çıkış yap"
              title="Çıkış yap"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Nav tabs */}
      <nav
        className="flex overflow-x-auto scrollbar-hide"
        aria-label="Ana navigasyon"
      >
        {NAV_TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => onTabChange(tab.key)}
            className={`whitespace-nowrap px-3 py-2 text-xs font-medium transition-colors border-b-2 ${
              activeTab === tab.key
                ? tab.color
                : "text-slate-500 border-transparent hover:text-slate-300 hover:bg-white/5"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </header>
  );
}
