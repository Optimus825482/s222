"use client";

import { useState, useEffect } from "react";
import {
  MessageSquare,
  Users,
  Database,
  TrendingUp,
  Send,
  RefreshCw,
  Bell,
} from "lucide-react";

interface AgentMessage {
  id: string;
  from_agent: string;
  to_agent: string;
  message_type: string;
  content: string;
  priority: number;
  requires_response: boolean;
  created_at: string;
}

interface SharedKnowledge {
  key: string;
  value: any;
  source_agent: string;
  tags: string[];
  created_at: string;
}

interface AgentStatus {
  agent_role: string;
  pending_messages: number;
  status: string;
}

const AGENT_COLORS: Record<string, string> = {
  orchestrator: "bg-purple-500",
  thinker: "bg-blue-500",
  researcher: "bg-green-500",
  speed: "bg-yellow-500",
  reasoner: "bg-orange-500",
  critic: "bg-red-500",
};

const AGENT_ICONS: Record<string, string> = {
  orchestrator: "🎯",
  thinker: "🧠",
  researcher: "🔍",
  speed: "⚡",
  reasoner: "🔢",
  critic: "✅",
};

export default function InterAgentMonitorPanel() {
  const [activeTab, setActiveTab] = useState<"messages" | "knowledge" | "agents">("messages");
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [knowledge, setKnowledge] = useState<SharedKnowledge[]>([]);
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    total_messages: 0,
    total_knowledge: 0,
    active_agents: 0,
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch message history
      const msgRes = await fetch("/api/inter-agent/messages");
      if (msgRes.ok) {
        const msgData = await msgRes.json();
        setMessages(msgData.messages || []);
      }

      // Fetch shared knowledge
      const knowRes = await fetch("/api/inter-agent/knowledge");
      if (knowRes.ok) {
        const knowData = await knowRes.json();
        setKnowledge(knowData.knowledge || []);
      }

      // Fetch agent statuses
      const statusRes = await fetch("/api/inter-agent/status");
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setAgentStatuses(statusData.agents || []);
        setStats({
          total_messages: statusData.total_messages || 0,
          total_knowledge: statusData.total_knowledge || 0,
          active_agents: statusData.active_agents || 0,
        });
      }
    } catch (err) {
      console.error("Failed to fetch inter-agent data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString("tr-TR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const getMessageTypeColor = (type: string) => {
    switch (type) {
      case "direct":
        return "bg-blue-500/20 text-blue-400";
      case "collab_request":
        return "bg-green-500/20 text-green-400";
      case "task_delegation":
        return "bg-orange-500/20 text-orange-400";
      case "alert":
        return "bg-red-500/20 text-red-400";
      case "broadcast":
        return "bg-purple-500/20 text-purple-400";
      default:
        return "bg-slate-500/20 text-slate-400";
    }
  };

  return (
    <div className="h-full flex flex-col bg-slate-900 text-white">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <MessageSquare className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-semibold">Agent İletişim Monitörü</h2>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 p-4 border-b border-slate-700">
        <div className="bg-slate-800 rounded-lg p-3">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <Send className="w-3 h-3" />
            Toplam Mesaj
          </div>
          <div className="text-2xl font-bold text-blue-400">{stats.total_messages}</div>
        </div>
        <div className="bg-slate-800 rounded-lg p-3">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <Database className="w-3 h-3" />
            Paylaşılan Bilgi
          </div>
          <div className="text-2xl font-bold text-green-400">{stats.total_knowledge}</div>
        </div>
        <div className="bg-slate-800 rounded-lg p-3">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <Users className="w-3 h-3" />
            Aktif Agent
          </div>
          <div className="text-2xl font-bold text-purple-400">{stats.active_agents}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-700">
        <button
          onClick={() => setActiveTab("messages")}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === "messages"
              ? "text-blue-400 border-b-2 border-blue-400"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <MessageSquare className="w-4 h-4 inline mr-2" />
          Mesajlar
        </button>
        <button
          onClick={() => setActiveTab("knowledge")}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === "knowledge"
              ? "text-green-400 border-b-2 border-green-400"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <Database className="w-4 h-4 inline mr-2" />
          Bilgi Havuzu
        </button>
        <button
          onClick={() => setActiveTab("agents")}
          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === "agents"
              ? "text-purple-400 border-b-2 border-purple-400"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <Users className="w-4 h-4 inline mr-2" />
          Agentlar
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === "messages" && (
          <div className="space-y-3">
            {messages.length === 0 ? (
              <div className="text-center text-slate-500 py-8">
                <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>Henüz mesaj yok</p>
                <p className="text-xs mt-1">Agentlar birbirleriyle iletişim kurduğunda burada görünecek</p>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className="bg-slate-800 rounded-lg p-3 border border-slate-700"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs ${getMessageTypeColor(msg.message_type)}`}>
                        {msg.message_type}
                      </span>
                      <span className="text-xs text-slate-500">{formatDate(msg.created_at)}</span>
                    </div>
                    {msg.requires_response && (
                      <span className="text-xs text-amber-400 flex items-center gap-1">
                        <Bell className="w-3 h-3" />
                        Yanıt bekleniyor
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className={`px-2 py-0.5 rounded text-xs ${AGENT_COLORS[msg.from_agent] || "bg-slate-600"}`}>
                      {AGENT_ICONS[msg.from_agent]} {msg.from_agent}
                    </span>
                    <span className="text-slate-500">→</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${AGENT_COLORS[msg.to_agent] || "bg-slate-600"}`}>
                      {AGENT_ICONS[msg.to_agent]} {msg.to_agent}
                    </span>
                  </div>
                  <p className="text-sm text-slate-300 mt-2 line-clamp-2">{msg.content}</p>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === "knowledge" && (
          <div className="space-y-3">
            {knowledge.length === 0 ? (
              <div className="text-center text-slate-500 py-8">
                <Database className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>Henüz paylaşılan bilgi yok</p>
                <p className="text-xs mt-1">Agentlar bilgi paylaştığında burada görünecek</p>
              </div>
            ) : (
              knowledge.map((know, idx) => (
                <div
                  key={idx}
                  className="bg-slate-800 rounded-lg p-3 border border-slate-700"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-green-400">{know.key}</span>
                    <span className="text-xs text-slate-500">{formatDate(know.created_at)}</span>
                  </div>
                  <p className="text-sm text-slate-300 mb-2">
                    {typeof know.value === "object"
                      ? JSON.stringify(know.value, null, 2).slice(0, 200)
                      : String(know.value).slice(0, 200)}
                  </p>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-xs ${AGENT_COLORS[know.source_agent] || "bg-slate-600"}`}>
                      {AGENT_ICONS[know.source_agent]} {know.source_agent}
                    </span>
                    {know.tags?.map((tag, i) => (
                      <span key={i} className="px-2 py-0.5 rounded text-xs bg-slate-700 text-slate-400">
                        #{tag}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === "agents" && (
          <div className="space-y-3">
            {agentStatuses.length === 0 ? (
              <div className="text-center text-slate-500 py-8">
                <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>Agent durumu bulunamadı</p>
              </div>
            ) : (
              agentStatuses.map((agent) => (
                <div
                  key={agent.agent_role}
                  className="bg-slate-800 rounded-lg p-3 border border-slate-700"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full ${AGENT_COLORS[agent.agent_role] || "bg-slate-600"} flex items-center justify-center text-lg`}>
                        {AGENT_ICONS[agent.agent_role]}
                      </div>
                      <div>
                        <h3 className="font-medium capitalize">{agent.agent_role}</h3>
                        <p className="text-xs text-slate-400">
                          {agent.pending_messages > 0
                            ? `${agent.pending_messages} bekleyen mesaj`
                            : "Bekleyen mesaj yok"}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          agent.status === "healthy" ? "bg-green-500" : "bg-red-500"
                        }`}
                      />
                      <span className="text-xs text-slate-400">{agent.status}</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}