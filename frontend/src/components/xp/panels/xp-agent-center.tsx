"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import {
  Users,
  Shield,
  GitBranch,
  MessageSquare,
  Fingerprint,
  Crown,
} from "lucide-react";

// Dynamic imports for heavy panels
const XpAgentsPanel = dynamic(
  () =>
    import("./xp-agents-panel").then((m) => ({
      default: m.XpAgentsPanel,
    })),
  { ssr: false },
);

const AutonomousOversightPanel = dynamic(
  () =>
    import("@/components/monitoring-panels").then((m) => ({
      default: m.AutonomousOversightPanel,
    })),
  { ssr: false },
);

const CoordinationPanel = dynamic(
  () =>
    import("@/components/coordination-panel").then((m) => ({
      default: m.CoordinationPanel,
    })),
  { ssr: false },
);

const AgentCommsPanel = dynamic(
  () =>
    import("@/components/agent-comms-panel").then((m) => ({
      default: m.AgentCommsPanel,
    })),
  { ssr: false },
);

const AgentIdentityEditor = dynamic(
  () =>
    import("@/components/agent-identity-editor").then((m) => ({
      default: m.AgentIdentityEditor,
    })),
  { ssr: false },
);

const DynamicRolePanel = dynamic(
  () =>
    import("@/components/dynamic-role-panel").then((m) => ({
      default: m.DynamicRolePanel,
    })),
  { ssr: false },
);

// Tab type
type Tab = "agents" | "oversight" | "coord" | "comms" | "identity" | "roles";

// Tab button style (matching XpWorkflowsWrapper pattern)
const TAB_BUTTON_STYLE = (isActive: boolean): React.CSSProperties => ({
  padding: "6px 14px",
  fontSize: 11,
  fontFamily: "Tahoma, sans-serif",
  fontWeight: isActive ? 600 : 400,
  background: isActive ? "#fff" : "transparent",
  border: isActive ? "1px solid #d6d2c2" : "1px solid transparent",
  borderBottom: isActive ? "1px solid #fff" : "1px solid #d6d2c2",
  borderRadius: "3px 3px 0 0",
  marginBottom: -1,
  cursor: "pointer",
  color: isActive ? "#000" : "#555",
  display: "flex",
  alignItems: "center",
  gap: 4,
});

// Tab configuration
const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "agents", label: "Agentlar", icon: <Users size={12} /> },
  { id: "oversight", label: "Otonom İzleme", icon: <Shield size={12} /> },
  { id: "coord", label: "Koordinasyon", icon: <GitBranch size={12} /> },
  { id: "comms", label: "İletişim", icon: <MessageSquare size={12} /> },
  { id: "identity", label: "Kimlik", icon: <Fingerprint size={12} /> },
  { id: "roles", label: "Roller", icon: <Crown size={12} /> },
];

export function XpAgentCenter() {
  const [tab, setTab] = useState<Tab>("agents");

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Tab bar */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #d6d2c2",
          background: "#ECE9D8",
          padding: "0 4px",
        }}
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={TAB_BUTTON_STYLE(tab === t.id)}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-hidden">
        {tab === "agents" && (
          <div className="h-full overflow-auto bg-white">
            <XpAgentsPanel />
          </div>
        )}
        {tab === "oversight" && (
          <div className="h-full overflow-auto bg-slate-900">
            <AutonomousOversightPanel />
          </div>
        )}
        {tab === "coord" && (
          <div className="h-full overflow-auto bg-slate-900">
            <CoordinationPanel />
          </div>
        )}
        {tab === "comms" && (
          <div className="h-full overflow-auto bg-slate-900">
            <AgentCommsPanel />
          </div>
        )}
        {tab === "identity" && (
          <div className="h-full overflow-auto bg-slate-900">
            <AgentIdentityEditor />
          </div>
        )}
        {tab === "roles" && (
          <div className="h-full overflow-auto bg-slate-900">
            <DynamicRolePanel />
          </div>
        )}
      </div>
    </div>
  );
}

export default XpAgentCenter;