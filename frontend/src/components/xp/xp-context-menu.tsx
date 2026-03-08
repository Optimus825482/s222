"use client";

import { useState } from "react";
import { FeatherIcon } from "./xp-feather-icon";

interface DesktopCtxMenuProps {
  x: number;
  y: number;
  onClose: () => void;
  onOpenApp: (id: string) => void;
  onResetIcons: () => void;
  onShowAbout: () => void;
  onChangeWallpaper: (key: string) => void;
  currentWallpaper: string;
}

export const WALLPAPER_PRESETS: Record<
  string,
  { label: string; gradient: string; preview: string }
> = {
  bliss: {
    label: "Bliss (Klasik)",
    gradient:
      "linear-gradient(180deg, #1a3a8a 0%, #1e4fa0 25%, #2a6ab8 45%, #4a8a3a 60%, #3a7a2a 75%, #2a5a1a 100%)",
    preview: "#1e4fa0",
  },
  royal: {
    label: "Kraliyet Mavisi",
    gradient:
      "linear-gradient(180deg, #0a1a4a 0%, #0e2a6a 30%, #1a3a8a 60%, #0e2a6a 85%, #0a1a4a 100%)",
    preview: "#0e2a6a",
  },
  ocean: {
    label: "Okyanus",
    gradient:
      "linear-gradient(135deg, #0a2a5a 0%, #0e3a7a 25%, #1a5090 50%, #0e3a7a 75%, #0a2a5a 100%)",
    preview: "#0e3a7a",
  },
  olive: {
    label: "Zeytin Yeşili",
    gradient:
      "linear-gradient(180deg, #2a3a1a 0%, #3a5a2a 30%, #4a6a3a 55%, #3a5a2a 80%, #2a3a1a 100%)",
    preview: "#3a5a2a",
  },
  silver: {
    label: "Gümüş",
    gradient:
      "linear-gradient(180deg, #4a5a6a 0%, #6a7a8a 30%, #8a9aaa 55%, #6a7a8a 80%, #4a5a6a 100%)",
    preview: "#6a7a8a",
  },
  sunset: {
    label: "Gün Batımı",
    gradient:
      "linear-gradient(180deg, #1a1a3a 0%, #3a1a4a 25%, #6a2a3a 50%, #8a4a2a 75%, #4a2a1a 100%)",
    preview: "#3a1a4a",
  },
  midnight: {
    label: "Gece Yarısı",
    gradient:
      "linear-gradient(180deg, #0a0a1a 0%, #0e1a2a 30%, #1a2a3a 55%, #0e1a2a 80%, #0a0a1a 100%)",
    preview: "#0e1a2a",
  },
};

export function DesktopContextMenu({
  x,
  y,
  onClose,
  onOpenApp,
  onResetIcons,
  onShowAbout,
  onChangeWallpaper,
  currentWallpaper,
}: DesktopCtxMenuProps) {
  const [showWpMenu, setShowWpMenu] = useState(false);
  return (
    <div
      className="xp-ctx-menu fixed z-[200] bg-white rounded shadow-[2px_2px_8px_rgba(0,0,0,0.3)] border border-gray-300 py-1 min-w-[180px] max-w-[90vw] text-[12px] text-gray-800"
      style={{
        left: Math.min(x, window.innerWidth - 200),
        top: Math.min(y, window.innerHeight - 250),
      }}
      onMouseDown={(e) => e.stopPropagation()}
    >
      <button
        onClick={() => {
          onClose();
          onOpenApp("chat");
        }}
        className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
      >
        <FeatherIcon name="message-square" color="currentColor" size={14} />
        Yeni Görev
      </button>
      <button
        onClick={() => {
          onClose();
          onOpenApp("reports");
        }}
        className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
      >
        <FeatherIcon name="folder" color="currentColor" size={14} />
        Raporlar
      </button>
      <button
        onClick={() => {
          onClose();
          onOpenApp("search");
        }}
        className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
      >
        <FeatherIcon name="search" color="currentColor" size={14} />
        Arama
      </button>
      <button
        onClick={() => {
          onClose();
          window.location.reload();
        }}
        className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
      >
        <FeatherIcon name="refresh-cw" color="currentColor" size={14} />
        Yenile
      </button>
      <div className="border-t border-gray-200 my-1" />
      <button
        onClick={() => {
          onClose();
          onOpenApp("insights");
        }}
        className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
      >
        <FeatherIcon name="cpu" color="currentColor" size={14} />
        Sistem Durumu
      </button>
      <button
        onClick={() => {
          onClose();
          onOpenApp("agents");
        }}
        className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
      >
        <FeatherIcon name="users" color="currentColor" size={14} />
        Agentlar
      </button>

      <div className="border-t border-gray-200 my-1" />
      {/* Wallpaper submenu */}
      <div className="relative">
        <button
          onClick={() => setShowWpMenu(!showWpMenu)}
          onMouseEnter={() => setShowWpMenu(true)}
          className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5 justify-between"
        >
          <span className="flex items-center gap-2.5">
            <FeatherIcon name="image" color="currentColor" size={14} />
            Arka Planı Değiştir
          </span>
          <span className="text-[10px]">▶</span>
        </button>
        {showWpMenu && (
          <div
            className="absolute left-full top-0 ml-1 bg-white rounded shadow-[2px_2px_8px_rgba(0,0,0,0.3)] border border-gray-300 py-1 min-w-[170px] text-[12px] text-gray-800 z-[201]"
            onMouseLeave={() => setShowWpMenu(false)}
          >
            {Object.entries(WALLPAPER_PRESETS).map(([key, wp]) => (
              <button
                key={key}
                onClick={() => {
                  onChangeWallpaper(key);
                  onClose();
                }}
                className={`w-full text-left px-3 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5 ${currentWallpaper === key ? "font-bold" : ""}`}
              >
                <span
                  className="w-4 h-3 rounded-sm border border-gray-400 shrink-0"
                  style={{ background: wp.preview }}
                />
                {wp.label}
                {currentWallpaper === key && <span className="ml-auto">✓</span>}
              </button>
            ))}
          </div>
        )}
      </div>
      <button
        onClick={() => {
          onClose();
          onResetIcons();
        }}
        className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
      >
        <FeatherIcon name="activity" color="currentColor" size={14} />
        Simgeleri Düzenle
      </button>
      <button
        onClick={() => {
          onClose();
          onShowAbout();
        }}
        className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
      >
        <FeatherIcon name="hard-drive" color="currentColor" size={14} />
        Hakkında
      </button>
    </div>
  );
}

interface IconCtxMenuProps {
  x: number;
  y: number;
  appId: string;
  onClose: () => void;
  onOpenApp: (id: string) => void;
  onShowProps: (id: string) => void;
}

export function IconContextMenu({
  x,
  y,
  appId,
  onClose,
  onOpenApp,
  onShowProps,
}: IconCtxMenuProps) {
  return (
    <div
      className="xp-ctx-menu fixed z-[200] bg-white rounded shadow-[2px_2px_8px_rgba(0,0,0,0.3)] border border-gray-300 py-1 min-w-[180px] max-w-[90vw] text-[12px] text-gray-800"
      style={{
        left: Math.min(x, window.innerWidth - 200),
        top: Math.min(y, window.innerHeight - 120),
      }}
      onMouseDown={(e) => e.stopPropagation()}
    >
      <button
        onClick={() => {
          onOpenApp(appId);
          onClose();
        }}
        className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5 font-bold"
      >
        <FeatherIcon name="folder" color="currentColor" size={14} />
        Aç
      </button>
      <div className="border-t border-gray-200 my-1" />
      <button
        onClick={() => {
          onShowProps(appId);
          onClose();
        }}
        className="w-full text-left px-4 py-1.5 hover:bg-[#2f71cd] hover:text-white flex items-center gap-2.5"
      >
        <FeatherIcon name="info" color="currentColor" size={14} />
        Özellikler
      </button>
    </div>
  );
}
