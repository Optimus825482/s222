"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  GraduationCap,
  Sparkles,
} from "lucide-react";
import dynamic from "next/dynamic";
import { api, getAutoSkills } from "@/lib/api";
import {
  Skill,
  SourceBadge,
  CategoryBadge,
  SkillDetailView,
  XpSkillsList,
} from "./xp-skills-list";

const SkillCreatorPanel = dynamic(
  () =>
    import("@/components/skill-creator-panel").then((m) => ({
      default: m.SkillCreatorPanel,
    })),
  { ssr: false },
);
const XpMarketplacePanel = dynamic(
  () =>
    import("./xp-marketplace-panel").then((m) => ({
      default: m.XpMarketplacePanel,
    })),
  { ssr: false },
);

type SkillsHubTab = "skills" | "categories" | "creator" | "marketplace" | "patterns";

const TABS: { key: SkillsHubTab; label: string; icon: string }[] = [
  { key: "skills", label: "Yetenekler", icon: "📚" },
  { key: "categories", label: "Kategori", icon: "📁" },
  { key: "patterns", label: "Kalıplar", icon: "🔄" },
  { key: "creator", label: "Oluşturucu", icon: "✨" },
  { key: "marketplace", label: "Marketplace", icon: "🏪" },
];

function CategoriesTab() {
  const [allSkills, setAllSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, a] = await Promise.all([
        api.listSkills() as Promise<Skill[]>,
        getAutoSkills() as Promise<Skill[]>,
      ]);
      setAllSkills([...s, ...a]);
    } catch {
      setAllSkills([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const onRefresh = () => load();
    window.addEventListener("skills-hub-refresh", onRefresh);
    return () => window.removeEventListener("skills-hub-refresh", onRefresh);
  }, [load]);

  const byCategory = useMemo(() => {
    const m: Record<string, Skill[]> = {};
    for (const sk of allSkills) {
      const cat = sk.category || "custom";
      if (!m[cat]) m[cat] = [];
      m[cat].push(sk);
    }
    return Object.entries(m).sort((a, b) => b[1].length - a[1].length);
  }, [allSkills]);

  if (selectedSkill) {
    return (
      <SkillDetailView
        skill={selectedSkill}
        onBack={() => {
          setSelectedSkill(null);
          load();
        }}
        showActions={true}
      />
    );
  }

  if (loading) {
    return (
      <div style={{ padding: 12, fontSize: 12, color: "#666" }}>Yükleniyor…</div>
    );
  }

  if (selectedCategory) {
    const list = byCategory.find(([c]) => c === selectedCategory)?.[1] ?? [];
    return (
      <div style={{ padding: 12, display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
        <button
          onClick={() => setSelectedCategory(null)}
          style={{
            background: "#ece9d8",
            border: "1px solid #999",
            borderRadius: 3,
            padding: "3px 10px",
            fontSize: 11,
            cursor: "pointer",
            marginBottom: 8,
            alignSelf: "flex-start",
          }}
        >
          ← Kategorilere dön
        </button>
        <div style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>
          {selectedCategory}: {list.length} yetenek
        </div>
        <div style={{ flex: 1, overflow: "auto" }}>
          {list.map((sk) => (
            <div
              key={sk.id}
              onClick={() => setSelectedSkill(sk)}
              style={{
                padding: "8px 10px",
                borderBottom: "1px solid #e0ddd0",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 8,
              }}
            >
              <span style={{ fontSize: 12, fontWeight: 500 }}>{sk.name}</span>
              <SourceBadge source={sk.source} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 12, fontFamily: "Tahoma, sans-serif" }}>
      <p style={{ fontSize: 11, color: "#555", marginBottom: 10 }}>
        Kategorilere tıklayarak o kategorideki yetenekleri listeleyebilirsiniz; listeden bir yeteneğe tıklayınca detayı açılır.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {byCategory.map(([cat, list]) => (
          <div
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "10px 12px",
              background: "#fffff0",
              border: "1px solid #d6d2c2",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            <span style={{ fontSize: 12, fontWeight: 600, color: "#333" }}>
              <CategoryBadge category={cat} /> {cat}
            </span>
            <span style={{ fontSize: 12, color: "#666" }}>{list.length} yetenek</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PatternsTab() {
  const [patterns, setPatterns] = useState<{ signature: string; count: number; tools_used: string[]; examples: unknown[] }[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setMsg("");
    try {
      const r = await api.getSelfSkillPatterns(3);
      setPatterns(r.patterns ?? []);
    } catch {
      setPatterns([]);
      setMsg("Kalıplar yüklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onGenerate = async (signature: string) => {
    setGenerating(signature);
    setMsg("");
    try {
      const r = await api.generateSelfSkillFromPattern(signature);
      if (r.ok) {
        setMsg("Skill oluşturuldu");
        window.dispatchEvent(new CustomEvent("skills-hub-refresh"));
        load();
      } else {
        setMsg(r.error ?? "Oluşturulamadı");
      }
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Hata");
    } finally {
      setGenerating(null);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 12, fontSize: 12, color: "#666" }}>
        Yükleniyor…
      </div>
    );
  }
  return (
    <div style={{ padding: 12, fontFamily: "Tahoma, sans-serif" }}>
      <p style={{ fontSize: 11, color: "#555", marginBottom: 8 }}>
        Aynı araç sırası 3+ kez tekrarlandığında burada listelenir. &quot;Skill oluştur&quot; ile otomatik yetenek üretilir.
      </p>
      {msg && <p style={{ fontSize: 11, color: msg.startsWith("Skill") ? "#2e7d32" : "#c62828", marginBottom: 8 }}>{msg}</p>}
      {patterns.length === 0 ? (
        <p style={{ fontSize: 12, color: "#888" }}>Henüz 3+ tekrar eden kalıp yok. Görevler çalıştıkça kayıt edilir.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {patterns.map((p) => (
            <div
              key={p.signature}
              style={{
                border: "1px solid #d6d2c2",
                borderRadius: 6,
                padding: 10,
                background: "#f5f3e8",
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 600, color: "#333" }}>
                {p.tools_used.join(" → ")}
              </div>
              <div style={{ fontSize: 10, color: "#666", marginTop: 4 }}>
                {p.count} tekrar
              </div>
              <button
                type="button"
                disabled={generating === p.signature}
                onClick={() => onGenerate(p.signature)}
                style={{
                  marginTop: 6,
                  fontSize: 10,
                  padding: "4px 10px",
                  background: "#6633cc",
                  color: "#fff",
                  border: "none",
                  borderRadius: 4,
                  cursor: generating === p.signature ? "not-allowed" : "pointer",
                }}
              >
                {generating === p.signature ? "…" : "Skill oluştur"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function XpSkillsHubPanel() {
  const [tab, setTab] = useState<SkillsHubTab>("skills");
  const [hygieneRunning, setHygieneRunning] = useState(false);
  const [hygieneResult, setHygieneResult] = useState<{
    checked: number;
    healthy: number;
    deactivated: Array<{ id: string; name: string; issues: string[]; action: string }>;
    deleted: Array<{ id: string; name: string; issues: string[]; action: string }>;
    dry_run: boolean;
    timestamp?: string;
  } | null>(null);
  const [hygieneError, setHygieneError] = useState<string | null>(null);

  const runHygiene = async (dryRun: boolean) => {
    setHygieneRunning(true);
    setHygieneResult(null);
    setHygieneError(null);
    try {
      const res = await api.runSkillHygiene(dryRun);
      setHygieneResult({
        checked: res.checked,
        healthy: res.healthy,
        deactivated: res.deactivated ?? [],
        deleted: res.deleted ?? [],
        dry_run: res.dry_run,
        timestamp: res.timestamp,
      });
      if (!dryRun)
        window.dispatchEvent(new CustomEvent("skills-hub-refresh"));
    } catch (e) {
      setHygieneError(e instanceof Error ? e.message : "İstek başarısız");
      setHygieneResult(null);
    } finally {
      setHygieneRunning(false);
    }
  };

  return (
    <div
      className="flex flex-col h-full"
      style={{
        background: "#fff",
        color: "#000",
        fontFamily: "Tahoma, sans-serif",
      }}
    >
      {/* Title bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          padding: "6px 10px",
          borderBottom: "1px solid #d6d2c2",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <GraduationCap size={16} color="#6633cc" />
          <span style={{ fontSize: 13, fontWeight: 700, color: "#333" }}>
            Yetenek Merkezi
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <button
            type="button"
            onClick={() => runHygiene(true)}
            disabled={hygieneRunning}
            title="Sadece rapor (değişiklik yapmaz)"
            style={{
              fontSize: 11,
              padding: "4px 8px",
              border: "1px solid #d6d2c2",
              borderRadius: 4,
              background: "#f5f3e8",
              color: "#555",
              cursor: hygieneRunning ? "not-allowed" : "pointer",
            }}
          >
            {hygieneRunning ? "…" : "Hygiene (kuru)"}
          </button>
          <button
            type="button"
            onClick={() => runHygiene(false)}
            disabled={hygieneRunning}
            title="Kalite kontrolü çalıştır — zayıf skill'leri devre dışı bırakır"
            style={{
              fontSize: 11,
              padding: "4px 8px",
              border: "1px solid #6633cc",
              borderRadius: 4,
              background: "#f0ebff",
              color: "#6633cc",
              cursor: hygieneRunning ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <Sparkles size={12} />
            {hygieneRunning ? "Çalışıyor…" : "Skill hygiene"}
          </button>
        </div>
      </div>
      {hygieneError && (
        <div
          style={{
            padding: "6px 10px",
            fontSize: 11,
            background: "#fee2e2",
            borderBottom: "1px solid #d6d2c2",
            color: "#b91c1c",
          }}
        >
          Hata: {hygieneError}
        </div>
      )}
      {hygieneResult && (
        <div
          style={{
            padding: "8px 10px",
            fontSize: 11,
            background: hygieneResult.dry_run ? "#fef3c7" : "#dcfce7",
            borderBottom: "1px solid #d6d2c2",
            color: "#333",
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4 }}>
            {hygieneResult.dry_run ? "Kuru çalıştırma (değişiklik yapılmadı)" : "Tamamlandı"}
            {hygieneResult.timestamp && (
              <span style={{ fontWeight: 400, color: "#666", marginLeft: 6 }}>
                — {new Date(hygieneResult.timestamp).toLocaleTimeString("tr-TR")}
              </span>
            )}
          </div>
          <div style={{ marginBottom: 4 }}>
            {hygieneResult.checked} yetenek kontrol edildi, {hygieneResult.healthy} sağlıklı
            {(hygieneResult.deactivated.length > 0 || hygieneResult.deleted.length > 0) && (
              <span>
                , {hygieneResult.deactivated.length + hygieneResult.deleted.length} kalitesiz yetenek <strong>devre dışı bırakıldı</strong>
                <span style={{ fontSize: 10, color: "#666", fontWeight: 400 }}> (veritabanından silinmedi, agent'lar artık kullanmıyor)</span>
              </span>
            )}
          </div>
          {(hygieneResult.deactivated.length > 0 || hygieneResult.deleted.length > 0) && (
            <div style={{ marginTop: 6, fontSize: 10, color: "#555" }}>
              {[...hygieneResult.deactivated, ...hygieneResult.deleted].map((e) => (
                <div key={e.id} style={{ marginBottom: 2 }}>
                  <strong>{e.name}</strong> ({e.id}): {e.issues?.join(", ") ?? e.action}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab bar */}
      <div style={{ display: "flex", borderBottom: "1px solid #d6d2c2" }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 4,
              padding: "7px 10px",
              fontSize: 12,
              fontWeight: tab === t.key ? 700 : 500,
              cursor: "pointer",
              background: tab === t.key ? "#f0ebff" : "#ece9d8",
              color: tab === t.key ? "#6633cc" : "#555",
              borderBottom:
                tab === t.key ? "2px solid #6633cc" : "2px solid transparent",
              border: "none",
              borderRight: "1px solid #d6d2c2",
            }}
          >
            <span>{t.icon}</span> {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: "auto" }}>
        {tab === "skills" && <XpSkillsList />}
        {tab === "categories" && <CategoriesTab />}
        {tab === "patterns" && <PatternsTab />}
        {tab === "creator" && <SkillCreatorPanel />}
        {tab === "marketplace" && <XpMarketplacePanel />}
      </div>
    </div>
  );
}