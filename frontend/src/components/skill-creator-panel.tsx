"use client";

import { useState } from "react";
import {
  CheckCircle2,
  XCircle,
  Search,
  Loader2,
  AlertTriangle,
  FileCheck,
  FlaskConical,
} from "lucide-react";

import { fetcher } from "@/lib/api";

// ── Types ──

interface ValidateResult {
  valid: boolean;
  score: number;
  line_count: number;
  issues: string[];
  suggestions: string[];
  has_frontmatter: boolean;
}

interface GradeExpectation {
  text: string;
  passed: boolean;
  evidence: string;
}

interface GradeResult {
  expectations: GradeExpectation[];
  summary: { passed: number; failed: number; total: number; pass_rate: number };
}

interface SkillSearchResult {
  name: string;
  description: string;
  path: string;
  relevance: number;
}

// ── Tab Button ──

function Tab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
        active
          ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
          : "text-slate-400 hover:text-slate-200 border border-transparent hover:border-border"
      }`}
    >
      {children}
    </button>
  );
}

// ── Validate Tab ──

function ValidateTab() {
  const [path, setPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ValidateResult | null>(null);
  const [error, setError] = useState("");

  const run = async () => {
    if (!path.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const r = await fetcher<ValidateResult>("/api/skill-creator/validate", {
        method: "POST",
        body: JSON.stringify({ skill_path: path.trim() }),
      });
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Validation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          value={path}
          onChange={(e) => setPath(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="skills/my-skill veya SKILL.md yolu..."
          className="flex-1 bg-surface-raised border border-border rounded-md px-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-amber-500/50"
        />
        <button
          onClick={run}
          disabled={loading || !path.trim()}
          className="px-3 py-1.5 text-xs font-medium rounded-md bg-amber-500/20 text-amber-400 border border-amber-500/40 hover:bg-amber-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            "Validate"
          )}
        </button>
      </div>

      {error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-3">
          {/* Score */}
          <div className="flex items-center justify-between bg-surface-raised/50 border border-border rounded-md px-3 py-2.5">
            <div className="flex items-center gap-2">
              {result.valid ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : (
                <XCircle className="w-4 h-4 text-red-400" />
              )}
              <span className="text-xs font-medium text-slate-200">
                {result.valid ? "Geçerli" : "Sorunlar var"}
              </span>
            </div>
            <div className="flex items-center gap-3 text-[11px]">
              <span className="text-slate-500">Skor</span>
              <span
                className={`font-bold text-sm ${
                  result.score >= 80
                    ? "text-emerald-400"
                    : result.score >= 50
                      ? "text-amber-400"
                      : "text-red-400"
                }`}
              >
                {result.score}/100
              </span>
            </div>
          </div>

          {/* Issues */}
          {result.issues.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-[10px] font-medium text-red-400 uppercase tracking-wide">
                Sorunlar ({result.issues.length})
              </div>
              {result.issues.map((issue, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 text-xs text-slate-300 bg-red-500/5 border border-red-500/10 rounded px-2.5 py-1.5"
                >
                  <XCircle className="w-3 h-3 text-red-400 mt-0.5 shrink-0" />
                  {issue}
                </div>
              ))}
            </div>
          )}

          {/* Suggestions */}
          {result.suggestions.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-[10px] font-medium text-amber-400 uppercase tracking-wide">
                Öneriler ({result.suggestions.length})
              </div>
              {result.suggestions.map((s, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 text-xs text-slate-400 bg-amber-500/5 border border-amber-500/10 rounded px-2.5 py-1.5"
                >
                  <AlertTriangle className="w-3 h-3 text-amber-400 mt-0.5 shrink-0" />
                  {s}
                </div>
              ))}
            </div>
          )}

          {/* Meta */}
          <div className="flex gap-3 text-[10px] text-slate-500 pt-1 border-t border-border">
            <span>{result.line_count} satır</span>
            <span>Frontmatter: {result.has_frontmatter ? "✓" : "✗"}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Grade Tab ──

function GradeTab() {
  const [output, setOutput] = useState("");
  const [expectations, setExpectations] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GradeResult | null>(null);
  const [error, setError] = useState("");

  const run = async () => {
    const exps = expectations
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    if (!output.trim() || exps.length === 0) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const r = await fetcher<GradeResult>("/api/skill-creator/grade", {
        method: "POST",
        body: JSON.stringify({
          output_text: output.trim(),
          expectations: exps,
        }),
      });
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Grading failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div>
        <label className="text-[10px] font-medium text-slate-400 uppercase tracking-wide block mb-1">
          Çıktı Metni
        </label>
        <textarea
          value={output}
          onChange={(e) => setOutput(e.target.value)}
          placeholder="Skill çıktısını yapıştırın..."
          rows={4}
          className="w-full bg-surface-raised border border-border rounded-md px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-amber-500/50 resize-none font-mono"
        />
      </div>
      <div>
        <label className="text-[10px] font-medium text-slate-400 uppercase tracking-wide block mb-1">
          Beklentiler (satır başına bir tane)
        </label>
        <textarea
          value={expectations}
          onChange={(e) => setExpectations(e.target.value)}
          placeholder={
            "YAML frontmatter içermeli\nÖrnekler bulunmalı\nDescription 50+ karakter olmalı"
          }
          rows={3}
          className="w-full bg-surface-raised border border-border rounded-md px-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-amber-500/50 resize-none font-mono"
        />
      </div>
      <button
        onClick={run}
        disabled={loading || !output.trim() || !expectations.trim()}
        className="px-3 py-1.5 text-xs font-medium rounded-md bg-amber-500/20 text-amber-400 border border-amber-500/40 hover:bg-amber-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin inline mr-1" />
        ) : null}
        Grade
      </button>

      {error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-3">
          {/* Summary bar */}
          <div className="flex items-center justify-between bg-surface-raised/50 border border-border rounded-md px-3 py-2.5">
            <span className="text-xs text-slate-300">
              <span className="text-emerald-400 font-bold">
                {result.summary.passed}
              </span>
              <span className="text-slate-500">
                {" "}
                / {result.summary.total} geçti
              </span>
            </span>
            <span
              className={`text-sm font-bold ${
                result.summary.pass_rate >= 0.8
                  ? "text-emerald-400"
                  : result.summary.pass_rate >= 0.5
                    ? "text-amber-400"
                    : "text-red-400"
              }`}
            >
              %{Math.round(result.summary.pass_rate * 100)}
            </span>
          </div>

          {/* Expectation results */}
          <div className="space-y-1.5">
            {result.expectations.map((exp, i) => (
              <div
                key={i}
                className={`rounded px-2.5 py-2 border text-xs ${
                  exp.passed
                    ? "bg-emerald-500/5 border-emerald-500/15 text-slate-300"
                    : "bg-red-500/5 border-red-500/15 text-slate-300"
                }`}
              >
                <div className="flex items-center gap-2">
                  {exp.passed ? (
                    <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                  ) : (
                    <XCircle className="w-3 h-3 text-red-400 shrink-0" />
                  )}
                  <span className="font-medium">{exp.text}</span>
                </div>
                <div className="text-[10px] text-slate-500 mt-1 ml-5">
                  {exp.evidence}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Search Tab ──

function SearchTab() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SkillSearchResult[]>([]);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  const run = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setSearched(true);
    try {
      const r = await fetcher<SkillSearchResult[]>(
        `/api/skill-creator/search?query=${encodeURIComponent(query.trim())}`,
      );
      setResults(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="Skill ara... (ör: code review, testing)"
          className="flex-1 bg-surface-raised border border-border rounded-md px-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-amber-500/50"
        />
        <button
          onClick={run}
          disabled={loading || !query.trim()}
          className="px-3 py-1.5 text-xs font-medium rounded-md bg-amber-500/20 text-amber-400 border border-amber-500/40 hover:bg-amber-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Search className="w-3.5 h-3.5" />
          )}
        </button>
      </div>

      {error && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      {results.length > 0 ? (
        <div className="space-y-1.5">
          {results.map((r, i) => (
            <div
              key={i}
              className="bg-surface-raised/50 border border-border rounded-md px-3 py-2 space-y-1"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-amber-400">
                  {r.name}
                </span>
                {r.relevance != null && (
                  <span className="text-[10px] text-slate-500">
                    %{Math.round(r.relevance * 100)} eşleşme
                  </span>
                )}
              </div>
              {r.description && (
                <div className="text-[11px] text-slate-400 line-clamp-2">
                  {r.description}
                </div>
              )}
              {r.path && (
                <div className="text-[10px] text-slate-600 font-mono truncate">
                  {r.path}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        searched &&
        !loading &&
        !error && (
          <div className="text-[11px] text-slate-500 text-center py-4">
            Sonuç bulunamadı
          </div>
        )
      )}
    </div>
  );
}

// ── Main Panel ──

const TABS = [
  { id: "validate", label: "Validate", icon: FileCheck },
  { id: "grade", label: "Grade", icon: FlaskConical },
  { id: "search", label: "Search", icon: Search },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function SkillCreatorPanel() {
  const [tab, setTab] = useState<TabId>("validate");

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Tab bar */}
      <div className="flex items-center gap-1.5 px-3 py-2 border-b border-border shrink-0">
        {TABS.map((t) => (
          <Tab key={t.id} active={tab === t.id} onClick={() => setTab(t.id)}>
            <span className="flex items-center gap-1.5">
              <t.icon className="w-3 h-3" />
              {t.label}
            </span>
          </Tab>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-auto p-3">
        {tab === "validate" && <ValidateTab />}
        {tab === "grade" && <GradeTab />}
        {tab === "search" && <SearchTab />}
      </div>
    </div>
  );
}

export default SkillCreatorPanel;
