"use client";

import { useState } from "react";
import { Map } from "lucide-react";
import { RoadmapDialog } from "@/components/roadmap-dialog";

export function XpRoadmapPanel() {
  const [showDialog, setShowDialog] = useState(false);
  return (
    <>
      <div className="flex flex-col h-full bg-white text-gray-900">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-[#d6d2c2]">
          <Map className="w-4 h-4 text-[#009999]" />
          <span className="text-xs font-medium text-gray-700">
            Geliştirme Yol Haritası
          </span>
          <button
            onClick={() => setShowDialog(true)}
            className="ml-auto text-[10px] px-2 py-0.5 rounded bg-[#ece9d8] text-[#006666] border border-[#d6d2c2] hover:bg-[#d6d2c2] transition-colors"
          >
            Tam Ekran
          </button>
        </div>
        <div className="flex-1 min-h-0 overflow-auto p-3">
          <RoadmapDialog
            open={showDialog}
            onClose={() => setShowDialog(false)}
          />
          <EmbeddedRoadmap />
        </div>
      </div>
    </>
  );
}

function EmbeddedRoadmap() {
  const phases = [
    {
      title: "Mevcut Durum (v2.0)",
      icon: "✅",
      status: "done" as const,
      progress: 100,
      color: "text-[#339966]",
      bar: "bg-emerald-500",
    },
    {
      title: "Faz 1 — Workflow Engine",
      icon: "⚡",
      status: "done" as const,
      progress: 100,
      color: "text-[#cc9900]",
      bar: "bg-emerald-500",
    },
    {
      title: "Faz 2 — Domain Skills",
      icon: "🧠",
      status: "done" as const,
      progress: 100,
      color: "text-purple-400",
      bar: "bg-emerald-500",
    },
    {
      title: "Faz 2.5 — Browser Use",
      icon: "🌐",
      status: "planned" as const,
      progress: 0,
      color: "text-lime-400",
      bar: "bg-lime-500",
    },
    {
      title: "Faz 3 — Veri Analizi",
      icon: "📊",
      status: "planned" as const,
      progress: 0,
      color: "text-sky-400",
      bar: "bg-sky-500",
    },
    {
      title: "Faz 4 — Gelişmiş RAG",
      icon: "📚",
      status: "planned" as const,
      progress: 0,
      color: "text-indigo-400",
      bar: "bg-indigo-500",
    },
    {
      title: "Faz 5 — Güvenlik",
      icon: "🛡️",
      status: "wip" as const,
      progress: 20,
      color: "text-red-400",
      bar: "bg-red-400",
    },
    {
      title: "Faz 6 — Performans",
      icon: "🚀",
      status: "done" as const,
      progress: 100,
      color: "text-[#cc9900]",
      bar: "bg-emerald-500",
    },
    {
      title: "Faz 7 — API Entegrasyon",
      icon: "🔌",
      status: "wip" as const,
      progress: 30,
      color: "text-cyan-400",
      bar: "bg-cyan-400",
    },
    {
      title: "Faz 8 — Multimedya",
      icon: "🎨",
      status: "wip" as const,
      progress: 20,
      color: "text-pink-400",
      bar: "bg-pink-400",
    },
    {
      title: "Faz 9 — Kişiselleştirme",
      icon: "👤",
      status: "wip" as const,
      progress: 55,
      color: "text-violet-400",
      bar: "bg-violet-400",
    },
    {
      title: "Faz 10 — Gerçek Zamanlı İşbirliği",
      icon: "🤝",
      status: "wip" as const,
      progress: 20,
      color: "text-rose-400",
      bar: "bg-rose-400",
    },
    {
      title: "Faz 11 — Otonom Ekosistem",
      icon: "🌐",
      status: "wip" as const,
      progress: 50,
      color: "text-orange-400",
      bar: "bg-orange-400",
    },
    {
      title: "Faz 12 — Kolektif Bilinç",
      icon: "🧬",
      status: "planned" as const,
      progress: 0,
      color: "text-fuchsia-400",
      bar: "bg-fuchsia-500",
    },
    {
      title: "Faz 13 — Kiro IDE",
      icon: "🔮",
      status: "wip" as const,
      progress: 30,
      color: "text-[#009999]",
      bar: "bg-teal-400",
    },
  ];

  const statusLabel = {
    done: "Tamamlandı",
    wip: "Devam Ediyor",
    planned: "Planlanmış",
  };
  const statusCls = {
    done: "bg-[#e6f5e6] text-[#339966]",
    wip: "bg-[#fff8e6] text-[#cc9900]",
    planned: "bg-gray-200 text-gray-500",
  };

  const totalProgress = Math.round(
    phases.reduce((s, p) => s + p.progress, 0) / phases.length,
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 mb-2">
        <div className="flex-1">
          <div className="h-2 rounded-full bg-[#ece9d8] overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-amber-400 to-rose-500 transition-all"
              style={{ width: `${totalProgress}%` }}
            />
          </div>
        </div>
        <span className="text-[11px] text-gray-500 tabular-nums shrink-0">
          %{totalProgress}
        </span>
      </div>
      {phases.map((p, i) => (
        <div
          key={i}
          className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg bg-[#f5f3e8] hover:bg-[#e8e4d4] transition-colors"
        >
          <span className="text-base shrink-0">{p.icon}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={`text-[11px] font-semibold truncate ${p.color}`}>
                {p.title}
              </span>
              <span
                className={`text-[9px] px-1.5 py-0.5 rounded-full shrink-0 ${statusCls[p.status]}`}
              >
                {statusLabel[p.status]}
              </span>
            </div>
            <div className="mt-1 flex items-center gap-2">
              <div className="flex-1 h-1 rounded-full bg-[#d6d2c2] overflow-hidden">
                <div
                  className={`h-full rounded-full ${p.bar} transition-all`}
                  style={{ width: `${p.progress}%` }}
                />
              </div>
              <span className="text-[9px] text-gray-500 tabular-nums w-6 text-right">
                %{p.progress}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
