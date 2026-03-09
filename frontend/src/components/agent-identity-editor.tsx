"use client";

import { useState, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import { api } from "@/lib/api";
import { AGENT_CONFIG } from "@/lib/agents";
import type { AgentRole, IdentityFileType } from "@/lib/types";

const allRoles = Object.keys(AGENT_CONFIG) as AgentRole[];
const crd = "bg-slate-800/50 border border-slate-700/50 rounded-lg p-4";

/** Strip YAML frontmatter for cleaner preview */
function stripFrontmatter(md: string): string {
  const m = md.match(/^---\s*\n[\s\S]*?\n---\s*\n?/);
  return m ? md.slice(m[0].length) : md;
}

const FILE_TABS: { key: IdentityFileType; label: string; icon: string }[] = [
  { key: "soul", label: "SOUL", icon: "🧬" },
  { key: "user", label: "Kullanıcı", icon: "👤" },
  { key: "memory", label: "Hafıza", icon: "🧠" },
  { key: "bootstrap", label: "Başlatma", icon: "🚀" },
];

export function AgentIdentityEditor() {
  const [role, setRole] = useState<AgentRole>("orchestrator");
  const [tab, setTab] = useState<IdentityFileType>("soul");
  const [contents, setContents] = useState<Record<IdentityFileType, string>>({
    soul: "",
    user: "",
    memory: "",
    bootstrap: "",
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [initializing, setInitializing] = useState(false);
  const [dirty, setDirty] = useState<Set<IdentityFileType>>(new Set());
  const [preview, setPreview] = useState(false);

  const loadIdentity = useCallback(async (r: AgentRole) => {
    setLoading(true);
    setError("");
    try {
      const data = await api.getAgentIdentity(r);
      setContents({
        soul: data.soul || "",
        user: data.user || "",
        memory: data.memory || "",
        bootstrap: data.bootstrap || "",
      });
      setDirty(new Set());
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Yüklenemedi";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadIdentity(role);
  }, [role, loadIdentity]);

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await api.updateIdentityFile(role, tab, contents[tab]);
      setSuccess(`${tab.toUpperCase()} kaydedildi`);
      setDirty((prev) => {
        const n = new Set(prev);
        n.delete(tab);
        return n;
      });
      setTimeout(() => setSuccess(""), 2000);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Kaydedilemedi";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleInitialize = async () => {
    setInitializing(true);
    setError("");
    try {
      const res = await api.initializeAllIdentities();
      setSuccess(`${res.initialized} agent başlatıldı`);
      await loadIdentity(role);
      setTimeout(() => setSuccess(""), 3000);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Başlatılamadı";
      setError(msg);
    } finally {
      setInitializing(false);
    }
  };

  const handleChange = (value: string) => {
    setContents((prev) => ({ ...prev, [tab]: value }));
    setDirty((prev) => new Set(prev).add(tab));
  };

  const agentCfg = AGENT_CONFIG[role];

  return (
    <div className="flex flex-col gap-3">
      {/* Header: Agent selector + Initialize button */}
      <div className="flex items-center gap-2 flex-wrap">
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as AgentRole)}
          className="bg-slate-800/60 border border-slate-700/50 rounded px-2 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/50"
          aria-label="Agent seçimi"
        >
          {allRoles.map((r) => (
            <option key={r} value={r}>
              {AGENT_CONFIG[r].icon} {AGENT_CONFIG[r].name} ({r})
            </option>
          ))}
        </select>
        <span
          className="text-[10px] px-2 py-0.5 rounded"
          style={{
            backgroundColor: agentCfg.color + "22",
            color: agentCfg.color,
          }}
        >
          {agentCfg.icon} {role}
        </span>
        <div className="flex-1" />
        <button
          onClick={handleInitialize}
          disabled={initializing}
          className="text-[10px] px-2 py-1 rounded bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/30 disabled:opacity-50 transition-colors"
        >
          {initializing ? "Başlatılıyor..." : "🔄 Tümünü Başlat"}
        </button>
      </div>

      {/* File tabs */}
      <div
        className="flex border-b border-slate-700/50"
        role="tablist"
        aria-label="Kimlik dosyası sekmeleri"
      >
        {FILE_TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            onClick={() => setTab(t.key)}
            className={`text-xs font-medium px-3 py-1.5 border-b-2 transition-colors ${
              tab === t.key
                ? "border-cyan-400 text-cyan-400"
                : "border-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            <span className="mr-1">{t.icon}</span>
            {t.label}
            {dirty.has(t.key) && <span className="ml-1 text-amber-400">●</span>}
          </button>
        ))}
      </div>

      {/* Status messages */}
      {error && (
        <div className="text-[10px] text-red-400 bg-red-900/20 rounded px-2 py-1">
          {error}
        </div>
      )}
      {success && (
        <div className="text-[10px] text-emerald-400 bg-emerald-900/20 rounded px-2 py-1">
          {success}
        </div>
      )}

      {/* Editor */}
      {loading ? (
        <div className={crd}>
          <div className="h-48 flex items-center justify-center text-slate-500 text-xs">
            Yükleniyor...
          </div>
        </div>
      ) : (
        <div className={crd}>
          {/* Edit / Preview toggle */}
          <div className="flex items-center gap-1 mb-2">
            <button
              onClick={() => setPreview(false)}
              className={`text-[10px] px-2 py-1 rounded transition-colors ${!preview ? "bg-cyan-600/20 text-cyan-400 border border-cyan-500/30" : "text-slate-500 hover:text-slate-300"}`}
            >
              ✏️ Düzenle
            </button>
            <button
              onClick={() => setPreview(true)}
              className={`text-[10px] px-2 py-1 rounded transition-colors ${preview ? "bg-cyan-600/20 text-cyan-400 border border-cyan-500/30" : "text-slate-500 hover:text-slate-300"}`}
            >
              👁 Önizleme
            </button>
          </div>

          {preview ? (
            <div className="w-full h-64 bg-slate-900/50 border border-slate-700/30 rounded p-3 overflow-y-auto select-text cursor-text">
              {contents[tab].trim() ? (
                <div className="prose prose-invert prose-sm max-w-none prose-headings:text-slate-700 prose-p:text-slate-300 prose-strong:text-slate-700 prose-code:text-cyan-300 prose-code:bg-slate-800/50 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-700/30 prose-li:text-slate-300 prose-a:text-cyan-400">
                  <ReactMarkdown>
                    {stripFrontmatter(contents[tab])}
                  </ReactMarkdown>
                </div>
              ) : (
                <span className="text-xs text-slate-600">İçerik yok</span>
              )}
            </div>
          ) : (
            <textarea
              value={contents[tab]}
              onChange={(e) => handleChange(e.target.value)}
              className="w-full h-64 bg-slate-900/50 border border-slate-700/30 rounded p-3 text-xs text-slate-300 font-mono resize-y focus:outline-none focus:border-cyan-500/50 placeholder-slate-600"
              placeholder={`${tab}.md içeriğini buraya yazın...`}
              spellCheck={false}
              aria-label={`${tab} dosyası editörü`}
            />
          )}
          <div className="flex items-center justify-between mt-2">
            <span className="text-[10px] text-slate-600">
              {contents[tab].length} karakter •{" "}
              {contents[tab].split("\n").length} satır
            </span>
            <button
              onClick={handleSave}
              disabled={saving || !dirty.has(tab)}
              className="text-[10px] px-3 py-1 rounded bg-cyan-600/20 text-cyan-400 hover:bg-cyan-600/30 disabled:opacity-40 transition-colors"
            >
              {saving ? "Kaydediliyor..." : "💾 Kaydet"}
            </button>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="text-[10px] text-slate-600 px-1">
        SOUL.md = Kişilik • user.md = Kullanıcı tercihleri • memory.md = Oturum
        hafızası • bootstrap.md = Başlatma protokolü
      </div>
    </div>
  );
}
