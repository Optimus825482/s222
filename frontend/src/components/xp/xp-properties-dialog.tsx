"use client";

import type { DesktopApp } from "./xp-apps";

interface Props {
  app: DesktopApp;
  onClose: () => void;
  onOpen: () => void;
}

export function XpPropertiesDialog({ app, onClose, onOpen }: Props) {
  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/40">
      <div className="w-full max-w-[92vw] sm:w-[380px] rounded-lg overflow-hidden shadow-2xl border border-[#0054e3]">
        <div className="flex items-center justify-between px-3 py-1.5 bg-gradient-to-r from-[#0054e3] via-[#0066ff] to-[#3b8aff]">
          <span className="text-white text-xs font-bold tracking-wide">
            {app.title} — Özellikler
          </span>
          <button
            onClick={onClose}
            className="w-5 h-5 rounded-sm bg-red-500 hover:bg-red-400 text-white text-[11px] font-bold flex items-center justify-center leading-none border border-red-700"
          >
            &#10005;
          </button>
        </div>
        <div className="bg-[#ece9d8] p-5">
          <div className="flex items-center gap-4 mb-4 pb-4 border-b border-gray-400/40">
            <div
              className="w-14 h-14 rounded-lg flex items-center justify-center shadow-md"
              style={{
                backgroundColor: app.color + "20",
                border: `2px solid ${app.color}`,
              }}
            >
              <span style={{ color: app.color }}>{app.icon}</span>
            </div>
            <div>
              <h3 className="text-[14px] font-bold text-gray-900">
                {app.title}
              </h3>
              <p className="text-[11px] text-gray-500 mt-0.5">
                Kategori: {app.group}
              </p>
            </div>
          </div>
          <div className="mb-4">
            <label className="text-[11px] font-bold text-gray-600 uppercase tracking-wider block mb-1.5">
              Açıklama
            </label>
            <p className="text-[12px] text-gray-700 leading-relaxed bg-white rounded border border-gray-300 p-3">
              {app.description}
            </p>
          </div>
          <div className="bg-white rounded border border-gray-300 p-3 mb-4">
            <div className="grid grid-cols-2 gap-y-2 text-[11px]">
              <span className="text-gray-500">Tür:</span>
              <span className="text-gray-800 font-medium">
                Uygulama Penceresi
              </span>
              <span className="text-gray-500">Varsayılan Boyut:</span>
              <span className="text-gray-800 font-medium">
                {app.defaultW} × {app.defaultH} px
              </span>
              <span className="text-gray-500">Grup:</span>
              <span className="text-gray-800 font-medium">{app.group}</span>
              <span className="text-gray-500">Kısayol:</span>
              <span className="text-gray-800 font-medium">
                Çift tıkla ile aç
              </span>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={onOpen}
              className="px-4 py-1.5 text-[12px] bg-white hover:bg-gray-50 border border-gray-400 rounded text-gray-700 font-medium shadow-sm active:shadow-inner"
            >
              Aç
            </button>
            <button
              onClick={onClose}
              className="px-5 py-1.5 text-[12px] bg-[#ece9d8] hover:bg-[#ddd8c6] border border-gray-400 rounded text-gray-700 font-medium shadow-sm active:shadow-inner"
            >
              Tamam
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
