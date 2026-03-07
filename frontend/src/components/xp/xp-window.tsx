"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type PointerEvent as RPointerEvent,
} from "react";

/* ── Types ── */
export interface WindowState {
  id: string;
  title: string;
  icon: ReactNode;
  x: number;
  y: number;
  w: number;
  h: number;
  zIndex: number;
  minimized: boolean;
  maximized: boolean;
  /** stored geometry before maximize */
  prevGeo?: { x: number; y: number; w: number; h: number };
}

interface Props {
  win: WindowState;
  isActive: boolean;
  children: ReactNode;
  onFocus: () => void;
  onClose: () => void;
  onMinimize: () => void;
  onMaximize: () => void;
  onMove: (x: number, y: number) => void;
  onResize: (x: number, y: number, w: number, h: number) => void;
}

type Dir = "n" | "s" | "e" | "w" | "ne" | "nw" | "se" | "sw";

const MIN_W = 320;
const MIN_H = 200;

export function XpWindow({
  win,
  isActive,
  children,
  onFocus,
  onClose,
  onMinimize,
  onMaximize,
  onMove,
  onResize,
}: Props) {
  const dragRef = useRef<{
    startX: number;
    startY: number;
    origX: number;
    origY: number;
  } | null>(null);
  const resizeRef = useRef<{
    dir: Dir;
    startX: number;
    startY: number;
    origX: number;
    origY: number;
    origW: number;
    origH: number;
  } | null>(null);
  const [animClass, setAnimClass] = useState("");

  /* ── Drag ── */
  const onDragStart = useCallback(
    (e: RPointerEvent<HTMLDivElement>) => {
      if (win.maximized) return;
      e.preventDefault();
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
      dragRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        origX: win.x,
        origY: win.y,
      };
      onFocus();
    },
    [win.x, win.y, win.maximized, onFocus],
  );

  const onDragMove = useCallback(
    (e: RPointerEvent<HTMLDivElement>) => {
      if (!dragRef.current) return;
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      onMove(dragRef.current.origX + dx, dragRef.current.origY + dy);
    },
    [onMove],
  );

  const onDragEnd = useCallback(() => {
    dragRef.current = null;
  }, []);

  /* ── Resize ── */
  const onResizeStart = useCallback(
    (dir: Dir) => (e: RPointerEvent<HTMLDivElement>) => {
      if (win.maximized) return;
      e.preventDefault();
      e.stopPropagation();
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
      resizeRef.current = {
        dir,
        startX: e.clientX,
        startY: e.clientY,
        origX: win.x,
        origY: win.y,
        origW: win.w,
        origH: win.h,
      };
      onFocus();
    },
    [win.x, win.y, win.w, win.h, win.maximized, onFocus],
  );

  const onResizeMove = useCallback(
    (e: RPointerEvent<HTMLDivElement>) => {
      const r = resizeRef.current;
      if (!r) return;
      const dx = e.clientX - r.startX;
      const dy = e.clientY - r.startY;
      let { origX: nx, origY: ny, origW: nw, origH: nh } = r;

      if (r.dir.includes("e")) nw = Math.max(MIN_W, r.origW + dx);
      if (r.dir.includes("s")) nh = Math.max(MIN_H, r.origH + dy);
      if (r.dir.includes("w")) {
        const newW = Math.max(MIN_W, r.origW - dx);
        nx = r.origX + (r.origW - newW);
        nw = newW;
      }
      if (r.dir.includes("n")) {
        const newH = Math.max(MIN_H, r.origH - dy);
        ny = r.origY + (r.origH - newH);
        nh = newH;
      }
      onResize(nx, ny, nw, nh);
    },
    [onResize],
  );

  const onResizeEnd = useCallback(() => {
    resizeRef.current = null;
  }, []);

  /* ── Minimize animation ── */
  useEffect(() => {
    if (win.minimized) {
      setAnimClass("minimizing");
      const t = setTimeout(() => setAnimClass(""), 200);
      return () => clearTimeout(t);
    }
  }, [win.minimized]);

  if (win.minimized && !animClass) return null;

  const style: React.CSSProperties = win.maximized
    ? { top: 0, left: 0, width: "100%", height: "100%", zIndex: win.zIndex }
    : {
        top: win.y,
        left: win.x,
        width: win.w,
        height: win.h,
        zIndex: win.zIndex,
      };

  return (
    <div
      className={`xp-window ${isActive ? "active" : ""} ${win.maximized ? "maximized" : ""} ${animClass}`}
      style={style}
      onPointerDown={onFocus}
    >
      {/* Title Bar */}
      <div
        className="xp-titlebar"
        onPointerDown={onDragStart}
        onPointerMove={onDragMove}
        onPointerUp={onDragEnd}
        onDoubleClick={onMaximize}
      >
        <div className="xp-titlebar-icon">{win.icon}</div>
        <div className="xp-titlebar-text">{win.title}</div>
        <div className="xp-titlebar-buttons">
          <button
            className="xp-btn xp-btn-minimize"
            onClick={(e) => {
              e.stopPropagation();
              onMinimize();
            }}
            aria-label="Küçült"
            title="Küçült"
          >
            <svg width="9" height="9" viewBox="0 0 9 9">
              <rect x="1" y="7" width="7" height="2" fill="white" />
            </svg>
          </button>
          <button
            className="xp-btn xp-btn-maximize"
            onClick={(e) => {
              e.stopPropagation();
              onMaximize();
            }}
            aria-label={win.maximized ? "Geri yükle" : "Büyüt"}
            title={win.maximized ? "Geri Yükle" : "Büyüt"}
          >
            {win.maximized ? (
              <svg width="9" height="9" viewBox="0 0 9 9">
                <rect
                  x="2"
                  y="0"
                  width="7"
                  height="7"
                  fill="none"
                  stroke="white"
                  strokeWidth="1.5"
                />
                <rect
                  x="0"
                  y="2"
                  width="7"
                  height="7"
                  fill="none"
                  stroke="white"
                  strokeWidth="1.5"
                />
              </svg>
            ) : (
              <svg width="9" height="9" viewBox="0 0 9 9">
                <rect
                  x="0.5"
                  y="0.5"
                  width="8"
                  height="8"
                  fill="none"
                  stroke="white"
                  strokeWidth="1.5"
                />
                <rect x="0.5" y="0.5" width="8" height="2" fill="white" />
              </svg>
            )}
          </button>
          <button
            className="xp-btn xp-btn-close"
            onClick={(e) => {
              e.stopPropagation();
              onClose();
            }}
            aria-label="Kapat"
            title="Kapat"
          >
            <svg width="9" height="9" viewBox="0 0 9 9">
              <line
                x1="1"
                y1="1"
                x2="8"
                y2="8"
                stroke="white"
                strokeWidth="1.8"
              />
              <line
                x1="8"
                y1="1"
                x2="1"
                y2="8"
                stroke="white"
                strokeWidth="1.8"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="xp-window-body">
        <div className="xp-window-content">{children}</div>
      </div>

      {/* Resize Handles */}
      {!win.maximized && (
        <>
          {(["n", "s", "e", "w", "ne", "nw", "se", "sw"] as Dir[]).map(
            (dir) => (
              <div
                key={dir}
                className={`xp-resize-handle xp-resize-${dir}`}
                onPointerDown={onResizeStart(dir)}
                onPointerMove={onResizeMove}
                onPointerUp={onResizeEnd}
              />
            ),
          )}
        </>
      )}
    </div>
  );
}
