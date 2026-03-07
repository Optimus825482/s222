"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Search,
  RefreshCw,
  ToggleLeft,
  ToggleRight,
  ChevronDown,
  ChevronUp,
  Package,
  Sparkles,
  Shield,
  Wrench,
} from "lucide-react";
import { domainApi } from "@/lib/api";

/* ── Types ── */
interface DomainSkill {
  domain_id: string;
  name: string;
  name_tr: string;
  description: string;
  source: "builtin" | "discovered";
  enabled: number;
  installed_at: string;
  usage_count: number;
  rating: number;
  version: string;
  author: string;
  capabilities: string[];
  tool_count: number;
  tools: { name: string; description: string; params: string[] }[];
  active: boolean;
}

const SOURCE_BADGE: Record<
  string,
  { label: string; cls: string; icon: typeof Package }
> = {
  builtin: {
    label: "Yerleşik",
    cls: "bg-emerald-400/10 text-emerald-400 border-emerald-400/30",
    icon: Shield,
  },
  discovered: {
    label: "Topluluk",
    cls: "bg-purple-400/10 text-purple-400 border-purple-400/30",
    icon: Sparkles,
  },
};

const DOMAIN_ICONS: Record<string, string> = {
  finance: "💰",
  legal: "⚖️",
  engineering: "🔧",
  academic: "🎓",
  healthcare: "🏥",
  marketing: "📈",
};

export function DomainMarketplacePanel() {
  const [skills, setSkills] = useState<DomainSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [discovering, setDiscovering] = useState(false);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "builtin" | "discovered">("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await domainApi.getMarketplace();
      setSkills(Array.isArray(data) ? data : []);
    } catch {
      setSkills([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDiscover = async () => {
    setDiscovering(true);
    try {
      await domainApi.discoverSkills();
      await load();
    } catch {
      /* silent */
    } finally {
      setDiscovering(false);
    }
  };

  const handleToggle = async (domainId: string, currentEnabled: number) => {
    setToggling(domainId);
    try {
      await domainApi.toggleDomain(domainId, !currentEnabled);
      setSkills((prev) =>
        prev.map((s) =>
          s.domain_id === domainId
            ? { ...s, enabled: currentEnabled ? 0 : 1 }
            : s,
        ),
      );
    } catch {
      /* silent */
    } finally {
      setToggling(null);
    }
  };

  const filtered = skills.filter((s) => {
    if (filter !== "all" && s.source !== filter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        s.name.toLowerCase().includes(q) ||
        s.name_tr.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.domain_id.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const builtinCount = skills.filter((s) => s.source === "builtin").length;
  const discoveredCount = skills.filter(
    (s) => s.source === "discovered",
  ).length;
  const enabledCount = skills.filter((s) => s.enabled).length;
  const totalTools = skills.reduce((sum, s) => sum + s.tool_count, 0);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 px-4 pt-4 pb-3 border-b border-border/50">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Package className="w-5 h-5 text-purple-400" />
            <h2 className="text-base font-bold text-slate-200">
              Skill Marketplace
            </h2>
          </div>
          <button
            onClick={handleDiscover}
            disabled={discovering}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20 hover:bg-purple-500/20 transition-colors disabled:opacity-50"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${discovering ? "animate-spin" : ""}`}
            />
            {discovering ? "Taranıyor…" : "Yeni Skill Tara"}
          </button>
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-3 text-[11px] text-slate-500 mb-3">
          <span>
            {skills.length} skill · {enabledCount} aktif · {totalTools} araç
          </span>
          <span className="text-slate-700">|</span>
          <span className="text-emerald-500">{builtinCount} yerleşik</span>
          <span className="text-purple-500">{discoveredCount} topluluk</span>
        </div>

        {/* Search + Filter */}
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Skill ara…"
              className="w-full pl-8 pr-3 py-1.5 text-sm bg-slate-800/50 border border-slate-700/50 rounded-lg text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-purple-500/50"
            />
          </div>
          <div className="flex rounded-lg border border-slate-700/50 overflow-hidden">
            {(["all", "builtin", "discovered"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2.5 py-1.5 text-[11px] font-medium transition-colors ${
                  filter === f
                    ? "bg-purple-500/20 text-purple-400"
                    : "text-slate-500 hover:text-slate-300 hover:bg-white/5"
                }`}
              >
                {f === "all"
                  ? "Tümü"
                  : f === "builtin"
                    ? "Yerleşik"
                    : "Topluluk"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
        {loading ? (
          <div className="flex items-center justify-center py-12 text-slate-500 text-sm">
            <RefreshCw className="w-4 h-4 animate-spin mr-2" />
            Yükleniyor…
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-sm">
            {search ? "Sonuç bulunamadı" : "Henüz skill yok"}
          </div>
        ) : (
          filtered.map((skill) => (
            <SkillCard
              key={skill.domain_id}
              skill={skill}
              expanded={expanded === skill.domain_id}
              onToggleExpand={() =>
                setExpanded(
                  expanded === skill.domain_id ? null : skill.domain_id,
                )
              }
              onToggleEnabled={() =>
                handleToggle(skill.domain_id, skill.enabled)
              }
              toggling={toggling === skill.domain_id}
            />
          ))
        )}
      </div>
    </div>
  );
}

/* ── Skill Card ── */
function SkillCard({
  skill,
  expanded,
  onToggleExpand,
  onToggleEnabled,
  toggling,
}: {
  skill: DomainSkill;
  expanded: boolean;
  onToggleExpand: () => void;
  onToggleEnabled: () => void;
  toggling: boolean;
}) {
  const badge = SOURCE_BADGE[skill.source] || SOURCE_BADGE.discovered;
  const BadgeIcon = badge.icon;
  const icon = DOMAIN_ICONS[skill.domain_id] || "🧩";
  const isEnabled = !!skill.enabled;

  return (
    <div
      className={`border rounded-lg transition-colors ${
        isEnabled
          ? "border-slate-700/50 bg-slate-800/30 hover:bg-slate-800/50"
          : "border-slate-800/50 bg-slate-900/30 opacity-60"
      }`}
    >
      {/* Card header */}
      <div className="flex items-center gap-3 px-4 py-3">
        <span className="text-2xl shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-slate-200">
              {skill.name_tr}
            </span>
            <span
              className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border ${badge.cls}`}
            >
              <BadgeIcon className="w-2.5 h-2.5" />
              {badge.label}
            </span>
            <span className="text-[10px] text-slate-600">v{skill.version}</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5 truncate">
            {skill.description}
          </p>
          <div className="flex items-center gap-3 mt-1 text-[10px] text-slate-600">
            <span>
              <Wrench className="w-3 h-3 inline mr-0.5" />
              {skill.tool_count} araç
            </span>
            <span>📊 {skill.usage_count} kullanım</span>
            <span>👤 {skill.author}</span>
          </div>
        </div>

        {/* Toggle + Expand */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onToggleEnabled}
            disabled={toggling || skill.source === "builtin"}
            className={`p-1 rounded transition-colors ${
              skill.source === "builtin"
                ? "opacity-30 cursor-not-allowed"
                : "hover:bg-white/5"
            }`}
            title={
              skill.source === "builtin"
                ? "Yerleşik skill'ler devre dışı bırakılamaz"
                : isEnabled
                  ? "Devre dışı bırak"
                  : "Etkinleştir"
            }
            aria-label={isEnabled ? "Devre dışı bırak" : "Etkinleştir"}
          >
            {isEnabled ? (
              <ToggleRight className="w-6 h-6 text-emerald-400" />
            ) : (
              <ToggleLeft className="w-6 h-6 text-slate-600" />
            )}
          </button>
          <button
            onClick={onToggleExpand}
            className="p-1 rounded hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors"
            aria-label={expanded ? "Daralt" : "Genişlet"}
          >
            {expanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 pb-3 pt-1 border-t border-slate-700/30 space-y-3">
          {/* Capabilities */}
          {skill.capabilities.length > 0 && (
            <div>
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                Yetenekler
              </span>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {skill.capabilities.map((cap) => (
                  <span
                    key={cap}
                    className="px-2 py-0.5 text-[10px] rounded-full bg-slate-700/50 text-slate-400 border border-slate-600/30"
                  >
                    {cap}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Tools list */}
          {skill.tools.length > 0 && (
            <div>
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                Araçlar
              </span>
              <div className="mt-1 space-y-1">
                {skill.tools.map((tool) => (
                  <div
                    key={tool.name}
                    className="flex items-start gap-2 text-[11px]"
                  >
                    <Wrench className="w-3 h-3 mt-0.5 text-slate-600 shrink-0" />
                    <div>
                      <span className="text-slate-300 font-mono">
                        {tool.name}
                      </span>
                      <span className="text-slate-600 ml-1.5">
                        {tool.description}
                      </span>
                      {tool.params && (
                        <div className="text-[10px] text-slate-700 mt-0.5">
                          Params: {tool.params.join(", ")}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
