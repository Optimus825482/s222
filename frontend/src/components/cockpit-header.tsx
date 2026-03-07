"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import { ChevronDown, HelpCircle, LogOut, Map, Menu } from "lucide-react";
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
  | "autonomous"
  | "comms"
  | "benchmark"
  | "errors"
  | "optimizer"
  | "costs";

interface DI {
  key: NavTab;
  label: string;
  icon: string;
  color: string;
}

interface TG {
  id: string;
  label: string;
  icon: string;
  color: string;
  items: DI[];
}

const PRIMARY_TABS: { key: NavTab; label: string; color: string }[] = [
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
];

const TAB_GROUPS: TG[] = [
  {
    id: "agents",
    label: "Agent",
    icon: "🤖",
    color: "text-rose-400 border-rose-400",
    items: [
      {
        key: "evolution",
        label: "Gelişim",
        icon: "📈",
        color: "text-amber-400",
      },
      {
        key: "coordination",
        label: "Koordinasyon",
        icon: "🔗",
        color: "text-pink-400",
      },
      {
        key: "ecosystem",
        label: "Ekosistem",
        icon: "🌐",
        color: "text-cyan-400",
      },
      {
        key: "autonomous",
        label: "Özerk Evrim",
        icon: "🤖",
        color: "text-rose-400",
      },
      { key: "comms", label: "İletişim", icon: "📡", color: "text-cyan-400" },
    ],
  },
  {
    id: "analytics",
    label: "Analitik",
    icon: "📊",
    color: "text-amber-400 border-amber-400",
    items: [
      {
        key: "benchmark",
        label: "Benchmark",
        icon: "🏆",
        color: "text-yellow-400",
      },
      { key: "errors", label: "Hatalar", icon: "🐛", color: "text-red-400" },
      {
        key: "optimizer",
        label: "Optimizer",
        icon: "⚡",
        color: "text-orange-400",
      },
      { key: "costs", label: "Maliyet", icon: "💰", color: "text-emerald-400" },
    ],
  },
];

function NavDropdown(props: {
  group: TG;
  activeTab: NavTab;
  onSelect: (t: NavTab) => void;
}) {
  const { group, activeTab, onSelect } = props;
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const fn = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener("mousedown", fn);
    return () => document.removeEventListener("mousedown", fn);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const fn = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", fn);
    return () => document.removeEventListener("keydown", fn);
  }, [open]);

  const match = group.items.find((i) => i.key === activeTab);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`whitespace-nowrap px-3 py-2 text-xs font-medium transition-colors border-b-2 flex items-center gap-1 ${
          match
            ? `${group.color} bg-white/5`
            : "text-slate-500 border-transparent hover:text-slate-300 hover:bg-white/5"
        }`}
        aria-expanded={open}
        aria-haspopup="true"
      >
        {group.icon} {match ? match.label : group.label}
        <ChevronDown
          className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div
          className="absolute top-full left-0 mt-1 z-50 min-w-[180px] bg-slate-800 border border-slate-700/60 rounded-lg shadow-xl py-1"
          role="menu"
        >
          {group.items.map((item) => {
            const sel = activeTab === item.key;
            return (
              <button
                key={item.key}
                role="menuitem"
                onClick={() => {
                  onSelect(item.key);
                  setOpen(false);
                }}
                className={`w-full text-left px-3 py-2 text-xs flex items-center gap-2 transition-colors ${
                  sel
                    ? `${item.color} bg-white/5 font-medium`
                    : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
                {sel && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-current" />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

interface Props {
  onMenuToggle: () => void;
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  onHelpOpen?: () => void;
  onRoadmapOpen?: () => void;
}

export function CockpitHeader({
  onMenuToggle,
  activeTab,
  onTabChange,
  onHelpOpen,
  onRoadmapOpen,
}: Props) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  return (
    <header className="shrink-0 border-b border-border bg-surface-raised safe-top">
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
        {onRoadmapOpen && (
          <button
            onClick={onRoadmapOpen}
            className="p-2 min-w-[36px] min-h-[36px] flex items-center justify-center rounded-lg hover:bg-surface-overlay text-slate-500 hover:text-slate-300 transition-colors"
            aria-label="Yol haritası"
            title="Yol Haritası"
          >
            <Map className="w-4 h-4" />
          </button>
        )}
        {onHelpOpen && (
          <button
            onClick={onHelpOpen}
            className="p-2 min-w-[36px] min-h-[36px] flex items-center justify-center rounded-lg hover:bg-surface-overlay text-slate-500 hover:text-slate-300 transition-colors"
            aria-label="Sistem rehberi"
            title="Sistem Rehberi"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        )}
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
      {/* Desktop: all tabs flat */}
      <nav
        className="hidden lg:flex items-center overflow-x-auto scrollbar-hide"
        aria-label="Ana navigasyon"
      >
        {PRIMARY_TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => onTabChange(tab.key)}
            className={`whitespace-nowrap px-3 py-2 text-xs font-medium transition-colors border-b-2 ${activeTab === tab.key ? tab.color : "text-slate-500 border-transparent hover:text-slate-300 hover:bg-white/5"}`}
          >
            {tab.label}
          </button>
        ))}
        {TAB_GROUPS.map((g) => (
          <Fragment key={g.id}>
            <div
              className="w-px h-5 bg-slate-700/50 mx-1 shrink-0"
              aria-hidden
            />
            {g.items.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => onTabChange(item.key)}
                className={`whitespace-nowrap px-2.5 py-2 text-xs font-medium transition-colors border-b-2 flex items-center gap-1 ${
                  activeTab === item.key
                    ? `${item.color} border-current bg-white/5`
                    : "text-slate-500 border-transparent hover:text-slate-300 hover:bg-white/5"
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </Fragment>
        ))}
      </nav>

      {/* Mobile: primary tabs + grouped dropdowns */}
      <nav
        className="lg:hidden flex items-center overflow-x-auto scrollbar-hide"
        aria-label="Ana navigasyon"
      >
        {PRIMARY_TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => onTabChange(tab.key)}
            className={`whitespace-nowrap px-3 py-2 text-xs font-medium transition-colors border-b-2 ${activeTab === tab.key ? tab.color : "text-slate-500 border-transparent hover:text-slate-300 hover:bg-white/5"}`}
          >
            {tab.label}
          </button>
        ))}
        <div className="w-px h-5 bg-slate-700/50 mx-1 shrink-0" aria-hidden />
        {TAB_GROUPS.map((g) => (
          <NavDropdown
            key={g.id}
            group={g}
            activeTab={activeTab}
            onSelect={onTabChange}
          />
        ))}
      </nav>
    </header>
  );
}
