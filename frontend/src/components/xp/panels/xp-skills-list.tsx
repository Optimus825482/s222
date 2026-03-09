"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Package,
  Wrench,
  Bot,
  Plus,
  X,
  CheckCircle,
} from "lucide-react";
import { api, getAutoSkills } from "@/lib/api";

// ── Types ──
export interface Skill {
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

// ── Category Colors ──
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

// ── Shared Input Style ──
export const SKILL_INPUT_STYLE: React.CSSProperties = {
  width: "100%",
  background: "#fff",
  border: "1px solid #7f9db9",
  borderRadius: 2,
  padding: "4px 8px",
  fontSize: 12,
  color: "#000",
  fontFamily: "Tahoma, sans-serif",
};

// ── Source Badge ──
export function SourceBadge({ source }: { source: string }) {
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

// ── Category Badge ──
export function CategoryBadge({ category }: { category: string }) {
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

// ── Skill Detail View ──
export function SkillDetailView({
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      .catch((e) =>
        setActionError(e instanceof Error ? e.message : "Geliştirme başarısız")
      )
      .finally(() => setImproving(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skill?.id, full?.source, skill?.source]);

  const handleDelete = useCallback(() => {
    if (!skill?.id || (full ?? skill).source === "builtin") return;
    if (!confirm("Bu yeteneği devre dışı bırakmak istediğinize emin misiniz?"))
      return;
    setActionError(null);
    api
      .deleteSkill(skill.id)
      .then(() => onBack())
      .catch((e) =>
        setActionError(e instanceof Error ? e.message : "Silme başarısız")
      );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skill?.id, full?.source, skill?.source, onBack]);

  const s = full ?? skill;
  const knowledge = s.knowledge;
  const keywords = s.keywords ?? [];
  const canEdit = s.source !== "builtin";

  return (
    <div
      style={{
        padding: 12,
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 8,
          flexShrink: 0,
        }}
      >
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
        <div style={{ fontSize: 11, color: "#b91c1c", marginBottom: 8 }}>
          {actionError}
        </div>
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
          <h3
            style={{
              margin: "0 0 6px",
              fontSize: 14,
              fontWeight: 700,
              color: "#000",
            }}
          >
            {s.name}
          </h3>
          <div
            style={{
              display: "flex",
              gap: 6,
              marginBottom: 8,
              flexWrap: "wrap",
            }}
          >
            <CategoryBadge category={s.category} />
            <SourceBadge source={s.source} />
          </div>
          {s.description && (
            <section style={{ marginBottom: 10 }}>
              <div
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  color: "#555",
                  marginBottom: 4,
                }}
              >
                Açıklama
              </div>
              <p
                style={{
                  fontSize: 12,
                  color: "#333",
                  margin: 0,
                  lineHeight: 1.5,
                  whiteSpace: "pre-wrap",
                }}
              >
                {s.description}
              </p>
            </section>
          )}
          {keywords.length > 0 && (
            <section style={{ marginBottom: 10 }}>
              <div
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  color: "#555",
                  marginBottom: 4,
                }}
              >
                Anahtar kelimeler
              </div>
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
              <div
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  color: "#555",
                  marginBottom: 4,
                }}
              >
                İçerik / Bilgi
              </div>
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

// ── Skills List Component ──
export function XpSkillsList() {
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
            style={SKILL_INPUT_STYLE}
          />
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="İsim"
            style={SKILL_INPUT_STYLE}
          />
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            style={SKILL_INPUT_STYLE}
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
            style={SKILL_INPUT_STYLE}
          />
          <textarea
            value={form.knowledge}
            onChange={(e) => setForm({ ...form, knowledge: e.target.value })}
            placeholder="Bilgi / Protokol"
            rows={3}
            style={{ ...SKILL_INPUT_STYLE, resize: "none" }}
          />
          <input
            value={form.keywords}
            onChange={(e) => setForm({ ...form, keywords: e.target.value })}
            placeholder="Anahtar kelimeler (virgülle)"
            style={SKILL_INPUT_STYLE}
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

export default XpSkillsList;