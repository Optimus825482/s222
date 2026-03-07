"use client";

import { useState, useEffect, useRef } from "react";
import type { ReactNode } from "react";
import type { WindowState } from "./xp-window";
import {
  Monitor,
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
  HelpCircle,
  Map,
} from "lucide-react";

/* ── Desktop icon definition (reused by start menu) ── */
export interface DesktopApp {
  id: string;
  title: string;
  icon: ReactNode;
  color: string;
  group: "core" | "agents" | "analytics";
}

export const DESKTOP_APPS: DesktopApp[] = [
  {
    id: "chat",
    title: "Sohbet",
    icon: <MessageSquare className="w-5 h-5" />,
    color: "#3b82f6",
    group: "core",
  },
  {
    id: "monitor",
    title: "Görev Merkezi",
    icon: <BarChart3 className="w-5 h-5" />,
    color: "#0ea5e9",
    group: "core",
  },
  {
    id: "insights",
    title: "Sistem",
    icon: <Settings className="w-5 h-5" />,
    color: "#10b981",
    group: "core",
  },
  {
    id: "memory",
    title: "Bellek",
    icon: <Brain className="w-5 h-5" />,
    color: "#a855f7",
    group: "core",
  },
  {
    id: "evolution",
    title: "Gelişim",
    icon: <TrendingUp className="w-5 h-5" />,
    color: "#f59e0b",
    group: "agents",
  },
  {
    id: "coordination",
    title: "Koordinasyon",
    icon: <Link2 className="w-5 h-5" />,
    color: "#ec4899",
    group: "agents",
  },
  {
    id: "ecosystem",
    title: "Ekosistem",
    icon: <Globe className="w-5 h-5" />,
    color: "#06b6d4",
    group: "agents",
  },
  {
    id: "autonomous",
    title: "Özerk Evrim",
    icon: <Bot className="w-5 h-5" />,
    color: "#f43f5e",
    group: "agents",
  },
  {
    id: "comms",
    title: "İletişim",
    icon: <Radio className="w-5 h-5" />,
    color: "#06b6d4",
    group: "agents",
  },
  {
    id: "benchmark",
    title: "Benchmark",
    icon: <Trophy className="w-5 h-5" />,
    color: "#eab308",
    group: "analytics",
  },
  {
    id: "errors",
    title: "Hatalar",
    icon: <Bug className="w-5 h-5" />,
    color: "#ef4444",
    group: "analytics",
  },
  {
    id: "optimizer",
    title: "Optimizer",
    icon: <Zap className="w-5 h-5" />,
    color: "#f97316",
    group: "analytics",
  },
  {
    id: "costs",
    title: "Maliyet",
    icon: <DollarSign className="w-5 h-5" />,
    color: "#10b981",
    group: "analytics",
  },
];

interface Props {
  windows: WindowState[];
  activeWindowId: string | null;
  onWindowClick: (id: string) => void;
  onOpenApp: (id: string) => void;
  onHelpOpen?: () => void;
  onRoadmapOpen?: () => void;
}

export function XpTaskbar({
  windows,
  activeWindowId,
  onWindowClick,
  onOpenApp,
  onHelpOpen,
  onRoadmapOpen,
}: Props) {
  const [clock, setClock] = useState("");
  const [startOpen, setStartOpen] = useState(false);
  const startRef = useRef<HTMLDivElement>(null);

  /* Clock */
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setClock(
        now.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }),
      );
    };
    tick();
    const iv = setInterval(tick, 30_000);
    return () => clearInterval(iv);
  }, []);

  /* Close start menu on outside click */
  useEffect(() => {
    if (!startOpen) return;
    const fn = (e: MouseEvent) => {
      if (startRef.current && !startRef.current.contains(e.target as Node)) {
        setStartOpen(false);
      }
    };
    document.addEventListener("mousedown", fn);
    return () => document.removeEventListener("mousedown", fn);
  }, [startOpen]);

  const coreApps = DESKTOP_APPS.filter((a) => a.group === "core");
  const agentApps = DESKTOP_APPS.filter((a) => a.group === "agents");
  const analyticsApps = DESKTOP_APPS.filter((a) => a.group === "analytics");

  return (
    <>
      {/* Start Menu */}
      {startOpen && (
        <div ref={startRef} className="xp-start-menu">
          <div className="xp-start-header">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-blue-700 flex items-center justify-center shadow-md">
              <Monitor className="w-5 h-5 text-white" />
            </div>
            <span>Ops Center</span>
          </div>
          <div className="xp-start-body">
            {/* Left column — apps */}
            <div className="xp-start-left">
              <div className="px-3 py-1 text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                Temel
              </div>
              {coreApps.map((app) => (
                <div
                  key={app.id}
                  className="xp-start-item"
                  onClick={() => {
                    onOpenApp(app.id);
                    setStartOpen(false);
                  }}
                >
                  <div
                    className="xp-start-item-icon"
                    style={{ color: app.color }}
                  >
                    {app.icon}
                  </div>
                  <span>{app.title}</span>
                </div>
              ))}
              <div className="xp-start-separator" />
              <div className="px-3 py-1 text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                Agent
              </div>
              {agentApps.map((app) => (
                <div
                  key={app.id}
                  className="xp-start-item"
                  onClick={() => {
                    onOpenApp(app.id);
                    setStartOpen(false);
                  }}
                >
                  <div
                    className="xp-start-item-icon"
                    style={{ color: app.color }}
                  >
                    {app.icon}
                  </div>
                  <span>{app.title}</span>
                </div>
              ))}
              <div className="xp-start-separator" />
              <div className="px-3 py-1 text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                Analitik
              </div>
              {analyticsApps.map((app) => (
                <div
                  key={app.id}
                  className="xp-start-item"
                  onClick={() => {
                    onOpenApp(app.id);
                    setStartOpen(false);
                  }}
                >
                  <div
                    className="xp-start-item-icon"
                    style={{ color: app.color }}
                  >
                    {app.icon}
                  </div>
                  <span>{app.title}</span>
                </div>
              ))}
            </div>
            {/* Right column — system */}
            <div className="xp-start-right">
              {onHelpOpen && (
                <div
                  className="xp-start-item"
                  onClick={() => {
                    onHelpOpen();
                    setStartOpen(false);
                  }}
                >
                  <div className="xp-start-item-icon text-blue-600">
                    <HelpCircle className="w-5 h-5" />
                  </div>
                  <span className="font-bold">Sistem Rehberi</span>
                </div>
              )}
              {onRoadmapOpen && (
                <div
                  className="xp-start-item"
                  onClick={() => {
                    onRoadmapOpen();
                    setStartOpen(false);
                  }}
                >
                  <div className="xp-start-item-icon text-blue-600">
                    <Map className="w-5 h-5" />
                  </div>
                  <span className="font-bold">Yol Haritası</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Taskbar */}
      <div className="xp-taskbar">
        {/* Start Button */}
        <button
          className="xp-start-btn"
          onClick={() => setStartOpen((v) => !v)}
          aria-label="Başlat menüsü"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="5" cy="5" r="3.5" fill="#ff0000" />
            <circle cx="11" cy="5" r="3.5" fill="#00cc00" />
            <circle cx="5" cy="11" r="3.5" fill="#0066ff" />
            <circle cx="11" cy="11" r="3.5" fill="#ffcc00" />
          </svg>
          <span>Başlat</span>
        </button>

        {/* Quick Launch Separator */}
        <div className="w-px h-6 bg-white/20 mx-1 flex-shrink-0" />

        {/* Window Buttons */}
        <div className="xp-taskbar-items">
          {windows.map((win) => {
            const app = DESKTOP_APPS.find((a) => a.id === win.id);
            return (
              <button
                key={win.id}
                className={`xp-taskbar-item ${activeWindowId === win.id ? "active" : ""} ${win.minimized ? "minimized" : ""}`}
                onClick={() => onWindowClick(win.id)}
                title={win.title}
              >
                <span
                  style={{ color: app?.color || "#fff" }}
                  className="flex-shrink-0"
                >
                  {app?.icon || <Monitor className="w-3.5 h-3.5" />}
                </span>
                <span className="truncate text-[11px]">{win.title}</span>
              </button>
            );
          })}
        </div>

        {/* System Tray */}
        <div className="xp-tray">
          <div className="xp-tray-clock">{clock}</div>
        </div>
      </div>
    </>
  );
}
