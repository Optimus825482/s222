"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Minus, Square, X, Maximize2 } from "lucide-react";

export interface WindowState {
  id: string;
  title: string;
  icon: ReactNode;
  x: number;
  y: number;
  w: number;
  h: number;
  minimized: boolean;
  maximized: boolean;
  zIndex: number;
}

interface Props {
  state: WindowState;
  onClose: (id: string) => void;
  onMinimize: (id: string) => void;
  onMaximize: (id: string) => void;
  onFocus: (id: string) => void;
  onMove: (id: string, x: number, y: number) => void;
  onResize: (id: string, w: number, h: number) => void;
  children: ReactNode;
}

export function XpWindow({
  state,
  onClose,
  onMinimize,
  onMaximize,
  onFocus,
  onMove,
  onResize,
  children,
}: Props) {
  const dragRef = useRef<{
    startX: number;
    startY: number;
    origX: number;
    origY: number;
  } | null>(null);
  const resizeRef = useRef<{
    startX: number;
    startY: number;
    origW: number;
    origH: number;
  } | null>(null);
  const windowRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);

  // Mobile detect
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  // Drag
  const handleDragStart = useCallback(
    (e: React.MouseEvent) => {
      if (state.maximized) return;
      if (typeof window !== "undefined" && window.innerWidth < 640) return;
      e.preventDefault();
      onFocus(state.id);
      dragRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        origX: state.x,
        origY: state.y,
      };
      setIsDragging(true);
    },
    [state.id, state.x, state.y, state.maximized, onFocus],
  );

  useEffect(() => {
    if (!isDragging) return;
    const handleMouseMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      onMove(state.id, dragRef.current.origX + dx, dragRef.current.origY + dy);
    };
    const handleMouseUp = () => {
      dragRef.current = null;
      setIsDragging(false);
    };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, state.id, onMove]);

  // Resize
  const handleResizeStart = useCallback(
    (e: React.MouseEvent) => {
      if (state.maximized) return;
      e.preventDefault();
      e.stopPropagation();
      onFocus(state.id);
      resizeRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        origW: state.w,
        origH: state.h,
      };
      setIsResizing(true);
    },
    [state.id, state.w, state.h, state.maximized, onFocus],
  );

  useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e: MouseEvent) => {
      if (!resizeRef.current) return;
      const dx = e.clientX - resizeRef.current.startX;
      const dy = e.clientY - resizeRef.current.startY;
      const newW = Math.max(320, resizeRef.current.origW + dx);
      const newH = Math.max(200, resizeRef.current.origH + dy);
      onResize(state.id, newW, newH);
    };
    const handleMouseUp = () => {
      resizeRef.current = null;
      setIsResizing(false);
    };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing, state.id, onResize]);

  if (state.minimized) return null;

  const style: React.CSSProperties = isMobile
    ? {
        top: 0,
        left: 0,
        width: "100vw",
        height: "calc(100dvh - 36px)",
        zIndex: state.zIndex,
        borderRadius: 0,
      }
    : state.maximized
      ? {
          top: 0,
          left: 0,
          width: "100%",
          height: "calc(100% - 40px)",
          zIndex: state.zIndex,
        }
      : {
          top: state.y,
          left: state.x,
          width: state.w,
          height: state.h,
          zIndex: state.zIndex,
        };

  return (
    <div
      ref={windowRef}
      className={`absolute flex flex-col select-none ${isDragging || isResizing ? "" : "transition-shadow"}`}
      style={style}
      onMouseDown={() => onFocus(state.id)}
      role="dialog"
      aria-label={state.title}
    >
      {/* XP Title Bar */}
      <div
        className={`xp-titlebar shrink-0 flex items-center relative ${isMobile ? "h-[26px]" : "h-[30px]"} px-[3px] cursor-move rounded-t-lg`}
        onMouseDown={handleDragStart}
        onDoubleClick={() => onMaximize(state.id)}
      >
        <span className="flex items-center gap-1.5 pl-1 text-white text-[11px] font-bold drop-shadow-[0_1px_1px_rgba(0,0,0,0.6)] truncate flex-1 pointer-events-none">
          <span className="w-4 h-4 flex items-center justify-center shrink-0">
            {state.icon}
          </span>
          {state.title}
        </span>

        {/* Mobile minimize pill */}
        {isMobile && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onMinimize(state.id);
            }}
            className="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 flex items-center justify-center w-12 h-5 z-10"
            aria-label="Küçült"
          >
            <span className="block w-10 h-[5px] rounded-full bg-white/50 active:bg-white/80 transition-colors" />
          </button>
        )}

        <div className="flex items-center gap-[2px] shrink-0">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onMinimize(state.id);
            }}
            className="xp-btn-minimize w-[21px] h-[21px] flex items-center justify-center rounded-sm"
            aria-label="Küçült"
          >
            <Minus className="w-3 h-3 text-white" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onMaximize(state.id);
            }}
            className="xp-btn-maximize w-[21px] h-[21px] flex items-center justify-center rounded-sm"
            aria-label={state.maximized ? "Geri yükle" : "Büyüt"}
          >
            {state.maximized ? (
              <Maximize2 className="w-3 h-3 text-white" />
            ) : (
              <Square className="w-2.5 h-2.5 text-white" />
            )}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClose(state.id);
            }}
            className="xp-btn-close w-[21px] h-[21px] flex items-center justify-center rounded-sm"
            aria-label="Kapat"
          >
            <X className="w-3 h-3 text-white" />
          </button>
        </div>
      </div>

      {/* Window Body */}
      <div className="xp-window-body flex-1 min-h-0 overflow-hidden">
        <div className="xp-window-content h-full flex flex-col overflow-hidden">
          {children}
        </div>
      </div>

      {/* Resize Handle */}
      {!state.maximized && !isMobile && (
        <div
          className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize z-10"
          onMouseDown={handleResizeStart}
          aria-hidden="true"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            className="text-slate-400"
          >
            <path
              d="M14 14L14 8M14 14L8 14M10 14L14 10"
              stroke="currentColor"
              strokeWidth="1.5"
              fill="none"
              strokeLinecap="round"
            />
          </svg>
        </div>
      )}
    </div>
  );
}
