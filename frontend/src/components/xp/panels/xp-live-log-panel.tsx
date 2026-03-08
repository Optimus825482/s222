"use client";

import { useSyncExternalStore } from "react";
import { getWSSnapshot, subscribeWS } from "@/lib/ws-store";
import { LiveEventLog } from "@/components/live-event-log";
import { Radio, ScrollText, Loader2, XCircle } from "lucide-react";

export function XpLiveLogPanel() {
  const snapshot = useSyncExternalStore(
    subscribeWS,
    getWSSnapshot,
    getWSSnapshot,
  );
  const { status, liveEvents } = snapshot;

  const isConnected =
    status === "idle" || status === "running" || status === "complete";
  const isActive = status === "running";
  const hasEvents = liveEvents.length > 0;

  return (
    <div className="flex flex-col h-full min-h-0 bg-white text-gray-900">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[#d6d2c2]">
        <ScrollText className="w-4 h-4 text-[#0099cc]" />
        <span className="text-xs font-medium text-gray-700">
          Canlı Olay Akışı
        </span>
        <span
          className={`ml-auto text-[10px] px-1.5 py-0.5 rounded ${
            isActive
              ? "bg-[#e6f5e6] text-[#339966]"
              : status === "connecting"
                ? "bg-[#fff8e6] text-[#cc9900]"
                : status === "error"
                  ? "bg-[#ffe6e6] text-[#cc3333]"
                  : isConnected
                    ? "bg-[#e6f5e6] text-[#339966]"
                    : "bg-gray-200 text-gray-500"
          }`}
        >
          {isActive
            ? "Aktif"
            : status === "connecting"
              ? "Bağlanıyor"
              : status === "error"
                ? "Hata"
                : status === "complete"
                  ? "Tamamlandı"
                  : isConnected
                    ? "Bağlı"
                    : "Bekleniyor"}
        </span>
      </div>

      <div className="flex-1 min-h-0 overflow-auto">
        {hasEvents ? (
          <LiveEventLog events={liveEvents} status={status} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-500 px-6">
            {status === "error" ? (
              <>
                <XCircle className="w-8 h-8 text-red-400/60" />
                <p className="text-xs text-center text-red-400/80">
                  WebSocket bağlantısı kurulamadı
                </p>
                <p className="text-[10px] text-center text-gray-500">
                  Backend&apos;in çalıştığından emin olun (port 8001)
                </p>
                <button
                  onClick={() => window.location.reload()}
                  className="mt-1 text-[10px] px-3 py-1 rounded bg-[#ece9d8] hover:bg-[#d6d2c2] text-[#0099cc] border border-[#d6d2c2] transition-colors"
                >
                  Yeniden Bağlan
                </button>
              </>
            ) : isConnected ? (
              <>
                <Radio className="w-8 h-8 text-[#339966]/40" />
                <p className="text-xs text-center">
                  WebSocket bağlı — görev bekleniyor
                </p>
                <p className="text-[10px] text-center text-gray-500">
                  Sohbet panelinden bir görev gönderin, olaylar burada görünecek
                </p>
              </>
            ) : (
              <>
                <Loader2 className="w-6 h-6 animate-spin text-yellow-400/60" />
                <p className="text-xs text-center">Bağlanıyor...</p>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
