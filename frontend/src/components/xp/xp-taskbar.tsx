"use client";

import { useState, useEffect, useRef } from "react";
import type { WindowState } from "./xp-window";
import {
  Bot,
  Monitor,
  Power,
  FolderOpen,
  HardDrive,
  Settings,
  HelpCircle,
  Search,
  Network,
  Users,
  History,
  Wrench,
  Wifi,
  Volume2,
  VolumeX,
  Mic,
  Code2,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useXpSounds } from "@/lib/use-xp-sounds";

interface DesktopApp {
  id: string;
  title: string;
  icon: React.ReactNode;
  group: string;
}

interface Props {
  windows: WindowState[];
  onWindowClick: (id: string) => void;
  onOpenApp: (appId: string) => void;
  onHelpOpen?: () => void;
  onAddShortcut?: (appId: string) => void;
  apps: DesktopApp[];
  removedFromStart?: string[];
  onRemoveFromStart?: (appId: string) => void;
  onAddBackToStart?: (appId: string) => void;
}

export function XpTaskbar({
  windows,
  onWindowClick,
  onOpenApp,
  onHelpOpen,
  onAddShortcut,
  apps,
  removedFromStart = [],
  onRemoveFromStart,
  onAddBackToStart,
}: Props) {
  const [startOpen, setStartOpen] = useState(false);
  const [startCtx, setStartCtx] = useState<{
    x: number;
    y: number;
    appId: string;
    isRemoved?: boolean;
  } | null>(null);
  const [clock, setClock] = useState("");
  const startRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { play } = useXpSounds();

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

  useEffect(() => {
    if (!startCtx) return;
    const handleDismiss = () => setStartCtx(null);
    document.addEventListener("mousedown", handleDismiss);
    return () => document.removeEventListener("mousedown", handleDismiss);
  }, [startCtx]);

  const pinnedApps = apps.filter((a) => !removedFromStart.includes(a.id));
  const removedApps = apps.filter((a) => removedFromStart.includes(a.id));

  const groups = new Map<string, DesktopApp[]>();
  for (const app of pinnedApps) {
    if (!groups.has(app.group)) groups.set(app.group, []);
    groups.get(app.group)!.push(app);
  }

  return (
    <div className="xp-taskbar h-[40px] flex items-stretch shrink-0 relative z-[9999]">
      {/* Start Menu Popup */}
      {startOpen && (
        <div
          ref={startRef}
          className="absolute bottom-[40px] left-0 w-[min(420px,100vw)] xp-start-menu rounded-t-lg overflow-hidden shadow-2xl"
        >
          {/* Header */}
          <div className="xp-start-header h-[54px] flex items-center gap-3 px-3">
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center border-2 border-white/40">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <span className="text-white text-sm font-bold drop-shadow-[0_1px_2px_rgba(0,0,0,0.5)]">
              Nexus AI Team
            </span>
          </div>

          {/* Body */}
          <div className="flex max-h-[calc(100dvh-140px)]">
            {/* Left: Pinned apps */}
            <div className="flex-1 bg-white py-2 px-1 overflow-y-auto">
              {Array.from(groups.entries()).map(([groupName, groupApps]) => (
                <div key={groupName}>
                  <div className="px-3 pt-3 pb-1.5 text-[11px] font-bold text-gray-400 uppercase tracking-wider">
                    {groupName}
                  </div>
                  {groupApps.map((app) => (
                    <button
                      key={app.id}
                      onClick={() => {
                        onOpenApp(app.id);
                        setStartOpen(false);
                        setStartCtx(null);
                      }}
                      onContextMenu={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setStartCtx({
                          x: e.clientX,
                          y: e.clientY,
                          appId: app.id,
                          isRemoved: false,
                        });
                      }}
                      className="w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-[#2f71cd] hover:text-white text-gray-800 rounded-sm transition-colors group"
                    >
                      <span className="w-8 h-8 flex items-center justify-center text-blue-600 group-hover:text-white shrink-0 pointer-events-none">
                        {app.icon}
                      </span>
                      <span className="text-[13px] font-medium">
                        {app.title}
                      </span>
                    </button>
                  ))}
                </div>
              ))}

              {/* Kaldırılanlar dropdown */}
              {removedApps.length > 0 && (
                <div className="border-t border-gray-200 mt-2 pt-2">
                  <details className="group/details">
                    <summary className="list-none cursor-pointer px-3 py-2 flex items-center gap-2 text-[11px] font-bold text-gray-500 uppercase tracking-wider hover:bg-gray-100 rounded-sm">
                      <span className="w-4 h-4 flex items-center justify-center text-gray-400 group-open/details:rotate-90 transition-transform">
                        ▸
                      </span>
                      Başlat Menüsünden Kaldırılanlar ({removedApps.length})
                    </summary>
                    <div className="mt-0.5 space-y-0.5">
                      {removedApps.map((app) => (
                        <button
                          key={app.id}
                          onClick={() => {
                            onOpenApp(app.id);
                            setStartOpen(false);
                            setStartCtx(null);
                          }}
                          onContextMenu={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setStartCtx({
                              x: e.clientX,
                              y: e.clientY,
                              appId: app.id,
                              isRemoved: true,
                            });
                          }}
                          className="w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-[#2f71cd] hover:text-white text-gray-600 rounded-sm transition-colors group/item"
                        >
                          <span className="w-8 h-8 flex items-center justify-center text-gray-500 group-hover/item:text-white shrink-0 pointer-events-none">
                            {app.icon}
                          </span>
                          <span className="text-[13px] font-medium">
                            {app.title}
                          </span>
                        </button>
                      ))}
                    </div>
                  </details>
                </div>
              )}
            </div>

            {/* Right: System links */}
            <div className="hidden sm:block w-[160px] xp-start-right py-2 px-2 space-y-0.5">
              <button
                onClick={() => {
                  onOpenApp("reports");
                  setStartOpen(false);
                }}
                className="w-full flex items-center gap-2.5 px-2 py-1.5 text-left hover:bg-white/10 text-white rounded-sm transition-colors text-[12px]"
              >
                <FolderOpen className="w-4 h-4 text-amber-300" />
                <span>Raporlarım</span>
              </button>
              <button
                onClick={() => {
                  onOpenApp("insights");
                  setStartOpen(false);
                }}
                className="w-full flex items-center gap-2.5 px-2 py-1.5 text-left hover:bg-white/10 text-white rounded-sm transition-colors text-[12px]"
              >
                <HardDrive className="w-4 h-4 text-slate-300" />
                <span>Sistem Durumu</span>
              </button>
              <button
                onClick={() => {
                  onOpenApp("agents");
                  setStartOpen(false);
                }}
                className="w-full flex items-center gap-2.5 px-2 py-1.5 text-left hover:bg-white/10 text-white rounded-sm transition-colors text-[12px]"
              >
                <Network className="w-4 h-4 text-cyan-300" />
                <span>Ağ Bağlantıları</span>
              </button>
              <button
                onClick={() => {
                  onOpenApp("optimizer");
                  setStartOpen(false);
                }}
                className="w-full flex items-center gap-2.5 px-2 py-1.5 text-left hover:bg-white/10 text-white rounded-sm transition-colors text-[12px]"
              >
                <Settings className="w-4 h-4 text-slate-300" />
                <span>Denetim Masası</span>
              </button>
              <button
                onClick={() => {
                  onOpenApp("search");
                  setStartOpen(false);
                }}
                className="w-full flex items-center gap-2.5 px-2 py-1.5 text-left hover:bg-white/10 text-white rounded-sm transition-colors text-[12px]"
              >
                <Search className="w-4 h-4 text-slate-300" />
                <span>Hata Arama</span>
              </button>
              <button
                onClick={() => {
                  onHelpOpen?.();
                  setStartOpen(false);
                }}
                className="w-full flex items-center gap-2.5 px-2 py-1.5 text-left hover:bg-white/10 text-white rounded-sm transition-colors text-[12px]"
              >
                <HelpCircle className="w-4 h-4 text-slate-300" />
                <span>Yardım</span>
              </button>
              <div className="border-t border-white/10 my-1.5" />
              <button
                onClick={() => {
                  onOpenApp("agents");
                  setStartOpen(false);
                }}
                className="w-full flex items-center gap-2.5 px-2 py-1.5 text-left hover:bg-white/10 text-white rounded-sm transition-colors text-[12px]"
              >
                <Users className="w-4 h-4 text-pink-300" />
                <span>Agentlar</span>
              </button>
              <button
                onClick={() => {
                  onOpenApp("sessions");
                  setStartOpen(false);
                }}
                className="w-full flex items-center gap-2.5 px-2 py-1.5 text-left hover:bg-white/10 text-white rounded-sm transition-colors text-[12px]"
              >
                <History className="w-4 h-4 text-blue-300" />
                <span>Oturumlar</span>
              </button>
              <button
                onClick={() => {
                  onOpenApp("tools");
                  setStartOpen(false);
                }}
                className="w-full flex items-center gap-2.5 px-2 py-1.5 text-left hover:bg-white/10 text-white rounded-sm transition-colors text-[12px]"
              >
                <Wrench className="w-4 h-4 text-purple-300" />
                <span>Araçlar</span>
              </button>
              <div className="border-t border-white/10 my-1.5" />
              <button
                onClick={() => {
                  router.push("/");
                  setStartOpen(false);
                }}
                className="w-full flex items-center gap-2.5 px-2 py-1.5 text-left hover:bg-white/10 text-white rounded-sm transition-colors text-[12px]"
              >
                <Monitor className="w-4 h-4 text-slate-300" />
                <span>Klasik Görünüm</span>
              </button>
            </div>
          </div>

          {/* Footer */}
          <div className="xp-start-footer h-[40px] flex items-center justify-end px-4 gap-2">
            <button
              onClick={() => {
                play("shutdown");
                setTimeout(() => {
                  router.push("/login");
                }, 300);
                setStartOpen(false);
              }}
              className="flex items-center gap-2 text-white text-[12px] font-medium hover:bg-white/10 px-3 py-1.5 rounded transition-colors"
            >
              <Power className="w-4 h-4" />
              Çıkış
            </button>
          </div>
        </div>
      )}

      {/* Start Menu Context Menu — z-index above start menu (9999) so it appears on top */}
      {startCtx && (
        <div
          className="fixed z-[10002] bg-white rounded shadow-[2px_2px_8px_rgba(0,0,0,0.3)] border border-gray-300 py-1 min-w-[200px] max-w-[90vw] text-[12px] text-gray-800"
          style={{
            left: Math.min(startCtx.x, window.innerWidth - 220),
            top: Math.min(startCtx.y, window.innerHeight - 60),
          }}
          onMouseDown={(e) => e.stopPropagation()}
        >
          {startCtx.isRemoved ? (
            <>
              <button
                onClick={() => {
                  onAddBackToStart?.(startCtx.appId);
                  setStartCtx(null);
                }}
                className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
              >
                <Bot className="w-3.5 h-3.5" />
                Başlat Menüsüne Ekle
              </button>
              <button
                onClick={() => {
                  if (onAddShortcut) onAddShortcut(startCtx.appId);
                  setStartCtx(null);
                  setStartOpen(false);
                }}
                className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
              >
                <Monitor className="w-3.5 h-3.5" />
                Masaüstüne Ekle
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => {
                  if (onAddShortcut) onAddShortcut(startCtx.appId);
                  setStartCtx(null);
                  setStartOpen(false);
                }}
                className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
              >
                <Monitor className="w-3.5 h-3.5" />
                Masaüstüne Ekle
              </button>
              <button
                onClick={() => {
                  onRemoveFromStart?.(startCtx.appId);
                  setStartCtx(null);
                }}
                className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
              >
                <FolderOpen className="w-3.5 h-3.5" />
                Başlat Menüsünden Kaldır
              </button>
            </>
          )}
        </div>
      )}

      {/* Start Button */}
      <button
        onClick={() => setStartOpen((v) => !v)}
        className={`xp-start-btn h-full px-3 flex items-center gap-1.5 text-white text-[12px] font-bold shrink-0 ${startOpen ? "xp-start-btn-active" : ""}`}
      >
        <span className="text-lg leading-none">🪟</span>
        Başlat
      </button>

      {/* Quick Launch Divider */}
      <div className="w-px h-[24px] self-center bg-white/20 mx-1" />

      {/* Open Windows */}
      <div className="flex-1 flex items-center gap-[2px] overflow-x-auto px-1 min-w-0">
        {windows
          .filter((w) => !w.minimized || true)
          .map((win) => (
            <button
              key={win.id}
              onClick={() => onWindowClick(win.id)}
              className={`xp-taskbar-item h-[28px] min-w-[80px] sm:min-w-[120px] max-w-[140px] sm:max-w-[180px] flex items-center gap-1 sm:gap-1.5 px-1.5 sm:px-2 rounded-sm text-[10px] sm:text-[11px] truncate shrink-0 transition-colors ${
                !win.minimized
                  ? "xp-taskbar-item-active text-white"
                  : "text-white/70 hover:bg-white/10"
              }`}
              title={win.title}
            >
              <span className="w-4 h-4 flex items-center justify-center shrink-0">
                {win.icon}
              </span>
              <span className="truncate">{win.title}</span>
            </button>
          ))}
      </div>

      {/* System Tray */}
      <VolumeControl />
      <div className="xp-tray flex items-center gap-1.5 sm:gap-2 px-2 sm:px-3 h-full shrink-0">
        <button
          onClick={() => {
            try {
              document.dispatchEvent(
                new KeyboardEvent("keydown", {
                  key: "F12",
                  code: "F12",
                  keyCode: 123,
                  which: 123,
                  bubbles: true,
                }),
              );
            } catch {
              // Fallback: some environments block programmatic F12
            }
          }}
          className="p-0.5 hover:bg-white/10 rounded transition-colors flex items-center justify-center"
          title="Geliştirici Seçenekleri (F12)"
        >
          <Code2 className="w-3.5 h-3.5 text-white/60" />
        </button>
        <button
          className="p-0.5 hover:bg-white/10 rounded transition-colors hidden sm:block"
          title="WiFi — Bağlı"
        >
          <Wifi className="w-3.5 h-3.5 text-green-400" />
        </button>
        <button
          className="p-0.5 hover:bg-white/10 rounded transition-colors hidden sm:block"
          title="Mikrofon"
        >
          <Mic className="w-3.5 h-3.5 text-white/70" />
        </button>
        <div className="w-px h-3 bg-white/15 hidden sm:block" />
        <span className="text-[10px] sm:text-[11px] text-white font-medium tabular-nums">
          {clock}
        </span>
      </div>
    </div>
  );
}

// Volume Control with popup slider
function VolumeControl() {
  const { volume, muted, setVolume, toggleMute } = useXpSounds();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const dismiss = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", dismiss);
    return () => document.removeEventListener("mousedown", dismiss);
  }, [open]);

  return (
    <div ref={ref} className="relative flex items-center h-full">
      <button
        onClick={() => setOpen((v) => !v)}
        className="p-1 hover:bg-white/10 rounded transition-colors"
        title={muted ? "Ses Kapalı" : `Ses: %${volume}`}
      >
        {muted ? (
          <VolumeX className="w-3.5 h-3.5 text-red-400" />
        ) : (
          <Volume2 className="w-3.5 h-3.5 text-white/70" />
        )}
      </button>

      {open && (
        <div className="absolute bottom-[44px] right-0 w-[180px] max-w-[90vw] bg-[#ece9d8] border border-[#0054e3] rounded-t-lg shadow-2xl overflow-hidden z-[300]">
          <div className="bg-gradient-to-r from-[#0054e3] via-[#0066ff] to-[#3b8aff] px-3 py-1.5">
            <span className="text-white text-[11px] font-bold">Ses Düzeyi</span>
          </div>
          <div className="p-3 space-y-3">
            <div className="flex items-center gap-2">
              <button
                onClick={toggleMute}
                className="p-1 rounded hover:bg-gray-300/50 transition-colors"
                title={muted ? "Sesi Aç" : "Sessize Al"}
              >
                {muted ? (
                  <VolumeX className="w-4 h-4 text-red-500" />
                ) : (
                  <Volume2 className="w-4 h-4 text-gray-700" />
                )}
              </button>
              <input
                type="range"
                min={0}
                max={100}
                value={muted ? 0 : volume}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setVolume(v);
                  if (muted && v > 0) toggleMute();
                }}
                className="flex-1 h-1.5 accent-[#0054e3] cursor-pointer"
                aria-label="Ses seviyesi"
              />
              <span className="text-[11px] text-gray-600 font-medium w-8 text-right tabular-nums">
                %{muted ? 0 : volume}
              </span>
            </div>
            <div className="flex items-center gap-2 pt-1 border-t border-gray-300/60">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={muted}
                  onChange={toggleMute}
                  className="w-3 h-3 accent-[#0054e3]"
                />
                <span className="text-[11px] text-gray-600">Sessiz</span>
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
