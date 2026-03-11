"use client";

import { useCallback, useEffect, useState } from "react";
import { Wrench, BarChart3 } from "lucide-react";
import dynamic from "next/dynamic";
import { fetcher } from "@/lib/api";

const TeachabilityPanel = dynamic(
  () =>
    import("@/components/tools-panels").then((m) => ({
      default: m.TeachabilityPanel,
    })),
  { ssr: false },
);
const EvalPanel = dynamic(
  () =>
    import("@/components/tools-panels").then((m) => ({
      default: m.EvalPanel,
    })),
  { ssr: false },
);

interface BehaviorSummary {
  total_events: number;
  by_action: Record<string, number>;
}

function UserBehaviorWidget() {
  const [data, setData] = useState<BehaviorSummary | null>(null);
  const load = useCallback(async () => {
    try {
      setData(await fetcher<BehaviorSummary>("/api/analytics/user-behavior"));
    } catch {
      setData(null);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  if (!data) return null;
  const top = Object.entries(data.by_action)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3);
  return (
    <div className="rounded-lg border border-[#d6d2c2] bg-[#faf9f6] p-3">
      <div className="flex items-center gap-2 mb-2">
        <BarChart3 className="w-4 h-4 text-[#6633cc]" />
        <span className="text-xs font-medium text-gray-700">Kullanıcı Davranışı</span>
      </div>
      <p className="text-xs text-gray-600 mb-2">
        Toplam <strong>{(data.total_events ?? 0).toLocaleString("tr-TR")}</strong> olay
      </p>
      {top.length > 0 && (
        <ul className="text-[11px] text-gray-500 space-y-0.5">
          {top.map(([action, count]) => (
            <li key={action}>
              {action}: {count}
            </li>
          ))}
        </ul>
      )}
      <p className="text-[10px] text-gray-400 mt-2">
        Detay için Başlat → İletişim → Kullanıcı Davranışı
      </p>
    </div>
  );
}

export function XpToolsPanel() {
  return (
    <div className="flex flex-col h-full bg-white text-gray-900">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[#d6d2c2]">
        <Wrench className="w-4 h-4 text-[#6633cc]" />
        <span className="text-xs font-medium text-gray-700">Araçlar</span>
      </div>
      <div className="flex-1 overflow-auto space-y-4 p-1">
        <TeachabilityPanel />
        <hr className="border-[#d6d2c2] mx-3" />
        <EvalPanel />
        <hr className="border-[#d6d2c2] mx-3" />
        <UserBehaviorWidget />
      </div>
    </div>
  );
}
