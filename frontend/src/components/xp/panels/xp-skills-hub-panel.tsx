"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  GraduationCap,
  Package,
  Wrench,
  Bot,
  Plus,
  X,
  CheckCircle,
  Sparkles,
} from "lucide-react";
import dynamic from "next/dynamic";
import { api, getAutoSkills } from "@/lib/api";

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

interface Skill {
  id: string;
  name: string;
  category: string;
  description?: string;
  source: string;
  use_count?: number;
  active?: boolean;
  knowledge?: string;
  keywords?: string[];
}

type SkillsHubTab = "skills" | "categories" | "creator" | "marketplace" | "patterns";

const TABS: { key: SkillsHubTab; label: string; icon: string }[] = [
  { key: "skills", label: "Yetenekler", icon: "📚" },
  { key: "categories", label: "Kategori", icon: "📁" },
  { key: "patterns", label: "Kalıplar", icon: "🔄" },
  { key: "creator", label: "Oluşturucu", icon: "✨" },
  { key: "marketplace", label: "Marketplace", icon: "🏪" },
];

const CAT_COLORS: Record<string, string> = {
  research: "#2e7d32",
  analysis: "#1565c0",
  orchestration: "#6a1b9a",
  coding: "#00838f",
  finance: "#e65100",
  reasoning: "#4527a0",
  architecture: "#37474f",
  medical: "#c62828",
  writing: "#558b2f",
  security: "#d84315",
  database: "#01579b",
  custom: "#6d4c41",
};

function SourceBadge({ source }: { source: string }) {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    builtin: { bg: "#dbeafe", text: "#1e40af", label: "📦 Yerleşik" },
    "auto-learned": { bg: "#fef3c7", text: "#92400e", label: "🤖 Otomatik" },
  };
  const s = map[source] ?? { bg: "#dcfce7", text: "#166534", label: "✏️ Özel" };
  return (
    <span
      style={{
        background: s.bg,
        color: s.text,
        padding: "1px 6px",
        borderRadius: 3,
        fontSize: 10,
        fontWeight: 600,
      }}
    >
      {s.label}
    </span>
  );
}

function CategoryBadge({ category }: { category: string }) {
  const color = CAT_COLORS[category] ?? "#555";
  return (
    <span
      style={{
        background: `${color}22`,
        color,
        border: `1px solid ${color}44`,
        padding: "1px 6px",
        borderRadius: 3,
        fontSize: 10,
        fontWeight: 500,
      }}
    >
      {category}
    </span>
  );
}

function SkillDetailView({
  skill,
  onBack,
  showActions = true,
}: {
  skill: Skill;
  onBack: () => void;
  showActions?: boolean;
}) {
  const [full, setFull] = useState<Skill | null>(skill);
  const [loading, setLoading] = useState(false);
  const [improving, setImproving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!skill?.id) return;
    api.getSkill(skill.id).then((s) => setFull(s as Skill)).catch(() => setFull(skill));
  }, [skill?.id]);

  useEffect(() => {
    if (!skill?.id) return;
    setFull(null);
    setLoading(true);
    setActionError(null);
    api
      .getSkill(skill.id)
      .then((s) => setFull(s as Skill))
      .catch(() => setFull(skill))
      .finally(() => setLoading(false));
  }, [skill?.id]);

  const handleImprove = useCallback(() => {
    if (!skill?.id || (full ?? skill).source === "builtin") return;
    setImproving(true);
    setActionError(null);
    api
      .improveSkill(skill.id)
      .then((updated) => {
        setFull(updated as Skill);
      })
      .catch((e) => setActionError(e instanceof Error ? e.message : "Geliştirme başarısız"))
      .finally(() => setImproving(false));
  }, [skill?.id, full, skill?.source]);

  const handleDelete = useCallback(() => {
    if (!skill?.id || (full ?? skill).source === "builtin") return;
    if (!confirm("Bu yeteneği devre dışı bırakmak istediğinize emin misiniz?")) return;
    setActionError(null);
    api
      .deleteSkill(skill.id)
      .then(() => onBack())
      .catch((e) => setActionError(e instanceof Error ? e.message : "Silme başarısız"));
  }, [skill?.id, full, skill?.source, onBack]);

  const s = full ?? skill;
  const knowledge = s.knowledge;
  const keywords = s.keywords ?? [];
  const canEdit = s.source !== "builtin";

  return (
    <div style={{ padding: 12, display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexShrink: 0 }}>
        <button
          onClick={onBack}
          style={{
            background: "#ece9d8",
            border: "1px solid #999",
            borderRadius: 3,
            padding: "3px 10px",
            fontSize: 11,
            cursor: "pointer",
          }}
        >
          ← Geri
        </button>
        {showActions && canEdit && (
          <>
            <button
              onClick={handleImprove}
              disabled={improving}
              style={{
                background: "#6633cc",
                color: "#fff",
                border: "none",
                borderRadius: 3,
                padding: "3px 10px",
                fontSize: 11,
                cursor: improving ? "not-allowed" : "pointer",
              }}
            >
              {improving ? "Geliştiriliyor…" : "Geliştir"}
            </button>
            <button
              onClick={handleDelete}
              style={{
                background: "#b91c1c",
                color: "#fff",
                border: "none",
                borderRadius: 3,
                padding: "3px 10px",
                fontSize: 11,
                cursor: "pointer",
              }}
            >
              Sil
            </button>
          </>
        )}
      </div>
      {actionError && (
        <div style={{ fontSize: 11, color: "#b91c1c", marginBottom: 8 }}>{actionError}</div>
      )}
      {loading ? (
        <div style={{ fontSize: 12, color: "#666" }}>Yükleniyor…</div>
      ) : (
        <div
          style={{
            background: "#fffff0",
            border: "1px solid #d6d2c2",
            borderRadius: 4,
            padding: 12,
            flex: 1,
            minHeight: 0,
            overflow: "auto",
          }}
        >
          <h3 style={{ margin: "0 0 6px", fontSize: 14, fontWeight: 700, color: "#000" }}>
            {s.name}
          </h3>
          <div style={{ display: "flex", gap: 6, marginBottom: 8, flexWrap: "wrap" }}>
            <CategoryBadge category={s.category} />
            <SourceBadge source={s.source} />
          </div>
          {s.description && (
            <section style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: "#555", marginBottom: 4 }}>Açıklama</div>
              <p style={{ fontSize: 12, color: "#333", margin: 0, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                {s.description}
              </p>
            </section>
          )}
          {keywords.length > 0 && (
            <section style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: "#555", marginBottom: 4 }}>Anahtar kelimeler</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {keywords.map((k) => (
                  <span
                    key={k}
                    style={{
                      background: "#e8e6d9",
                      color: "#444",
                      padding: "2px 6px",
                      borderRadius: 3,
                      fontSize: 10,
                    }}
                  >
                    {k}
                  </span>
                ))}
              </div>
            </section>
          )}
          {knowledge && (
            <section style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: "#555", marginBottom: 4 }}>İçerik / Bilgi</div>
              <pre
                style={{
                  margin: 0,
                  fontSize: 11,
                  color: "#333",
                  lineHeight: 1.5,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  background: "#f9f9f0",
                  border: "1px solid #e0ddd0",
                  borderRadius: 3,
                  padding: 8,
                  maxHeight: 320,
                  overflow: "auto",
                }}
              >
                {knowledge}
              </pre>
            </section>
          )}
          <div style={{ fontSize: 11, color: "#666", marginTop: 8 }}>
            Kullanım: {s.use_count ?? 0} kez
          </div>
        </div>
      )}
    </div>
  );
}

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

function XpSkillsList() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [autoSkills, setAutoSkills] = useState<Skill[]>([]);
  const [selected, setSelected] = useState<Skill | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    skill_id: "",
    name: "",
    description: "",
    knowledge: "",
    category: "custom",
    keywords: "",
  });
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    try {
      const [s, a] = await Promise.all([
        api.listSkills() as Promise<Skill[]>,
        getAutoSkills() as Promise<Skill[]>,
      ]);
      setSkills(s);
      setAutoSkills(a);
    } catch {
      /* */
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const onRefresh = () => load();
    window.addEventListener("skills-hub-refresh", onRefresh);
    return () => window.removeEventListener("skills-hub-refresh", onRefresh);
  }, [load]);

  const handleCreate = async () => {
    if (!form.skill_id || !form.name || !form.knowledge) return;
    setMsg("");
    try {
      await api.createSkill({
        ...form,
        keywords: form.keywords
          ? form.keywords.split(",").map((k) => k.trim())
          : [],
      });
      setMsg("Skill oluşturuldu ✓");
      setForm({
        skill_id: "",
        name: "",
        description: "",
        knowledge: "",
        category: "custom",
        keywords: "",
      });
      setShowForm(false);
      load();
    } catch (e) {
      setMsg(`${e instanceof Error ? e.message : "Hata"}`);
    }
  };

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleDelete = async (id: string) => {
    try {
      await api.deleteSkill(id);
      setSelected(null);
      load();
    } catch {
      /* */
    }
  };

  if (selected)
    return (
      <SkillDetailView skill={selected} onBack={() => setSelected(null)} />
    );

  const builtin = skills.filter((s) => s.source === "builtin");
  const custom = skills.filter(
    (s) => s.source !== "builtin" && s.source !== "auto-learned",
  );
  const all = [...skills, ...autoSkills].sort(
    (a, b) => (b.use_count ?? 0) - (a.use_count ?? 0),
  );

  const inputStyle: React.CSSProperties = {
    width: "100%",
    background: "#fff",
    border: "1px solid #7f9db9",
    borderRadius: 2,
    padding: "4px 8px",
    fontSize: 12,
    color: "#000",
    fontFamily: "Tahoma, sans-serif",
  };

  return (
    <div style={{ padding: 8, fontFamily: "Tahoma, sans-serif" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <div style={{ display: "flex", gap: 10, fontSize: 11, color: "#444" }}>
          <span>
            <Package
              size={12}
              style={{ display: "inline", verticalAlign: -2 }}
            />{" "}
            Yerleşik: {builtin.length}
          </span>
          <span>
            <Wrench
              size={12}
              style={{ display: "inline", verticalAlign: -2 }}
            />{" "}
            Özel: {custom.length}
          </span>
          {autoSkills.length > 0 && (
            <span title="Öğrenilmiş yetenekler (Otomatik Keşif veya agent create_skill ile oluşturuldu; tam yetenek olarak find_skill ile kullanılır)">
              <Bot
                size={12}
                style={{
                  display: "inline",
                  verticalAlign: -2,
                  color: "#b45309",
                }}
              />{" "}
              Otomatik: {autoSkills.length}
            </span>
          )}
        </div>
        <p style={{ fontSize: 10, color: "#666", margin: "4px 0 0", maxWidth: 420 }}>
          Otomatik / learned = tam yetenek; agent&apos;lar find_skill ile bulup kullanır.
        </p>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{
            background: "#ece9d8",
            border: "1px solid #999",
            borderRadius: 3,
            padding: "3px 10px",
            fontSize: 11,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 3,
          }}
        >
          {showForm ? (
            <>
              <X size={12} /> Kapat
            </>
          ) : (
            <>
              <Plus size={12} /> Yeni
            </>
          )}
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div
          style={{
            background: "#fffff0",
            border: "1px solid #d6d2c2",
            borderRadius: 4,
            padding: 10,
            marginBottom: 8,
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <input
            value={form.skill_id}
            onChange={(e) => setForm({ ...form, skill_id: e.target.value })}
            placeholder="Skill ID"
            style={inputStyle}
          />
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="İsim"
            style={inputStyle}
          />
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            style={inputStyle}
          >
            {[
              "custom",
              "coding",
              "research",
              "analysis",
              "writing",
              "security",
              "finance",
              "database",
            ].map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <input
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Açıklama"
            style={inputStyle}
          />
          <textarea
            value={form.knowledge}
            onChange={(e) => setForm({ ...form, knowledge: e.target.value })}
            placeholder="Bilgi / Protokol"
            rows={3}
            style={{ ...inputStyle, resize: "none" }}
          />
          <input
            value={form.keywords}
            onChange={(e) => setForm({ ...form, keywords: e.target.value })}
            placeholder="Anahtar kelimeler (virgülle)"
            style={inputStyle}
          />
          <button
            onClick={handleCreate}
            style={{
              background: "#d4edda",
              border: "1px solid #28a745",
              borderRadius: 3,
              padding: "5px 0",
              fontSize: 12,
              fontWeight: 600,
              color: "#155724",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 4,
            }}
          >
            <CheckCircle size={14} /> Oluştur
          </button>
        </div>
      )}
      {msg && (
        <div style={{ fontSize: 11, color: "#666", marginBottom: 6 }}>
          {msg}
        </div>
      )}

      {/* Skills Table */}
      <div
        style={{
          border: "1px solid #d6d2c2",
          borderRadius: 4,
          overflow: "hidden",
        }}
      >
        <table
          style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}
        >
          <thead>
            <tr
              style={{
                background: "#ece9d8",
                borderBottom: "1px solid #d6d2c2",
              }}
            >
              <th
                style={{
                  textAlign: "left",
                  padding: "6px 10px",
                  fontSize: 11,
                  fontWeight: 700,
                  color: "#333",
                }}
              >
                İSİM
              </th>
              <th
                style={{
                  textAlign: "left",
                  padding: "6px 10px",
                  fontSize: 11,
                  fontWeight: 700,
                  color: "#333",
                }}
              >
                KATEGORİ
              </th>
              <th
                style={{
                  textAlign: "left",
                  padding: "6px 10px",
                  fontSize: 11,
                  fontWeight: 700,
                  color: "#333",
                }}
              >
                KAYNAK
              </th>
              <th
                style={{
                  textAlign: "right",
                  padding: "6px 10px",
                  fontSize: 11,
                  fontWeight: 700,
                  color: "#333",
                }}
              >
                KULLANIM
              </th>
            </tr>
          </thead>
          <tbody>
            {all.map((s, i) => (
              <tr
                key={`${s.source}-${s.id}`}
                onClick={() => setSelected(s)}
                style={{
                  background: i % 2 === 0 ? "#fff" : "#f8f6f0",
                  borderBottom: "1px solid #e8e4d4",
                  cursor: "pointer",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.background = "#e8e4ff";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.background =
                    i % 2 === 0 ? "#fff" : "#f8f6f0";
                }}
              >
                <td
                  style={{
                    padding: "5px 10px",
                    fontWeight: 600,
                    color: "#000",
                  }}
                >
                  {s.name}
                </td>
                <td style={{ padding: "5px 10px" }}>
                  <CategoryBadge category={s.category} />
                </td>
                <td style={{ padding: "5px 10px" }}>
                  <SourceBadge source={s.source} />
                </td>
                <td
                  style={{
                    padding: "5px 10px",
                    textAlign: "right",
                    color: "#555",
                    fontWeight: 500,
                  }}
                >
                  {s.use_count ?? 0}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {all.length === 0 && (
          <div
            style={{
              textAlign: "center",
              padding: 24,
              fontSize: 12,
              color: "#888",
            }}
          >
            Henüz skill yok
          </div>
        )}
      </div>
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
            title="Kalite kontrolü çalıştır — zayıf skill’leri devre dışı bırakır"
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
                <span style={{ fontSize: 10, color: "#666", fontWeight: 400 }}> (veritabanından silinmedi, agent’lar artık kullanmıyor)</span>
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
