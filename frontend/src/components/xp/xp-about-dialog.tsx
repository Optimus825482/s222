"use client";

import { FeatherIcon } from "./xp-feather-icon";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function XpAboutDialog({ open, onClose }: Props) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/40">
      <div className="w-full max-w-[92vw] sm:w-[440px] rounded-lg overflow-hidden shadow-2xl border border-[#0054e3]">
        <div className="flex items-center justify-between px-3 py-1.5 bg-gradient-to-r from-[#0054e3] via-[#0066ff] to-[#3b8aff]">
          <span className="text-white text-xs font-bold tracking-wide">
            Hakkında
          </span>
          <button
            onClick={onClose}
            className="w-5 h-5 rounded-sm bg-red-500 hover:bg-red-400 text-white text-[11px] font-bold flex items-center justify-center leading-none border border-red-700"
          >
            &#10005;
          </button>
        </div>
        <div className="bg-white p-6">
          <div className="flex items-center gap-4 mb-5">
            <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-[#0054e3] to-[#7c3aed] flex items-center justify-center shadow-lg">
              <FeatherIcon name="hexagon" color="white" size={36} />
            </div>
            <div>
              <h2 className="text-[15px] font-bold text-gray-900 leading-tight">
                Multi-Agent İşletim Sistemi
              </h2>
              <p className="text-[11px] text-gray-500 mt-0.5">Sürüm 1.0.0</p>
            </div>
          </div>
          <div className="border-t border-gray-200 my-4" />
          <p className="text-[12px] text-gray-700 leading-relaxed mb-4">
            Otonom yapay zeka agentlarını orkestre eden, izleyen ve optimize
            eden yeni nesil çoklu-agent yönetim platformu. Gerçek zamanlı görev
            akışı, bellek yönetimi, benchmark analizi ve tam özerk evrim
            desteği.
          </p>
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
            <p className="text-[11px] text-gray-400 mb-3 text-center uppercase tracking-wider">
              Ekip
            </p>
            <div className="flex items-start justify-center gap-8">
              <div className="flex flex-col items-center gap-1.5">
                <div className="w-11 h-11 rounded-full bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center text-white text-sm font-bold shadow">
                  EE
                </div>
                <p className="text-[13px] font-semibold text-gray-800">
                  Erkan Erdem
                </p>
                <p className="text-[10px] text-blue-600 font-medium">
                  Full Stack Developer
                </p>
              </div>
              <div className="flex flex-col items-center gap-1.5">
                <div className="w-11 h-11 rounded-full bg-gradient-to-br from-purple-500 to-pink-400 flex items-center justify-center text-white text-sm font-bold shadow">
                  YA
                </div>
                <p className="text-[13px] font-semibold text-gray-800">
                  Yiğit Avcı
                </p>
                <p className="text-[10px] text-purple-600 font-medium">
                  Project Builder
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center justify-between mt-5">
            <p className="text-[10px] text-gray-400">
              © 2025 Tüm hakları saklıdır.
            </p>
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
