"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { XpWindow, type WindowState } from "./xp-window";
import { XpTaskbar, DESKTOP_APPS } from "./xp-taskbar";
import "./xp-styles.css";

/* ── Window content registry (passed from page) ── */
export interface WindowContentMap {
  [appId: string]: ReactNode;
}

interface Props {
  contentMap: WindowContentMap;
  onHelpOpen?: () => void;
  onRoadmapOpen?: () => void;
}

let nextZ = 100;

function getDefaultGeo(id: string, idx: number) {
  const col = idx % 4;
  const row = Math.floor(idx / 4);
  return {
    x: 60 + col * 40 + idx * 25,
    y: 40 + row * 30 + idx * 20,
    w: 700,
    h: 500,
  };
}

export function XpDesktop({ contentMap, onHelpOpen, onRoadmapOpen }: Props) {
  const [windows, setWindows] = useState<WindowState[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const desktopRef = useRef<HTMLDivElement>(null);
  const [desktopRect, setDesktopRect] = useState<DOMRect | null>(null);
  const [selectedIcon, setSelectedIcon] = useState<string | null>(null);

  /* Track desktop size */
  useEffect(() => {
    const el = desktopRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() =>
      setDesktopRect(el.getBoundingClientRect()),
    );
    ro.observe(el);
    setDesktopRect(el.getBoundingClientRect());
    return () => ro.disconnect();
  }, []);

  /* ── Open / Focus window ── */
  const openApp = useCallback((appId: string) => {
    setWindows((prev) => {
      const existing = prev.find((w) => w.id === appId);
      if (existing) {
        // If minimized, restore; bring to front
        nextZ++;
        return prev.map((w) =>
          w.id === appId ? { ...w, minimized: false, zIndex: nextZ } : w,
        );
      }
      // Create new window
      const app = DESKTOP_APPS.find((a) => a.id === appId);
      if (!app) return prev;
      nextZ++;
      const geo = getDefaultGeo(appId, prev.length);
      const newWin: WindowState = {
        id: appId,
        title: app.title,
        icon: app.icon,
        ...geo,
        zIndex: nextZ,
        minimized: false,
        maximized: false,
      };
      return [...prev, newWin];
    });
    setActiveId(appId);
  }, []);

  const focusWindow = useCallback((id: string) => {
    nextZ++;
    setWindows((prev) =>
      prev.map((w) => (w.id === id ? { ...w, zIndex: nextZ } : w)),
    );
    setActiveId(id);
  }, []);

  const closeWindow = useCallback((id: string) => {
    setWindows((prev) => prev.filter((w) => w.id !== id));
    setActiveId((prev) => (prev === id ? null : prev));
  }, []);

  const minimizeWindow = useCallback((id: string) => {
    setWindows((prev) =>
      prev.map((w) => (w.id === id ? { ...w, minimized: true } : w)),
    );
    setActiveId((prev) => (prev === id ? null : prev));
  }, []);

  const maximizeWindow = useCallback((id: string) => {
    setWindows((prev) =>
      prev.map((w) => {
        if (w.id !== id) return w;
        if (w.maximized) {
          // Restore
          return {
            ...w,
            maximized: false,
            x: w.prevGeo?.x ?? w.x,
            y: w.prevGeo?.y ?? w.y,
            w: w.prevGeo?.w ?? w.w,
            h: w.prevGeo?.h ?? w.h,
            prevGeo: undefined,
          };
        }
        // Maximize
        return {
          ...w,
          maximized: true,
          prevGeo: { x: w.x, y: w.y, w: w.w, h: w.h },
        };
      }),
    );
  }, []);

  const moveWindow = useCallback((id: string, x: number, y: number) => {
    setWindows((prev) => prev.map((w) => (w.id === id ? { ...w, x, y } : w)));
  }, []);

  const resizeWindow = useCallback(
    (id: string, x: number, y: number, w: number, h: number) => {
      setWindows((prev) =>
        prev.map((win) => (win.id === id ? { ...win, x, y, w, h } : win)),
      );
    },
    [],
  );

  /* Taskbar window click: toggle minimize/restore */
  const handleTaskbarClick = useCallback(
    (id: string) => {
      const win = windows.find((w) => w.id === id);
      if (!win) return;
      if (win.minimized) {
        openApp(id);
      } else if (activeId === id) {
        minimizeWindow(id);
      } else {
        focusWindow(id);
      }
    },
    [windows, activeId, openApp, minimizeWindow, focusWindow],
  );

  /* Desktop click deselects */
  const handleDesktopClick = useCallback(() => {
    setSelectedIcon(null);
  }, []);

  return (
    <div
      className="xp-desktop flex flex-col h-dvh"
      onClick={handleDesktopClick}
    >
      {/* Desktop area */}
      <div ref={desktopRef} className="flex-1 relative overflow-hidden">
        {/* Desktop Icons */}
        <div
          className="absolute inset-0 p-3 flex flex-col flex-wrap gap-1 content-start"
          style={{ pointerEvents: "auto" }}
        >
          {DESKTOP_APPS.map((app) => (
            <div
              key={app.id}
              className={`xp-desktop-icon ${selectedIcon === app.id ? "selected" : ""}`}
              onClick={(e) => {
                e.stopPropagation();
                setSelectedIcon(app.id);
              }}
              onDoubleClick={(e) => {
                e.stopPropagation();
                openApp(app.id);
              }}
              role="button"
              tabIndex={0}
              aria-label={app.title}
              onKeyDown={(e) => {
                if (e.key === "Enter") openApp(app.id);
              }}
            >
              <div className="xp-desktop-icon-img" style={{ color: app.color }}>
                {app.icon}
              </div>
              <span className="xp-desktop-icon-label">{app.title}</span>
            </div>
          ))}
        </div>

        {/* Windows */}
        {windows.map((win) => (
          <XpWindow
            key={win.id}
            win={win}
            isActive={activeId === win.id}
            onFocus={() => focusWindow(win.id)}
            onClose={() => closeWindow(win.id)}
            onMinimize={() => minimizeWindow(win.id)}
            onMaximize={() => maximizeWindow(win.id)}
            onMove={(x, y) => moveWindow(win.id, x, y)}
            onResize={(x, y, w, h) => resizeWindow(win.id, x, y, w, h)}
            desktopRect={desktopRect}
          >
            {contentMap[win.id] || (
              <div className="p-4 text-sm text-gray-500">
                İçerik yükleniyor...
              </div>
            )}
          </XpWindow>
        ))}
      </div>

      {/* Taskbar */}
      <XpTaskbar
        windows={windows}
        activeWindowId={activeId}
        onWindowClick={handleTaskbarClick}
        onOpenApp={openApp}
        onHelpOpen={onHelpOpen}
        onRoadmapOpen={onRoadmapOpen}
      />
    </div>
  );
}
