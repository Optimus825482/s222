"use client";

import { useState, useEffect, useCallback } from "react";
import { Users, Globe, Wrench } from "lucide-react";
import { AGENT_CONFIG } from "@/lib/agents";
import { api } from "@/lib/api";
import type { AgentRole } from "@/lib/types";
import dynamic from "next/dynamic";

const AgentEcosystemMap = dynamic(
  () =>
    import("@/components/agent-ecosystem-map").then((m) => ({
      default: m.AgentEcosystemMap,
    })),
  { ssr: false },
);

type Tab = "agents" | "ecosystem" | "tools";

export function XpAgentsPanel() {
  const [tab, setTab] = useState<Tab>("agents");
  const [toolsByRole, setToolsByRole] = useState<Record<string, string[]>>({});
  const [toolsLoading, setToolsLoading] = useState(false);

  const loadTools = useCallback(async () => {
    setToolsLoading(true);
    try {
      const data = await api.getAgentTools();
      setToolsByRole(data);
    } catch {
      setToolsByRole({});
    } finally {
      setToolsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === "tools") loadTools();
  }, [tab, loadTools]);

  return (
    <div className="flex flex-col h-full bg-white text-gray-900">
      {/* Tab bar */}
      <div className="flex border-b border-[#d6d2c2] bg-[#ece9d8]">
        <button
          onClick={() => setTab("agents")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border-r border-[#d6d2c2] transition-colors ${
            tab === "agents"
              ? "bg-white text-gray-900 border-b-white -mb-px"
              : "text-gray-600 hover:bg-[#f5f3e8]"
          }`}
        >
          <Users className="w-3.5 h-3.5 text-[#cc3366]" />
          Agent Durumları
        </button>
        <button
          onClick={() => setTab("tools")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border-r border-[#d6d2c2] transition-colors ${
            tab === "tools"
              ? "bg-white text-gray-900 border-b-white -mb-px"
              : "text-gray-600 hover:bg-[#f5f3e8]"
          }`}
        >
          <Wrench className="w-3.5 h-3.5 text-[#8b5cf6]" />
          Araçlar
        </button>
        <button
          onClick={() => setTab("ecosystem")}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border-r border-[#d6d2c2] transition-colors ${
            tab === "ecosystem"
              ? "bg-white text-gray-900 border-b-white -mb-px"
              : "text-gray-600 hover:bg-[#f5f3e8]"
          }`}
        >
          <Globe className="w-3.5 h-3.5 text-[#06b6d4]" />
          Ekosistem
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-auto">
        {tab === "agents" && (
          <div className="p-3 space-y-2">
            {(
              Object.entries(AGENT_CONFIG) as [
                AgentRole,
                (typeof AGENT_CONFIG)[AgentRole],
              ][]
            ).map(([role, cfg]) => (
              <div
                key={role}
                className="rounded-lg bg-[#f5f3e8] p-3 border-l-2"
                style={{ borderColor: cfg.color }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{cfg.icon}</span>
                    <span
                      className="text-xs font-semibold"
                      style={{ color: cfg.color }}
                    >
                      {cfg.name}
                    </span>
                  </div>
                  <span className="text-[10px] text-gray-500">idle</span>
                </div>
                <div className="text-[10px] text-gray-500 mt-1 capitalize">
                  {role}
                </div>
              </div>
            ))}
          </div>
        )}
        {tab === "tools" && (
          <div className="p-3 space-y-3">
            {toolsLoading ? (
              <p className="text-xs text-gray-500">Yükleniyor…</p>
            ) : (
              Object.entries(toolsByRole).map(([role, tools]) => {
                const cfg = AGENT_CONFIG[role as AgentRole];
                const name = cfg?.name ?? role;
                const color = cfg?.color ?? "#6b7280";
                return (
                  <div
                    key={role}
                    className="rounded-lg bg-[#f5f3e8] p-3 border-l-2"
                    style={{ borderColor: color }}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-semibold" style={{ color }}>
                        {name}
                      </span>
                      <span className="text-[10px] text-gray-500">
                        {tools?.length ?? 0} araç
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {(tools ?? []).map((t) => (
                        <span
                          key={t}
                          className="px-1.5 py-0.5 rounded text-[10px] bg-white border border-[#d6d2c2] text-gray-700"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
        {tab === "ecosystem" && <AgentEcosystemMap />}
      </div>
    </div>
  );
}
