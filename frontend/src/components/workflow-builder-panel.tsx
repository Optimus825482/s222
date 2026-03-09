"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Workflow,
  Play,
  Plus,
  Trash2,
  Settings,
  ChevronRight,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Calendar,
  Timer,
  Zap,
  HelpCircle,
  Sparkles,
  Wand2,
  Bot,
} from "lucide-react";
import { api } from "@/lib/api";
import type {
  WorkflowTemplate,
  WorkflowRunResult,
  ScheduledWorkflow,
} from "@/lib/types";

/* ── Local Types ───────────────────────────────────────────────── */
type StepType = "tool_call" | "agent_call" | "condition" | "parallel";
type WfTab = "guide" | "templates" | "custom" | "scheduler" | "assistant";

interface CustomStep {
  step_id: string;
  step_type: StepType;
  tool_name?: string;
  tool_args?: string;
  agent_role?: string;
  agent_prompt?: string;
  field?: string;
  operator?: string;
  value?: string;
  then_step?: string;
  else_step?: string;
  parallel_steps?: string[];
  on_error: "rollback";
}

/* ── Constants ─────────────────────────────────────────────────── */
const TOOLS = [
  "web_search",
  "web_fetch",
  "code_execute",
  "rag_query",
  "rag_ingest",
  "rag_list_documents",
  "save_memory",
  "recall_memory",
  "list_memories",
  "memory_stats",
  "find_skill",
  "use_skill",
  "create_skill",
  "research_create_skill",
  "idea_to_project",
  "spawn_subagent",
  "request_approval",
  "self_evaluate",
  "get_agent_baseline",
  "get_best_agent",
  "mcp_call",
  "mcp_list_tools",
  "generate_image",
  "generate_chart",
  "generate_presentation",
  "run_workflow",
  "list_workflows",
  "domain_expert",
  "list_domain_tools",
  "check_budget",
  "check_error_patterns",
  "list_teachings",
  "decompose_task",
  "direct_response",
  "synthesize_results",
] as const;

const AGENTS = [
  "thinker",
  "speed",
  "researcher",
  "reasoner",
  "critic",
] as const;

const OPERATORS = ["eq", "neq", "contains", "gt", "lt"] as const;

const STEP_TYPES: { value: StepType; label: string }[] = [
  { value: "tool_call", label: "Araç Çağrısı" },
  { value: "agent_call", label: "Ajan Çağrısı" },
  { value: "condition", label: "Koşul" },
  { value: "parallel", label: "Paralel" },
];

/* ── Shared Styles ─────────────────────────────────────────────── */
const crd = "bg-slate-800/50 border border-slate-700/50 rounded-lg p-3";
const inp =
  "bg-slate-800/60 border border-slate-700/50 rounded px-2 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500/50 w-full";
const btnPrimary =
  "inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] font-medium bg-cyan-600/80 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors";
const btnDanger =
  "inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] bg-red-600/30 hover:bg-red-500/40 text-red-400 hover:text-red-300 transition-colors";

/* ── Helpers ───────────────────────────────────────────────────── */
const dur = (ms: number) =>
  ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;

const fdt = (iso: string | null) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
};

const makeStep = (index: number): CustomStep => ({
  step_id: `step_${index}`,
  step_type: "tool_call",
  tool_name: TOOLS[0],
  tool_args: "{}",
  on_error: "rollback",
});

/* ── Tab Definitions ───────────────────────────────────────────── */
const TABS: { key: WfTab; label: string; icon: typeof Workflow }[] = [
  { key: "guide", label: "Nasıl Kullanılır", icon: HelpCircle },
  { key: "templates", label: "Şablonlar", icon: Workflow },
  { key: "custom", label: "Özel Workflow", icon: Settings },
  { key: "scheduler", label: "Zamanlayıcı", icon: Calendar },
  { key: "assistant", label: "Asistanla Oluştur", icon: Bot },
];

/* ══════════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════════════════════ */

export function WorkflowBuilderPanel() {
  const [tab, setTab] = useState<WfTab>("guide");

  /* ── Templates state ─────────────────────────────────────────── */
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [tplLoading, setTplLoading] = useState(true);
  const [selectedTpl, setSelectedTpl] = useState<WorkflowTemplate | null>(null);
  const [tplVars, setTplVars] = useState<Record<string, string>>({});
  const [tplRunning, setTplRunning] = useState(false);
  const [tplResult, setTplResult] = useState<WorkflowRunResult | null>(null);

  /* ── Custom workflow state ───────────────────────────────────── */
  const [steps, setSteps] = useState<CustomStep[]>([makeStep(0)]);
  const [customRunning, setCustomRunning] = useState(false);
  const [customResult, setCustomResult] = useState<WorkflowRunResult | null>(
    null,
  );

  /* ── Scheduler state ─────────────────────────────────────────── */
  const [schedules, setSchedules] = useState<ScheduledWorkflow[]>([]);
  const [schLoading, setSchLoading] = useState(true);
  const [schForm, setSchForm] = useState({
    template: "",
    cron_expression: "0 * * * *",
    variables: "{}",
  });
  const [schAdding, setSchAdding] = useState(false);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  /* ── Error state ─────────────────────────────────────────────── */
  const [error, setError] = useState("");

  /* ── AI Assistant state ──────────────────────────────────────── */
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiImproving, setAiImproving] = useState(false);
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiGenerated, setAiGenerated] = useState<{
    name: string;
    description: string;
    steps: Array<Record<string, unknown>>;
    variables: Record<string, unknown>;
  } | null>(null);
  const [aiRunning, setAiRunning] = useState(false);
  const [aiResult, setAiResult] = useState<WorkflowRunResult | null>(null);

  /* ── Load templates ──────────────────────────────────────────── */
  const loadTemplates = useCallback(async () => {
    setTplLoading(true);
    try {
      const data = await api.getTemplates();
      setTemplates(data);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Şablonlar yüklenemedi");
    } finally {
      setTplLoading(false);
    }
  }, []);

  /* ── Load schedules ──────────────────────────────────────────── */
  const loadSchedules = useCallback(async () => {
    setSchLoading(true);
    try {
      const data = await api.getSchedules();
      setSchedules(data);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Zamanlamalar yüklenemedi");
    } finally {
      setSchLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  useEffect(() => {
    if (tab === "scheduler") loadSchedules();
  }, [tab, loadSchedules]);

  /* ── Template actions ────────────────────────────────────────── */
  const selectTemplate = (tpl: WorkflowTemplate) => {
    setSelectedTpl(tpl);
    setTplResult(null);
    const vars: Record<string, string> = {};
    tpl.required_variables.forEach((v) => (vars[v] = ""));
    setTplVars(vars);
  };

  const runTemplate = async () => {
    if (!selectedTpl) return;
    setTplRunning(true);
    setTplResult(null);
    try {
      const result = await api.runWorkflow(selectedTpl.id, tplVars);
      setTplResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Workflow çalıştırılamadı");
    } finally {
      setTplRunning(false);
    }
  };

  /* ── Custom workflow actions ─────────────────────────────────── */
  const addStep = () => {
    setSteps((prev) => [...prev, makeStep(prev.length)]);
  };

  const removeStep = (idx: number) => {
    setSteps((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateStep = (idx: number, patch: Partial<CustomStep>) => {
    setSteps((prev) =>
      prev.map((s, i) => (i === idx ? { ...s, ...patch } : s)),
    );
  };

  const runCustom = async () => {
    setCustomRunning(true);
    setCustomResult(null);
    try {
      const payload = steps.map((s) => {
        const base: Record<string, unknown> = {
          step_id: s.step_id,
          step_type: s.step_type,
          on_error: s.on_error,
        };
        if (s.step_type === "tool_call") {
          base.tool_name = s.tool_name;
          try {
            base.tool_args = JSON.parse(s.tool_args || "{}");
          } catch {
            base.tool_args = {};
          }
        } else if (s.step_type === "agent_call") {
          base.agent_role = s.agent_role;
          base.agent_prompt = s.agent_prompt;
        } else if (s.step_type === "condition") {
          base.condition = {
            field: s.field,
            operator: s.operator,
            value: s.value,
          };
          base.then_step = s.then_step;
          base.else_step = s.else_step;
        } else if (s.step_type === "parallel") {
          base.parallel_steps = s.parallel_steps;
        }
        return base;
      });
      const result = await api.runWorkflow("custom", {}, payload);
      setCustomResult(result);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Özel workflow çalıştırılamadı",
      );
    } finally {
      setCustomRunning(false);
    }
  };

  /* ── Scheduler actions ───────────────────────────────────────── */
  const addSchedule = async () => {
    setSchAdding(true);
    try {
      let vars: Record<string, unknown> = {};
      try {
        vars = JSON.parse(schForm.variables);
      } catch {
        /* keep empty */
      }
      await api.addSchedule({
        schedule_id: crypto.randomUUID().slice(0, 8),
        template: schForm.template,
        cron_expression: schForm.cron_expression,
        variables: vars,
        enabled: true,
      });
      await loadSchedules();
      setSchForm({
        template: "",
        cron_expression: "0 * * * *",
        variables: "{}",
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Zamanlama eklenemedi");
    } finally {
      setSchAdding(false);
    }
  };

  const toggleSchedule = async (id: string, enabled: boolean) => {
    setTogglingId(id);
    try {
      await api.toggleSchedule(id, !enabled);
      await loadSchedules();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Durum değiştirilemedi");
    } finally {
      setTogglingId(null);
    }
  };

  const removeSchedule = async (id: string) => {
    setDeletingId(id);
    try {
      await api.removeSchedule(id);
      await loadSchedules();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Zamanlama silinemedi");
    } finally {
      setDeletingId(null);
    }
  };

  /* ── AI Assistant actions ────────────────────────────────────── */
  const aiImprovePrompt = async () => {
    if (!aiPrompt.trim()) return;
    setAiImproving(true);
    setError("");
    try {
      const res = await api.aiImproveWorkflowPrompt(aiPrompt);
      setAiPrompt(res.improved_prompt);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Prompt geliştirilemedi");
    } finally {
      setAiImproving(false);
    }
  };

  const aiGenerate = async () => {
    if (!aiPrompt.trim()) return;
    setAiGenerating(true);
    setAiGenerated(null);
    setAiResult(null);
    setError("");
    try {
      const res = await api.aiGenerateWorkflow(aiPrompt);
      setAiGenerated(res.workflow);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Workflow oluşturulamadı");
    } finally {
      setAiGenerating(false);
    }
  };

  const aiRunGenerated = async () => {
    if (!aiGenerated) return;
    setAiRunning(true);
    setAiResult(null);
    setError("");
    try {
      const result = await api.runWorkflow(
        "custom",
        aiGenerated.variables || {},
        aiGenerated.steps,
      );
      setAiResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Workflow çalıştırılamadı");
    } finally {
      setAiRunning(false);
    }
  };

  /* ══════════════════════════════════════════════════════════════
     RENDER
     ══════════════════════════════════════════════════════════════ */
  return (
    <div className="space-y-3 p-2">
      {/* ── Tab Bar ──────────────────────────────────────────── */}
      <div className="flex items-center gap-1 border-b border-slate-700/50 pb-2">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => {
                setTab(t.key);
                setError("");
              }}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-t text-[11px] font-medium transition-colors ${
                active
                  ? "bg-slate-800/80 text-cyan-400 border border-slate-700/50 border-b-transparent -mb-px"
                  : "text-slate-500 hover:text-slate-300 hover:bg-slate-800/30"
              }`}
            >
              <Icon className="w-3 h-3" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* ── Error Banner ─────────────────────────────────────── */}
      {error && (
        <div
          className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-[11px] text-red-400 flex items-center gap-2"
          role="alert"
        >
          <XCircle className="w-3.5 h-3.5 shrink-0" />
          {error}
          <button
            onClick={() => setError("")}
            className="ml-auto text-red-500 hover:text-red-300 text-[10px]"
          >
            Kapat
          </button>
        </div>
      )}

      {/* ── Tab: Nasıl Kullanılır ─────────────────────────────── */}
      {tab === "guide" && (
        <div className="space-y-3 text-[11px] text-slate-400 leading-relaxed">
          {/* Hero */}
          <div
            className={`${crd} border-cyan-500/20 bg-gradient-to-br from-cyan-950/30 to-slate-800/50`}
          >
            <div className="flex items-center gap-2 mb-2">
              <Workflow className="w-5 h-5 text-cyan-400" />
              <span className="text-sm font-semibold text-slate-200">
                İş Akışı Motoru
              </span>
            </div>
            <p>
              Araştırma, kod inceleme ve derin analiz gibi çok adımlı görevleri
              otomatikleştirin. Hazır şablonları tek tıkla çalıştırın veya kendi
              özel pipeline&apos;ınızı oluşturun.
            </p>
          </div>

          {/* 1 — Şablonlar */}
          <div className={crd}>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-cyan-600/30 text-cyan-400 text-[10px] font-bold">
                1
              </span>
              <span className="text-xs font-medium text-slate-200">
                Şablonlar — Hazır Pipeline&apos;lar
              </span>
            </div>
            <p className="mb-2">
              <span className="text-cyan-400 font-medium">Şablonlar</span>{" "}
              sekmesine gidin. Sistem önceden tanımlı workflow&apos;ları
              listeler:
            </p>
            <div className="grid gap-1.5 pl-1">
              <div className="flex items-start gap-2">
                <Zap className="w-3 h-3 text-amber-400 mt-0.5 shrink-0" />
                <span>
                  <span className="text-slate-300">deep_research</span> — Bir
                  konuyu web&apos;de araştırır, RAG ile zenginleştirir, rapor
                  üretir
                </span>
              </div>
              <div className="flex items-start gap-2">
                <Zap className="w-3 h-3 text-amber-400 mt-0.5 shrink-0" />
                <span>
                  <span className="text-slate-300">code_review</span> — Kodu
                  analiz eder, güvenlik/performans önerileri sunar
                </span>
              </div>
              <div className="flex items-start gap-2">
                <Zap className="w-3 h-3 text-amber-400 mt-0.5 shrink-0" />
                <span>
                  <span className="text-slate-300">full_analysis</span> —
                  Araştırma + akıl yürütme + sentez pipeline&apos;ı
                </span>
              </div>
            </div>
            <div className="mt-2 bg-slate-900/50 rounded p-2 border border-slate-700/30">
              <span className="text-[10px] text-slate-500">Kullanım:</span>
              <span className="text-slate-300">
                {" "}
                Şablona tıklayın → değişkenleri doldurun (ör. konu, dil) →{" "}
              </span>
              <span className="text-cyan-400 font-medium">Çalıştır</span>
            </div>
          </div>

          {/* 2 — Özel Workflow */}
          <div className={crd}>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-purple-600/30 text-purple-400 text-[10px] font-bold">
                2
              </span>
              <span className="text-xs font-medium text-slate-200">
                Özel Workflow — Kendi Pipeline&apos;ınız
              </span>
            </div>
            <p className="mb-2">
              <span className="text-purple-400 font-medium">Özel Workflow</span>{" "}
              sekmesinde adım adım kendi iş akışınızı tasarlayın:
            </p>
            <div className="grid gap-1.5 pl-1">
              <div className="flex items-start gap-2">
                <ChevronRight className="w-3 h-3 text-slate-500 mt-0.5 shrink-0" />
                <span>
                  <span className="text-emerald-400">Araç Çağrısı</span> —
                  web_search, code_execute, rag_query, generate_image, mcp_call
                  gibi 35 aracı çağırın
                </span>
              </div>
              <div className="flex items-start gap-2">
                <ChevronRight className="w-3 h-3 text-slate-500 mt-0.5 shrink-0" />
                <span>
                  <span className="text-blue-400">Ajan Çağrısı</span> — thinker,
                  researcher, critic gibi ajanları görevlendirin
                </span>
              </div>
              <div className="flex items-start gap-2">
                <ChevronRight className="w-3 h-3 text-slate-500 mt-0.5 shrink-0" />
                <span>
                  <span className="text-amber-400">Koşul</span> — Bir önceki
                  adımın sonucuna göre dallanma yapın
                </span>
              </div>
              <div className="flex items-start gap-2">
                <ChevronRight className="w-3 h-3 text-slate-500 mt-0.5 shrink-0" />
                <span>
                  <span className="text-pink-400">Paralel</span> — Birden fazla
                  adımı aynı anda çalıştırın
                </span>
              </div>
            </div>
            <div className="mt-2 bg-slate-900/50 rounded p-2 border border-slate-700/30">
              <span className="text-[10px] text-slate-500">İpucu:</span>
              <span className="text-slate-300">
                {" "}
                Her adımda hata stratejisi{" "}
              </span>
              <span className="text-orange-400">rollback</span>
              <span className="text-slate-300">
                {" "}
                olarak ayarlıdır — bir adım başarısız olursa önceki adımlar geri
                alınır.
              </span>
            </div>
          </div>

          {/* 3 — Zamanlayıcı */}
          <div className={crd}>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-green-600/30 text-green-400 text-[10px] font-bold">
                3
              </span>
              <span className="text-xs font-medium text-slate-200">
                Zamanlayıcı — Otomatik Tetikleme
              </span>
            </div>
            <p className="mb-2">
              <span className="text-green-400 font-medium">Zamanlayıcı</span>{" "}
              sekmesinde workflow&apos;ları cron ifadesiyle periyodik
              çalıştırın:
            </p>
            <div className="grid gap-1 pl-1 font-mono text-[10px]">
              <div className="flex items-center gap-2">
                <Clock className="w-3 h-3 text-slate-500 shrink-0" />
                <span className="text-slate-300">0 * * * *</span>
                <span className="text-slate-500 font-sans">
                  → Her saat başı
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-3 h-3 text-slate-500 shrink-0" />
                <span className="text-slate-300">0 9 * * 1-5</span>
                <span className="text-slate-500 font-sans">
                  → Hafta içi her sabah 09:00
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-3 h-3 text-slate-500 shrink-0" />
                <span className="text-slate-300">*/30 * * * *</span>
                <span className="text-slate-500 font-sans">
                  → Her 30 dakikada bir
                </span>
              </div>
            </div>
            <div className="mt-2 bg-slate-900/50 rounded p-2 border border-slate-700/30">
              <span className="text-[10px] text-slate-500">Kullanım:</span>
              <span className="text-slate-300">
                {" "}
                Şablon seçin → cron ifadesini girin → değişkenleri JSON olarak
                yazın →{" "}
              </span>
              <span className="text-green-400 font-medium">Ekle</span>
            </div>
          </div>

          {/* 4 — Geçmiş */}
          <div className={crd}>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-slate-600/30 text-slate-300 text-[10px] font-bold">
                4
              </span>
              <span className="text-xs font-medium text-slate-200">
                Geçmiş — Sonuçları İnceleyin
              </span>
            </div>
            <p>
              Masaüstündeki{" "}
              <span className="text-cyan-400">Workflow Geçmişi</span>{" "}
              penceresinden tüm çalıştırmaları görüntüleyin. Her kayıt adım
              sonuçlarını, süreyi ve hata detaylarını içerir. Başarısız bir
              workflow&apos;u tek tıkla tekrar çalıştırabilirsiniz.
            </p>
          </div>

          {/* CTA */}
          <button
            onClick={() => setTab("templates")}
            className={`${btnPrimary} w-full justify-center`}
          >
            <Play className="w-3.5 h-3.5" />
            Hadi Başlayalım — Şablonlara Git
          </button>
        </div>
      )}

      {/* ── Tab: Şablonlar ───────────────────────────────────── */}
      {tab === "templates" && (
        <div className="space-y-2">
          {tplLoading ? (
            <div className="flex items-center justify-center py-12 text-slate-500 gap-2 text-xs">
              <Loader2 className="w-4 h-4 animate-spin" /> Şablonlar yükleniyor…
            </div>
          ) : templates.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 gap-2 text-slate-500">
              <Workflow className="w-7 h-7 opacity-40" />
              <span className="text-xs">Şablon bulunamadı</span>
            </div>
          ) : (
            <>
              {/* Template Cards */}
              <div className="grid gap-2">
                {templates.map((tpl) => (
                  <button
                    key={tpl.id}
                    onClick={() => selectTemplate(tpl)}
                    className={`${crd} text-left transition-all hover:border-cyan-500/30 ${
                      selectedTpl?.id === tpl.id
                        ? "border-cyan-500/50 ring-1 ring-cyan-500/20"
                        : ""
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Zap className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                          <span className="text-xs text-slate-200 font-medium truncate">
                            {tpl.name}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-500 mt-1 line-clamp-2">
                          {tpl.description}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[10px] text-slate-600 bg-slate-700/40 px-1.5 py-0.5 rounded">
                          {tpl.step_count} adım
                        </span>
                        <ChevronRight className="w-3 h-3 text-slate-600" />
                      </div>
                    </div>
                    {tpl.required_variables.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {tpl.required_variables.map((v) => (
                          <span
                            key={v}
                            className="text-[9px] text-cyan-400/70 bg-cyan-500/10 px-1.5 py-0.5 rounded"
                          >
                            {v}
                          </span>
                        ))}
                      </div>
                    )}
                  </button>
                ))}
              </div>

              {/* Selected Template → Variable Inputs + Run */}
              {selectedTpl && (
                <div className={`${crd} space-y-3`}>
                  <div className="flex items-center gap-2 text-xs text-slate-300">
                    <Settings className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="font-medium">{selectedTpl.name}</span>
                    <span className="text-[10px] text-slate-600">
                      — Değişkenler
                    </span>
                  </div>

                  {selectedTpl.required_variables.length > 0 ? (
                    <div className="space-y-2">
                      {selectedTpl.required_variables.map((varName) => (
                        <div key={varName}>
                          <label className="text-[10px] text-slate-500 mb-1 block">
                            {varName}
                          </label>
                          <input
                            type="text"
                            value={tplVars[varName] || ""}
                            onChange={(e) =>
                              setTplVars((prev) => ({
                                ...prev,
                                [varName]: e.target.value,
                              }))
                            }
                            placeholder={`${varName} değerini girin…`}
                            className={inp}
                          />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[10px] text-slate-600">
                      Bu şablon değişken gerektirmiyor.
                    </p>
                  )}

                  <button
                    onClick={runTemplate}
                    disabled={tplRunning}
                    className={btnPrimary}
                  >
                    {tplRunning ? (
                      <>
                        <Loader2 className="w-3 h-3 animate-spin" />
                        Çalışıyor…
                      </>
                    ) : (
                      <>
                        <Play className="w-3 h-3" />
                        Çalıştır
                      </>
                    )}
                  </button>

                  {/* Run Result */}
                  {tplResult && <RunResultBadge result={tplResult} />}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Tab: Özel Workflow ────────────────────────────────── */}
      {tab === "custom" && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-400 flex items-center gap-1.5">
              <Settings className="w-3 h-3" />
              Adımlar ({steps.length})
            </span>
            <button onClick={addStep} className={btnPrimary}>
              <Plus className="w-3 h-3" />
              Adım Ekle
            </button>
          </div>

          <div className="space-y-2">
            {steps.map((step, idx) => (
              <div key={step.step_id} className={`${crd} space-y-2`}>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-cyan-400 font-mono">
                    {step.step_id}
                  </span>
                  {steps.length > 1 && (
                    <button
                      onClick={() => removeStep(idx)}
                      className={btnDanger}
                      aria-label={`${step.step_id} sil`}
                    >
                      <Trash2 className="w-2.5 h-2.5" />
                      Sil
                    </button>
                  )}
                </div>

                {/* Step Type Select */}
                <div>
                  <label className="text-[10px] text-slate-500 mb-1 block">
                    Adım Tipi
                  </label>
                  <select
                    value={step.step_type}
                    onChange={(e) =>
                      updateStep(idx, {
                        step_type: e.target.value as StepType,
                      })
                    }
                    className={inp}
                  >
                    {STEP_TYPES.map((st) => (
                      <option key={st.value} value={st.value}>
                        {st.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* tool_call fields */}
                {step.step_type === "tool_call" && (
                  <>
                    <div>
                      <label className="text-[10px] text-slate-500 mb-1 block">
                        Araç
                      </label>
                      <select
                        value={step.tool_name || TOOLS[0]}
                        onChange={(e) =>
                          updateStep(idx, { tool_name: e.target.value })
                        }
                        className={inp}
                      >
                        {TOOLS.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-500 mb-1 block">
                        Argümanlar (JSON)
                      </label>
                      <textarea
                        value={step.tool_args || "{}"}
                        onChange={(e) =>
                          updateStep(idx, { tool_args: e.target.value })
                        }
                        rows={2}
                        className={`${inp} resize-none font-mono`}
                      />
                    </div>
                  </>
                )}

                {/* agent_call fields */}
                {step.step_type === "agent_call" && (
                  <>
                    <div>
                      <label className="text-[10px] text-slate-500 mb-1 block">
                        Ajan Rolü
                      </label>
                      <select
                        value={step.agent_role || AGENTS[0]}
                        onChange={(e) =>
                          updateStep(idx, { agent_role: e.target.value })
                        }
                        className={inp}
                      >
                        {AGENTS.map((a) => (
                          <option key={a} value={a}>
                            {a}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] text-slate-500 mb-1 block">
                        Prompt
                      </label>
                      <textarea
                        value={step.agent_prompt || ""}
                        onChange={(e) =>
                          updateStep(idx, { agent_prompt: e.target.value })
                        }
                        rows={2}
                        placeholder="Ajana gönderilecek prompt…"
                        className={`${inp} resize-none`}
                      />
                    </div>
                  </>
                )}

                {/* condition fields */}
                {step.step_type === "condition" && (
                  <>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="text-[10px] text-slate-500 mb-1 block">
                          Alan
                        </label>
                        <input
                          type="text"
                          value={step.field || ""}
                          onChange={(e) =>
                            updateStep(idx, { field: e.target.value })
                          }
                          placeholder="field"
                          className={inp}
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-500 mb-1 block">
                          Operatör
                        </label>
                        <select
                          value={step.operator || "eq"}
                          onChange={(e) =>
                            updateStep(idx, { operator: e.target.value })
                          }
                          className={inp}
                        >
                          {OPERATORS.map((op) => (
                            <option key={op} value={op}>
                              {op}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-500 mb-1 block">
                          Değer
                        </label>
                        <input
                          type="text"
                          value={step.value || ""}
                          onChange={(e) =>
                            updateStep(idx, { value: e.target.value })
                          }
                          placeholder="value"
                          className={inp}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] text-slate-500 mb-1 block">
                          Doğruysa (step_id)
                        </label>
                        <input
                          type="text"
                          value={step.then_step || ""}
                          onChange={(e) =>
                            updateStep(idx, { then_step: e.target.value })
                          }
                          placeholder="step_X"
                          className={inp}
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-500 mb-1 block">
                          Yanlışsa (step_id)
                        </label>
                        <input
                          type="text"
                          value={step.else_step || ""}
                          onChange={(e) =>
                            updateStep(idx, { else_step: e.target.value })
                          }
                          placeholder="step_Y"
                          className={inp}
                        />
                      </div>
                    </div>
                  </>
                )}

                {/* parallel fields */}
                {step.step_type === "parallel" && (
                  <div>
                    <label className="text-[10px] text-slate-500 mb-1 block">
                      Paralel Adımlar
                    </label>
                    <div className="flex flex-wrap gap-1.5">
                      {steps
                        .filter((_, i) => i !== idx)
                        .map((s) => {
                          const selected =
                            step.parallel_steps?.includes(s.step_id) ?? false;
                          return (
                            <button
                              key={s.step_id}
                              onClick={() => {
                                const current = step.parallel_steps || [];
                                const next = selected
                                  ? current.filter((id) => id !== s.step_id)
                                  : [...current, s.step_id];
                                updateStep(idx, { parallel_steps: next });
                              }}
                              className={`text-[10px] px-2 py-0.5 rounded border transition-colors ${
                                selected
                                  ? "bg-cyan-600/30 border-cyan-500/50 text-cyan-300"
                                  : "bg-slate-700/30 border-slate-600/50 text-slate-500 hover:text-slate-300"
                              }`}
                            >
                              {s.step_id}
                            </button>
                          );
                        })}
                      {steps.length <= 1 && (
                        <span className="text-[10px] text-slate-600">
                          Paralel çalıştırmak için birden fazla adım ekleyin
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Run Custom */}
          <button
            onClick={runCustom}
            disabled={customRunning || steps.length === 0}
            className={btnPrimary}
          >
            {customRunning ? (
              <>
                <Loader2 className="w-3 h-3 animate-spin" />
                Çalışıyor…
              </>
            ) : (
              <>
                <Play className="w-3 h-3" />
                Özel Workflow Çalıştır
              </>
            )}
          </button>

          {customResult && <RunResultBadge result={customResult} />}
        </div>
      )}

      {/* ── Tab: Zamanlayıcı ──────────────────────────────────── */}
      {tab === "scheduler" && (
        <div className="space-y-3">
          {/* Existing Schedules */}
          {schLoading ? (
            <div className="flex items-center justify-center py-10 text-slate-500 gap-2 text-xs">
              <Loader2 className="w-4 h-4 animate-spin" /> Zamanlamalar
              yükleniyor…
            </div>
          ) : schedules.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 gap-2 text-slate-500">
              <Calendar className="w-7 h-7 opacity-40" />
              <span className="text-xs">Henüz zamanlama yok</span>
            </div>
          ) : (
            <div className="space-y-1.5">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider px-1">
                Aktif Zamanlamalar ({schedules.length})
              </span>
              {schedules.map((sch) => (
                <div
                  key={sch.schedule_id}
                  className={`${crd} flex flex-col gap-2`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <Timer className="w-3 h-3 text-cyan-400 shrink-0" />
                      <span className="text-xs text-slate-200 font-mono truncate">
                        {sch.template}
                      </span>
                      <span className="text-[10px] text-slate-500 bg-slate-700/40 px-1.5 py-0.5 rounded font-mono shrink-0">
                        {sch.cron_expression}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {/* Toggle */}
                      <button
                        onClick={() =>
                          toggleSchedule(sch.schedule_id, sch.enabled)
                        }
                        disabled={togglingId === sch.schedule_id}
                        className={`relative w-8 h-4 rounded-full transition-colors ${
                          sch.enabled ? "bg-cyan-600/80" : "bg-slate-700"
                        } ${togglingId === sch.schedule_id ? "opacity-50" : ""}`}
                        aria-label={
                          sch.enabled ? "Devre dışı bırak" : "Etkinleştir"
                        }
                      >
                        <span
                          className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${
                            sch.enabled ? "translate-x-4.5" : "translate-x-0.5"
                          }`}
                        />
                      </button>
                      {/* Delete */}
                      <button
                        onClick={() => removeSchedule(sch.schedule_id)}
                        disabled={deletingId === sch.schedule_id}
                        className={btnDanger}
                        aria-label="Zamanlamayı sil"
                      >
                        {deletingId === sch.schedule_id ? (
                          <Loader2 className="w-2.5 h-2.5 animate-spin" />
                        ) : (
                          <Trash2 className="w-2.5 h-2.5" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Schedule Meta */}
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-slate-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-2.5 h-2.5" />
                      Son: {fdt(sch.last_run)}
                    </span>
                    <span className="flex items-center gap-1">
                      <ChevronRight className="w-2.5 h-2.5" />
                      Sonraki: {fdt(sch.next_run)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Play className="w-2.5 h-2.5" />
                      {sch.run_count} çalışma
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded ${
                        sch.enabled
                          ? "bg-emerald-500/15 text-emerald-400"
                          : "bg-slate-700/50 text-slate-600"
                      }`}
                    >
                      {sch.enabled ? "Aktif" : "Pasif"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* New Schedule Form */}
          <div className={`${crd} space-y-3`}>
            <span className="text-[11px] text-slate-300 font-medium flex items-center gap-1.5">
              <Plus className="w-3 h-3 text-cyan-400" />
              Yeni Zamanlama
            </span>

            <div>
              <label className="text-[10px] text-slate-500 mb-1 block">
                Şablon
              </label>
              <select
                value={schForm.template}
                onChange={(e) =>
                  setSchForm((prev) => ({ ...prev, template: e.target.value }))
                }
                className={inp}
              >
                <option value="">Şablon seçin…</option>
                {templates.map((tpl) => (
                  <option key={tpl.id} value={tpl.id}>
                    {tpl.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[10px] text-slate-500 mb-1 block">
                Cron İfadesi
              </label>
              <input
                type="text"
                value={schForm.cron_expression}
                onChange={(e) =>
                  setSchForm((prev) => ({
                    ...prev,
                    cron_expression: e.target.value,
                  }))
                }
                placeholder="0 * * * *"
                className={`${inp} font-mono`}
              />
              <span className="text-[9px] text-slate-600 mt-0.5 block">
                Örn: 0 */6 * * * (her 6 saatte), 0 9 * * 1-5 (hafta içi 09:00)
              </span>
            </div>

            <div>
              <label className="text-[10px] text-slate-500 mb-1 block">
                Değişkenler (JSON)
              </label>
              <textarea
                value={schForm.variables}
                onChange={(e) =>
                  setSchForm((prev) => ({
                    ...prev,
                    variables: e.target.value,
                  }))
                }
                rows={2}
                placeholder='{"key": "value"}'
                className={`${inp} resize-none font-mono`}
              />
            </div>

            <button
              onClick={addSchedule}
              disabled={
                schAdding || !schForm.template || !schForm.cron_expression
              }
              className={btnPrimary}
            >
              {schAdding ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Ekleniyor…
                </>
              ) : (
                <>
                  <Plus className="w-3 h-3" />
                  Zamanlama Ekle
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* ── Tab: Asistanla Oluştur ───────────────────────────── */}
      {tab === "assistant" && (
        <div className="space-y-3">
          {/* Hero */}
          <div
            className={`${crd} border-purple-500/20 bg-gradient-to-br from-purple-950/30 to-slate-800/50`}
          >
            <div className="flex items-center gap-2 mb-1.5">
              <Sparkles className="w-4 h-4 text-purple-400" />
              <span className="text-xs font-semibold text-slate-200">
                AI ile İş Akışı Oluştur
              </span>
            </div>
            <p className="text-[10px] text-slate-400">
              Ne yapmak istediğinizi doğal dilde yazın, AI sizin için otomatik
              workflow oluşturur. Prompt geliştirme butonu ile açıklamanızı
              netleştirebilirsiniz.
            </p>
          </div>

          {/* Prompt Input */}
          <div className={`${crd} space-y-2`}>
            <label className="text-[10px] text-slate-500 mb-1 block">
              İş Akışı Açıklaması
            </label>
            <textarea
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              rows={4}
              placeholder="Örn: Her gün sabah 9'da yapay zeka haberlerini araştır, önemli gelişmeleri özetle ve hafızaya kaydet..."
              className={`${inp} resize-none`}
            />

            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              {/* Improve Prompt */}
              <button
                onClick={aiImprovePrompt}
                disabled={aiImproving || !aiPrompt.trim()}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] font-medium bg-purple-600/40 hover:bg-purple-500/50 disabled:opacity-50 disabled:cursor-not-allowed text-purple-300 transition-colors border border-purple-500/30"
                title="Promptu AI ile geliştir"
              >
                {aiImproving ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Geliştiriliyor…
                  </>
                ) : (
                  <>
                    <Wand2 className="w-3 h-3" />
                    Promptu Geliştir
                  </>
                )}
              </button>

              {/* Generate Workflow */}
              <button
                onClick={aiGenerate}
                disabled={aiGenerating || !aiPrompt.trim()}
                className={btnPrimary}
              >
                {aiGenerating ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Oluşturuluyor…
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3 h-3" />
                    Workflow Oluştur
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Generated Workflow Preview */}
          {aiGenerated && (
            <div className={`${crd} space-y-3 border-cyan-500/20`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-xs font-medium text-slate-200">
                    {aiGenerated.name}
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 bg-slate-700/40 px-1.5 py-0.5 rounded">
                  {aiGenerated.steps.length} adım
                </span>
              </div>

              {aiGenerated.description && (
                <p className="text-[10px] text-slate-400">
                  {aiGenerated.description}
                </p>
              )}

              {/* Steps Preview */}
              <div className="space-y-1">
                {aiGenerated.steps.map((step, idx) => (
                  <div
                    key={String(step.step_id || idx)}
                    className="flex items-center gap-2 bg-slate-900/50 rounded px-2 py-1.5 border border-slate-700/30"
                  >
                    <span className="text-[9px] text-cyan-400 font-mono w-12 shrink-0">
                      {String(step.step_id || `step_${idx}`)}
                    </span>
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded ${
                        step.step_type === "tool_call"
                          ? "bg-emerald-500/15 text-emerald-400"
                          : step.step_type === "agent_call"
                            ? "bg-blue-500/15 text-blue-400"
                            : step.step_type === "condition"
                              ? "bg-amber-500/15 text-amber-400"
                              : "bg-pink-500/15 text-pink-400"
                      }`}
                    >
                      {step.step_type === "tool_call"
                        ? "Araç"
                        : step.step_type === "agent_call"
                          ? "Ajan"
                          : step.step_type === "condition"
                            ? "Koşul"
                            : "Paralel"}
                    </span>
                    <span className="text-[10px] text-slate-300 truncate">
                      {step.step_type === "tool_call"
                        ? String(step.tool_name || "")
                        : step.step_type === "agent_call"
                          ? String(step.agent_role || "")
                          : step.step_type === "parallel"
                            ? `[${((step.parallel_steps as string[]) || []).join(", ")}]`
                            : "koşul"}
                    </span>
                  </div>
                ))}
              </div>

              {/* Variables */}
              {aiGenerated.variables &&
                Object.keys(aiGenerated.variables).length > 0 && (
                  <div>
                    <span className="text-[10px] text-slate-500 block mb-1">
                      Değişkenler:
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(aiGenerated.variables).map(([k, v]) => (
                        <span
                          key={k}
                          className="text-[9px] text-cyan-400/70 bg-cyan-500/10 px-1.5 py-0.5 rounded"
                        >
                          {k}: {String(v) || '""'}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

              {/* Run / Edit Buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={aiRunGenerated}
                  disabled={aiRunning}
                  className={btnPrimary}
                >
                  {aiRunning ? (
                    <>
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Çalışıyor…
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3" />
                      Test Et
                    </>
                  )}
                </button>
                <button
                  onClick={() => {
                    setAiGenerated(null);
                    setAiResult(null);
                  }}
                  className={btnDanger}
                >
                  <Trash2 className="w-2.5 h-2.5" />
                  Temizle
                </button>
              </div>

              {aiResult && <RunResultBadge result={aiResult} />}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Run Result Badge ──────────────────────────────────────────── */
function RunResultBadge({ result }: { result: WorkflowRunResult }) {
  const success = result.status === "completed";
  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-[11px] ${
        success
          ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
          : "bg-red-500/10 border-red-500/30 text-red-400"
      }`}
    >
      {success ? (
        <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
      ) : (
        <XCircle className="w-3.5 h-3.5 shrink-0" />
      )}
      <span className="font-medium">{success ? "Başarılı" : "Başarısız"}</span>
      <span className="text-[10px] opacity-70">
        — {dur(result.duration_ms)}
      </span>
      {result.error && (
        <span className="text-[10px] opacity-70 truncate ml-1">
          {result.error}
        </span>
      )}
    </div>
  );
}
