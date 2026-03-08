"use client";

import { useCallback, useEffect, useState } from "react";
import { domainApi } from "@/lib/api";
import {
  Search,
  Package,
  Star,
  Sparkles,
  RefreshCw,
  Zap,
  BookOpen,
  Scale,
  Cpu,
  GraduationCap,
} from "lucide-react";

interface MarketplaceItem {
  id: string;
  type: "domain" | "skill";
  name: string;
  name_tr: string;
  description: string;
  capabilities: string[];
  tool_count: number;
  tools: { name: string; description: string; params?: string[] }[];
  installed: boolean;
  rating: number;
  downloads: number;
  category: string;
  tags: string[];
}

interface MarketplaceStats {
  total_items: number;
  domain_count: number;
  skill_count: number;
  total_tools: number;
  installed_count: number;
}

interface AutoDetectMatch {
  domain_id: string;
  name: string;
  name_tr: string;
  score: number;
  matched_keywords: string[];
  suggested_tools: { name: string; description: string; relevance: number }[];
  capabilities: string[];
}

const DOMAIN_ICONS: Record<string, React.ReactNode> = {
  "domain:finance": <Scale className="w-5 h-5" />,
  "domain:legal": <BookOpen className="w-5 h-5" />,
  "domain:engineering": <Cpu className="w-5 h-5" />,
  "domain:academic": <GraduationCap className="w-5 h-5" />,
};

const DOMAIN_COLORS: Record<string, string> = {
  "domain:finance": "text-emerald-400 bg-emerald-400/10 border-emerald-400/30",
  "domain:legal": "text-purple-400 bg-purple-400/10 border-purple-400/30",
  "domain:engineering": "text-sky-400 bg-sky-400/10 border-sky-400/30",
  "domain:academic": "text-amber-400 bg-amber-400/10 border-amber-400/30",
};

const CATEGORY_TABS = [
  { id: "all", label: "Tümü" },
  { id: "domain", label: "Domain Modülleri" },
  { id: "skill", label: "Beceriler" },
  { id: "custom", label: "Özel" },
];

export function XpMarketplacePanel() {
  const [catalog, setCatalog] = useState<MarketplaceItem[]>([]);
  const [stats, setStats] = useState<MarketplaceStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [expandedItem, setExpandedItem] = useState<string | null>(null);

  // Auto-detect state
  const [detectQuery, setDetectQuery] = useState("");
  const [detectResults, setDetectResults] = useState<AutoDetectMatch[]>([]);
  const [detecting, setDetecting] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [catalogRes, statsRes] = await Promise.all([
        domainApi.getMarketplaceCatalog(
          category !== "all" ? category : undefined,
          search || undefined,
        ),
        domainApi.getMarketplaceStats(),
      ]);
      setCatalog(catalogRes.items || []);
      setStats(statsRes);
    } catch {
      setCatalog([]);
    } finally {
      setLoading(false);
    }
  }, [category, search]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDetect = async () => {
    if (!detectQuery.trim()) return;
    setDetecting(true);
    try {
      const res = await domainApi.autoDetect(detectQuery.trim());
      setDetectResults(res.matches || []);
    } catch {
      setDetectResults([]);
    } finally {
      setDetecting(false);
    }
  };

  const renderStars = (rating: number | undefined) => {
    const r = Number(rating ?? 0);
    const full = Math.floor(r);
    const half = r - full >= 0.5;
    return (
      <span className="flex items-center gap-0.5">
        {Array.from({ length: 5 }, (_, i) => (
          <Star
            key={i}
            className={`w-3 h-3 ${i < full ? "text-amber-400 fill-amber-400" : i === full && half ? "text-amber-400 fill-amber-400/50" : "text-slate-600"}`}
          />
        ))}
        <span className="text-[10px] text-slate-500 ml-1">
          {r.toFixed(1)}
        </span>
      </span>
    );
  };

  return (
    <div className="flex flex-col h-full bg-[#ECE9D8]">
      {/* Stats Header */}
      <div className="bg-gradient-to-r from-[#0A246A] to-[#3A6EA5] px-3 py-2 flex items-center gap-4 text-white">
        <Package className="w-5 h-5" />
        <span className="font-bold text-sm">Skill Marketplace</span>
        {stats && (
          <div className="flex items-center gap-3 ml-auto text-[11px] text-blue-100">
            <span>{stats.total_items} öğe</span>
            <span>·</span>
            <span>{stats.domain_count} domain</span>
            <span>·</span>
            <span>{stats.skill_count} beceri</span>
            <span>·</span>
            <span>{stats.total_tools} araç</span>
          </div>
        )}
        <button
          onClick={loadData}
          className="p-1 hover:bg-white/20 rounded transition-colors"
          title="Yenile"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
          />
        </button>
      </div>

      {/* Auto-Detect Section */}
      <div className="bg-[#F1EFE2] border-b border-[#ACA899] px-3 py-2">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-600 shrink-0" />
          <span className="text-[11px] font-semibold text-[#0A246A] shrink-0">
            Otomatik Tespit:
          </span>
          <input
            type="text"
            value={detectQuery}
            onChange={(e) => setDetectQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleDetect()}
            placeholder="Sorgunuzu yazın, uygun domain otomatik tespit edilsin..."
            className="flex-1 text-[11px] px-2 py-1 border border-[#7F9DB9] rounded-sm bg-white text-black focus:outline-none focus:border-[#0A246A]"
          />
          <button
            onClick={handleDetect}
            disabled={detecting || !detectQuery.trim()}
            className="px-2 py-1 text-[10px] font-semibold bg-[#0A246A] text-white rounded-sm hover:bg-[#3A6EA5] disabled:opacity-50 transition-colors"
          >
            {detecting ? "..." : "Tespit Et"}
          </button>
        </div>
        {detectResults.length > 0 && (
          <div className="mt-2 space-y-1">
            {detectResults.map((m) => (
              <div
                key={m.domain_id}
                className="flex items-center gap-2 bg-white border border-[#ACA899] rounded-sm px-2 py-1.5"
              >
                <div
                  className={`p-1 rounded ${DOMAIN_COLORS[`domain:${m.domain_id}`] || "text-slate-400 bg-slate-100"}`}
                >
                  {DOMAIN_ICONS[`domain:${m.domain_id}`] || (
                    <Zap className="w-4 h-4" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-bold text-[#0A246A]">
                      {m.name_tr}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded-full font-semibold">
                      Skor: {m.score}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                    {m.matched_keywords.slice(0, 4).map((kw) => (
                      <span
                        key={kw}
                        className="text-[9px] px-1 py-0.5 bg-blue-50 text-blue-600 rounded"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
                {m.suggested_tools.length > 0 && (
                  <div className="text-[10px] text-slate-500 shrink-0">
                    {m.suggested_tools.length} önerilen araç
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Search + Category Tabs */}
      <div className="bg-[#F1EFE2] border-b border-[#ACA899] px-3 py-1.5 flex items-center gap-2">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Ara..."
            className="w-full text-[11px] pl-7 pr-2 py-1 border border-[#7F9DB9] rounded-sm bg-white text-black focus:outline-none focus:border-[#0A246A]"
          />
        </div>
        <div className="flex items-center gap-0.5">
          {CATEGORY_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setCategory(tab.id)}
              className={`px-2 py-1 text-[10px] font-semibold rounded-sm transition-colors ${
                category === tab.id
                  ? "bg-[#0A246A] text-white"
                  : "bg-white border border-[#ACA899] text-[#0A246A] hover:bg-[#D6D2C2]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Catalog Grid */}
      <div className="flex-1 overflow-y-auto p-3">
        {loading ? (
          <div className="flex items-center justify-center h-32 text-[11px] text-slate-500">
            Yükleniyor...
          </div>
        ) : catalog.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-[11px] text-slate-500">
            Sonuç bulunamadı
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {catalog.map((item) => {
              const isExpanded = expandedItem === item.id;
              const colorCls =
                DOMAIN_COLORS[item.id] ||
                "text-slate-500 bg-slate-100 border-slate-300";
              const icon =
                DOMAIN_ICONS[item.id] ||
                (item.type === "skill" ? (
                  <Zap className="w-5 h-5" />
                ) : (
                  <Package className="w-5 h-5" />
                ));

              return (
                <div
                  key={item.id}
                  className={`bg-white border rounded shadow-sm transition-all cursor-pointer hover:shadow-md ${
                    isExpanded
                      ? "border-[#0A246A] ring-1 ring-[#0A246A]/20"
                      : "border-[#ACA899]"
                  }`}
                  onClick={() => setExpandedItem(isExpanded ? null : item.id)}
                >
                  <div className="p-2.5">
                    <div className="flex items-start gap-2">
                      <div
                        className={`p-1.5 rounded border shrink-0 ${colorCls}`}
                      >
                        {icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[12px] font-bold text-[#0A246A] truncate">
                            {item.name_tr || item.name}
                          </span>
                          <span
                            className={`text-[9px] px-1.5 py-0.5 rounded-full font-semibold ${
                              item.type === "domain"
                                ? "bg-blue-100 text-blue-700"
                                : "bg-green-100 text-green-700"
                            }`}
                          >
                            {item.type === "domain" ? "Domain" : "Skill"}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-600 mt-0.5 line-clamp-2">
                          {item.description}
                        </p>
                        <div className="flex items-center gap-2 mt-1.5">
                          {item.tool_count > 0 && (
                            <span className="text-[9px] px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">
                              {item.tool_count} araç
                            </span>
                          )}
                          {renderStars(item.rating)}
                          {item.installed && (
                            <span className="text-[9px] px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded font-semibold ml-auto">
                              ✓ Yüklü
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Tags */}
                    {item.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {item.tags.slice(0, 4).map((tag) => (
                          <span
                            key={tag}
                            className="text-[9px] px-1 py-0.5 bg-[#F1EFE2] text-[#0A246A] rounded border border-[#D6D2C2]"
                          >
                            {tag}
                          </span>
                        ))}
                        {item.tags.length > 4 && (
                          <span className="text-[9px] text-slate-400">
                            +{item.tags.length - 4}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Expanded: Tools & Capabilities */}
                  {isExpanded && (
                    <div className="border-t border-[#D6D2C2] bg-[#FAFAF7] px-2.5 py-2 space-y-2">
                      {item.capabilities.length > 0 && (
                        <div>
                          <span className="text-[10px] font-bold text-[#0A246A]">
                            Yetenekler:
                          </span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {item.capabilities.map((cap) => (
                              <span
                                key={cap}
                                className="text-[9px] px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded border border-blue-200"
                              >
                                {cap}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {item.tools.length > 0 && (
                        <div>
                          <span className="text-[10px] font-bold text-[#0A246A]">
                            Araçlar:
                          </span>
                          <div className="space-y-1 mt-1">
                            {item.tools.map((tool) => (
                              <div
                                key={tool.name}
                                className="flex items-start gap-1.5 text-[10px]"
                              >
                                <span className="text-emerald-600 mt-0.5 shrink-0">
                                  ▸
                                </span>
                                <div>
                                  <span className="font-mono font-semibold text-[#0A246A]">
                                    {tool.name}
                                  </span>
                                  <span className="text-slate-500 ml-1">
                                    — {tool.description}
                                  </span>
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
            })}
          </div>
        )}
      </div>
    </div>
  );
}
