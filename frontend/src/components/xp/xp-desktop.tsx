"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { XpWindow, type WindowState } from "./xp-window";
import { XpTaskbar } from "./xp-taskbar";
import { APPS } from "./xp-apps";
import {
  DesktopContextMenu,
  IconContextMenu,
  WALLPAPER_PRESETS,
} from "./xp-context-menu";
import { XpAboutDialog } from "./xp-about-dialog";
import { XpPropertiesDialog } from "./xp-properties-dialog";
import { SystemGuideDialog } from "@/components/system-guide-dialog";
import { useXpSounds } from "@/lib/use-xp-sounds";
import "./xp-styles.css";

/* ── Helpers ── */
let _nextZ = 100;
function nextZ() {
  return ++_nextZ;
}
function cascade(index: number) {
  const offset = (index % 8) * 30;
  return { x: 60 + offset, y: 40 + offset };
}

/* ── Main Component ── */
export function XpDesktop() {
  const { play } = useXpSounds();
  const [windows, setWindows] = useState<WindowState[]>([]);
  const [showGuide, setShowGuide] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [wallpaper, setWallpaper] = useState("bliss");
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number } | null>(null);
  const [iconCtxMenu, setIconCtxMenu] = useState<{
    x: number;
    y: number;
    appId: string;
  } | null>(null);
  const [propsDialog, setPropsDialog] = useState<string | null>(null);
  const [iconPositions, setIconPositions] = useState<
    Record<string, { x: number; y: number }>
  >({});
  const [startMenuRemovedIds, setStartMenuRemovedIds] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const raw = localStorage.getItem("xp-start-menu-removed");
      if (!raw) return [];
      const parsed = JSON.parse(raw) as unknown;
      return Array.isArray(parsed) ? parsed.filter((x) => typeof x === "string") : [];
    } catch {
      return [];
    }
  });
  const dragIcon = useRef<{
    id: string;
    startX: number;
    startY: number;
    origX: number;
    origY: number;
  } | null>(null);
  const [isDraggingIcon, setIsDraggingIcon] = useState(false);
  const desktopRef = useRef<HTMLDivElement>(null);
  const iconGridInitializedRef = useRef(false);

  // Window dimensions for resize/rotate — grid recalculates when size changes
  const [dimensions, setDimensions] = useState({ w: 0, h: 0 });
  useEffect(() => {
    const update = () =>
      setDimensions({ w: window.innerWidth, h: window.innerHeight });
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  // Initialize / recalc icon positions (mobile: by width; desktop: by height; resize/rotate: reflow)
  useEffect(() => {
    if (dimensions.w === 0 && dimensions.h === 0) return;

    const isMobile = dimensions.w < 768;
    const gap = isMobile ? 68 : 96;
    const rowH = isMobile ? 78 : 100;
    const { w: width, h: height } = dimensions;

    let cols: number;
    if (isMobile) {
      const cellW = gap;
      cols = Math.max(1, Math.floor((width - 16) / cellW));
    } else {
      cols = Math.max(1, Math.floor((height - 80) / rowH));
    }

    const defaults: Record<string, { x: number; y: number }> = {};
    APPS.forEach((app, i) => {
      const row = Math.floor(i / cols);
      const col = i % cols;
      defaults[app.id] = { x: 8 + col * gap, y: 8 + row * rowH };
    });

    if (!iconGridInitializedRef.current) {
      iconGridInitializedRef.current = true;
      const stored = localStorage.getItem("xp-icon-positions");
      if (stored) {
        try {
          const parsed = JSON.parse(stored) as Record<string, { x: number; y: number }>;
          const merged = { ...defaults };
          for (const app of APPS) {
            if (parsed[app.id]) merged[app.id] = parsed[app.id];
          }
          setIconPositions(merged);
          return;
        } catch {
          /* ignore */
        }
      }
    }
    setIconPositions(defaults);
  }, [dimensions]);

  // Save positions to localStorage
  useEffect(() => {
    if (Object.keys(iconPositions).length > 0) {
      localStorage.setItem("xp-icon-positions", JSON.stringify(iconPositions));
    }
  }, [iconPositions]);

  // Load wallpaper from localStorage
  useEffect(() => {
    const stored = localStorage.getItem("xp-wallpaper");
    if (stored && WALLPAPER_PRESETS[stored]) setWallpaper(stored);
  }, []);

  // Save wallpaper to localStorage
  const changeWallpaper = useCallback((key: string) => {
    setWallpaper(key);
    localStorage.setItem("xp-wallpaper", key);
  }, []);

  // Startup sound
  useEffect(() => {
    const t = setTimeout(() => play("startup"), 500);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Icon drag handlers
  const handleIconDragStart = useCallback(
    (e: React.MouseEvent, appId: string) => {
      e.preventDefault();
      const pos = iconPositions[appId];
      if (!pos) return;
      dragIcon.current = {
        id: appId,
        startX: e.clientX,
        startY: e.clientY,
        origX: pos.x,
        origY: pos.y,
      };
      setIsDraggingIcon(true);
    },
    [iconPositions],
  );

  useEffect(() => {
    if (!isDraggingIcon) return;
    const handleMove = (e: MouseEvent) => {
      const drag = dragIcon.current;
      if (!drag) return;
      const dx = e.clientX - drag.startX;
      const dy = e.clientY - drag.startY;
      setIconPositions((prev) => ({
        ...prev,
        [drag.id]: {
          x: Math.max(0, drag.origX + dx),
          y: Math.max(0, drag.origY + dy),
        },
      }));
    };
    const handleUp = () => {
      dragIcon.current = null;
      setIsDraggingIcon(false);
    };
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleUp);
    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleUp);
    };
  }, [isDraggingIcon]);

  const openApp = useCallback((appId: string) => {
    if (appId === "help") {
      setShowGuide(true);
      return;
    }
    setWindows((prev) => {
      const existing = prev.find((w) => w.id === appId);
      if (existing) {
        return prev.map((w) =>
          w.id === appId ? { ...w, minimized: false, zIndex: nextZ() } : w,
        );
      }
      const app = APPS.find((a) => a.id === appId);
      if (!app) return prev;
      const pos = cascade(prev.length);
      const isMobile = window.innerWidth < 768;
      const newWin: WindowState = {
        id: app.id,
        title: app.title,
        icon: app.icon,
        x: isMobile ? 0 : pos.x,
        y: isMobile ? 0 : pos.y,
        w: isMobile ? window.innerWidth : app.defaultW,
        h: isMobile ? window.innerHeight - 36 : app.defaultH,
        minimized: false,
        maximized: isMobile,
        zIndex: nextZ(),
      };
      return [...prev, newWin];
    });
  }, []);

  // Listen for "open-app" custom events
  useEffect(() => {
    const handler = (e: Event) => {
      const appId = (e as CustomEvent<string>).detail;
      if (appId) openApp(appId);
    };
    window.addEventListener("open-app", handler);
    return () => window.removeEventListener("open-app", handler);
  }, [openApp]);

  const closeWindow = useCallback((id: string) => {
    setWindows((prev) => prev.filter((w) => w.id !== id));
  }, []);

  const minimizeWindow = useCallback((id: string) => {
    setWindows((prev) =>
      prev.map((w) => (w.id === id ? { ...w, minimized: true } : w)),
    );
  }, []);

  const maximizeWindow = useCallback((id: string) => {
    setWindows((prev) =>
      prev.map((w) =>
        w.id === id ? { ...w, maximized: !w.maximized, zIndex: nextZ() } : w,
      ),
    );
  }, []);

  const focusWindow = useCallback((id: string) => {
    setWindows((prev) =>
      prev.map((w) => (w.id === id ? { ...w, zIndex: nextZ() } : w)),
    );
  }, []);

  const moveWindow = useCallback((id: string, x: number, y: number) => {
    setWindows((prev) => prev.map((w) => (w.id === id ? { ...w, x, y } : w)));
  }, []);

  const resizeWindow = useCallback((id: string, w: number, h: number) => {
    setWindows((prev) =>
      prev.map((win) => (win.id === id ? { ...win, w, h } : win)),
    );
  }, []);

  const handleDesktopContext = useCallback((e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest(".xp-desktop-icon, .xp-window"))
      return;
    e.preventDefault();
    setCtxMenu({ x: e.clientX, y: e.clientY });
  }, []);

  // Dismiss context menus on click outside
  useEffect(() => {
    if (!ctxMenu && !iconCtxMenu) return;
    const dismiss = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest(".xp-ctx-menu")) return;
      setCtxMenu(null);
      setIconCtxMenu(null);
    };
    window.addEventListener("pointerdown", dismiss);
    return () => window.removeEventListener("pointerdown", dismiss);
  }, [ctxMenu, iconCtxMenu]);

  const handleTaskbarClick = useCallback((id: string) => {
    setWindows((prev) => {
      const win = prev.find((w) => w.id === id);
      if (!win) return prev;
      if (win.minimized) {
        return prev.map((w) =>
          w.id === id ? { ...w, minimized: false, zIndex: nextZ() } : w,
        );
      }
      const maxZ = prev.length > 0 ? Math.max(...prev.map((w) => w.zIndex)) : 0;
      if (win.zIndex === maxZ) {
        return prev.map((w) => (w.id === id ? { ...w, minimized: true } : w));
      }
      return prev.map((w) => (w.id === id ? { ...w, zIndex: nextZ() } : w));
    });
  }, []);

  const resetIcons = useCallback(() => {
    const isMobile = window.innerWidth < 768;
    const gap = isMobile ? 80 : 96;
    const rowH = isMobile ? 84 : 100;
    const cols = Math.floor((window.innerHeight - 80) / rowH);
    const positions: Record<string, { x: number; y: number }> = {};
    APPS.forEach((app, i) => {
      const col = Math.floor(i / cols);
      const row = i % cols;
      positions[app.id] = { x: 8 + col * gap, y: 8 + row * rowH };
    });
    setIconPositions(positions);
    localStorage.removeItem("xp-icon-positions");
  }, []);

  useEffect(() => {
    localStorage.setItem("xp-start-menu-removed", JSON.stringify(startMenuRemovedIds));
  }, [startMenuRemovedIds]);

  const taskbarApps = APPS.map((a) => ({
    id: a.id,
    title: a.title,
    icon: a.icon,
    group: a.group,
  }));

  const propsApp = propsDialog ? APPS.find((a) => a.id === propsDialog) : null;

  return (
    <div className="xp-desktop-root flex flex-col h-dvh overflow-hidden select-none">
      {/* Desktop Area */}
      <div
        ref={desktopRef}
        className="flex-1 relative overflow-hidden xp-wallpaper"
        style={{
          background:
            WALLPAPER_PRESETS[wallpaper]?.gradient ??
            WALLPAPER_PRESETS.bliss.gradient,
        }}
        onContextMenu={handleDesktopContext}
      >
        {/* Desktop Icons */}
        {APPS.map((app) => {
          const pos = iconPositions[app.id];
          if (!pos) return null;
          return (
            <button
              key={app.id}
              onMouseDown={(e) => {
                if (window.innerWidth >= 768) handleIconDragStart(e, app.id);
              }}
              onClick={() => {
                if (window.innerWidth < 768) openApp(app.id);
              }}
              onDoubleClick={() => openApp(app.id)}
              onContextMenu={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setIconCtxMenu({ x: e.clientX, y: e.clientY, appId: app.id });
                setCtxMenu(null);
              }}
              className="xp-desktop-icon absolute flex flex-col items-center gap-1 sm:gap-1.5 w-[68px] sm:w-[80px] p-1.5 sm:p-2 rounded hover:bg-white/10 active:bg-white/20 transition-colors group z-10"
              style={{ left: pos.x, top: pos.y }}
              title={`${app.title} — çift tıkla`}
            >
              <span
                className="w-10 h-10 sm:w-12 sm:h-12 flex items-center justify-center drop-shadow-[0_2px_6px_rgba(0,0,0,0.6)] group-hover:scale-110 transition-transform"
                style={{ color: app.color }}
              >
                {app.icon}
              </span>
              <span className="text-[10px] sm:text-[11px] text-white text-center leading-tight drop-shadow-[0_1px_3px_rgba(0,0,0,0.8)] line-clamp-2 font-medium">
                {app.title}
              </span>
            </button>
          );
        })}

        {/* Windows */}
        {windows.map((win) => {
          const app = APPS.find((a) => a.id === win.id);
          if (!app) return null;
          return (
            <XpWindow
              key={win.id}
              state={win}
              onClose={closeWindow}
              onMinimize={minimizeWindow}
              onMaximize={maximizeWindow}
              onFocus={focusWindow}
              onMove={moveWindow}
              onResize={resizeWindow}
            >
              {app.render()}
            </XpWindow>
          );
        })}

        {/* Desktop Right-Click Context Menu */}
        {ctxMenu && (
          <DesktopContextMenu
            x={ctxMenu.x}
            y={ctxMenu.y}
            onClose={() => setCtxMenu(null)}
            onOpenApp={openApp}
            onResetIcons={resetIcons}
            onShowAbout={() => setShowAbout(true)}
            onChangeWallpaper={changeWallpaper}
            currentWallpaper={wallpaper}
          />
        )}

        {/* Icon Right-Click Context Menu */}
        {iconCtxMenu && (
          <IconContextMenu
            x={iconCtxMenu.x}
            y={iconCtxMenu.y}
            appId={iconCtxMenu.appId}
            onClose={() => setIconCtxMenu(null)}
            onOpenApp={openApp}
            onShowProps={(id) => setPropsDialog(id)}
          />
        )}
      </div>

      {/* Properties Dialog */}
      {propsApp && (
        <XpPropertiesDialog
          app={propsApp}
          onClose={() => setPropsDialog(null)}
          onOpen={() => {
            openApp(propsApp.id);
            setPropsDialog(null);
          }}
        />
      )}

      {/* About Dialog */}
      <XpAboutDialog open={showAbout} onClose={() => setShowAbout(false)} />

      {/* System Guide Dialog */}
      <SystemGuideDialog open={showGuide} onClose={() => setShowGuide(false)} />

      {/* Taskbar */}
      <XpTaskbar
        windows={windows}
        onWindowClick={handleTaskbarClick}
        onOpenApp={openApp}
        onHelpOpen={() => setShowGuide(true)}
        onAddShortcut={(appId) => {
          const app = APPS.find((a) => a.id === appId);
          if (!app) return;
          setIconPositions((prev) => ({
            ...prev,
            [appId]: {
              x: Math.max(16, Math.floor(window.innerWidth / 2 - 40)),
              y: Math.max(16, Math.floor(window.innerHeight / 3)),
            },
          }));
        }}
        apps={taskbarApps}
        removedFromStart={startMenuRemovedIds}
        onRemoveFromStart={(appId) => {
          setStartMenuRemovedIds((prev) =>
            prev.includes(appId) ? prev : [...prev, appId],
          );
        }}
        onAddBackToStart={(appId) => {
          setStartMenuRemovedIds((prev) => prev.filter((id) => id !== appId));
        }}
      />
    </div>
  );
}
