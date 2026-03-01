"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  getMemoryStats,
  getMemoryLayers,
  deleteMemory,
  getAutoSkills,
  getDbHealth,
} from "@/lib/api";
import {
  BookOpen,
  Upload,
  Loader2,
  CheckCircle,
  FileText,
  Puzzle,
  Plus,
  X,
  Trash2,
  Plug,
  Circle,
  GraduationCap,
  Save,
  BarChart3,
  Star,
  Package,
  Wrench,
  Brain,
  Layers,
  Database,
  Bot,
} from "lucide-react";

// ── RAG Panel ───────────────────────────────────────────────────

export function RagPanel() {
  const [docs, setDocs] = useState<{ title: string; chunk_count: number }[]>(
    [],
  );
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const loadDocs = useCallback(async () => {
    try {
      const d = (await api.ragDocuments()) as {
        title: string;
        chunk_count: number;
      }[];
      setDocs(d);
    } catch {
      /* backend offline */
    }
  }, []);

  useEffect(() => {
    loadDocs();
  }, [loadDocs]);

  const handleIngest = async () => {
    if (!title.trim() || !content.trim()) return;
    setLoading(true);
    setMsg("");
    try {
      const res = (await api.ragIngest(content, title)) as {
        success: boolean;
        chunks?: number;
      };
      if (res.success) {
        setMsg(`${res.chunks ?? 0} chunk yüklendi`);
        setTitle("");
        setContent("");
        loadDocs();
      }
    } catch (e) {
      setMsg(`Hata: ${e instanceof Error ? e.message : "Bilinmeyen hata"}`);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-3 px-3 lg:px-4">
      <div className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
        <BookOpen className="w-4 h-4" aria-hidden="true" /> RAG Pipeline
      </div>
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Doküman başlığı"
        aria-label="Doküman başlığı"
        className="w-full bg-surface border border-border rounded px-3 lg:px-4 py-1.5 min-h-[44px] text-xs text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-blue-500/50"
      />
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="İçerik yapıştır..."
        aria-label="Doküman içeriği"
        rows={3}
        className="w-full bg-surface border border-border rounded px-3 lg:px-4 py-1.5 text-xs text-slate-300 placeholder:text-slate-600 resize-none focus:outline-none focus:border-blue-500/50"
      />
      <button
        onClick={handleIngest}
        disabled={loading || !title.trim() || !content.trim()}
        aria-label={loading ? "Doküman yükleniyor" : "Dokümanı yükle"}
        className="w-full min-h-[44px] py-1.5 rounded bg-blue-600/20 text-blue-400 text-xs font-medium hover:bg-blue-600/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer flex items-center justify-center gap-1.5"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" /> Yükleniyor...
          </>
        ) : (
          <>
            <Upload className="w-4 h-4" /> Yükle
          </>
        )}
      </button>
      {msg && <div className="text-[10px] text-slate-400">{msg}</div>}
      {docs.length > 0 && (
        <div className="space-y-1">
          <div className="text-[10px] text-slate-500">
            {docs.length} doküman
          </div>
          {docs.slice(0, 6).map((d, i) => (
            <div
              key={i}
              className="text-[10px] text-slate-500 flex items-center gap-1"
            >
              <FileText className="w-3 h-3 shrink-0" aria-hidden="true" />{" "}
              {d.title} ({d.chunk_count} chunk)
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Skills Panel ────────────────────────────────────────────────

interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  source: string;
  knowledge?: string;
  keywords?: string[];
  use_count?: number;
  avg_score?: number;
}

// ── Skill Detail Modal ──────────────────────────────────────────

function SkillDetailModal({
  skillId,
  onClose,
  onDelete,
}: {
  skillId: string;
  onClose: () => void;
  onDelete: (id: string) => void;
}) {
  const [skill, setSkill] = useState<Skill | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .getSkill(skillId)
      .then((s) => setSkill(s as Skill))
      .catch(() => setSkill(null))
      .finally(() => setLoading(false));
  }, [skillId]);

  const sourceColor: Record<string, string> = {
    builtin: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    user: "bg-green-500/15 text-green-400 border-green-500/30",
    "auto-learned": "bg-amber-500/15 text-amber-400 border-amber-500/30",
  };
  const sourceBadge =
    sourceColor[skill?.source ?? ""] ??
    "bg-slate-500/15 text-slate-400 border-slate-500/30";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Skill detayı"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-lg max-h-[85vh] flex flex-col rounded-xl bg-[#1a1f2e] border border-border shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-5 py-4 border-b border-border shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <Puzzle
              className="w-4 h-4 text-blue-400 shrink-0"
              aria-hidden="true"
            />
            <span className="text-sm font-semibold text-slate-200 truncate">
              {loading ? "Yükleniyor..." : (skill?.name ?? "Skill bulunamadı")}
            </span>
          </div>
          <button
            onClick={onClose}
            aria-label="Modalı kapat"
            className="min-w-[36px] min-h-[36px] flex items-center justify-center text-slate-500 hover:text-slate-300 cursor-pointer shrink-0 rounded hover:bg-white/5 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-slate-500" />
            </div>
          ) : !skill ? (
            <div className="text-sm text-slate-500 text-center py-8">
              Skill yüklenemedi
            </div>
          ) : (
            <>
              {/* Badges row */}
              <div className="flex flex-wrap gap-1.5">
                <span className="px-2 py-0.5 rounded border text-[10px] font-medium bg-teal-500/10 text-teal-400 border-teal-500/30">
                  {skill.category}
                </span>
                <span
                  className={`px-2 py-0.5 rounded border text-[10px] font-medium ${sourceBadge}`}
                >
                  {skill.source === "auto-learned"
                    ? "🤖 Otomatik"
                    : skill.source === "builtin"
                      ? "📦 Yerleşik"
                      : "✏️ Kullanıcı"}
                </span>
                {skill.use_count != null && (
                  <span className="px-2 py-0.5 rounded border text-[10px] bg-surface-raised border-border text-slate-400">
                    {skill.use_count}x kullanıldı
                  </span>
                )}
                {skill.avg_score != null && skill.avg_score > 0 && (
                  <span className="px-2 py-0.5 rounded border text-[10px] bg-surface-raised border-border text-slate-400 flex items-center gap-1">
                    <Star
                      className="w-3 h-3 text-amber-400"
                      aria-hidden="true"
                    />
                    {skill.avg_score.toFixed(1)}
                  </span>
                )}
              </div>

              {/* Description */}
              {skill.description && (
                <div>
                  <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-1">
                    Açıklama
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {skill.description}
                  </p>
                </div>
              )}

              {/* Knowledge / Çalışma Metodu */}
              {skill.knowledge && (
                <div>
                  <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-1.5 flex items-center gap-1">
                    <Brain className="w-3 h-3" aria-hidden="true" /> Çalışma
                    Metodu
                  </div>
                  <div className="bg-surface rounded-lg border border-border p-3 max-h-48 overflow-y-auto">
                    <pre className="text-[11px] text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                      {skill.knowledge}
                    </pre>
                  </div>
                </div>
              )}

              {/* Keywords */}
              {skill.keywords && skill.keywords.length > 0 && (
                <div>
                  <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider mb-1.5">
                    Anahtar Kelimeler
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {skill.keywords.map((kw) => (
                      <span
                        key={kw}
                        className="px-1.5 py-0.5 rounded bg-surface-raised border border-border text-[10px] text-slate-400"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        {skill && (
          <div className="px-5 py-3 border-t border-border shrink-0 flex justify-end">
            <button
              onClick={() => {
                onDelete(skill.id);
                onClose();
              }}
              aria-label={`${skill.name} skill'ini sil`}
              className="flex items-center gap-1.5 px-3 min-h-[36px] rounded text-[11px] text-red-400 hover:text-red-300 hover:bg-red-500/10 border border-red-500/20 transition-colors cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" /> Sil
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export function SkillsPanel() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [autoSkills, setAutoSkills] = useState<Skill[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);
  const [form, setForm] = useState({
    skill_id: "",
    name: "",
    description: "",
    knowledge: "",
    category: "custom",
    keywords: "",
  });
  const [msg, setMsg] = useState("");

  const loadSkills = useCallback(async () => {
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
    loadSkills();
  }, [loadSkills]);

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
      setMsg("Skill oluşturuldu");
      setForm({
        skill_id: "",
        name: "",
        description: "",
        knowledge: "",
        category: "custom",
        keywords: "",
      });
      setShowForm(false);
      loadSkills();
    } catch (e) {
      setMsg(`${e instanceof Error ? e.message : "Hata"}`);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteSkill(id);
      loadSkills();
    } catch {
      /* */
    }
  };

  const builtin = skills.filter((s) => s.source === "builtin");
  const custom = skills.filter(
    (s) => s.source !== "builtin" && s.source !== "auto-learned",
  );

  return (
    <div className="space-y-3 px-3 lg:px-4">
      {selectedSkillId && (
        <SkillDetailModal
          skillId={selectedSkillId}
          onClose={() => setSelectedSkillId(null)}
          onDelete={(id) => {
            handleDelete(id);
            setSelectedSkillId(null);
          }}
        />
      )}
      <div className="flex items-center justify-between">
        <div className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
          <Puzzle className="w-4 h-4" aria-hidden="true" /> Skills
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          aria-label={showForm ? "Skill formunu kapat" : "Yeni skill ekle"}
          aria-expanded={showForm}
          className="min-h-[44px] min-w-[44px] flex items-center justify-center text-[10px] text-blue-400 hover:text-blue-300 cursor-pointer"
        >
          {showForm ? (
            <>
              <X className="w-4 h-4" /> <span className="ml-1">Kapat</span>
            </>
          ) : (
            <>
              <Plus className="w-4 h-4" /> <span className="ml-1">Yeni</span>
            </>
          )}
        </button>
      </div>

      {showForm && (
        <div className="space-y-2 p-2 rounded bg-surface border border-border">
          <input
            value={form.skill_id}
            onChange={(e) => setForm({ ...form, skill_id: e.target.value })}
            placeholder="Skill ID"
            aria-label="Skill ID"
            className="w-full bg-surface-raised border border-border rounded px-3 lg:px-4 py-1 min-h-[44px] text-[11px] text-slate-300 placeholder:text-slate-600 focus:outline-none"
          />
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="İsim"
            aria-label="Skill ismi"
            className="w-full bg-surface-raised border border-border rounded px-3 lg:px-4 py-1 min-h-[44px] text-[11px] text-slate-300 placeholder:text-slate-600 focus:outline-none"
          />
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            aria-label="Skill kategorisi"
            className="w-full bg-surface-raised border border-border rounded px-3 lg:px-4 py-1 min-h-[44px] text-[11px] text-slate-300 focus:outline-none cursor-pointer"
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
            aria-label="Skill açıklaması"
            className="w-full bg-surface-raised border border-border rounded px-3 lg:px-4 py-1 min-h-[44px] text-[11px] text-slate-300 placeholder:text-slate-600 focus:outline-none"
          />
          <textarea
            value={form.knowledge}
            onChange={(e) => setForm({ ...form, knowledge: e.target.value })}
            placeholder="Bilgi / Protokol"
            aria-label="Skill bilgi ve protokolü"
            rows={3}
            className="w-full bg-surface-raised border border-border rounded px-3 lg:px-4 py-1 text-[11px] text-slate-300 placeholder:text-slate-600 resize-none focus:outline-none"
          />
          <input
            value={form.keywords}
            onChange={(e) => setForm({ ...form, keywords: e.target.value })}
            placeholder="Anahtar kelimeler (virgülle)"
            aria-label="Skill anahtar kelimeleri"
            className="w-full bg-surface-raised border border-border rounded px-3 lg:px-4 py-1 min-h-[44px] text-[11px] text-slate-300 placeholder:text-slate-600 focus:outline-none"
          />
          <button
            onClick={handleCreate}
            aria-label="Skill oluştur"
            className="w-full min-h-[44px] py-1.5 rounded bg-green-600/20 text-green-400 text-[11px] font-medium hover:bg-green-600/30 transition-colors cursor-pointer flex items-center justify-center gap-1.5"
          >
            <CheckCircle className="w-4 h-4" /> Oluştur
          </button>
        </div>
      )}

      {msg && <div className="text-[10px] text-slate-400">{msg}</div>}

      {/* Auto-learned skills */}
      {autoSkills.length > 0 && (
        <div className="space-y-1">
          <div className="text-[10px] text-slate-500 flex items-center gap-1">
            <Bot className="w-3 h-3 text-amber-400" aria-hidden="true" />
            <span>Otomatik: {autoSkills.length}</span>
          </div>
          {autoSkills.map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between text-[10px] text-slate-400 py-0.5"
            >
              <button
                onClick={() => setSelectedSkillId(s.id)}
                aria-label={`${s.name} skill detayını görüntüle`}
                className="flex items-center gap-1 min-w-0 flex-1 text-left cursor-pointer hover:text-slate-200 transition-colors min-h-[44px] pr-1"
              >
                <span className="text-teal-400 shrink-0">[{s.category}]</span>
                <span className="truncate">{s.name}</span>
                <span className="shrink-0 px-1 py-0.5 rounded bg-amber-500/15 text-amber-400 text-[9px] font-medium">
                  🤖 Otomatik
                </span>
              </button>
              <button
                onClick={() => handleDelete(s.id)}
                aria-label={`${s.name} skill'ini sil`}
                className="min-w-[44px] min-h-[44px] flex items-center justify-center text-red-400 hover:text-red-300 cursor-pointer shrink-0"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Custom skills */}
      {custom.length > 0 && (
        <div className="space-y-1">
          <div className="text-[10px] text-slate-500 flex items-center gap-1">
            <Wrench className="w-3 h-3" aria-hidden="true" /> Özel:{" "}
            {custom.length}
          </div>
          {custom.map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between text-[10px] text-slate-400 py-0.5"
            >
              <button
                onClick={() => setSelectedSkillId(s.id)}
                aria-label={`${s.name} skill detayını görüntüle`}
                className="flex items-center gap-1 min-w-0 flex-1 text-left cursor-pointer hover:text-slate-200 transition-colors min-h-[44px] pr-1"
              >
                <span className="text-teal-400">[{s.category}]</span> {s.name}
              </button>
              <button
                onClick={() => handleDelete(s.id)}
                aria-label={`${s.name} skill'ini sil`}
                className="min-w-[44px] min-h-[44px] flex items-center justify-center text-red-400 hover:text-red-300 cursor-pointer"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="text-[10px] text-slate-600 flex items-center gap-1">
        <Package className="w-3 h-3" aria-hidden="true" /> Yerleşik:{" "}
        {builtin.length} · Toplam: {skills.length + autoSkills.length}
      </div>
    </div>
  );
}

// ── Memory Panel ────────────────────────────────────────────────

interface MemoryItem {
  id: number;
  content: string;
  layer: string;
  category: string;
  created_at?: string;
}

interface MemoryStats {
  total_memories: number;
  with_embeddings?: number;
  backend?: string;
  layers?: Record<string, number>;
  error?: string;
}

interface MemoryLayers {
  working: MemoryItem[];
  episodic: MemoryItem[];
  semantic: MemoryItem[];
}

type MemoryTab = "genel" | "katmanlar";

export function MemoryPanel() {
  const [tab, setTab] = useState<MemoryTab>("genel");
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [layers, setLayers] = useState<MemoryLayers>({
    working: [],
    episodic: [],
    semantic: [],
  });
  const [dbHealth, setDbHealth] = useState<{
    status: string;
    backend?: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [s, l, h] = await Promise.all([
        getMemoryStats() as Promise<MemoryStats | null>,
        getMemoryLayers() as Promise<MemoryLayers>,
        getDbHealth() as Promise<{ status: string; backend?: string }>,
      ]);
      setStats(s);
      setLayers(l);
      setDbHealth(h);
    } catch {
      /* backend offline */
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDelete = async (id: number) => {
    const ok = await deleteMemory(id);
    if (ok) loadData();
  };

  const allMemories = [
    ...layers.working,
    ...layers.episodic,
    ...layers.semantic,
  ];

  const layerColor: Record<string, string> = {
    working: "text-blue-400",
    episodic: "text-teal-400",
    semantic: "text-amber-400",
  };

  return (
    <div className="space-y-3 px-3 lg:px-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
          <Brain className="w-4 h-4" aria-hidden="true" /> Bellek
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          aria-label="Belleği yenile"
          className="min-h-[44px] min-w-[44px] flex items-center justify-center text-slate-500 hover:text-slate-300 cursor-pointer disabled:opacity-40"
        >
          <Loader2 className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Stats row */}
      <div className="flex flex-wrap gap-1.5">
        <span className="px-1.5 py-0.5 rounded bg-surface-raised border border-border text-[10px] text-slate-400 flex items-center gap-1">
          <Database className="w-3 h-3" aria-hidden="true" />
          {stats?.total_memories ?? 0} kayıt
        </span>
        {stats?.with_embeddings != null && (
          <span className="px-1.5 py-0.5 rounded bg-surface-raised border border-border text-[10px] text-slate-400">
            {stats.with_embeddings} vektör
          </span>
        )}
        <span
          className={`px-1.5 py-0.5 rounded border text-[10px] font-medium ${
            dbHealth?.status === "ok"
              ? "bg-green-500/10 border-green-500/30 text-green-400"
              : "bg-slate-500/10 border-slate-500/30 text-slate-500"
          }`}
        >
          {dbHealth?.backend ?? "—"}
        </span>
      </div>

      {/* Tabs */}
      <div className="flex gap-1" role="tablist" aria-label="Bellek görünümü">
        {(["genel", "katmanlar"] as MemoryTab[]).map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`flex-1 min-h-[36px] text-[10px] font-medium rounded transition-colors cursor-pointer ${
              tab === t
                ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                : "text-slate-500 hover:text-slate-400 border border-transparent"
            }`}
          >
            {t === "genel" ? "Genel" : "Katmanlar"}
          </button>
        ))}
      </div>

      {/* Tab: Genel */}
      {tab === "genel" && (
        <div className="space-y-1" role="tabpanel">
          {allMemories.length === 0 ? (
            <div className="text-[10px] text-slate-600">Henüz bellek yok</div>
          ) : (
            allMemories.slice(0, 15).map((m) => (
              <div
                key={m.id}
                className="flex items-start justify-between gap-1 text-[10px] text-slate-400 py-0.5"
              >
                <span className="flex items-start gap-1 min-w-0">
                  <span
                    className={`shrink-0 font-medium ${layerColor[m.layer] ?? "text-slate-500"}`}
                  >
                    [{m.layer}]
                  </span>
                  <span className="truncate">{m.content?.slice(0, 70)}</span>
                </span>
                <button
                  onClick={() => handleDelete(m.id)}
                  aria-label={`Belleği sil: ${m.id}`}
                  className="min-w-[44px] min-h-[44px] flex items-center justify-center text-red-400 hover:text-red-300 cursor-pointer shrink-0"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
          {allMemories.length > 15 && (
            <div className="text-[10px] text-slate-600">
              +{allMemories.length - 15} daha
            </div>
          )}
        </div>
      )}

      {/* Tab: Katmanlar */}
      {tab === "katmanlar" && (
        <div className="space-y-3" role="tabpanel">
          {(
            [
              {
                key: "working",
                label: "Working",
                icon: "⚡",
                color: "text-blue-400",
                bg: "bg-blue-500/10 border-blue-500/20",
              },
              {
                key: "episodic",
                label: "Episodic",
                icon: "📖",
                color: "text-teal-400",
                bg: "bg-teal-500/10 border-teal-500/20",
              },
              {
                key: "semantic",
                label: "Semantic",
                icon: "🧠",
                color: "text-amber-400",
                bg: "bg-amber-500/10 border-amber-500/20",
              },
            ] as const
          ).map(({ key, label, icon, color, bg }) => {
            const items = layers[key];
            return (
              <div key={key} className="space-y-1">
                <div
                  className={`flex items-center justify-between px-2 py-1 rounded border ${bg}`}
                >
                  <span
                    className={`text-[10px] font-medium ${color} flex items-center gap-1`}
                  >
                    <Layers className="w-3 h-3" aria-hidden="true" />
                    {icon} {label}
                  </span>
                  <span className={`text-[10px] font-bold ${color}`}>
                    {items.length}
                  </span>
                </div>
                {items.slice(0, 5).map((m) => (
                  <div
                    key={m.id}
                    className="flex items-start justify-between gap-1 text-[10px] text-slate-500 pl-2"
                  >
                    <span className="truncate">{m.content?.slice(0, 60)}</span>
                    <button
                      onClick={() => handleDelete(m.id)}
                      aria-label={`Belleği sil: ${m.id}`}
                      className="min-w-[44px] min-h-[44px] flex items-center justify-center text-red-400/60 hover:text-red-400 cursor-pointer shrink-0"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
                {items.length === 0 && (
                  <div className="text-[10px] text-slate-600 pl-2">Boş</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── MCP Panel ───────────────────────────────────────────────────

interface McpServer {
  id: string;
  name: string;
  url?: string;
  command?: string;
  description?: string;
  tool_count?: number;
  active?: boolean;
}

export function McpPanel() {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ server_id: "", url: "", name: "" });
  const [msg, setMsg] = useState("");

  const loadServers = useCallback(async () => {
    try {
      const s = (await api.mcpServers()) as McpServer[];
      setServers(s);
    } catch {
      /* */
    }
  }, []);

  useEffect(() => {
    loadServers();
  }, [loadServers]);

  const handleAdd = async () => {
    if (!form.server_id || !form.url) return;
    setMsg("");
    try {
      await api.addMcpServer(form.server_id, form.url, form.name);
      setMsg("Sunucu eklendi");
      setForm({ server_id: "", url: "", name: "" });
      setShowForm(false);
      loadServers();
    } catch (e) {
      setMsg(`${e instanceof Error ? e.message : "Hata"}`);
    }
  };

  return (
    <div className="space-y-3 px-3 lg:px-4">
      <div className="flex items-center justify-between">
        <div className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
          <Plug className="w-4 h-4" aria-hidden="true" /> MCP Servers
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          aria-label={showForm ? "MCP formunu kapat" : "Yeni MCP sunucusu ekle"}
          aria-expanded={showForm}
          className="min-h-[44px] min-w-[44px] flex items-center justify-center text-[10px] text-blue-400 hover:text-blue-300 cursor-pointer"
        >
          {showForm ? (
            <>
              <X className="w-4 h-4" /> <span className="ml-1">Kapat</span>
            </>
          ) : (
            <>
              <Plus className="w-4 h-4" /> <span className="ml-1">Ekle</span>
            </>
          )}
        </button>
      </div>

      {showForm && (
        <div className="space-y-2 p-2 rounded bg-surface border border-border">
          <input
            value={form.server_id}
            onChange={(e) => setForm({ ...form, server_id: e.target.value })}
            placeholder="Server ID"
            aria-label="MCP Server ID"
            className="w-full bg-surface-raised border border-border rounded px-3 lg:px-4 py-1 min-h-[44px] text-[11px] text-slate-300 placeholder:text-slate-600 focus:outline-none"
          />
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="İsim"
            aria-label="MCP sunucu ismi"
            className="w-full bg-surface-raised border border-border rounded px-3 lg:px-4 py-1 min-h-[44px] text-[11px] text-slate-300 placeholder:text-slate-600 focus:outline-none"
          />
          <input
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
            placeholder="URL / Komut"
            aria-label="MCP sunucu URL veya komutu"
            className="w-full bg-surface-raised border border-border rounded px-3 lg:px-4 py-1 min-h-[44px] text-[11px] text-slate-300 placeholder:text-slate-600 focus:outline-none"
          />
          <button
            onClick={handleAdd}
            aria-label="MCP sunucusunu kaydet"
            className="w-full min-h-[44px] py-1.5 rounded bg-green-600/20 text-green-400 text-[11px] font-medium hover:bg-green-600/30 transition-colors cursor-pointer flex items-center justify-center gap-1.5"
          >
            <CheckCircle className="w-4 h-4" /> Kaydet
          </button>
        </div>
      )}

      {msg && <div className="text-[10px] text-slate-400">{msg}</div>}

      {servers.length > 0 ? (
        <div className="space-y-1.5">
          {servers.map((s) => (
            <div
              key={s.id}
              className="text-[10px] text-slate-400 flex flex-col gap-0.5 p-2 rounded bg-surface-raised border border-border/50"
            >
              <div className="flex items-center gap-1.5">
                <Circle
                  className="w-2.5 h-2.5 fill-green-400 text-green-400 shrink-0"
                  aria-hidden="true"
                />
                <span className="text-slate-200 font-medium text-[11px]">
                  {s.name || s.id}
                </span>
                {s.tool_count != null && s.tool_count > 0 && (
                  <span className="ml-auto text-[9px] text-blue-400 bg-blue-400/10 px-1.5 py-0.5 rounded">
                    {s.tool_count} tool
                  </span>
                )}
              </div>
              {s.description && (
                <span className="text-slate-500 text-[9px] leading-relaxed pl-4">
                  {s.description}
                </span>
              )}
              {s.command && (
                <span className="text-slate-600 text-[9px] font-mono pl-4 truncate">
                  {s.command}{" "}
                  {Array.isArray((s as any).args)
                    ? (s as any).args.slice(0, 2).join(" ")
                    : ""}
                </span>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-[10px] text-slate-600">Henüz MCP sunucusu yok</div>
      )}
    </div>
  );
}

// ── Teachability Panel ──────────────────────────────────────────

interface Teaching {
  id: string;
  instruction: string;
  category: string;
  use_count: number;
}

export function TeachabilityPanel() {
  const [teachings, setTeachings] = useState<Teaching[]>([]);
  const [input, setInput] = useState("");
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    try {
      const t = (await api.getTeachings()) as Teaching[];
      setTeachings(t);
    } catch {
      /* */
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleAdd = async () => {
    if (!input.trim()) return;
    setMsg("");
    try {
      await api.addTeaching(input);
      setMsg("Kaydedildi");
      setInput("");
      load();
    } catch (e) {
      setMsg(`${e instanceof Error ? e.message : "Hata"}`);
    }
  };

  return (
    <div className="space-y-3 px-3 lg:px-4">
      <div className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
        <GraduationCap className="w-4 h-4" aria-hidden="true" /> Teachability
      </div>
      <div className="flex gap-1">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="Tercih veya öğreti ekle..."
          aria-label="Yeni öğreti veya tercih"
          className="flex-1 bg-surface border border-border rounded px-3 lg:px-4 py-1.5 min-h-[44px] text-xs text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-blue-500/50"
        />
        <button
          onClick={handleAdd}
          aria-label="Öğretiyi kaydet"
          className="min-w-[44px] min-h-[44px] px-2 py-1.5 rounded bg-blue-600/20 text-blue-400 text-xs hover:bg-blue-600/30 transition-colors cursor-pointer flex items-center justify-center"
        >
          <Save className="w-4 h-4" />
        </button>
      </div>
      {msg && <div className="text-[10px] text-slate-400">{msg}</div>}
      {teachings.length > 0 ? (
        <div className="space-y-1">
          {teachings.slice(0, 8).map((t) => (
            <div key={t.id} className="text-[10px] text-slate-500">
              <span className="text-teal-400">[{t.category}]</span>{" "}
              {t.instruction.slice(0, 80)}
              <span className="text-slate-600 ml-1">({t.use_count}x)</span>
            </div>
          ))}
          <div className="text-[10px] text-slate-600">
            {teachings.length} aktif öğreti
          </div>
        </div>
      ) : (
        <div className="text-[10px] text-slate-600">Henüz öğreti yok</div>
      )}
    </div>
  );
}

// ── Eval Panel ──────────────────────────────────────────────────

interface EvalStat {
  agent_role: string;
  avg_score: number;
  total_tasks: number;
}

export function EvalPanel() {
  const [stats, setStats] = useState<EvalStat[]>([]);

  useEffect(() => {
    api
      .evalStats()
      .then((s) => setStats(s as EvalStat[]))
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-3 px-3 lg:px-4">
      <div className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
        <BarChart3 className="w-4 h-4" aria-hidden="true" /> Agent Eval
      </div>
      {stats.length > 0 ? (
        <div className="space-y-2">
          {stats.map((s) => {
            const color =
              s.avg_score >= 4
                ? "#10b981"
                : s.avg_score >= 3
                  ? "#f59e0b"
                  : "#ef4444";
            const pct = Math.min((s.avg_score / 5) * 100, 100);
            return (
              <div key={s.agent_role}>
                <div className="flex items-center justify-between text-[11px]">
                  <span style={{ color }} className="font-medium">
                    {s.agent_role}
                  </span>
                  <span className="text-slate-500 flex items-center gap-1">
                    <Star className="w-3 h-3" aria-hidden="true" />{" "}
                    {s.avg_score.toFixed(1)}/5 · {s.total_tasks} görev
                  </span>
                </div>
                <div
                  className="h-1.5 bg-surface-raised rounded-full mt-1 overflow-hidden"
                  role="progressbar"
                  aria-valuenow={s.avg_score}
                  aria-valuemin={0}
                  aria-valuemax={5}
                  aria-label={`${s.agent_role} skoru: ${s.avg_score.toFixed(1)}/5`}
                >
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${pct}%`, backgroundColor: color }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-[10px] text-slate-600">
          Henüz değerlendirme verisi yok
        </div>
      )}
    </div>
  );
}
