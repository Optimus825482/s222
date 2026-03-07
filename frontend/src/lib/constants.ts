// Shared constants for frontend
// Centralized to avoid duplication across components

import { AgentRole, AgentStatus } from "./types";

export const AGENT_ROLES: AgentRole[] = [
  "orchestrator",
  "thinker",
  "speed",
  "researcher",
  "reasoner",
  "critic",
];

// Unicode emoji constants for agent roles
export const ROLE_ICON: Record<AgentRole, string> = {
  orchestrator: "\uD83E\uDDE0", // 🧠
  thinker: "\uD83D\uDD2C",      // 🔬
  speed: "\u26A1",              // ⚡
  researcher: "\uD83D\uDD0D",   // 🔍
  reasoner: "\uD83C\uDF0A",     // 🌊
  critic: "\uD83C\uDFAF",       // 🎯
};

export const ROLE_COLOR: Record<AgentRole, string> = {
  orchestrator: "#ec4899",
  thinker: "#00e5ff",
  speed: "#a78bfa",
  researcher: "#f59e0b",
  reasoner: "#10b981",
  critic: "#06b6d4",
};

export const STATUS_DOT: Record<AgentStatus, string> = {
  active: "bg-green-400",
  idle: "bg-yellow-400",
  error: "bg-red-400",
  offline: "bg-gray-500",
};

export const STATUS_LABEL: Record<AgentStatus, string> = {
  active: "Aktif",
  idle: "Boşta",
  error: "Hata",
  offline: "Çevrimdışı",
};
